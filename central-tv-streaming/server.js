const express = require('express');
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const cookieParser = require('cookie-parser');
const { WebSocketServer, WebSocket } = require('ws');
const multer = require('multer');
const net = require('net');
const seamlessLoopManager = require('./scripts/seamless-loop.js');

const HTTP_PORT = process.env.HTTP_PORT || 8080;
const HTTPS_PORT = process.env.HTTPS_PORT || 8443;
const MEDIAMTX_HOST = process.env.MEDIAMTX_HOST || '127.0.0.1';
const MEDIAMTX_WEBRTC_PORT = process.env.MEDIAMTX_WEBRTC_PORT || 8889;
const MEDIAMTX_HLS_PORT = process.env.MEDIAMTX_HLS_PORT || 8888;

const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';
const STREAMER_USER = process.env.STREAMER_USER || 'streamer';
const STREAMER_PASSWORD = process.env.STREAMER_PASSWORD || 'streamer123';

// Active Session tokens map: token -> { user, role, expiresAt }
const activeSessions = new Map();

const DATA_DIR = path.join(__dirname, 'data');
const MEDIA_DIR = path.join(__dirname, 'media');
const CERTS_DIR = path.join(__dirname, 'certs');

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(MEDIA_DIR)) fs.mkdirSync(MEDIA_DIR, { recursive: true });

const DEVICES_FILE = path.join(DATA_DIR, 'devices.json');
const CHANNELS_FILE = path.join(DATA_DIR, 'channels.json');
const USERS_FILE = path.join(DATA_DIR, 'users.json');

// --- In-Memory State & Persistence Helpers ---
function loadJson(file, fallback) {
  try {
    if (fs.existsSync(file)) {
      return JSON.parse(fs.readFileSync(file, 'utf8'));
    }
  } catch (e) {
    console.error(`Error reading ${file}:`, e.message);
  }
  return fallback;
}

function saveJson(file, data) {
  try {
    fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf8');
  } catch (e) {
    console.error(`Error saving ${file}:`, e.message);
  }
}

// Initial Channels
const DEFAULT_CHANNELS = [
  {
    id: 'ch-live',
    name: 'Live Broadcast (Screen / Camera)',
    type: 'webrtc',
    streamKey: 'live',
    description: 'Ultra-low-latency real-time video stream from presenter laptop'
  },
  {
    id: 'ch-signage',
    name: 'Corporate Digital Signage',
    type: 'signage',
    description: 'Automated corporate announcements, image carousel & company loop'
  },
  {
    id: 'ch-dashboard',
    name: 'Live Metrics / Kiosk Dashboard',
    type: 'url',
    url: '/dashboard.html',
    description: 'Full-screen web dashboard / status monitor'
  }
];

let channels = loadJson(CHANNELS_FILE, DEFAULT_CHANNELS);
let devices = loadJson(DEVICES_FILE, {});
let activeAlert = null;
let masterVideoIndex = 0; // Synchronized global video index across all TVs

// Connected WebSocket Clients map: deviceId -> ws
const connectedSockets = new Map();

// --- Express Application ---
const app = express();
app.disable('x-powered-by');

// Security Headers Middleware (OWASP Hardening)
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Content-Security-Policy', "default-src 'self' 'unsafe-inline' 'unsafe-eval' blob: data:; connect-src 'self' ws: wss: http: https:; media-src 'self' blob:; img-src 'self' data: blob:; font-src 'self'; frame-src 'self' *;");
  next();
});

// --- Reverse Proxy for MediaMTX (WebRTC WHIP/WHEP and HLS) ---
// Eliminates Mixed Content (HTTPS -> HTTP:8889) blocks and resolves mDNS candidate obfuscation
function proxyToMediaMTX(targetPort, baseUrl) {
  return (req, res) => {
    const targetPath = req.url;
    console.log(`[PROXY] Request received for ${baseUrl}${targetPath}`);
    let rawIp = (req.headers['x-forwarded-for'] ? req.headers['x-forwarded-for'].split(',')[0].trim() : (req.socket.remoteAddress || ''));
    let clientIp = rawIp.replace(/^::ffff:/, '');

    const isSdp = (req.headers['content-type'] && (
      req.headers['content-type'].includes('application/sdp') ||
      req.headers['content-type'].includes('application/trickle-ice-sdpfrag')
    ));

    const rewriteLocation = (loc) => {
      if (!loc) return loc;
      try {
        if (loc.startsWith('http://') || loc.startsWith('https://')) {
          const u = new URL(loc);
          return baseUrl + u.pathname + (u.search || '');
        }
      } catch {}
      if (!loc.startsWith(baseUrl)) {
        return baseUrl + loc;
      }
      return loc;
    };

    if (isSdp && (req.method === 'POST' || req.method === 'PATCH')) {
      const chunks = [];
      req.on('data', chunk => chunks.push(chunk));
      req.on('end', () => {
        let body = Buffer.concat(chunks).toString('utf8');
        if (clientIp && !clientIp.includes(':') && clientIp !== '127.0.0.1') {
          body = body.replace(/[a-zA-Z0-9-]+\.local/gi, clientIp);
        }
        const bodyBuf = Buffer.from(body, 'utf8');

        const headers = { ...req.headers, host: `${MEDIAMTX_HOST}:${targetPort}` };
        headers['content-length'] = bodyBuf.length;

        const options = {
          hostname: MEDIAMTX_HOST,
          port: targetPort,
          path: targetPath,
          method: req.method,
          headers
        };

        const proxyReq = http.request(options, (proxyRes) => {
          if (proxyRes.headers.location) {
            proxyRes.headers.location = rewriteLocation(proxyRes.headers.location);
          }
          res.writeHead(proxyRes.statusCode, proxyRes.headers);
          proxyRes.pipe(res);
        });

        proxyReq.on('error', (err) => {
          console.error(`[PROXY] MediaMTX error on port ${targetPort} (${req.method} ${targetPath}):`, err.message);
          if (!res.headersSent) {
            res.status(502).json({ error: 'Streaming gateway unavailable', details: err.message });
          }
        });

        proxyReq.write(bodyBuf);
        proxyReq.end();
      });
      return;
    }

    const options = {
      hostname: MEDIAMTX_HOST,
      port: targetPort,
      path: targetPath,
      method: req.method,
      headers: { ...req.headers, host: `${MEDIAMTX_HOST}:${targetPort}` }
    };

    const proxyReq = http.request(options, (proxyRes) => {
      if (proxyRes.headers.location) {
        proxyRes.headers.location = rewriteLocation(proxyRes.headers.location);
      }
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });

    proxyReq.on('error', (err) => {
      console.error(`[PROXY] MediaMTX error on port ${targetPort} (${req.method} ${targetPath}):`, err.message);
      if (!res.headersSent) {
        res.status(502).json({ error: 'Streaming gateway unavailable', details: err.message });
      }
    });

    req.pipe(proxyReq);
  };
}

app.use('/webrtc', proxyToMediaMTX(MEDIAMTX_WEBRTC_PORT, '/webrtc'));
app.use('/hls', proxyToMediaMTX(MEDIAMTX_HLS_PORT, '/hls'));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(cookieParser());

// Rate Limiter for Login Attempts (Anti-Brute-Force)
const loginAttempts = new Map(); // ip -> { count, lockedUntil }
function checkRateLimit(req, res, next) {
  const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
  const now = Date.now();
  const attempt = loginAttempts.get(ip);

  if (attempt && attempt.lockedUntil > now) {
    const remainingSecs = Math.ceil((attempt.lockedUntil - now) / 1000);
    return res.status(429).json({
      success: false,
      error: `Too many failed login attempts. Temporarily locked for ${remainingSecs} seconds.`
    });
  }
  next();
}

function recordFailedLogin(ip) {
  const now = Date.now();
  const attempt = loginAttempts.get(ip) || { count: 0, lockedUntil: 0 };
  attempt.count++;
  if (attempt.count >= 5) {
    attempt.lockedUntil = now + 5 * 60 * 1000; // 5 minute lock
    attempt.count = 0;
  }
  loginAttempts.set(ip, attempt);
}

function recordSuccessfulLogin(ip) {
  loginAttempts.delete(ip);
}

// Input Sanitization Helper
function sanitizeText(str, maxLen = 100) {
  if (typeof str !== 'string') return '';
  return str.replace(/[<>'"]/g, '').substring(0, maxLen).trim();
}

// Helper to retrieve active session object
function getSession(req) {
  const token = req.cookies?.tv_session || (req.headers['authorization'] ? req.headers['authorization'].replace('Bearer ', '') : null);
  if (!token) return null;
  const session = activeSessions.get(token);
  if (!session) return null;
  if (Date.now() > session.expiresAt) {
    activeSessions.delete(token);
    return null;
  }
  return session;
}

function isValidSession(req) {
  return getSession(req) !== null;
}

// User credentials lookup (Environment variables + data/users.json)
function authenticateUser(username, password) {
  if (username === ADMIN_USER && password === ADMIN_PASSWORD) {
    return { username: ADMIN_USER, role: 'admin' };
  }
  if (username === STREAMER_USER && password === STREAMER_PASSWORD) {
    return { username: STREAMER_USER, role: 'streamer' };
  }
  try {
    if (fs.existsSync(USERS_FILE)) {
      const users = JSON.parse(fs.readFileSync(USERS_FILE, 'utf8'));
      if (Array.isArray(users)) {
        const found = users.find(u => u.username === username && u.password === password);
        if (found) return { username: found.username, role: found.role || 'streamer' };
      }
    }
  } catch (e) {
    console.error('Error reading users.json:', e.message);
  }
  return null;
}

// Strict API Authentication & Role-Based Access Control (RBAC)
function requireAuth(req, res, next) {
  const session = getSession(req);
  if (!session) {
    return res.status(401).json({ success: false, error: 'Unauthorized: Valid session required' });
  }
  req.user = session;
  next();
}

function requireRole(allowedRoles) {
  return (req, res, next) => {
    const session = getSession(req);
    if (!session) {
      return res.status(401).json({ success: false, error: 'Unauthorized: Valid session required' });
    }
    if (!allowedRoles.includes(session.role)) {
      return res.status(403).json({ success: false, error: `Forbidden: Requires ${allowedRoles.join(' or ')} privileges` });
    }
    req.user = session;
    next();
  };
}

const requireAdmin = requireRole(['admin']);

// Protected Page Guards: Redirect unauthenticated requests to /login.html
app.get('/admin.html', (req, res, next) => {
  const session = getSession(req);
  if (!session) {
    return res.redirect(`/login.html?redirect=${encodeURIComponent(req.originalUrl)}`);
  }
  if (session.role === 'streamer') {
    return res.redirect('/presenter.html');
  }
  next();
});

app.get('/presenter.html', (req, res, next) => {
  const session = getSession(req);
  if (!session) {
    return res.redirect(`/login.html?redirect=${encodeURIComponent(req.originalUrl)}`);
  }
  next();
});

// Serve static frontend assets
app.use(express.static(path.join(__dirname, 'public')));
app.use('/media', express.static(MEDIA_DIR, {
  maxAge: '7d',
  setHeaders: (res) => {
    res.setHeader('Cache-Control', 'public, max-age=604800, immutable');
    res.setHeader('Accept-Ranges', 'bytes');
  }
}));
app.use('/packages', express.static(path.join(__dirname, 'production-installation-packages')));
app.use('/docs', express.static(path.join(__dirname, 'documentation-and-pdfs')));

// Configure Multer for secure media uploads (Whitelisted Extensions & Size Limits)
const ALLOWED_EXTENSIONS = new Set(['.mp4', '.webm', '.mkv', '.mov', '.m4v']);
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, MEDIA_DIR),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const base = path.basename(file.originalname, ext).replace(/[^a-zA-Z0-9_-]/g, '_');
    cb(null, `${Date.now()}_${base}${ext}`);
  }
});

const upload = multer({
  storage,
  limits: {
    fileSize: 500 * 1024 * 1024, // 500 MB max per file
    files: 15
  },
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      return cb(new Error('Rejected: Only validated video formats (.mp4, .webm, .mkv, .mov, .m4v) are allowed.'));
    }
    cb(null, true);
  }
});

// --- REST APIs ---

// 0. Authentication APIs
app.post('/api/auth/login', checkRateLimit, (req, res) => {
  const { username, password } = req.body;
  const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress;

  if (!username || !password) {
    return res.status(400).json({ success: false, error: 'Username and password required' });
  }

  const authenticated = authenticateUser(username, password);
  if (authenticated) {
    recordSuccessfulLogin(ip);
    const token = crypto.randomBytes(32).toString('hex');
    activeSessions.set(token, {
      user: authenticated.username,
      role: authenticated.role,
      expiresAt: Date.now() + 7 * 24 * 3600 * 1000 // 7 days
    });

    res.cookie('tv_session', token, {
      httpOnly: true,
      sameSite: 'lax',
      maxAge: 7 * 24 * 3600 * 1000,
      path: '/'
    });

    console.log(`[AUTH] Successful login for user: ${authenticated.username} (Role: ${authenticated.role}) from ${ip}`);
    return res.json({
      success: true,
      token,
      user: { username: authenticated.username, role: authenticated.role }
    });
  }

  recordFailedLogin(ip);
  console.warn(`[AUTH] Failed login attempt for user: ${username} from ${ip}`);
  return res.status(401).json({ success: false, error: 'Invalid username or password' });
});

app.get('/api/auth/me', (req, res) => {
  const session = getSession(req);
  if (session) {
    return res.json({ authenticated: true, user: session.user, role: session.role });
  }
  return res.status(401).json({ authenticated: false });
});

app.get('/api/auth/users', requireAdmin, (req, res) => {
  try {
    const users = fs.existsSync(USERS_FILE) ? JSON.parse(fs.readFileSync(USERS_FILE, 'utf8')) : [];
    // Sanitize passwords before returning
    const safeUsers = users.map(u => ({ username: u.username, role: u.role, description: u.description }));
    res.json({ success: true, users: safeUsers });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

app.post('/api/auth/logout', (req, res) => {
  const token = req.cookies?.tv_session || (req.headers['authorization'] ? req.headers['authorization'].replace('Bearer ', '') : null);
  if (token) activeSessions.delete(token);
  res.clearCookie('tv_session', { path: '/' });
  res.json({ success: true, message: 'Logged out successfully' });
});

// 1. Devices API
app.get('/api/devices', (req, res) => {
  const now = Date.now();
  // Device is strictly ONLINE only if active socket exists AND heartbeat received within 25 seconds
  const list = Object.values(devices).map(dev => {
    const ws = connectedSockets.get(dev.id);
    const isSocketOpen = ws && ws.readyState === WebSocket.OPEN;
    const lastSeenMs = dev.lastSeen ? new Date(dev.lastSeen).getTime() : 0;
    const isHeartbeatFresh = (now - lastSeenMs) <= 25000;
    return {
      ...dev,
      online: Boolean(isSocketOpen && isHeartbeatFresh)
    };
  });
  res.json({ devices: list });
});

app.post('/api/devices/register', (req, res) => {
  const { id, name, site } = req.body;
  const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;

  if (!id) return res.status(400).json({ error: 'Device ID required' });

  const cleanId = sanitizeText(id, 50);
  const cleanName = sanitizeText(name, 100);
  const cleanSite = sanitizeText(site, 100);

  if (!devices[cleanId]) {
    devices[cleanId] = {
      id: cleanId,
      name: cleanName || `TV Display (${cleanId.substring(0, 6)})`,
      site: cleanSite || 'Headquarters',
      ip: clientIp,
      currentChannel: 'ch-signage',
      volume: 100,
      lastSeen: new Date().toISOString()
    };
  } else {
    devices[cleanId].ip = clientIp;
    devices[cleanId].lastSeen = new Date().toISOString();
    if (cleanSite) devices[cleanId].site = cleanSite;
    if (cleanName) devices[cleanId].name = cleanName;
  }

  saveJson(DEVICES_FILE, devices);
  res.json({ success: true, device: devices[cleanId] });
});

app.post('/api/devices/:id/update', requireAdmin, (req, res) => {
  const { id } = req.params;
  const { name, site, currentChannel, volume } = req.body;
  if (!devices[id]) return res.status(404).json({ error: 'Device not found' });

  if (name !== undefined) devices[id].name = sanitizeText(name, 100);
  if (site !== undefined) devices[id].site = sanitizeText(site, 100);
  if (volume !== undefined) devices[id].volume = Math.max(0, Math.min(100, parseInt(volume, 10) || 100));

  if (currentChannel !== undefined) {
    devices[id].currentChannel = currentChannel;
    // Dispatch to this specific TV
    const ws = connectedSockets.get(id);
    if (ws && ws.readyState === WebSocket.OPEN) {
      const ch = channels.find(c => c.id === currentChannel);
      ws.send(JSON.stringify({ type: 'SWITCH_CHANNEL', channel: ch }));
    }
  }

  saveJson(DEVICES_FILE, devices);
  res.json({ success: true, device: devices[id] });
});

app.delete('/api/devices/:id', requireAdmin, (req, res) => {
  const { id } = req.params;
  if (!devices[id]) return res.status(404).json({ success: false, error: 'Device not found' });

  delete devices[id];
  if (connectedSockets.has(id)) {
    const ws = connectedSockets.get(id);
    try {
      ws.send(JSON.stringify({ type: 'DECOMMISSION' }));
      ws.close();
    } catch (e) {}
    connectedSockets.delete(id);
  }
  saveJson(DEVICES_FILE, devices);
  console.log(`[DEVICES] Device deleted: ${id}`);
  res.json({ success: true, message: `Device ${id} deleted` });
});

app.post('/api/devices/prune-offline', requireAdmin, (req, res) => {
  let prunedCount = 0;
  for (const id of Object.keys(devices)) {
    if (!connectedSockets.has(id)) {
      delete devices[id];
      prunedCount++;
    }
  }
  saveJson(DEVICES_FILE, devices);
  console.log(`[DEVICES] Pruned ${prunedCount} offline devices`);
  res.json({ success: true, prunedCount });
});

app.post('/api/devices/:id/reload', requireAuth, (req, res) => {
  const { id } = req.params;
  const targetWs = connectedSockets.get(id);
  if (targetWs && targetWs.readyState === WebSocket.OPEN) {
    targetWs.send(JSON.stringify({ type: 'RELOAD_PLAYER' }));
    return res.json({ success: true, message: `Reload signal sent to TV ${id}` });
  }
  res.status(404).json({ error: `TV ${id} is not connected` });
});

app.post('/api/devices/reload-all', requireAuth, (req, res) => {
  let count = 0;
  connectedSockets.forEach(ws => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'RELOAD_PLAYER' }));
      count++;
    }
  });
  res.json({ success: true, count, message: `Reload signal sent to ${count} TV displays` });
});

app.get('/api/force-reload', (req, res) => {
  let count = 0;
  connectedSockets.forEach(ws => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'RELOAD_PLAYER' }));
      count++;
    }
  });
  res.json({ success: true, count, message: `Forced reload signal sent to ${count} TV displays` });
});

// 2. Channels API
app.get('/api/channels', (req, res) => {
  res.json({ channels });
});

app.post('/api/channels', requireAdmin, (req, res) => {
  const { id, name, type, streamKey, url, description } = req.body;
  if (!id || !name || !type) return res.status(400).json({ error: 'Missing channel fields' });

  const cleanId = sanitizeText(id, 50);
  const cleanName = sanitizeText(name, 100);
  const existingIdx = channels.findIndex(c => c.id === cleanId);
  const newCh = { id: cleanId, name: cleanName, type, streamKey: streamKey || 'live', url: url || '', description: sanitizeText(description, 200) };

  if (existingIdx >= 0) {
    channels[existingIdx] = newCh;
  } else {
    channels.push(newCh);
  }

  saveJson(CHANNELS_FILE, channels);
  res.json({ success: true, channel: newCh });
});

// 3. Central Broadcast Commands
app.post('/api/broadcast/channel', requireAuth, (req, res) => {
  const { channelId, target, site } = req.body;
  const ch = channels.find(c => c.id === channelId);
  if (!ch) return res.status(404).json({ error: 'Channel not found' });

  let updatedCount = 0;
  console.log(`[API] Broadcast triggered for channel: ${channelId}, target: ${target}`);

  // Broadcast command to WebSockets
  connectedSockets.forEach((ws, devId) => {
    const dev = devices[devId];
    let matches = false;

    if (target === 'all' || !target) {
      matches = true;
    } else if (target === 'site' && dev && dev.site === site) {
      matches = true;
    } else if (target === devId) {
      matches = true;
    }

    if (matches) {
      console.log(`[API] Switching TV: ${devId}`);
      if (dev) {
        dev.currentChannel = channelId;
      }
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'SWITCH_CHANNEL', channel: ch }));
        updatedCount++;
      }
    }
  });

  saveJson(DEVICES_FILE, devices);
  res.json({ success: true, updatedCount, channel: ch });
});

// 4. Emergency Alerts
app.post('/api/broadcast/alert', requireAdmin, (req, res) => {
  const { message, severity = 'critical', duration = 30 } = req.body;
  if (!message) return res.status(400).json({ error: 'Alert message required' });

  activeAlert = {
    message: sanitizeText(message, 300),
    severity: sanitizeText(severity, 20),
    duration: Math.max(5, Math.min(300, parseInt(duration, 10) || 30)),
    timestamp: Date.now()
  };

  const payload = JSON.stringify({ type: 'EMERGENCY_ALERT', alert: activeAlert });
  connectedSockets.forEach(ws => {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  });

  res.json({ success: true, alert: activeAlert });
});

app.post('/api/broadcast/clear-alert', requireAdmin, (req, res) => {
  activeAlert = null;
  const payload = JSON.stringify({ type: 'CLEAR_ALERT' });
  connectedSockets.forEach(ws => {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  });
  res.json({ success: true, message: 'Alert cleared' });
});

// Synchronize all TVs to a specific video in the playlist
app.post('/api/broadcast/sync-video', requireAuth, (req, res) => {
  const { index = 0 } = req.body;
  masterVideoIndex = parseInt(index, 10) || 0;

  // Set all registered devices to 'ch-signage' so dashboard and devices agree
  Object.keys(devices).forEach(devId => {
    if (devices[devId]) {
      devices[devId].currentChannel = 'ch-signage';
      devices[devId].lastSeen = new Date().toISOString();
    }
  });
  saveJson(DEVICES_FILE, devices);

  const payload = JSON.stringify({
    type: 'SYNC_VIDEO',
    index: masterVideoIndex,
    channelId: 'ch-signage'
  });

  connectedSockets.forEach((ws, devId) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(payload);
      if (devices[devId]) {
        devices[devId].currentVideoIndex = masterVideoIndex;
      }
    }
  });

  console.log(`[Sync] All connected TVs synchronized to video index: ${masterVideoIndex}`);
  res.json({ success: true, masterVideoIndex });
});

// 5. Media Assets API
app.get('/api/media', (req, res) => {
  fs.readdir(MEDIA_DIR, (err, files) => {
    if (err) return res.status(500).json({ error: err.message });
    const mediaFiles = files
      .filter(f => !f.startsWith('.') && f !== 'seamless_master_loop.mp4' && !f.endsWith('.tmp.mp4'))
      .sort()
      .map(f => {
        const stat = fs.statSync(path.join(MEDIA_DIR, f));
        return {
          filename: f,
          url: `/media/${encodeURIComponent(f)}`,
          size: stat.size,
          updatedAt: stat.mtime
        };
      });

    // Provide seamless master loop if available
    let seamlessLoop = null;
    try {
      seamlessLoop = seamlessLoopManager.getSeamlessMetadata(MEDIA_DIR, DATA_DIR);
    } catch (e) {
      console.error('[SeamlessLoop] Error resolving metadata:', e.message);
    }

    res.json({ media: mediaFiles, seamlessLoop });
  });
});

app.post('/api/upload-media', requireAuth, upload.array('files', 15), (req, res) => {
  const uploaded = (req.files || []).map(f => `/media/${f.filename}`);

  // Rebuild seamless loop in background
  try {
    seamlessLoopManager.buildSeamlessMasterLoop(MEDIA_DIR, DATA_DIR);
  } catch (e) {
    console.error('[SeamlessLoop] Rebuild on upload failed:', e.message);
  }

  // Broadcast playlist update to all connected TV players
  const payload = JSON.stringify({ type: 'PLAYLIST_UPDATED' });
  connectedSockets.forEach(ws => {
    if (ws.readyState === WebSocket.OPEN) ws.send(payload);
  });

  res.json({ success: true, uploaded });
});

app.delete('/api/media/:filename', requireAuth, (req, res) => {
  const filename = path.basename(req.params.filename);
  const filePath = path.join(MEDIA_DIR, filename);

  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);

    // Rebuild seamless loop in background
    try {
      seamlessLoopManager.buildSeamlessMasterLoop(MEDIA_DIR, DATA_DIR);
    } catch (e) {
      console.error('[SeamlessLoop] Rebuild on delete failed:', e.message);
    }

    // Broadcast playlist update
    const payload = JSON.stringify({ type: 'PLAYLIST_UPDATED' });
    connectedSockets.forEach(ws => {
      if (ws.readyState === WebSocket.OPEN) ws.send(payload);
    });
    return res.json({ success: true, message: 'File deleted' });
  }
  return res.status(404).json({ error: 'File not found' });
});

// 5.1 Management Tools & Auto-Discovery API
app.post('/api/tools/detect-tvs', requireAdmin, async (req, res) => {
  try {
    const detector = require('./scripts/tv-network-detector.js');
    const nets = detector.getNetworkInterfaces();
    const selectedNet = nets.find(n => n.ip.startsWith('192.168.')) || nets[0];
    if (!selectedNet) {
      return res.status(400).json({ success: false, error: 'No active network interfaces found' });
    }
    const subnetBase = selectedNet.ip.substring(0, selectedNet.ip.lastIndexOf('.'));
    const foundIps = await detector.scanSubnetForTvs(subnetBase, 3001, 1000);

    const results = [];
    for (let i = 0; i < foundIps.length; i++) {
      const tvIp = foundIps[i];
      const tvName = `LG-Smart-TV-${i + 1}`;
      try {
        await detector.connectAndLaunchTv(tvIp, selectedNet.ip, tvName);
        results.push({ ip: tvIp, name: tvName, status: 'launched' });
      } catch (e) {
        results.push({ ip: tvIp, name: tvName, status: 'failed', error: e.message });
      }
    }

    res.json({ success: true, detectedCount: foundIps.length, results });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// 6. System Info Endpoint
app.get('/api/system/status', (req, res) => {
  const host = req.hostname;
  res.json({
    status: 'online',
    httpPort: HTTP_PORT,
    httpsPort: HTTPS_PORT,
    mediamtx: {
      webrtcUrl: `http://${host}:${MEDIAMTX_WEBRTC_PORT}`,
      hlsUrl: `http://${host}:${MEDIAMTX_HLS_PORT}`
    },
    connectedTVs: connectedSockets.size,
    totalDevices: Object.keys(devices).length,
    activeAlert
  });
});

// --- Server Initializers ---
const httpServer = http.createServer(app);
// Extend keep-alive timeout so TV video streams survive brief laptop sleep/wake
// Default Node.js keep-alive is 5s which drops mid-stream on suspend
httpServer.keepAliveTimeout = 120000; // 2 minutes
httpServer.headersTimeout = 125000;

// Check if SSL certs exist for HTTPS server
let httpsServer = null;
const keyPath = path.join(CERTS_DIR, 'server.key');
const certPath = path.join(CERTS_DIR, 'server.cert');
if (fs.existsSync(keyPath) && fs.existsSync(certPath)) {
  try {
    const credentials = {
      key: fs.readFileSync(keyPath),
      cert: fs.readFileSync(certPath)
    };
    httpsServer = https.createServer(credentials, app);
    httpsServer.keepAliveTimeout = 120000;
    httpsServer.headersTimeout = 125000;
  } catch (e) {
    console.warn('Could not load SSL certs, running HTTP only:', e.message);
  }
}

// Global Express Error Handler (OWASP Information Disclosure Prevention)
app.use((err, req, res, next) => {
  console.error('[Error Handler]', err.message);
  if (err instanceof multer.MulterError) {
    return res.status(400).json({ success: false, error: `Upload error: ${err.message}` });
  } else if (err) {
    return res.status(400).json({ success: false, error: err.message || 'Request processing error' });
  }
  next();
});

// WebSocket Server attached to HTTP server (and HTTPS if available)
const wss = new WebSocketServer({ server: httpServer, path: '/ws/control', maxPayload: 64 * 1024 });

function handleWsConnection(ws, req) {
  let registeredId = null;

  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);

      if (data.type === 'REGISTER') {
        const rawId = typeof data.id === 'string' ? data.id : '';
        const cleanId = rawId.replace(/[^a-zA-Z0-9_-]/g, '').substring(0, 50);
        registeredId = cleanId || `tv-${Math.random().toString(36).substr(2, 6)}`;
        connectedSockets.set(registeredId, ws);

        const cleanName = sanitizeText(data.name, 100);
        const cleanSite = sanitizeText(data.site, 100);

        if (!devices[registeredId]) {
          devices[registeredId] = {
            id: registeredId,
            name: cleanName || `TV Screen ${registeredId}`,
            site: cleanSite || 'Headquarters',
            ip: req.socket.remoteAddress,
            currentChannel: 'ch-signage',
            volume: 100,
            lastSeen: new Date().toISOString()
          };
        } else {
          devices[registeredId].lastSeen = new Date().toISOString();
        }
        if (data.currentVideo !== undefined) {
          devices[registeredId].currentVideo = data.currentVideo ? sanitizeText(data.currentVideo, 255) : null;
        }
        if (typeof data.currentVideoIndex === 'number') {
          devices[registeredId].currentVideoIndex = data.currentVideoIndex;
        }
        if (typeof data.totalVideos === 'number') {
          devices[registeredId].totalVideos = data.totalVideos;
        }
        if (data.mode) {
          devices[registeredId].playbackMode = sanitizeText(data.mode, 50);
        }
        saveJson(DEVICES_FILE, devices);

        // Send confirmation with current channel, active alert & master playlist index
        const currentCh = channels.find(c => c.id === devices[registeredId].currentChannel) || channels[0];
        ws.send(JSON.stringify({
          type: 'REGISTRATION_SUCCESS',
          device: devices[registeredId],
          currentChannel: currentCh,
          alert: activeAlert,
          masterVideoIndex: masterVideoIndex,
          mediamtxHost: MEDIAMTX_HOST,
          webrtcPort: MEDIAMTX_WEBRTC_PORT,
          hlsPort: MEDIAMTX_HLS_PORT
        }));

        console.log(`[WS] TV Connected & Registered: ${registeredId} (${devices[registeredId].name})`);
      }

      if (data.type === 'VIDEO_ADVANCE') {
        if (registeredId && typeof data.nextIndex === 'number' && Number.isInteger(data.nextIndex) && data.nextIndex >= 0 && data.nextIndex < 1000) {
          masterVideoIndex = data.nextIndex;
          if (devices[registeredId]) {
            devices[registeredId].currentVideoIndex = data.nextIndex;
            if (data.currentVideo) {
              devices[registeredId].currentVideo = sanitizeText(data.currentVideo, 255);
            }
            if (typeof data.totalVideos === 'number') {
              devices[registeredId].totalVideos = data.totalVideos;
            }
          }
        }
      }

      if (data.type === 'PLAYBACK_STATUS' || data.type === 'HEARTBEAT') {
        if (registeredId && devices[registeredId]) {
          devices[registeredId].lastSeen = new Date().toISOString();
          if (data.currentVideo !== undefined) {
            devices[registeredId].currentVideo = data.currentVideo ? sanitizeText(data.currentVideo, 255) : null;
          }
          if (typeof data.currentVideoIndex === 'number') {
            devices[registeredId].currentVideoIndex = data.currentVideoIndex;
          }
          if (typeof data.totalVideos === 'number') {
            devices[registeredId].totalVideos = data.totalVideos;
          }
          if (data.mode) {
            devices[registeredId].playbackMode = sanitizeText(data.mode, 50);
          }
        }
        if (data.type === 'HEARTBEAT') {
          ws.send(JSON.stringify({ type: 'PONG' }));
        }
      }
    } catch (err) {
      console.error('[WS] Parse error:', err.message);
    }
  });

  ws.on('close', () => {
    if (registeredId) {
      if (connectedSockets.get(registeredId) === ws) {
        connectedSockets.delete(registeredId);
        console.log(`[WS] TV Disconnected: ${registeredId}`);
      }
    }
  });
}

wss.on('connection', handleWsConnection);

// Server-Side WebSocket Liveness & Ghost Connection Watchdog (Reaper)
setInterval(() => {
  const now = Date.now();
  connectedSockets.forEach((ws, id) => {
    const dev = devices[id];
    const lastSeenMs = dev?.lastSeen ? new Date(dev.lastSeen).getTime() : 0;
    // Heartbeats sent every 10s. If no heartbeat for > 25s, TV was powered off or network dropped without TCP FIN
    if (now - lastSeenMs > 25000) {
      console.log(`[Watchdog] TV ${id} (${dev?.name || 'Unknown'}) missed heartbeats (>25s). Marking offline and cleaning socket.`);
      connectedSockets.delete(id);
      try {
        ws.terminate();
      } catch (e) {}
    } else if (ws.readyState === WebSocket.OPEN) {
      try {
        ws.ping();
      } catch (e) {}
    }
  });
}, 10000);

// Start HTTP Server
httpServer.listen(HTTP_PORT, '0.0.0.0', () => {
  console.log(`=======================================================`);
  console.log(`Central TV Streaming Manager running on:`);
  console.log(`   HTTP:  http://0.0.0.0:${HTTP_PORT}`);
  console.log(`   Admin: http://0.0.0.0:${HTTP_PORT}/admin.html`);
  console.log(`   Cast:  http://0.0.0.0:${HTTP_PORT}/presenter.html`);
  console.log(`   TV:    http://0.0.0.0:${HTTP_PORT}/player.html`);
  console.log(`=======================================================`);
});

// Start HTTPS Server if configured
if (httpsServer) {
  const wssSecure = new WebSocketServer({ server: httpsServer, path: '/ws/control' });
  wssSecure.on('connection', handleWsConnection);

  httpsServer.listen(HTTPS_PORT, '0.0.0.0', () => {
    console.log(`   ➜ HTTPS: https://0.0.0.0:${HTTPS_PORT}`);
    console.log(`=======================================================`);
  });
}

// --- Automated TV Self-Healing Watchdog ---
// Periodically checks if any registered Smart TV is powered ON (port 3001 open)
// but has dropped its browser/WebSocket session, and automatically relaunches it.
function checkPortOpen(ip, port, timeout = 1500) {
  return new Promise(resolve => {
    const s = new net.Socket();
    s.setTimeout(timeout);
    s.on('connect', () => { s.destroy(); resolve(true); });
    s.on('error', () => { s.destroy(); resolve(false); });
    s.on('timeout', () => { s.destroy(); resolve(false); });
    s.connect(port, ip);
  });
}

function relaunchLgTv(ip, key, targetUrl) {
  try {
    const ws = new WebSocket(`wss://${ip}:3001`, { rejectUnauthorized: false });
    const timer = setTimeout(() => { try { ws.terminate(); } catch (e) {} }, 5000);

    ws.on('open', () => {
      ws.send(JSON.stringify({
        id: 'reg_watchdog',
        type: 'register',
        payload: {
          forcePairing: false,
          pairingType: 'PROMPT',
          'client-key': key,
          manifest: { permissions: ['LAUNCH', 'LAUNCH_WEBAPP', 'APP_TO_APP', 'CONTROL_AUDIO', 'CONTROL_POWER'] }
        }
      }));
    });

    ws.on('message', (msg) => {
      try {
        const d = JSON.parse(msg.toString());
        if (d.type === 'registered') {
          ws.send(JSON.stringify({
            id: 'launch_watchdog',
            type: 'request',
            uri: 'ssap://system.launcher/launch',
            payload: {
              id: 'com.webos.app.browser',
              params: { target: targetUrl }
            }
          }));
        }
        if (d.id === 'launch_watchdog') {
          clearTimeout(timer);
          ws.close();
        }
      } catch (err) {}
    });

    ws.on('error', () => { clearTimeout(timer); });
  } catch (e) {}
}

async function runTvSelfHealingWatchdog() {
  for (const [devId, dev] of Object.entries(devices)) {
    if (!dev.ip || dev.ip === '127.0.0.1' || dev.ip === '::1' || dev.ip.startsWith('172.')) continue;
    const isWsConnected = connectedSockets.has(devId);
    if (!isWsConnected) {
      const isOpen = await checkPortOpen(dev.ip, 3001);
      if (isOpen) {
        const keyFile = path.join(__dirname, 'data', `lg_tv_key_${dev.ip}.txt`);
        if (fs.existsSync(keyFile)) {
          console.log(`[Watchdog] Smart TV ${dev.name} (${dev.ip}) is active but browser is closed. Auto-relaunching player...`);
          const key = fs.readFileSync(keyFile, 'utf8').trim();
          const targetUrl = `http://192.168.0.151:${HTTP_PORT}/player.html?name=${encodeURIComponent(dev.name)}&site=${encodeURIComponent(dev.site)}`;
          relaunchLgTv(dev.ip, key, targetUrl);
        }
      }
    }
  }
}

// Run TV self-healing watchdog every 30 seconds
setInterval(runTvSelfHealingWatchdog, 30000);

