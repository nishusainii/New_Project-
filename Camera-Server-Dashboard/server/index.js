const express = require('express');
const http = require('http');
const path = require('path');
const os = require('os');
const { WebSocketServer } = require('ws');
const CameraManager = require('./cameraManager');
const MediaMTXManager = require('./mediamtxManager');
const {
  hashPassword,
  verifyPassword,
  generateToken,
  verifyToken,
  rateLimitLogin,
  securityHeaders,
  validateCameraInput
} = require('./security');

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });

const PORT = process.env.PORT || 3000;

// Initialize Managers
const cameraManager = new CameraManager();
const mediamtxManager = new MediaMTXManager();

// Sync MediaMTX config on launch
mediamtxManager.generateConfig(cameraManager.getAll());
mediamtxManager.start();

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('[Server] Shutting down...');
  mediamtxManager.stop();
  process.exit(0);
});

process.on('SIGTERM', () => {
  mediamtxManager.stop();
  process.exit(0);
});

// VAPT & Hardening: Disable information disclosure headers & attach enterprise security headers
app.disable('x-powered-by');
app.use(securityHeaders);

// Middleware
app.use(express.json({ limit: '1mb' }));
app.use(express.static(path.resolve(__dirname, '../public')));

// API Routes

// 0. Authentication Routes (Hardened with Salted Hash Verification & Rate Limiting)
const VALID_USERS = [
  {
    username: 'admin',
    passwordHash: hashPassword(process.env.ADMIN_PASSWORD || 'innspark@2026'),
    name: 'Security Admin',
    role: 'Chief Security Officer',
    office: 'Innspark Delhi Office',
    permissions: ['all']
  },
  {
    username: 'operator',
    passwordHash: hashPassword(process.env.OPERATOR_PASSWORD || 'innspark@2026'),
    name: 'SOC Operator',
    role: 'Surveillance Officer',
    office: 'Innspark Delhi Office',
    permissions: ['view', 'ptz', 'snapshot']
  },
  {
    username: 'supervisor',
    passwordHash: hashPassword(process.env.SUPERVISOR_PASSWORD || 'innspark@2026'),
    name: 'Floor Supervisor',
    role: 'Operations Lead',
    office: 'Innspark Delhi Office',
    permissions: ['view', 'snapshot']
  }
];

app.post('/api/auth/login', rateLimitLogin, (req, res) => {
  const { username, password } = req.body;
  
  const user = VALID_USERS.find(u => 
    u.username.toLowerCase() === (username || '').toLowerCase()
  );

  if (!user || !verifyPassword(password || '', user.passwordHash)) {
    if (req.authSecurity) req.authSecurity.recordFailedAttempt();
    return res.status(401).json({
      success: false,
      message: 'Invalid credentials. Access denied.'
    });
  }

  if (req.authSecurity) req.authSecurity.recordSuccess();

  const token = generateToken({
    username: user.username,
    role: user.role,
    office: user.office
  }, 8);

  res.json({
    success: true,
    token,
    user: {
      username: user.username,
      name: user.name,
      role: user.role,
      office: user.office,
      permissions: user.permissions
    }
  });
});

app.get('/api/auth/verify', (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ success: false, message: 'Unauthenticated' });
  }
  const token = authHeader.split(' ')[1];
  const payload = verifyToken(token);
  if (!payload) {
    return res.status(401).json({ success: false, message: 'Invalid or expired session token.' });
  }
  res.json({ success: true, message: 'Authenticated', user: payload });
});

// 1. Get Cameras
app.get('/api/cameras', (req, res) => {
  const { floor } = req.query;
  const cameras = cameraManager.getAll(floor);
  res.json({
    success: true,
    count: cameras.length,
    cameras
  });
});

// 2. Get Single Camera
app.get('/api/cameras/:id', (req, res) => {
  const cam = cameraManager.getById(req.params.id);
  if (!cam) return res.status(404).json({ success: false, error: 'Camera not found' });
  res.json({ success: true, camera: cam });
});

// 3. Create Camera (with Strict Input Sanitization)
app.post('/api/cameras', (req, res) => {
  const validation = validateCameraInput(req.body);
  if (!validation.isValid) {
    return res.status(400).json({ success: false, errors: validation.errors });
  }
  const newCam = cameraManager.create(req.body);
  mediamtxManager.generateConfig(cameraManager.getAll());
  broadcast({ type: 'CAMERA_ADDED', camera: newCam });
  res.status(201).json({ success: true, camera: newCam });
});

// 4. Update Camera (with Strict Input Sanitization)
app.put('/api/cameras/:id', (req, res) => {
  const validation = validateCameraInput(req.body);
  if (!validation.isValid) {
    return res.status(400).json({ success: false, errors: validation.errors });
  }
  const updated = cameraManager.update(req.params.id, req.body);
  if (!updated) return res.status(404).json({ success: false, error: 'Camera not found' });
  mediamtxManager.generateConfig(cameraManager.getAll());
  broadcast({ type: 'CAMERA_UPDATED', camera: updated });
  res.json({ success: true, camera: updated });
});

// 5. Delete Camera
app.delete('/api/cameras/:id', (req, res) => {
  const deleted = cameraManager.delete(req.params.id);
  if (!deleted) return res.status(404).json({ success: false, error: 'Camera not found' });
  mediamtxManager.generateConfig(cameraManager.getAll());
  broadcast({ type: 'CAMERA_DELETED', id: req.params.id });
  res.json({ success: true, message: 'Camera deleted' });
});

// 6. Batch update
app.post('/api/cameras/batch', (req, res) => {
  const result = cameraManager.batchUpdate(req.body);
  mediamtxManager.generateConfig(cameraManager.getAll());
  broadcast({ type: 'CAMERAS_RELOADED' });
  res.json({ success: true, updatedCount: result.count });
});

// 7. Test Camera RTSP / IP connection
app.post('/api/cameras/:id/test', async (req, res) => {
  const cam = cameraManager.getById(req.params.id);
  if (!cam) return res.status(404).json({ success: false, error: 'Camera not found' });

  const result = await cameraManager.pingCamera(cam.ip, cam.port || 554, 2000);
  res.json({
    success: true,
    camera: cam.name,
    ip: cam.ip,
    port: cam.port || 554,
    status: result.online ? 'reachable' : 'unreachable',
    details: result
  });
});

// 8. Snapshot frame generator
app.get('/api/cameras/:id/snapshot', (req, res) => {
  const cam = cameraManager.getById(req.params.id);
  if (!cam) return res.status(404).send('Camera not found');

  // Return a stylish high-contrast SVG surveillance frame placeholder
  const now = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
    <rect width="640" height="360" fill="#0d1117" />
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#161b22" stroke-width="1"/>
    </pattern>
    <rect width="640" height="360" fill="url(#grid)" />
    <!-- Crosshairs -->
    <circle cx="320" cy="180" r="45" fill="none" stroke="#238636" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.6"/>
    <line x1="300" y1="180" x2="340" y2="180" stroke="#238636" stroke-width="1.5" opacity="0.8"/>
    <line x1="320" y1="160" x2="320" y2="200" stroke="#238636" stroke-width="1.5" opacity="0.8"/>
    <!-- Corner brackets -->
    <path d="M 20 50 L 20 20 L 50 20" fill="none" stroke="#388bfd" stroke-width="2"/>
    <path d="M 620 50 L 620 20 L 590 20" fill="none" stroke="#388bfd" stroke-width="2"/>
    <path d="M 20 310 L 20 340 L 50 340" fill="none" stroke="#388bfd" stroke-width="2"/>
    <path d="M 620 310 L 620 340 L 590 340" fill="none" stroke="#388bfd" stroke-width="2"/>
    <!-- Text overlays -->
    <rect x="25" y="25" width="85" height="24" rx="4" fill="#da3633" />
    <text x="35" y="41" fill="#ffffff" font-family="monospace" font-size="12" font-weight="bold">● LIVE REC</text>
    <text x="120" y="41" fill="#7ee787" font-family="monospace" font-size="13">${cam.name.toUpperCase()}</text>
    <text x="500" y="41" fill="#8b949e" font-family="monospace" font-size="12">${cam.floorName}</text>
    <text x="25" y="335" fill="#58a6ff" font-family="monospace" font-size="12">IP: ${cam.ip}:${cam.port || 554}</text>
    <text x="320" y="335" fill="#f0883e" font-family="monospace" font-size="12">${now}</text>
    <text x="320" y="195" fill="#c9d1d9" font-family="sans-serif" font-size="14" text-anchor="middle" font-weight="600">${cam.resolution}</text>
  </svg>`;

  res.setHeader('Content-Type', 'image/svg+xml');
  res.send(svg);
});

// 9. System Status & Gateway Telemetry
app.get('/api/system/status', async (req, res) => {
  const gatewayStatus = await mediamtxManager.checkStatus();
  const cpus = os.cpus();
  const load = os.loadavg();
  const freeMem = os.freemem();
  const totalMem = os.totalmem();

  res.json({
    success: true,
    gateway: {
      running: mediamtxManager.isRunning,
      version: 'v1.21.2',
      webrtcPort: 8889,
      hlsPort: 8888,
      rtspPort: 8554,
      apiPort: 9997,
      status: gatewayStatus
    },
    system: {
      uptime: Math.floor(process.uptime()),
      loadAvg: load[0].toFixed(2),
      cpuCores: cpus.length,
      memoryUsage: `${Math.round((1 - freeMem / totalMem) * 100)}%`,
      freeMemMB: Math.round(freeMem / 1024 / 1024),
      totalMemMB: Math.round(totalMem / 1024 / 1024),
      nodeVersion: process.version
    },
    cameras: {
      total: cameraManager.getAll().length,
      online: cameraManager.getAll().filter(c => c.isOnline).length,
      recording: cameraManager.getAll().filter(c => c.recording).length,
      byFloor: {
        floor1: cameraManager.getAll(1).length,
        floor2: cameraManager.getAll(2).length,
        floor3: cameraManager.getAll(3).length,
        floor4: cameraManager.getAll(4).length
      }
    }
  });
});

// 10. Security Events & Motion Logs
app.get('/api/system/events', (req, res) => {
  res.json({
    success: true,
    events: cameraManager.getAlerts(25)
  });
});

// WebSocket broadcasting
function broadcast(data) {
  const payload = JSON.stringify(data);
  wss.clients.forEach(client => {
    if (client.readyState === 1) {
      client.send(payload);
    }
  });
}

// Simulated real-time motion and telemetry loop
setInterval(() => {
  if (wss.clients.size === 0) return;

  const allCams = cameraManager.getAll();
  if (allCams.length === 0) return;

  // 25% chance every 4 seconds to trigger a motion alert on a random camera
  if (Math.random() < 0.35) {
    const randomCam = allCams[Math.floor(Math.random() * allCams.length)];
    const alert = cameraManager.addAlert({
      type: 'motion',
      severity: Math.random() > 0.8 ? 'alert' : 'info',
      cameraId: randomCam.id,
      cameraName: randomCam.name,
      floor: randomCam.floor,
      message: `Motion detected in ${randomCam.zone} (${randomCam.name})`
    });

    broadcast({
      type: 'MOTION_EVENT',
      event: alert
    });
  }

  // Live telemetry packet
  broadcast({
    type: 'TELEMETRY_UPDATE',
    stats: {
      timestamp: Date.now(),
      viewers: wss.clients.size,
      cpuPercent: Math.min(100, Math.floor(12 + Math.random() * 15)),
      networkThroughput: (42.5 + Math.random() * 8.2).toFixed(1), // Mbps
      fpsAverage: (29.8 + Math.random() * 0.4).toFixed(1)
    }
  });
}, 3000);

// Start HTTP Server
server.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(`   INNCCTV SURVEILLANCE OPERATIONS CENTER (SOC)     `);
  console.log(`   Dashboard:  http://localhost:${PORT}             `);
  console.log(`   MediaMTX:   RTSP:8554 | HLS:8888 | WebRTC:8889   `);
  console.log(`   Total IP Cameras Configured: ${cameraManager.getAll().length} (Floors 1-4)`);
  console.log(`====================================================`);
});
