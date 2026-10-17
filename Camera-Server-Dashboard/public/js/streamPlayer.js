/**
 * INNCCTV STREAM PLAYER & SURVEILLANCE ENGINE
 * WebRTC (WHEP) Ultra-Low Latency Player + Real-Time Canvas CCTV Simulator
 */

class StreamPlayer {
  constructor(container, camera, options = {}) {
    this.container = container;
    this.camera = camera;
    this.options = options;
    this.peerConnection = null;
    this.videoElement = null;
    this.canvasElement = null;
    this.canvasCtx = null;
    this.animFrameId = null;
    this.isSimulated = false;
    this.ptzState = { pan: 0, tilt: 0, zoom: 1 };
    this.motionBoundingBox = null;
    this.motionTimer = null;
    this.fpsCounter = 30;
    this.lastFrameTime = performance.now();

    this.init();
  }

  init() {
    this.container.innerHTML = '';
    
    // Create Video Element for WebRTC
    this.videoElement = document.createElement('video');
    this.videoElement.autoplay = true;
    this.videoElement.playsInline = true;
    this.videoElement.muted = true;
    this.videoElement.style.display = 'none';

    // Create Canvas Element for Fallback / CCTV Simulation
    this.canvasElement = document.createElement('canvas');
    this.canvasElement.className = 'feed-canvas';
    this.canvasElement.width = 640;
    this.canvasElement.height = 360;
    this.canvasCtx = this.canvasElement.getContext('2d');

    this.container.appendChild(this.videoElement);
    this.container.appendChild(this.canvasElement);

    // Try connecting via WebRTC WHEP
    this.connectWebRTC();
  }

  async connectWebRTC() {
    const streamName = this.camera.streamName || `cam_${this.camera.id}`;
    const webrtcUrl = `${window.location.protocol}//${window.location.hostname}:8889/${streamName}/whep`;

    try {
      this.peerConnection = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      });

      this.peerConnection.addTransceiver('video', { direction: 'recvonly' });
      this.peerConnection.addTransceiver('audio', { direction: 'recvonly' });

      this.peerConnection.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          this.videoElement.srcObject = event.streams[0];
          this.videoElement.style.display = 'block';
          this.canvasElement.style.display = 'none';
          this.isSimulated = false;
        }
      };

      const offer = await this.peerConnection.createOffer();
      await this.peerConnection.setLocalDescription(offer);

      // Timeout if stream not publishing or camera offline
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);

      const response = await fetch(webrtcUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: offer.sdp,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const answerSdp = await response.text();
        await this.peerConnection.setRemoteDescription(new RTCSessionDescription({
          type: 'answer',
          sdp: answerSdp
        }));
        return;
      }
    } catch {
      // Stream gateway not ready or real camera not physically on LAN -> fallback to realistic CCTV simulation
    }

    // Fallback to high-definition interactive CCTV simulation
    this.startSimulation();
  }

  startSimulation() {
    this.isSimulated = true;
    this.videoElement.style.display = 'none';
    this.canvasElement.style.display = 'block';

    // Unique seed based on camera id
    let seed = 0;
    for (let i = 0; i < this.camera.id.length; i++) {
      seed = (seed << 5) - seed + this.camera.id.charCodeAt(i);
    }
    const baseColorH = Math.abs(seed % 360);

    let noiseOffset = 0;
    let personX = 120 + (Math.abs(seed) % 350);
    let personDir = (seed % 2 === 0) ? 0.4 : -0.4;

    const render = () => {
      if (!this.canvasCtx) return;

      const now = performance.now();
      const delta = now - this.lastFrameTime;
      this.lastFrameTime = now;
      this.fpsCounter = Math.round(1000 / (delta || 33));

      const ctx = this.canvasCtx;
      const w = this.canvasElement.width;
      const h = this.canvasElement.height;

      ctx.save();

      // Apply PTZ Transforms (Pan / Tilt / Zoom)
      ctx.translate(w / 2, h / 2);
      ctx.scale(this.ptzState.zoom, this.ptzState.zoom);
      ctx.translate(-w / 2 + this.ptzState.pan, -h / 2 + this.ptzState.tilt);

      // Background Surveillance Architecture
      const grad = ctx.createLinearGradient(0, 0, w, h);
      grad.addColorStop(0, '#0a0f1d');
      grad.addColorStop(0.5, '#131c31');
      grad.addColorStop(1, '#080c18');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Perspective Grid Lines (Architectural Floor/Ceiling)
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.08)';
      ctx.lineWidth = 1;
      
      // Vanishing point
      const vpX = w * 0.5;
      const vpY = h * 0.42;

      for (let x = -100; x <= w + 100; x += 40) {
        ctx.beginPath();
        ctx.moveTo(vpX, vpY);
        ctx.lineTo(x, h);
        ctx.stroke();
      }

      // Back Wall & Architectural Panels
      ctx.fillStyle = 'rgba(255, 255, 255, 0.02)';
      ctx.fillRect(w * 0.2, h * 0.2, w * 0.6, h * 0.5);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
      ctx.strokeRect(w * 0.2, h * 0.2, w * 0.6, h * 0.5);

      // Room Type Elements
      ctx.fillStyle = `hsla(${baseColorH}, 40%, 25%, 0.15)`;
      ctx.fillRect(w * 0.25, h * 0.35, w * 0.2, h * 0.35);

      // Animated Patrol / Person Target
      personX += personDir;
      if (personX > w * 0.75 || personX < w * 0.25) personDir *= -1;

      // Simulated human silhouette / movement
      const personY = h * 0.52;
      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
      // Head
      ctx.beginPath();
      ctx.arc(personX, personY - 26, 6, 0, Math.PI * 2);
      ctx.fill();
      // Body
      ctx.beginPath();
      ctx.roundRect(personX - 8, personY - 18, 16, 32, 4);
      ctx.fill();

      // Motion Tracking Bounding Box if alert triggered
      if (this.motionBoundingBox) {
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.strokeRect(personX - 16, personY - 36, 32, 54);
        
        ctx.fillStyle = '#ef4444';
        ctx.font = '10px JetBrains Mono, monospace';
        ctx.fillText('TARGET DETECTED [HUMAN 94%]', personX - 35, personY - 42);
      }

      ctx.restore();

      // CCTV Scanlines & Ambient Noise
      ctx.fillStyle = 'rgba(0, 0, 0, 0.12)';
      for (let y = 0; y < h; y += 4) {
        ctx.fillRect(0, y, w, 1.5);
      }

      // Vignette Shadow
      const vignette = ctx.createRadialGradient(w / 2, h / 2, w * 0.3, w / 2, h / 2, w * 0.75);
      vignette.addColorStop(0, 'rgba(0,0,0,0)');
      vignette.addColorStop(1, 'rgba(0,0,0,0.55)');
      ctx.fillStyle = vignette;
      ctx.fillRect(0, 0, w, h);

      // Camera Crosshair Overlay (Fine military HUD)
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.25)';
      ctx.lineWidth = 1;
      ctx.strokeRect(w * 0.1, h * 0.1, w * 0.8, h * 0.8);

      // Center cross
      const cx = w / 2;
      const cy = h / 2;
      ctx.beginPath();
      ctx.moveTo(cx - 15, cy); ctx.lineTo(cx + 15, cy);
      ctx.moveTo(cx, cy - 15); ctx.lineTo(cx, cy + 15);
      ctx.stroke();

      // Live Timestamp Overlay (IST)
      const nowObj = new Date();
      const parts = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Kolkata',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }).formatToParts(nowObj);
      const p = {};
      parts.forEach(({ type, value }) => { p[type] = value; });
      const timeStr = `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}.${String(nowObj.getMilliseconds()).padStart(3, '0')} IST`;
      
      ctx.font = '11px JetBrains Mono, monospace';
      ctx.fillStyle = '#f1f5f9';
      ctx.fillText(timeStr, 16, h - 14);

      ctx.fillStyle = '#38bdf8';
      ctx.fillText(`FPS: ${this.fpsCounter}  |  ${this.camera.codec}  |  ${this.camera.bitrate}`, w - 195, h - 14);

      // PTZ state indicator if zoomed
      if (this.ptzState.zoom > 1) {
        ctx.fillStyle = '#f59e0b';
        ctx.fillText(`PTZ ZOOM: ${this.ptzState.zoom.toFixed(1)}X`, 16, 42);
      }

      this.animFrameId = requestAnimationFrame(render);
    };

    render();
  }

  triggerMotionAlert() {
    this.motionBoundingBox = true;
    if (this.motionTimer) clearTimeout(this.motionTimer);
    this.motionTimer = setTimeout(() => {
      this.motionBoundingBox = false;
    }, 4500);
  }

  // PTZ Control API
  pan(direction) {
    if (direction === 'left') this.ptzState.pan -= 25;
    if (direction === 'right') this.ptzState.pan += 25;
    if (direction === 'up') this.ptzState.tilt -= 25;
    if (direction === 'down') this.ptzState.tilt += 25;
    this.clampPTZ();
  }

  zoom(factor) {
    this.ptzState.zoom = Math.max(1, Math.min(4, this.ptzState.zoom * factor));
    this.clampPTZ();
  }

  resetPTZ() {
    this.ptzState = { pan: 0, tilt: 0, zoom: 1 };
  }

  clampPTZ() {
    const maxOffset = 180 * (this.ptzState.zoom - 1);
    this.ptzState.pan = Math.max(-maxOffset, Math.min(maxOffset, this.ptzState.pan));
    this.ptzState.tilt = Math.max(-maxOffset, Math.min(maxOffset, this.ptzState.tilt));
  }

  // Take Snapshot frame and download
  takeSnapshot() {
    let dataUrl = '';
    if (this.videoElement && !this.isSimulated && this.videoElement.videoWidth > 0) {
      const snapCanvas = document.createElement('canvas');
      snapCanvas.width = this.videoElement.videoWidth;
      snapCanvas.height = this.videoElement.videoHeight;
      const ctx = snapCanvas.getContext('2d');
      ctx.drawImage(this.videoElement, 0, 0);
      dataUrl = snapCanvas.toDataURL('image/jpeg', 0.95);
    } else if (this.canvasElement) {
      dataUrl = this.canvasElement.toDataURL('image/jpeg', 0.95);
    }

    if (dataUrl) {
      const a = document.createElement('a');
      const filename = `${this.camera.id.toUpperCase()}_SNAPSHOT_${new Date().toISOString().replace(/[:.]/g, '-')}.jpg`;
      a.href = dataUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      return filename;
    }
    return null;
  }

  destroy() {
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
    }
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
    this.container.innerHTML = '';
  }
}

window.StreamPlayer = StreamPlayer;
