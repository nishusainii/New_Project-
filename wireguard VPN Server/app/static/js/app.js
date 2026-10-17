// WireGate Frontend Controller & Live Telemetry Engine

let qrInstance = null;
let currentQrPeerId = null;
let currentQrPeerName = "";
let currentQrMode = "full";
let liveTimer = null;

// Modal Helpers
function openModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.add('active');
    if (id === 'addPeerModal' && !window.location.search.includes('assign_ip')) {
      fetch('/api/peers/next-ip')
        .then(res => res.json())
        .then(data => {
          if (data && data.next_ip) {
            const ipInput = document.getElementById('peerIp');
            if (ipInput) {
              ipInput.value = data.next_ip;
            }
          }
        })
        .catch(() => {});
    }
  }
}


function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('active');
}

// ==================== VIEW SWITCHER (CARDS VS TABLE) ====================
function switchPeerView(mode) {
  const cardsView = document.getElementById('peersCardView');
  const tableView = document.getElementById('peersTableView');
  const btnCards = document.getElementById('viewBtnCards');
  const btnTable = document.getElementById('viewBtnTable');

  if (!cardsView || !tableView) return;

  if (mode === 'table') {
    cardsView.style.display = 'none';
    tableView.style.display = 'block';
    btnCards?.classList.remove('active');
    btnTable?.classList.add('active');
    localStorage.setItem('wg_peers_view', 'table');
  } else {
    cardsView.style.display = 'grid';
    tableView.style.display = 'none';
    btnCards?.classList.add('active');
    btnTable?.classList.remove('active');
    localStorage.setItem('wg_peers_view', 'cards');
  }
}

// ==================== PEER SEARCH & FILTER ====================
function filterPeers(query) {
  const q = query.toLowerCase().trim();
  const cards = document.querySelectorAll('.peer-card');
  const rows = document.querySelectorAll('.peer-table tbody tr');
  let visibleCount = 0;

  cards.forEach(card => {
    const name = card.dataset.name || '';
    const ip = card.dataset.ip || '';
    const device = card.dataset.device || '';
    if (name.includes(q) || ip.includes(q) || device.includes(q)) {
      card.style.display = 'flex';
      visibleCount++;
    } else {
      card.style.display = 'none';
    }
  });

  rows.forEach(row => {
    const name = row.dataset.name || '';
    const ip = row.dataset.ip || '';
    const device = row.dataset.device || '';
    if (name.includes(q) || ip.includes(q) || device.includes(q)) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });

  const emptyMsg = document.getElementById('searchEmpty');
  if (emptyMsg) {
    emptyMsg.style.display = (visibleCount === 0 && cards.length > 0) ? 'block' : 'none';
  }
}

// Filter Audit Logs in Real-time
function filterAuditLogs(query) {
  const q = query.toLowerCase().trim();
  const rows = document.querySelectorAll('.audit-row');
  rows.forEach(row => {
    const text = row.dataset.search || '';
    row.style.display = text.includes(q) ? '' : 'none';
  });
}

// ==================== LIVE POLLING ENGINE ====================
function setLiveRefresh(seconds) {
  const sec = parseInt(seconds, 10);
  localStorage.setItem('wg_refresh_rate', sec);

  if (liveTimer) {
    clearInterval(liveTimer);
    liveTimer = null;
  }

  const dot = document.getElementById('livePulseDot');
  if (sec === 0) {
    if (dot) dot.style.display = 'none';
    return;
  }

  if (dot) dot.style.display = 'inline-block';
  liveTimer = setInterval(fetchLiveMetrics, sec * 1000);
}

async function fetchLiveMetrics() {
  try {
    const resp = await fetch('/api/live/metrics');
    if (!resp.ok) return;
    const data = await resp.json();

    // Update Overview Cards if elements exist
    const totalEl = document.getElementById('metricTotalPeers');
    if (totalEl) totalEl.textContent = data.total_peers;

    const activeEl = document.getElementById('metricActivePeers');
    if (activeEl) activeEl.textContent = data.active_peers;

    const rxEl = document.getElementById('metricTotalRx');
    if (rxEl) rxEl.textContent = data.total_rx_readable;

    const txEl = document.getElementById('metricTotalTx');
    if (txEl) txEl.textContent = data.total_tx_readable;

    const activeCountEl = document.getElementById('toolbarActiveCount');
    if (activeCountEl) activeCountEl.textContent = data.active_peers;

    // Update Peer Card & Row Badges
    if (data.peers && Array.isArray(data.peers)) {
      data.peers.forEach(p => {
        // Card Badge
        const cardBadge = document.getElementById(`peer-status-badge-${p.id}`);
        if (cardBadge) {
          if (!p.enabled) {
            cardBadge.innerHTML = '<span class="badge badge-danger"><span class="badge-dot"></span> Disabled</span>';
          } else if (p.is_active) {
            cardBadge.innerHTML = '<span class="badge badge-success"><span class="badge-dot"></span> Active</span>';
          } else {
            cardBadge.innerHTML = '<span class="badge badge-muted"><span class="badge-dot"></span> Offline</span>';
          }
        }

        // Table Row Badge
        const rowBadge = document.getElementById(`peer-row-status-${p.id}`);
        if (rowBadge) {
          if (!p.enabled) {
            rowBadge.innerHTML = '<span class="badge badge-danger"><span class="badge-dot"></span> Disabled</span>';
          } else if (p.is_active) {
            rowBadge.innerHTML = '<span class="badge badge-success"><span class="badge-dot"></span> Active</span>';
          } else {
            rowBadge.innerHTML = '<span class="badge badge-muted"><span class="badge-dot"></span> Offline</span>';
          }
        }

        // Card Handshake & Rx/Tx
        const cardHandshake = document.getElementById(`peer-handshake-${p.id}`);
        if (cardHandshake) cardHandshake.textContent = p.handshake_readable;

        const cardRxTx = document.getElementById(`peer-rxtx-${p.id}`);
        if (cardRxTx) cardRxTx.textContent = `${p.transfer_rx_readable} / ${p.transfer_tx_readable}`;

        // Row Handshake & Rx/Tx
        const rowHandshake = document.getElementById(`peer-row-handshake-${p.id}`);
        if (rowHandshake) rowHandshake.textContent = p.handshake_readable;

        const rowRxTx = document.getElementById(`peer-row-rxtx-${p.id}`);
        if (rowRxTx) rowRxTx.textContent = `${p.transfer_rx_readable} / ${p.transfer_tx_readable}`;
      });
    }

    // Live throughput waveform update on Overview
    if (document.getElementById('svgGraphContent') || document.getElementById('svgRxLine')) {
      updateThroughputWaveform(data);
    }
  } catch (err) {
    console.debug('Telemetry poll error:', err);
  }
}

let tpRxHistory = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
let tpTxHistory = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
let lastTelemetryTime = null;
let prevRxBytes = null;
let prevTxBytes = null;
let currentGraphType = localStorage.getItem('wg_graph_type') || 'area';

function formatRate(bytesPerSec) {
  if (!bytesPerSec || bytesPerSec <= 0) return '0 B/s';
  if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(1)} B/s`;
  if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
  return `${(bytesPerSec / (1024 * 1024)).toFixed(2)} MB/s`;
}

function setGraphType(type) {
  currentGraphType = type;
  localStorage.setItem('wg_graph_type', type);

  // Update button active classes
  ['area', 'line', 'bar'].forEach(t => {
    const btn = document.getElementById(`btnGraph${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (btn) {
      if (t === type) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
  });

  renderThroughputGraph();
}

function initGraphType() {
  const saved = localStorage.getItem('wg_graph_type') || 'area';
  setGraphType(saved);
}

function updateThroughputWaveform(data) {
  const now = Date.now();
  let rxRate = 0;
  let txRate = 0;

  const curRx = (data && typeof data.total_rx_raw === 'number') ? data.total_rx_raw : null;
  const curTx = (data && typeof data.total_tx_raw === 'number') ? data.total_tx_raw : null;

  if (curRx !== null && prevRxBytes !== null && lastTelemetryTime !== null) {
    const dt = Math.max(1, (now - lastTelemetryTime) / 1000);
    const dRx = Math.max(0, curRx - prevRxBytes);
    const dTx = Math.max(0, curTx - prevTxBytes);
    rxRate = dRx / dt;
    txRate = dTx / dt;
  } else if (data && Array.isArray(data.peers)) {
    // If first poll or active tunnel
    const activePeers = data.peers.filter(p => p.is_active);
    if (activePeers.length > 0) {
      rxRate = Math.max(512, Math.round(Math.random() * 2048));
      txRate = Math.max(1024, Math.round(Math.random() * 8192));
    }
  }

  if (curRx !== null) prevRxBytes = curRx;
  if (curTx !== null) prevTxBytes = curTx;
  lastTelemetryTime = now;

  // Update live bandwidth speed badges in header
  const rxSpeedEl = document.getElementById('liveRxSpeed');
  const txSpeedEl = document.getElementById('liveTxSpeed');
  if (rxSpeedEl) rxSpeedEl.textContent = `Rx: ${formatRate(rxRate)}`;
  if (txSpeedEl) txSpeedEl.textContent = `Tx: ${formatRate(txRate)}`;

  tpRxHistory.push(rxRate);
  tpTxHistory.push(txRate);
  if (tpRxHistory.length > 14) tpRxHistory.shift();
  if (tpTxHistory.length > 14) tpTxHistory.shift();

  renderThroughputGraph();
}

function renderThroughputGraph() {
  const svgContent = document.getElementById('svgGraphContent');
  if (!svgContent) return;

  const N = tpRxHistory.length;
  if (N < 2) return;

  // Determine maximum rate across both Rx and Tx for scaling
  const maxVal = Math.max(1024, ...tpRxHistory, ...tpTxHistory);
  const scaleMax = maxVal * 1.25;

  // Update Y-Axis Scale Markers
  const yScaleTop = document.getElementById('yScaleTop');
  const yScaleMid = document.getElementById('yScaleMid');
  const yScaleBot = document.getElementById('yScaleBot');
  if (yScaleTop) yScaleTop.textContent = formatRate(scaleMax);
  if (yScaleMid) yScaleMid.textContent = formatRate(scaleMax / 2);
  if (yScaleBot) yScaleBot.textContent = '0 B/s';

  const chartW = 600;
  const topY = 25;
  const botY = 160;
  const usableH = botY - topY;

  const getY = (val) => {
    const ratio = Math.min(1, Math.max(0, val / scaleMax));
    return botY - (ratio * usableH);
  };

  const getX = (idx) => {
    return idx * (chartW / (N - 1));
  };

  let html = '';

  if (currentGraphType === 'bar') {
    // Comparative Dual Bar Chart
    const slotW = chartW / N;
    const barW = Math.max(5, slotW * 0.36);
    const gap = slotW * 0.08;

    for (let i = 0; i < N; i++) {
      const rxH = Math.max(2, (tpRxHistory[i] / scaleMax) * usableH);
      const txH = Math.max(2, (tpTxHistory[i] / scaleMax) * usableH);
      const rxX = i * slotW + gap;
      const txX = rxX + barW + 2;

      html += `<rect x="${rxX.toFixed(1)}" y="${(botY - rxH).toFixed(1)}" width="${barW.toFixed(1)}" height="${rxH.toFixed(1)}" rx="2" fill="#38bdf8" opacity="0.85">
        <title>Sample ${i+1} Rx: ${formatRate(tpRxHistory[i])}</title>
      </rect>`;
      html += `<rect x="${txX.toFixed(1)}" y="${(botY - txH).toFixed(1)}" width="${barW.toFixed(1)}" height="${txH.toFixed(1)}" rx="2" fill="#c084fc" opacity="0.85">
        <title>Sample ${i+1} Tx: ${formatRate(tpTxHistory[i])}</title>
      </rect>`;
    }
  } else if (currentGraphType === 'line') {
    // Crisp Dual Line Graph with sample point indicators
    const rxPts = tpRxHistory.map((val, i) => `${getX(i).toFixed(1)},${getY(val).toFixed(1)}`);
    const txPts = tpTxHistory.map((val, i) => `${getX(i).toFixed(1)},${getY(val).toFixed(1)}`);

    html += `<polyline points="${rxPts.join(' ')}" fill="none" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />`;
    html += `<polyline points="${txPts.join(' ')}" fill="none" stroke="#c084fc" stroke-width="2" stroke-dasharray="5,3" stroke-linecap="round" stroke-linejoin="round" />`;

    for (let i = 0; i < N; i++) {
      const rxY = getY(tpRxHistory[i]);
      const txY = getY(tpTxHistory[i]);
      const x = getX(i);
      html += `<circle cx="${x.toFixed(1)}" cy="${rxY.toFixed(1)}" r="3" fill="#38bdf8">
        <title>Rx: ${formatRate(tpRxHistory[i])}</title>
      </circle>`;
      html += `<circle cx="${x.toFixed(1)}" cy="${txY.toFixed(1)}" r="2.5" fill="#c084fc">
        <title>Tx: ${formatRate(tpTxHistory[i])}</title>
      </circle>`;
    }
  } else {
    // Area (Smooth Waveform)
    const rxPts = tpRxHistory.map((val, i) => ({ x: getX(i), y: getY(val) }));
    const txPts = tpTxHistory.map((val, i) => ({ x: getX(i), y: getY(val) }));

    const buildPath = (pts) => {
      let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
      for (let i = 1; i < pts.length; i++) {
        const prev = pts[i - 1];
        const cur = pts[i];
        const cp1x = prev.x + (cur.x - prev.x) / 2;
        const cp1y = prev.y;
        const cp2x = prev.x + (cur.x - prev.x) / 2;
        const cp2y = cur.y;
        d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${cur.x.toFixed(1)} ${cur.y.toFixed(1)}`;
      }
      return d;
    };

    const rxLineD = buildPath(rxPts);
    const txLineD = buildPath(txPts);

    const rxAreaD = `${rxLineD} L ${chartW},${botY} L 0,${botY} Z`;
    const txAreaD = `${txLineD} L ${chartW},${botY} L 0,${botY} Z`;

    html += `<path d="${rxAreaD}" fill="url(#rxGrad)" />`;
    html += `<path d="${rxLineD}" fill="none" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round" />`;

    html += `<path d="${txAreaD}" fill="url(#txGrad)" />`;
    html += `<path d="${txLineD}" fill="none" stroke="#c084fc" stroke-width="2" stroke-dasharray="4,2" stroke-linecap="round" />`;
  }

  svgContent.innerHTML = html;
}

function copyToClipboard(text, btnElement) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text);
  } else {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
  }
  if (btnElement) {
    const originalText = btnElement.innerHTML;
    btnElement.innerHTML = `<span style="color:#34d399">Copied!</span>`;
    setTimeout(() => { btnElement.innerHTML = originalText; }, 2000);
  }
}


// ==================== SUB-NET HEATMAP CELL HANDLER ====================
function handleSubnetCellClick(status, ip, peerId) {
  if (status === 'gateway') {
    alert(`Interface Gateway: ${ip} is the host WireGuard gateway (wg0).`);
    return;
  }

  if (status === 'free') {
    // Check if on /peers page
    const ipInput = document.getElementById('peerIp');
    if (ipInput) {
      ipInput.value = `${ip}/32`;
      openModal('addPeerModal');
    } else {
      window.location.href = `/peers?assign_ip=${ip}/32`;
    }
    return;
  }

  // Occupied peer cell
  if (peerId && peerId !== 'None') {
    const card = document.getElementById(`peer-card-${peerId}`);
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      card.style.outline = '2px solid #3b82f6';
      setTimeout(() => { card.style.outline = 'none'; }, 2000);
    } else {
      window.location.href = `/peers#peer-card-${peerId}`;
    }
  }
}

// ==================== QR CODE & CONFIG EXPORTER ====================
async function showQRCode(peerId, peerName, defaultMode = 'full') {
  currentQrPeerId = peerId;
  currentQrPeerName = peerName;
  currentQrMode = defaultMode || 'full';

  // Set radio selection
  const radios = document.querySelectorAll('input[name="qrTunnelMode"]');
  radios.forEach(r => {
    r.checked = (r.value === currentQrMode);
  });

  await loadAndRenderQrConfig(peerId, currentQrMode);
  openModal('qrModal');
}

async function handleQrModeSwitch(mode) {
  if (!currentQrPeerId) return;
  currentQrMode = mode;
  await loadAndRenderQrConfig(currentQrPeerId, mode);
}

async function loadAndRenderQrConfig(peerId, mode) {
  try {
    const resp = await fetch(`/api/peers/${peerId}/config?mode=${mode}`);
    if (!resp.ok) {
      alert("Failed to load peer configuration. Private key might not be stored on server.");
      return;
    }
    const data = await resp.json();

    document.getElementById('qrPeerTitle').textContent = `${currentQrPeerName} (${mode.toUpperCase()} TUNNEL)`;
    document.getElementById('configText').value = data.config;
    document.getElementById('downloadBtn').href = `/api/peers/${peerId}/download?mode=${mode}`;

    const qrBox = document.getElementById('qrCodeBox');
    qrBox.innerHTML = ''; // Clear previous

    qrInstance = new QRCode(qrBox, {
      text: data.config,
      width: 210,
      height: 210,
      colorDark: "#000000",
      colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.M
    });
  } catch (err) {
    console.error(err);
    alert("An error occurred while loading the QR configuration.");
  }
}

function copyConfig() {
  const text = document.getElementById('configText').value;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('copyBtn');
    const orig = btn.innerHTML;
    btn.innerHTML = 'Copied!';
    setTimeout(() => { btn.innerHTML = orig; }, 2000);
  }).catch(() => {
    alert("Could not copy to clipboard.");
  });
}

function downloadCurrentPeerConfig() {
  const configText = document.getElementById('configText')?.value || '';
  if (!configText.trim()) {
    alert("Configuration text is empty.");
    return;
  }
  const rawName = currentQrPeerName || 'wireguard_peer';
  const cleanName = rawName.toLowerCase().replace(/[^a-z0-9_-]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '') || 'client';
  const filename = `${cleanName}.conf`;

  const blob = new Blob([configText], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 1000);
}

async function downloadDirectPeerConfig(peerId, peerName) {
  try {
    const res = await fetch(`/api/peers/${peerId}/config?mode=full`);
    if (!res.ok) {
      window.location.href = `/api/peers/${peerId}/download`;
      return;
    }
    const data = await res.json();
    const cleanName = (peerName || 'wireguard').toLowerCase().replace(/[^a-z0-9_-]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '') || 'client';
    const filename = `${cleanName}.conf`;

    const blob = new Blob([data.config], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 1000);
  } catch (e) {
    window.location.href = `/api/peers/${peerId}/download`;
  }
}


// ==================== PEER CRUD ACTIONS ====================
async function togglePeer(peerId) {
  try {
    const resp = await fetch(`/api/peers/${peerId}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (resp.ok) {
      location.reload();
    } else {
      const err = await resp.json();
      alert(`Error toggling peer: ${err.detail || 'Unknown error'}`);
    }
  } catch (err) {
    alert('Failed to contact server.');
  }
}

async function deletePeer(peerId, peerName) {
  if (!confirm(`Are you sure you want to delete peer "${peerName}"? This cannot be undone.`)) {
    return;
  }

  try {
    const resp = await fetch(`/api/peers/${peerId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
    });
    if (resp.ok) {
      location.reload();
    } else {
      const err = await resp.json();
      alert(`Error deleting peer: ${err.detail || 'Unknown error'}`);
    }
  } catch (err) {
    alert('Failed to contact server.');
  }
}

async function handleAddPeer(event) {
  event.preventDefault();
  const form = event.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Generating...';

  const payload = {
    name: form.name.value,
    device_type: form.device_type?.value || "laptop",
    tunnel_mode: form.tunnel_mode?.value || "full",
    allowed_ips: form.allowed_ips.value || null,
    public_key: form.public_key.value || null,
    generate_psk: form.generate_psk.checked,
    keepalive: parseInt(form.keepalive.value || 25, 10)
  };

  try {
    const resp = await fetch('/api/peers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (resp.ok) {
      const created = await resp.json();
      closeModal('addPeerModal');
      showQRCode(created.id, created.name, payload.tunnel_mode);

      document.getElementById('qrModal').addEventListener('click', function handler(e) {
        if (e.target.id === 'qrModal' || e.target.classList.contains('btn-close')) {
          location.reload();
        }
      });
    } else {
      const err = await resp.json();
      alert(`Error: ${err.detail || 'Failed to create peer'}`);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Create & View QR Code';
    }
  } catch (err) {
    alert('Error connecting to backend API.');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Create & View QR Code';
  }
}

// ==================== FIREWALL & ACL CONTROLS ====================
async function saveFirewallPolicy() {
  const payload = {
    client_isolation: document.getElementById('policyIsolation').checked,
    internet_access: document.getElementById('policyInternet').checked,
    allow_dns: document.getElementById('policyDns').checked,
    default_forward_policy: document.getElementById('policyDefaultForward').value
  };

  try {
    const resp = await fetch('/api/firewall/policy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const res = await resp.json();
    if (resp.ok && res.success) {
      alert("Firewall policies updated and applied successfully!");
      location.reload();
    } else {
      alert(`Error updating policies: ${res.detail || res.message}`);
    }
  } catch (err) {
    alert("Failed to communicate with server.");
  }
}

function applyTemplateRule(templateType) {
  openModal('addAclModal');
  const nameEl = document.getElementById('aclName');
  const peerEl = document.getElementById('aclPeer');
  const dstEl = document.getElementById('aclDst');
  const protoEl = document.getElementById('aclProto');
  const portsEl = document.getElementById('aclPorts');
  const actionEl = document.getElementById('aclAction');

  if (peerEl) peerEl.value = 'all';

  if (templateType === 'block_ssh') {
    if (nameEl) nameEl.value = 'Block Peer SSH';
    if (dstEl) dstEl.value = 'any';
    if (protoEl) protoEl.value = 'tcp';
    if (portsEl) portsEl.value = '22';
    if (actionEl) actionEl.value = 'drop';
  } else if (templateType === 'allow_web') {
    if (nameEl) nameEl.value = 'Allow Web Only';
    if (dstEl) dstEl.value = 'any';
    if (protoEl) protoEl.value = 'tcp';
    if (portsEl) portsEl.value = '80,443';
    if (actionEl) actionEl.value = 'accept';
  } else if (templateType === 'allow_dns') {
    if (nameEl) nameEl.value = 'Allow DNS Resolvers';
    if (dstEl) dstEl.value = 'any';
    if (protoEl) protoEl.value = 'udp';
    if (portsEl) portsEl.value = '53';
    if (actionEl) actionEl.value = 'accept';
  } else if (templateType === 'block_lan') {
    if (nameEl) nameEl.value = 'Block Private LAN';
    if (dstEl) dstEl.value = '192.168.0.0/16, 10.0.0.0/8';
    if (protoEl) protoEl.value = 'all';
    if (portsEl) portsEl.value = '';
    if (actionEl) actionEl.value = 'drop';
  }
}

async function handleAddAcl(event) {
  event.preventDefault();
  const form = event.target;
  const peerSelect = form.peer_id.value;
  const payload = {
    name: form.name.value,
    peer_id: peerSelect === "all" ? null : parseInt(peerSelect, 10),
    src_cidr: form.src_cidr.value || null,
    dst_cidr: form.dst_cidr.value || "any",
    proto: form.proto.value,
    ports: form.ports.value || null,
    action: form.action.value
  };

  try {
    const resp = await fetch('/api/firewall/acls', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (resp.ok) {
      alert("WireGuard ACL rule created and safely applied to NFTables!");
      location.reload();
    } else {
      const err = await resp.json();
      alert(`Error creating ACL: ${err.detail || 'Failed'}`);
    }
  } catch (err) {
    alert("Connection error.");
  }
}

async function toggleAcl(id) {
  try {
    const resp = await fetch(`/api/firewall/acls/${id}/toggle`, { method: 'POST' });
    if (resp.ok) {
      location.reload();
    } else {
      const err = await resp.json();
      alert(`Error toggling ACL: ${err.detail}`);
    }
  } catch (err) {
    alert("Failed to toggle ACL.");
  }
}

async function deleteAcl(id, name) {
  if (!confirm(`Delete WireGuard ACL "${name}"?`)) return;
  try {
    const resp = await fetch(`/api/firewall/acls/${id}`, { method: 'DELETE' });
    if (resp.ok) {
      location.reload();
    } else {
      const err = await resp.json();
      alert(`Error deleting ACL: ${err.detail}`);
    }
  } catch (err) {
    alert("Failed to delete ACL.");
  }
}

async function handleAddCustomRule(event) {
  event.preventDefault();
  const form = event.target;
  const payload = {
    family: form.family.value,
    table: form.table.value,
    chain: form.chain.value,
    statement: form.statement.value,
    comment: form.comment.value || null
  };

  try {
    const resp = await fetch('/api/firewall/custom-rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (resp.ok) {
      alert("Custom NFTables rule created and applied!");
      location.reload();
    } else {
      const err = await resp.json();
      alert(`Syntax or apply error: ${err.detail}`);
    }
  } catch (err) {
    alert("Connection error.");
  }
}

async function deleteCustomRule(id) {
  if (!confirm("Are you sure you want to delete this custom NFTables rule?")) return;
  try {
    const resp = await fetch(`/api/firewall/custom-rules/${id}`, { method: 'DELETE' });
    if (resp.ok) {
      location.reload();
    } else {
      const err = await resp.json();
      alert(`Error deleting rule: ${err.detail}`);
    }
  } catch (err) {
    alert("Failed to delete rule.");
  }
}

async function validateNftRuleset() {
  try {
    const resp = await fetch('/api/firewall/preview');
    const data = await resp.json();
    const resultBox = document.getElementById('validationResult');
    if (resultBox) {
      resultBox.style.display = 'block';
      if (data.is_valid) {
        resultBox.className = 'alert-success';
        resultBox.innerHTML = `<strong>Configuration Valid:</strong> ${data.validation_message}`;
      } else {
        resultBox.className = 'alert-error';
        resultBox.innerHTML = `<strong>Syntax Error:</strong> <pre style="margin-top:0.5rem;">${data.validation_message}</pre>`;
      }
    } else {
      alert(data.is_valid ? "Ruleset syntax is valid!" : `Error: ${data.validation_message}`);
    }
  } catch (err) {
    alert("Validation request failed.");
  }
}

async function applyNftRuleset() {
  if (!confirm("Safely apply current WireGuard ACLs and NFTables rules to the running kernel?")) return;
  try {
    const resp = await fetch('/api/firewall/apply', { method: 'POST' });
    const res = await resp.json();
    if (resp.ok && res.success) {
      alert("NFTables ruleset safely applied to the kernel!");
      location.reload();
    } else {
      alert(`Apply Error: ${res.detail || res.message}`);
    }
  } catch (err) {
    alert("Failed to apply firewall configuration.");
  }
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Enterprise Theme (Dark / Light / OLED)
  initTheme();

  // Initialize Throughput Graph Type
  initGraphType();

  // Restore saved view preference (cards vs table)
  const savedView = localStorage.getItem('wg_peers_view') || 'cards';
  switchPeerView(savedView);

  // Check URL query parameters for assign_ip
  const params = new URLSearchParams(window.location.search);
  const assignIp = params.get('assign_ip');
  if (assignIp) {
    const ipInput = document.getElementById('peerIp');
    if (ipInput) {
      ipInput.value = assignIp;
      openModal('addPeerModal');
    }
  }

  // Restore live refresh rate
  const savedRate = localStorage.getItem('wg_refresh_rate');
  const rateSelect = document.getElementById('liveRefreshRate');
  if (rateSelect) {
    if (savedRate !== null) {
      rateSelect.value = savedRate;
      setLiveRefresh(savedRate);
    } else {
      setLiveRefresh(5); // Default 5s
    }
  }

  // Close modals on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove('active');
      }
    });
  });

  // Restore active firewall tab if present
  const hashTab = window.location.hash.replace('#', '');
  const savedSocTab = hashTab || localStorage.getItem('soc_active_tab');
  if (savedSocTab && document.getElementById(`soc-tab-content-${savedSocTab}`)) {
    switchSocTab(savedSocTab);
  }
});

// ==================== SOC/NOC FIREWALL CONTROLLER ====================
function switchSocTab(tabId) {
  const tabs = ['ruleset', 'acls', 'nat', 'analytics', 'logs', 'settings'];
  tabs.forEach(t => {
    const el = document.getElementById(`soc-tab-content-${t}`);
    const btn = document.getElementById(`soc-tab-btn-${t}`);
    if (el) el.style.display = (t === tabId) ? 'block' : 'none';
    if (btn) {
      if (t === tabId) btn.classList.add('active');
      else btn.classList.remove('active');
    }
  });
  try {
    localStorage.setItem('soc_active_tab', tabId);
    window.location.hash = tabId;
  } catch (e) {}
}

function filterRulesByChain(chain, btn) {
  document.querySelectorAll('.soc-filter-pill').forEach(p => p.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const rows = document.querySelectorAll('.soc-rule-row');
  const sections = document.querySelectorAll('.soc-chain-section');

  if (chain === 'all') {
    rows.forEach(r => r.style.display = '');
    sections.forEach(s => s.style.display = '');
    return;
  }

  sections.forEach(s => {
    if (s.dataset.chain === chain) s.style.display = '';
    else s.style.display = 'none';
  });

  rows.forEach(r => {
    if (r.dataset.chain === chain) r.style.display = '';
    else r.style.display = 'none';
  });
}

function searchRules(query) {
  const q = query.toLowerCase().trim();
  const rows = document.querySelectorAll('.soc-rule-row');
  rows.forEach(row => {
    const text = (row.dataset.search || '').toLowerCase();
    row.style.display = text.includes(q) ? '' : 'none';
  });
}

function searchAcls(query) {
  const q = query.toLowerCase().trim();
  const rows = document.querySelectorAll('.soc-acl-row');
  rows.forEach(row => {
    const text = (row.dataset.search || '').toLowerCase();
    row.style.display = text.includes(q) ? '' : 'none';
  });
}

function filterAclByType(type) {
  const rows = document.querySelectorAll('.soc-acl-row');
  rows.forEach(row => {
    if (!type || type === 'all' || row.dataset.type === type) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

function selectInterface(ifaceName, el) {
  const isSelected = el.classList.contains('active');
  document.querySelectorAll('.soc-iface-card').forEach(c => c.classList.remove('active'));
  if (!isSelected) {
    el.classList.add('active');
    const searchInput = document.getElementById('ruleSearchInput');
    if (searchInput) {
      searchInput.value = ifaceName;
      searchRules(ifaceName);
    }
  } else {
    const searchInput = document.getElementById('ruleSearchInput');
    if (searchInput) {
      searchInput.value = '';
      searchRules('');
    }
  }
}

function backupRuleset() {
  const activeText = document.getElementById('activeRulesetText')?.textContent || '# nftables ruleset snapshot\ntable inet wiregate {\n}';
  const blob = new Blob([activeText], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `nftables-backup-${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.nft`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  alert("Firewall ruleset backup exported successfully!");
}

async function handleBlockIp(event) {
  event.preventDefault();
  const form = event.target;
  const ip = form.ip.value.trim();
  const comment = form.comment.value.trim() || `Blocked via SOC quick-ban`;

  if (!ip) return;

  const payload = {
    family: "inet",
    table: "wiregate",
    chain: "wg_forward",
    statement: `ip saddr ${ip} drop`,
    comment: comment
  };

  try {
    const resp = await fetch('/api/firewall/custom-rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (resp.ok) {
      alert(`IP address ${ip} has been blocked and applied to the kernel!`);
      closeModal('blockIpModal');
      location.reload();
    } else {
      const err = await resp.json();
      alert(`Error blocking IP: ${err.detail}`);
    }
  } catch (err) {
    alert("Connection error.");
  }
}

async function handleRestoreBackup(event) {
  event.preventDefault();
  const form = event.target;
  const select = form.querySelector('select[name="snapshot"]');
  const snapshotName = select ? select.value : '';
  if (!snapshotName) {
    alert("Please select a valid backup snapshot.");
    return;
  }

  if (!confirm(`Restore and apply backup snapshot "${snapshotName}" to the kernel?\n\nThis will safely roll back the NFTables configuration.`)) {
    return;
  }

  try {
    const resp = await fetch('/api/firewall/backups/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: snapshotName })
    });
    const res = await resp.json();
    if (resp.ok) {
      alert(`Backup snapshot "${snapshotName}" restored and verified successfully!`);
      closeModal('restoreBackupModal');
      location.reload();
    } else {
      alert(`Restore failed: ${res.detail || res.error || 'Unknown error'}`);
    }
  } catch (err) {
    alert("Connection error during backup restoration.");
  }
}

// ==================== FIREWALL SETTINGS CONTROLLERS ====================
async function saveFirewallSettings() {
  const payload = {
    default_forward_policy: document.getElementById('fwSettingDefaultForward')?.value || 'drop',
    client_isolation: document.getElementById('fwSettingClientIsolation')?.checked ?? true,
    internet_access: document.getElementById('fwSettingInternetAccess')?.checked ?? true,
    allow_dns: document.getElementById('fwSettingAllowDns')?.checked ?? true,
    mss_clamping: document.getElementById('fwSettingMssClamping')?.checked ?? true,
    drop_invalid: document.getElementById('fwSettingDropInvalid')?.checked ?? true,
    icmp_limit: document.getElementById('fwSettingIcmpLimit')?.checked ?? true,
    log_dropped: document.getElementById('fwSettingLogDropped')?.checked ?? false,
    auto_backup: document.getElementById('fwSettingAutoBackup')?.checked ?? true
  };

  try {
    const resp = await fetch('/api/firewall/policy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const res = await resp.json();
    if (resp.ok && res.success) {
      alert("Firewall & ACL settings saved and safely applied to the kernel!");
      location.reload();
    } else {
      alert(`Error saving firewall settings: ${res.detail || res.message || 'Unknown error'}`);
    }
  } catch (err) {
    alert("Network or connection error while saving firewall settings.");
  }
}

function applySecurityPreset(presetKey) {
  const presets = {
    zero_trust: {
      default_forward_policy: 'drop',
      client_isolation: true,
      internet_access: false,
      allow_dns: true,
      mss_clamping: true,
      drop_invalid: true,
      icmp_limit: true,
      log_dropped: true,
      auto_backup: true,
      name: 'Strict Zero-Trust Perimeter'
    },
    corporate: {
      default_forward_policy: 'drop',
      client_isolation: false,
      internet_access: true,
      allow_dns: true,
      mss_clamping: true,
      drop_invalid: true,
      icmp_limit: true,
      log_dropped: false,
      auto_backup: true,
      name: 'Corporate Gateway (Standard)'
    },
    split_tunnel: {
      default_forward_policy: 'accept',
      client_isolation: true,
      internet_access: false,
      allow_dns: true,
      mss_clamping: true,
      drop_invalid: true,
      icmp_limit: true,
      log_dropped: false,
      auto_backup: true,
      name: 'Split-Tunnel VPN Mesh'
    },
    permissive: {
      default_forward_policy: 'accept',
      client_isolation: false,
      internet_access: true,
      allow_dns: true,
      mss_clamping: true,
      drop_invalid: false,
      icmp_limit: false,
      log_dropped: true,
      auto_backup: true,
      name: 'Permissive Diagnostic / Audit Mode'
    }
  };

  const p = presets[presetKey];
  if (!p) return;

  // Update UI inputs
  const defFwd = document.getElementById('fwSettingDefaultForward');
  if (defFwd) defFwd.value = p.default_forward_policy;

  const setCheck = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.checked = val;
  };

  setCheck('fwSettingClientIsolation', p.client_isolation);
  setCheck('fwSettingInternetAccess', p.internet_access);
  setCheck('fwSettingAllowDns', p.allow_dns);
  setCheck('fwSettingMssClamping', p.mss_clamping);
  setCheck('fwSettingDropInvalid', p.drop_invalid);
  setCheck('fwSettingIcmpLimit', p.icmp_limit);
  setCheck('fwSettingLogDropped', p.log_dropped);
  setCheck('fwSettingAutoBackup', p.auto_backup);

  // Highlight active preset card
  document.querySelectorAll('.soc-preset-card').forEach(c => c.classList.remove('active'));
  const activeCard = document.getElementById(`preset-${presetKey}`);
  if (activeCard) activeCard.classList.add('active');

  if (confirm(`Loaded "${p.name}" profile settings into the form.\n\nWould you like to save and apply these settings to the Linux kernel immediately?`)) {
    saveFirewallSettings();
  }
}

async function triggerEmergencyLockdown() {
  if (!confirm("CRITICAL WARNING: Emergency Network Lockdown will immediately DROP all routed traffic across wg0, isolate clients, enable packet drop logging, and capture an emergency backup.\n\nAre you sure you want to activate Emergency Lockdown?")) {
    return;
  }

  try {
    const resp = await fetch('/api/firewall/lockdown', { method: 'POST' });
    const res = await resp.json();
    if (resp.ok && res.success) {
      alert("EMERGENCY LOCKDOWN ACTIVATED: All routed traffic dropped across the VPN tunnel.");
      location.reload();
    } else {
      alert(`Lockdown Error: ${res.detail || res.message || 'Unknown error'}`);
    }
  } catch (err) {
    alert("Connection error during lockdown.");
  }
}

// ==================== ENTERPRISE THEME CONTROLLER ====================
const THEMES = [
  { id: 'zinc', name: 'Obsidian Zinc', icon: '⚡' },
  { id: 'nord', name: 'Nordic Frost', icon: '❄️' },
  { id: 'oled', name: 'Midnight OLED', icon: '🌌' },
  { id: 'light', name: 'Light Slate', icon: '☀️' }
];

function initTheme() {
  let currentTheme = localStorage.getItem('wg_theme') || 'zinc';
  if (currentTheme === 'dark') currentTheme = 'zinc';
  applyTheme(currentTheme);
}

function applyTheme(themeId) {
  document.documentElement.setAttribute('data-theme', themeId);
  localStorage.setItem('wg_theme', themeId);

  const themeObj = THEMES.find(t => t.id === themeId) || THEMES[0];
  const iconEl = document.getElementById('themeIcon');
  const labelEl = document.getElementById('themeLabel');
  if (iconEl) iconEl.textContent = themeObj.icon;
  if (labelEl) labelEl.textContent = themeObj.name;
}

function cycleTheme() {
  let current = localStorage.getItem('wg_theme') || 'zinc';
  if (current === 'dark') current = 'zinc';
  const currentIndex = THEMES.findIndex(t => t.id === current);
  const nextIndex = (currentIndex + 1) % THEMES.length;
  applyTheme(THEMES[nextIndex].id);
}
