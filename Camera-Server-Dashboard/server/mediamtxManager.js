const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class MediaMTXManager {
  constructor(options = {}) {
    this.binPath = options.binPath || path.resolve(__dirname, '../bin/mediamtx');
    this.configPath = options.configPath || path.resolve(__dirname, '../config/mediamtx.yml');
    this.process = null;
    this.isRunning = false;
    this.apiBase = 'http://127.0.0.1:9997/v3';
  }

  // Generate mediamtx.yml from cameras list
  generateConfig(cameras = []) {
    const header = `# MediaMTX Gateway Configuration - Auto-generated
api: true
apiAddress: 127.0.0.1:9997

rtsp: true
rtspAddress: :8554

hls: true
hlsAddress: :8888
hlsAllowOrigins: ["*"]

webrtc: true
webrtcAddress: :8889
webrtcAllowOrigins: ["*"]

logLevel: info
logDestinations: [stdout]

paths:
`;

    let pathsSection = '';
    for (const cam of cameras) {
      if (cam.streamName && cam.rtspUrl) {
        pathsSection += `  ${cam.streamName}:\n`;
        pathsSection += `    source: ${cam.rtspUrl}\n`;
        pathsSection += `    sourceOnDemand: yes\n`;
      }
    }

    pathsSection += `  all_others:\n`;

    fs.writeFileSync(this.configPath, header + pathsSection, 'utf8');
  }

  start() {
    if (this.isRunning) return;

    if (!fs.existsSync(this.binPath)) {
      console.warn(`[MediaMTX] Binary not found at ${this.binPath}`);
      return;
    }

    console.log(`[MediaMTX] Starting gateway using ${this.configPath}...`);
    this.process = spawn(this.binPath, [this.configPath], {
      stdio: ['ignore', 'pipe', 'pipe']
    });

    this.isRunning = true;

    this.process.stdout.on('data', (data) => {
      const msg = data.toString().trim();
      if (msg) console.log(`[MediaMTX] ${msg}`);
    });

    this.process.stderr.on('data', (data) => {
      const msg = data.toString().trim();
      if (msg) console.error(`[MediaMTX:ERR] ${msg}`);
    });

    this.process.on('close', (code) => {
      console.log(`[MediaMTX] Gateway stopped with exit code ${code}`);
      this.isRunning = false;
      this.process = null;
    });
  }

  stop() {
    if (this.process) {
      console.log('[MediaMTX] Stopping gateway...');
      this.process.kill('SIGTERM');
      this.isRunning = false;
      this.process = null;
    }
  }

  async checkStatus() {
    try {
      const res = await fetch(`${this.apiBase}/paths/list`);
      if (res.ok) {
        const data = await res.json();
        return { running: true, paths: data.itemCount || 0, details: data };
      }
    } catch {
      // offline or starting
    }
    return { running: this.isRunning, paths: 0 };
  }
}

module.exports = MediaMTXManager;
