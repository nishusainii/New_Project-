/**
 * INNCCTV ENTERPRISE SECURITY & HARDENING MODULE
 * Implements VAPT defenses: Password Hashing, Timing-Safe Checks,
 * Signed HMAC Tokens, Anti-Brute-Force Rate Limiting, and Security Headers.
 */

const crypto = require('crypto');

// Secret Key for HMAC Token generation (can be overridden by environment variable)
const JWT_SECRET = process.env.INNCCTV_SECRET || crypto.randomBytes(32).toString('hex');

// 1. Cryptographic Password Hashing (scrypt + random salt)
function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const derivedKey = crypto.scryptSync(password, salt, 64);
  return `${salt}:${derivedKey.toString('hex')}`;
}

function verifyPassword(password, storedHash) {
  try {
    const [salt, key] = storedHash.split(':');
    if (!salt || !key) return false;
    const keyBuffer = Buffer.from(key, 'hex');
    const derivedKey = crypto.scryptSync(password, salt, 64);
    return crypto.timingSafeEqual(keyBuffer, derivedKey);
  } catch {
    return false;
  }
}

// 2. Cryptographic Signed Token (HMAC-SHA256) with Expiration
function generateToken(payload, expiresInHours = 8) {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const exp = Math.floor(Date.now() / 1000) + (expiresInHours * 3600);
  const body = Buffer.from(JSON.stringify({ ...payload, exp })).toString('base64url');
  const signature = crypto.createHmac('sha256', JWT_SECRET).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${signature}`;
}

function verifyToken(token) {
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;

  const [header, body, signature] = parts;
  const expectedSignature = crypto.createHmac('sha256', JWT_SECRET).update(`${header}.${body}`).digest('base64url');

  try {
    const sigBuf = Buffer.from(signature);
    const expBuf = Buffer.from(expectedSignature);
    if (sigBuf.length !== expBuf.length || !crypto.timingSafeEqual(sigBuf, expBuf)) {
      return null;
    }
    const payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf8'));
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) {
      return null; // Expired
    }
    return payload;
  } catch {
    return null;
  }
}

// 3. Anti-Brute-Force Rate Limiting (Tracks failed login attempts per client IP)
const loginAttempts = new Map();

function rateLimitLogin(req, res, next) {
  const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
  const now = Date.now();
  const windowMs = 15 * 60 * 1000; // 15 minutes lockout
  const maxAttempts = 5;

  let record = loginAttempts.get(ip);
  if (!record) {
    record = { count: 0, firstAttempt: now, lockedUntil: 0 };
    loginAttempts.set(ip, record);
  }

  // Check if IP is currently locked
  if (record.lockedUntil > now) {
    const remainingSeconds = Math.ceil((record.lockedUntil - now) / 1000);
    return res.status(429).json({
      success: false,
      error: `Too many failed login attempts. IP temporarily locked for security. Try again in ${remainingSeconds}s.`
    });
  }

  // Clean old window
  if (now - record.firstAttempt > windowMs) {
    record.count = 0;
    record.firstAttempt = now;
  }

  req.authSecurity = {
    recordFailedAttempt: () => {
      record.count += 1;
      if (record.count >= maxAttempts) {
        record.lockedUntil = now + windowMs;
        console.warn(`[Security Alert] IP ${ip} temporarily locked out due to ${maxAttempts} consecutive failed logins.`);
      }
    },
    recordSuccess: () => {
      loginAttempts.delete(ip);
    }
  };

  next();
}

// 4. Enterprise Security Headers Middleware
function securityHeaders(req, res, next) {
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  
  // Content Security Policy tailored for CCTV operations
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self' ws: wss: http://*:8889 https://*:8889 http://*:8888 https://*:8888;"
  );
  next();
}

// 5. Input Sanitizer & Validator for Cameras
function validateCameraInput(data) {
  const errors = [];

  if (!data.name || typeof data.name !== 'string' || data.name.trim().length === 0) {
    errors.push('Camera name is required.');
  }

  // Validate IP format (IPv4 or hostname)
  const ipv4Regex = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
  if (data.ip && !ipv4Regex.test(data.ip) && data.ip !== 'localhost') {
    errors.push('Invalid IPv4 address format.');
  }

  // Validate RTSP URL
  if (data.rtspUrl) {
    if (!data.rtspUrl.startsWith('rtsp://') && !data.rtspUrl.startsWith('rtsps://')) {
      errors.push('RTSP URL must begin with rtsp:// or rtsps://');
    }
    // Block command injection characters
    if (/[;&|`$<>]/.test(data.rtspUrl)) {
      errors.push('RTSP URL contains forbidden shell metacharacters.');
    }
  }

  // Validate Floor
  const floorNum = parseInt(data.floor, 10);
  if (isNaN(floorNum) || floorNum < 1 || floorNum > 100) {
    errors.push('Floor must be a valid integer between 1 and 100.');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

module.exports = {
  hashPassword,
  verifyPassword,
  generateToken,
  verifyToken,
  rateLimitLogin,
  securityHeaders,
  validateCameraInput
};
