const fs = require('fs');
const path = require('path');
const net = require('net');
const { spawn } = require('child_process');

class CameraManager {
  constructor(filePath) {
    this.filePath = filePath || path.resolve(__dirname, '../config/cameras.json');
    this.cameras = [];
    this.alerts = [];
    this.loadCameras();
  }

  loadCameras() {
    try {
      if (fs.existsSync(this.filePath)) {
        const raw = fs.readFileSync(this.filePath, 'utf8');
        this.cameras = JSON.parse(raw);
      } else {
        this.cameras = [];
      }
    } catch (err) {
      console.error('[CameraManager] Error loading cameras:', err.message);
      this.cameras = [];
    }
  }

  saveCameras() {
    try {
      fs.writeFileSync(this.filePath, JSON.stringify(this.cameras, null, 2), 'utf8');
      return true;
    } catch (err) {
      console.error('[CameraManager] Error saving cameras:', err.message);
      return false;
    }
  }

  getAll(floor = null) {
    if (floor !== null && floor !== undefined && floor !== 'all') {
      const floorNum = parseInt(floor, 10);
      return this.cameras.filter(c => c.floor === floorNum);
    }
    return this.cameras;
  }

  getById(id) {
    return this.cameras.find(c => c.id === id);
  }

  create(cameraData) {
    const id = cameraData.id || `cam-${Date.now().toString().slice(-4)}`;
    const streamName = cameraData.streamName || `cam_${id.replace(/[^a-zA-Z0-9_]/g, '')}`;
    const newCam = {
      id,
      streamName,
      name: cameraData.name || 'New Camera',
      floor: parseInt(cameraData.floor, 10) || 1,
      floorName: cameraData.floorName || `Floor ${cameraData.floor || 1}`,
      zone: cameraData.zone || 'General',
      type: cameraData.type || 'Dome',
      ip: cameraData.ip || '192.168.1.100',
      port: parseInt(cameraData.port, 10) || 554,
      rtspUrl: cameraData.rtspUrl || `rtsp://admin:admin123@${cameraData.ip || '192.168.1.100'}:554/stream1`,
      isOnline: cameraData.isOnline ?? true,
      recording: cameraData.recording ?? true,
      ptzSupported: !!cameraData.ptzSupported,
      resolution: cameraData.resolution || '1920x1080 @ 30fps',
      bitrate: cameraData.bitrate || '2.2 Mbps',
      codec: cameraData.codec || 'H.264',
      mapCoords: cameraData.mapCoords || { x: 50, y: 50, angle: 90 },
      notes: cameraData.notes || ''
    };

    this.cameras.push(newCam);
    this.saveCameras();
    return newCam;
  }

  update(id, updateData) {
    const idx = this.cameras.findIndex(c => c.id === id);
    if (idx === -1) return null;

    this.cameras[idx] = {
      ...this.cameras[idx],
      ...updateData,
      floor: updateData.floor !== undefined ? parseInt(updateData.floor, 10) : this.cameras[idx].floor,
      port: updateData.port !== undefined ? parseInt(updateData.port, 10) : this.cameras[idx].port
    };

    this.saveCameras();
    return this.cameras[idx];
  }

  delete(id) {
    const idx = this.cameras.findIndex(c => c.id === id);
    if (idx === -1) return false;
    this.cameras.splice(idx, 1);
    this.saveCameras();
    return true;
  }

  batchUpdate(updates) {
    // updates could be: { floor: 2, ipPrefix: "10.0.1.", username: "admin", password: "pwd" }
    let modifiedCount = 0;
    this.cameras = this.cameras.map((cam, i) => {
      if (!updates.floor || updates.floor === 'all' || cam.floor === parseInt(updates.floor, 10)) {
        let updatedCam = { ...cam };
        if (updates.ipPrefix) {
          const suffix = 100 + i + 1;
          updatedCam.ip = `${updates.ipPrefix}${suffix}`;
        }
        if (updates.username && updates.password) {
          updatedCam.rtspUrl = `rtsp://${updates.username}:${updates.password}@${updatedCam.ip}:${updatedCam.port || 554}/stream1`;
        }
        modifiedCount++;
        return updatedCam;
      }
      return cam;
    });

    this.saveCameras();
    return { count: modifiedCount, cameras: this.cameras };
  }

  // Check if camera host/port is reachable via TCP
  async pingCamera(ip, port = 554, timeout = 2000) {
    return new Promise((resolve) => {
      const socket = new net.Socket();
      let isResolved = false;

      socket.setTimeout(timeout);

      socket.on('connect', () => {
        if (!isResolved) {
          isResolved = true;
          socket.destroy();
          resolve({ online: true, latency: 15 });
        }
      });

      socket.on('timeout', () => {
        if (!isResolved) {
          isResolved = true;
          socket.destroy();
          resolve({ online: false, error: 'Connection timed out' });
        }
      });

      socket.on('error', (err) => {
        if (!isResolved) {
          isResolved = true;
          socket.destroy();
          resolve({ online: false, error: err.message });
        }
      });

      socket.connect(port, ip);
    });
  }

  // Generate an event / alert
  addAlert(alert) {
    const item = {
      id: `ev-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      timestamp: new Date().toISOString(),
      type: alert.type || 'motion',
      severity: alert.severity || 'warning',
      cameraId: alert.cameraId,
      cameraName: alert.cameraName,
      floor: alert.floor,
      message: alert.message
    };
    this.alerts.unshift(item);
    if (this.alerts.length > 50) this.alerts.pop();
    return item;
  }

  getAlerts(limit = 20) {
    return this.alerts.slice(0, limit);
  }
}

module.exports = CameraManager;
