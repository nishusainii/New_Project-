/**
 * INNCCTV SOC CONTROLLER & STATE MANAGER
 * Coordinates 24 Cameras, 4 Floors, Grid Switcher, WebSockets, Modals & Patrol Tour
 */

const AppState = {
  cameras: [],
  filteredCameras: [],
  currentFloor: 'all',
  currentView: 'grid', // 'grid' or 'map'
  currentGridClass: 'grid-6-floor',
  focusedCamera: null,
  streamPlayers: new Map(),
  ws: null,
  isPatrolActive: false,
  patrolTimer: null,
  floorMap: null
};

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
  checkAuthSession();
  initClock();
  initWebSocket();
  initFloorMap();
  setupUIEventListeners();
  loadCameras();
});

// Authentication Session Guard
function checkAuthSession() {
  const token = localStorage.getItem('innspark_token');
  const userRaw = localStorage.getItem('innspark_user');

  if (!token || !userRaw) {
    window.location.href = '/login.html';
    return;
  }

  try {
    const user = JSON.parse(userRaw);
    if (!user.name || user.name.toLowerCase().includes('nishu')) {
      user.name = 'Security Admin';
      localStorage.setItem('innspark_user', JSON.stringify(user));
    }
    const nameEl = document.getElementById('officerName');
    const roleEl = document.getElementById('officerRole');
    if (nameEl) nameEl.textContent = user.name || 'Security Admin';
    if (roleEl) roleEl.textContent = user.role || 'Officer';
  } catch (e) {
    window.location.href = '/login.html';
  }
}

function logout() {
  localStorage.removeItem('innspark_token');
  localStorage.removeItem('innspark_user');
  window.location.href = '/login.html';
}

// Real-time Indian Standard Time (IST) Clock
function initClock() {
  const clockEl = document.getElementById('liveClock');
  if (!clockEl) return;
  const update = () => {
    const now = new Date();
    const options = {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    };
    const parts = new Intl.DateTimeFormat('en-GB', options).formatToParts(now);
    const p = {};
    parts.forEach(({ type, value }) => { p[type] = value; });
    clockEl.textContent = `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second} IST`;
  };
  setInterval(update, 1000);
  update();
}

// WebSocket Connection for Telemetry & Real-Time Alerts
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  AppState.ws = new WebSocket(wsUrl);

  AppState.ws.onopen = () => {
    console.log('[WS] Connected to CCTV telemetry feed');
  };

  AppState.ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleWebSocketMessage(msg);
    } catch (e) {
      console.error('[WS] Parse error', e);
    }
  };

  AppState.ws.onclose = () => {
    console.warn('[WS] Telemetry disconnected. Retrying in 3s...');
    setTimeout(initWebSocket, 3000);
  };
}

function handleWebSocketMessage(msg) {
  if (msg.type === 'TELEMETRY_UPDATE') {
    const { viewers, cpuPercent, networkThroughput, fpsAverage } = msg.stats;
    const cpuEl = document.getElementById('valCpu');
    const netEl = document.getElementById('valNet');
    const fpsEl = document.getElementById('valFps');
    if (cpuEl) cpuEl.textContent = `${cpuPercent}%`;
    if (netEl) netEl.textContent = `${networkThroughput} Mb/s`;
    if (fpsEl) fpsEl.textContent = `${fpsAverage} FPS`;
  } else if (msg.type === 'MOTION_EVENT') {
    addIncidentItem(msg.event);
    highlightCameraMotion(msg.event.cameraId);
  } else if (msg.type === 'CAMERAS_RELOADED' || msg.type === 'CAMERA_UPDATED') {
    loadCameras();
  }
}

// Load Cameras from Express API
async function loadCameras() {
  try {
    const res = await fetch('/api/cameras');
    const data = await res.json();
    if (data.success) {
      AppState.cameras = data.cameras;
      updateHeaderTelemetry();
      applyFloorFilter(AppState.currentFloor);
    }
  } catch (err) {
    console.error('Failed to load cameras:', err);
  }
}

// Header Badges & Counts
function updateHeaderTelemetry() {
  const total = AppState.cameras.length;
  const online = AppState.cameras.filter(c => c.isOnline).length;
  const rec = AppState.cameras.filter(c => c.recording).length;

  const totalEl = document.getElementById('valTotalCams');
  const onlineEl = document.getElementById('valOnlineCams');
  const recEl = document.getElementById('valRecCams');

  if (totalEl) totalEl.textContent = total;
  if (onlineEl) onlineEl.textContent = `${online}/${total}`;
  if (recEl) recEl.textContent = `${rec}/${total}`;
}

// Floor Filtering
function applyFloorFilter(floor) {
  AppState.currentFloor = floor;

  // Update tabs
  document.querySelectorAll('.floor-tab').forEach(tab => {
    tab.classList.toggle('active', tab.getAttribute('data-floor') === String(floor));
  });

  if (floor === 'all') {
    AppState.filteredCameras = [...AppState.cameras];
    setGridLayout('grid-24-matrix');
  } else {
    AppState.filteredCameras = AppState.cameras.filter(c => c.floor === parseInt(floor, 10));
    setGridLayout('grid-6-floor');
  }

  renderMatrix();

  if (AppState.floorMap && floor !== 'all') {
    AppState.floorMap.setFloor(floor, AppState.cameras);
  }
}

// Render Video Tiles Matrix
function renderMatrix() {
  const matrix = document.getElementById('cameraMatrix');
  if (!matrix) return;

  // Destroy old players
  AppState.streamPlayers.forEach(player => player.destroy());
  AppState.streamPlayers.clear();

  matrix.className = `camera-matrix ${AppState.currentGridClass}`;
  matrix.innerHTML = '';

  const searchVal = (document.getElementById('cameraSearch')?.value || '').toLowerCase();
  const visibleCams = AppState.filteredCameras.filter(c => 
    c.name.toLowerCase().includes(searchVal) ||
    c.id.toLowerCase().includes(searchVal) ||
    c.ip.includes(searchVal) ||
    c.zone.toLowerCase().includes(searchVal)
  );

  if (visibleCams.length === 0) {
    matrix.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 60px; color: var(--text-dim); font-size: 1rem;">
      No cameras found matching your search.
    </div>`;
    return;
  }

  visibleCams.forEach(cam => {
    const card = createCameraCard(cam);
    matrix.appendChild(card);

    // Mount stream player
    const stage = card.querySelector('.video-stage');
    const player = new StreamPlayer(stage, cam);
    AppState.streamPlayers.set(cam.id, player);
  });
}

// Create Single Camera Card Element
function createCameraCard(cam) {
  const card = document.createElement('div');
  card.className = 'camera-card';
  card.id = `card-${cam.id}`;

  card.innerHTML = `
    <div class="video-stage"></div>

    <!-- Top Overlay -->
    <div class="cam-overlay-top">
      <div class="cam-badge-tag">
        <span class="pulse-dot ${cam.isOnline ? '' : 'pulse-dot recording'}"></span>
        <span>${cam.id.toUpperCase()}</span>
      </div>
      ${cam.recording ? `<div class="rec-indicator"><span class="pulse-dot recording" style="width:6px;height:6px;"></span> REC</div>` : ''}
    </div>

    <!-- Bottom Overlay -->
    <div class="cam-overlay-bottom">
      <div class="cam-meta-strip">
        <span>${cam.resolution.split(' ')[0]}</span>
        <span>${cam.ip}</span>
      </div>
    </div>

    <!-- Quick Hover Actions -->
    <div class="cam-quick-actions">
      <button class="quick-act-btn" title="Focus Fullscreen" onclick="openFullscreenModal('${cam.id}')">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>
      </button>
      <button class="quick-act-btn" title="Digital PTZ Control" onclick="openPTZModal('${cam.id}')">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/></svg>
      </button>
      <button class="quick-act-btn" title="Take Snapshot" onclick="triggerSnapshot('${cam.id}')">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
      </button>
      <button class="quick-act-btn" title="Edit Camera" onclick="openConfigModal('${cam.id}')">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
      </button>
      <button class="quick-act-btn btn-delete-cam" title="Remove Camera" onclick="deleteCamera('${cam.id}', '${cam.name.replace(/'/g, "\\'")}')">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
      </button>
    </div>

    <!-- Card Footer -->
    <div class="camera-footer">
      <div class="cam-title-info">
        <span class="cam-name-text" title="${cam.name}">${cam.name}</span>
        <span class="cam-floor-pill">F${cam.floor}</span>
      </div>
      <div class="cam-codec-tag">${cam.codec}</div>
    </div>
  `;

  return card;
}

// Grid Layout Switcher
function setGridLayout(gridClass) {
  AppState.currentGridClass = gridClass;
  const matrix = document.getElementById('cameraMatrix');
  if (matrix) matrix.className = `camera-matrix ${gridClass}`;

  document.querySelectorAll('.grid-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-grid') === gridClass);
  });
}

// 2D Floor Plan Setup
function initFloorMap() {
  AppState.floorMap = new FloorMap('floormapCanvasContainer', (cam) => {
    openFullscreenModal(cam.id);
  });
}

function setViewMode(mode) {
  AppState.currentView = mode;
  const matrix = document.getElementById('cameraMatrix');
  const floormapWrapper = document.getElementById('floormapWrapper');

  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
  });

  if (mode === 'grid') {
    matrix.style.display = 'grid';
    floormapWrapper.classList.remove('active');
  } else {
    matrix.style.display = 'none';
    floormapWrapper.classList.add('active');
    const floorToRender = AppState.currentFloor === 'all' ? 1 : AppState.currentFloor;
    AppState.floorMap.setFloor(floorToRender, AppState.cameras);
  }
}

// Patrol / Tour Mode (Cycles views)
function togglePatrolMode() {
  AppState.isPatrolActive = !AppState.isPatrolActive;
  const btn = document.getElementById('btnPatrol');
  if (btn) btn.classList.toggle('patrol-active', AppState.isPatrolActive);

  if (AppState.isPatrolActive) {
    let floorIndex = 1;
    AppState.patrolTimer = setInterval(() => {
      applyFloorFilter(floorIndex);
      floorIndex = floorIndex >= 4 ? 1 : floorIndex + 1;
    }, 7000);
  } else {
    clearInterval(AppState.patrolTimer);
    AppState.patrolTimer = null;
  }
}

// Incident / Motion Alerts Handling
function addIncidentItem(alert) {
  const list = document.getElementById('incidentList');
  if (!list) return;

  const item = document.createElement('div');
  item.className = `incident-item ${alert.severity === 'alert' ? 'alert' : ''}`;
  item.onclick = () => openFullscreenModal(alert.cameraId);

  const timeFormatted = new Date(alert.timestamp).toLocaleTimeString();

  item.innerHTML = `
    <div class="incident-time">
      <span>${timeFormatted}</span>
      <span>FLOOR ${alert.floor}</span>
    </div>
    <div class="incident-title">${alert.message}</div>
    <div class="incident-loc">${alert.cameraName}</div>
  `;

  list.insertBefore(item, list.firstChild);
  if (list.children.length > 30) list.removeChild(list.lastChild);
}

function highlightCameraMotion(camId) {
  const card = document.getElementById(`card-${camId}`);
  if (card) {
    card.classList.add('alert-active');
    setTimeout(() => card.classList.remove('alert-active'), 4500);
  }
  const player = AppState.streamPlayers.get(camId);
  if (player) {
    player.triggerMotionAlert();
  }
}

// Snapshot Trigger
function triggerSnapshot(camId) {
  const player = AppState.streamPlayers.get(camId);
  if (player) {
    const filename = player.takeSnapshot();
    if (filename) {
      showToast(`Snapshot captured: ${filename}`);
    }
  }
}

// Fullscreen Modal
let fullscreenPlayer = null;
function openFullscreenModal(camId) {
  const cam = AppState.cameras.find(c => c.id === camId);
  if (!cam) return;
  AppState.focusedCamera = cam;

  const modal = document.getElementById('fullscreenModal');
  const title = document.getElementById('fullscreenModalTitle');
  const stage = document.getElementById('fullscreenVideoStage');

  title.textContent = `[${cam.id.toUpperCase()}] ${cam.name} (Floor ${cam.floor} - ${cam.zone})`;
  modal.classList.add('active');

  if (fullscreenPlayer) fullscreenPlayer.destroy();
  fullscreenPlayer = new StreamPlayer(stage, cam);
}

function closeFullscreenModal() {
  const modal = document.getElementById('fullscreenModal');
  modal.classList.remove('active');
  if (fullscreenPlayer) {
    fullscreenPlayer.destroy();
    fullscreenPlayer = null;
  }
}

// PTZ Controller Modal
let ptzTargetCamId = null;
function openPTZModal(camId) {
  const cam = AppState.cameras.find(c => c.id === camId);
  if (!cam) return;
  ptzTargetCamId = camId;

  document.getElementById('ptzModalTitle').textContent = `PTZ Controls: ${cam.name}`;
  document.getElementById('ptzModal').classList.add('active');
}

function closePTZModal() {
  document.getElementById('ptzModal').classList.remove('active');
  ptzTargetCamId = null;
}

function triggerPTZAction(action) {
  const player = AppState.streamPlayers.get(ptzTargetCamId) || (fullscreenPlayer ? fullscreenPlayer : null);
  if (!player) return;

  if (action === 'up' || action === 'down' || action === 'left' || action === 'right') {
    player.pan(action);
  } else if (action === 'zoomIn') {
    player.zoom(1.25);
  } else if (action === 'zoomOut') {
    player.zoom(0.8);
  } else if (action === 'reset') {
    player.resetPTZ();
  }
}

// Camera Configuration Modal (Add & Edit)
function openConfigModal(camId = null) {
  const modal = document.getElementById('configModal');
  const title = document.getElementById('configModalTitle');
  const form = document.getElementById('cameraConfigForm');

  if (camId) {
    const cam = AppState.cameras.find(c => c.id === camId);
    if (!cam) return;
    title.textContent = `Edit IP Camera [${cam.id.toUpperCase()}]`;
    document.getElementById('cfgCamId').value = cam.id;
    document.getElementById('cfgName').value = cam.name;
    document.getElementById('cfgFloor').value = cam.floor;
    document.getElementById('cfgZone').value = cam.zone;
    document.getElementById('cfgType').value = cam.type;
    document.getElementById('cfgIp').value = cam.ip;
    document.getElementById('cfgPort').value = cam.port || 554;
    document.getElementById('cfgRtspUrl').value = cam.rtspUrl;
    document.getElementById('cfgResolution').value = cam.resolution;
    document.getElementById('cfgCodec').value = cam.codec;
  } else {
    title.textContent = 'Add New IP Camera';
    form.reset();
    document.getElementById('cfgCamId').value = '';
    document.getElementById('cfgFloor').value = AppState.currentFloor === 'all' ? 1 : AppState.currentFloor;
  }

  const deleteBtn = document.getElementById('btnDeleteInModal');
  if (deleteBtn) {
    deleteBtn.style.display = camId ? 'inline-flex' : 'none';
  }

  document.getElementById('pingResultBox').style.display = 'none';
  modal.classList.add('active');
}

async function deleteCamera(id, name) {
  if (!confirm(`Are you sure you want to remove Camera ${id.toUpperCase()} (${name || 'Selected Camera'})?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/cameras/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Camera ${id.toUpperCase()} removed successfully`);
      loadCameras();
    } else {
      showToast(data.error || 'Failed to remove camera');
    }
  } catch (err) {
    showToast(`Error removing camera: ${err.message}`);
  }
}

function deleteCameraFromModal() {
  const id = document.getElementById('cfgCamId').value;
  const name = document.getElementById('cfgName').value;
  if (!id) return;
  closeConfigModal();
  deleteCamera(id, name);
}

function closeConfigModal() {
  document.getElementById('configModal').classList.remove('active');
}

async function saveCameraConfig(e) {
  e.preventDefault();
  const id = document.getElementById('cfgCamId').value;
  const payload = {
    name: document.getElementById('cfgName').value,
    floor: parseInt(document.getElementById('cfgFloor').value, 10),
    floorName: `Floor ${document.getElementById('cfgFloor').value}`,
    zone: document.getElementById('cfgZone').value,
    type: document.getElementById('cfgType').value,
    ip: document.getElementById('cfgIp').value,
    port: parseInt(document.getElementById('cfgPort').value, 10),
    rtspUrl: document.getElementById('cfgRtspUrl').value,
    resolution: document.getElementById('cfgResolution').value,
    codec: document.getElementById('cfgCodec').value
  };

  try {
    const url = id ? `/api/cameras/${id}` : '/api/cameras';
    const method = id ? 'PUT' : 'POST';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeConfigModal();
      showToast(id ? 'Camera updated successfully' : 'Camera added successfully');
      loadCameras();
    }
  } catch (err) {
    showToast(`Error saving camera: ${err.message}`);
  }
}

// Test Connection / Ping RTSP Endpoint
async function testCameraConnection() {
  const id = document.getElementById('cfgCamId').value;
  const ip = document.getElementById('cfgIp').value;
  const port = document.getElementById('cfgPort').value || 554;
  const resultBox = document.getElementById('pingResultBox');

  resultBox.style.display = 'block';
  resultBox.innerHTML = `<span style="color:var(--accent-blue);">Testing TCP socket reachability to ${ip}:${port}...</span>`;

  try {
    const res = await fetch(`/api/cameras/${id || 'test'}/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip, port })
    });
    const data = await res.json();
    if (data.status === 'reachable') {
      resultBox.innerHTML = `<span style="color:var(--accent-green);">● REACHABLE: Socket open on port ${port} (Ready for RTSP streaming)</span>`;
    } else {
      resultBox.innerHTML = `<span style="color:var(--accent-red);">● UNREACHABLE: ${data.details.error || 'Connection timed out'}. (Will use simulated stream until IP is online).</span>`;
    }
  } catch (e) {
    resultBox.innerHTML = `<span style="color:var(--accent-amber);">Connection test initiated. Ensure camera is on same subnet.</span>`;
  }
}

// Batch IP Configuration Modal
function openBatchModal() {
  document.getElementById('batchModal').classList.add('active');
}

function closeBatchModal() {
  document.getElementById('batchModal').classList.remove('active');
}

async function saveBatchConfig(e) {
  e.preventDefault();
  const payload = {
    floor: document.getElementById('batchFloor').value,
    ipPrefix: document.getElementById('batchIpPrefix').value,
    username: document.getElementById('batchUser').value,
    password: document.getElementById('batchPass').value
  };

  try {
    const res = await fetch('/api/cameras/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      closeBatchModal();
      showToast('Batch IP configuration applied across floor');
      loadCameras();
    }
  } catch (err) {
    showToast(`Batch update failed: ${err.message}`);
  }
}

// Toast Notification
function showToast(msg) {
  let toast = document.getElementById('socToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'socToast';
    toast.style.cssText = `
      position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
      background: #0d1322; border: 1px solid var(--accent-blue);
      color: #fff; padding: 10px 20px; border-radius: 8px;
      font-size: 0.85rem; font-family: var(--font-sans);
      box-shadow: 0 10px 30px rgba(0,0,0,0.8); z-index: 2000;
      transition: opacity 0.3s ease;
    `;
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  setTimeout(() => { toast.style.opacity = '0'; }, 3500);
}

// UI Event Listeners Setup
function setupUIEventListeners() {
  // Floor tab clicks
  document.querySelectorAll('.floor-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      applyFloorFilter(tab.getAttribute('data-floor'));
    });
  });

  // View mode clicks
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      setViewMode(btn.getAttribute('data-mode'));
    });
  });

  // Grid layout clicks
  document.querySelectorAll('.grid-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      setGridLayout(btn.getAttribute('data-grid'));
    });
  });

  // Search input
  const search = document.getElementById('cameraSearch');
  if (search) {
    search.addEventListener('input', () => renderMatrix());
  }

  // Drawer toggle
  const drawerToggle = document.getElementById('btnToggleDrawer');
  const drawer = document.getElementById('incidentDrawer');
  if (drawerToggle && drawer) {
    drawerToggle.addEventListener('click', () => {
      drawer.classList.toggle('collapsed');
    });
  }

  // Form submits
  document.getElementById('cameraConfigForm')?.addEventListener('submit', saveCameraConfig);
  document.getElementById('batchConfigForm')?.addEventListener('submit', saveBatchConfig);
}
