let devices = [];
let channels = [];
let availableSites = new Set(['Headquarters', 'Remote Site']);

document.addEventListener('DOMContentLoaded', () => {
  fetchInitialData();
  setInterval(fetchDevices, 3000);
});

async function fetchInitialData() {
  await Promise.all([fetchAdminAuth(), fetchChannels(), fetchDevices(), fetchMedia(), fetchSystemStatus()]);
}

async function fetchAdminAuth() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated) {
        const badge = document.getElementById('admin-user-badge');
        if (badge) {
          badge.style.display = 'inline-flex';
          badge.textContent = `Admin: ${data.user}`;
        }
      }
    }
  } catch (e) {}
}

async function fetchSystemStatus() {
  try {
    const res = await fetch('/api/system/status');
    const data = await res.json();
    document.getElementById('connected-count').textContent = `${data.connectedTVs} TVs Connected`;

    const alertBox = document.getElementById('active-alert-box');
    const alertText = document.getElementById('active-alert-text');
    if (data.activeAlert) {
      alertBox.style.display = 'block';
      alertText.textContent = `${data.activeAlert.message} (Triggered ${new Date(data.activeAlert.timestamp).toLocaleTimeString()})`;
    } else {
      alertBox.style.display = 'none';
    }
  } catch (err) {
    console.error('Error fetching system status:', err);
  }
}

async function fetchChannels() {
  try {
    const res = await fetch('/api/channels');
    const data = await res.json();
    channels = data.channels || [];
    renderChannels();
  } catch (err) {
    console.error('Error fetching channels:', err);
  }
}

// Security Sanitization Helpers (OWASP XSS Mitigation)
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function sanitizeAttr(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/[^a-zA-Z0-9_-]/g, '');
}

function renderChannels() {
  const container = document.getElementById('channels-list');
  container.innerHTML = channels.map(ch => {
    let iconSvg = '';
    let badgeClass = 'badge-blue';
    if (ch.type === 'webrtc') {
      badgeClass = 'badge-green';
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" stroke-width="2"><circle cx="12" cy="12" r="2"></circle><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"></path></svg>`;
    } else if (ch.type === 'url') {
      badgeClass = 'badge-blue';
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>`;
    } else {
      badgeClass = 'badge-cyan';
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`;
    }

    return `
    <div style="background: rgba(5, 8, 15, 0.6); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; gap: 12px; transition: border-color 0.2s ease;">
      <div style="display: flex; align-items: center; gap: 12px; min-width: 0;">
        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(255,255,255,0.04); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
          ${iconSvg}
        </div>
        <div style="min-width: 0;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <strong style="font-size: 14px; color: #ffffff;">${escapeHtml(ch.name)}</strong>
            <span class="badge ${badgeClass}" style="font-size: 10px; padding: 1px 6px;">${escapeHtml(ch.type).toUpperCase()}</span>
          </div>
          <div style="font-size: 11.5px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;">
            ${escapeHtml(ch.description || '')}
          </div>
        </div>
      </div>
      <button onclick="broadcastGlobalChannel('${sanitizeAttr(ch.id)}')" class="btn btn-secondary btn-sm" style="font-size: 11px; padding: 4px 10px; flex-shrink: 0;" title="Switch all TVs to this channel">
        Push to All
      </button>
    </div>
  `;
  }).join('');
}

async function fetchDevices() {
  try {
    const res = await fetch('/api/devices');
    const data = await res.json();
    devices = data.devices || [];

    // Collect all unique site tags
    devices.forEach(d => {
      if (d.site) availableSites.add(d.site);
    });
    updateSiteFilterDropdown();

    // Update KPI Telemetry Bar
    const onlineCount = devices.filter(d => d.online).length;
    const totalCount = devices.length;
    const kpiOnline = document.getElementById('kpi-online-tvs');
    if (kpiOnline) {
      kpiOnline.textContent = `${onlineCount} / ${totalCount} Online`;
    }

    const kpiMode = document.getElementById('kpi-broadcast-mode');
    if (kpiMode) {
      const hasLive = devices.some(d => d.online && d.currentChannel === 'ch-live');
      kpiMode.textContent = hasLive ? 'WebRTC Live Stream' : 'Signage Video Loop';
    }

    renderDevices();
    fetchSystemStatus();
  } catch (err) {
    console.error('Error fetching devices:', err);
  }
}

function updateSiteFilterDropdown() {
  const filter = document.getElementById('site-filter');
  const currentVal = filter.value;
  let optionsHtml = `<option value="all">All Sites (Headquarters + Remote)</option>`;

  availableSites.forEach(site => {
    const escapedSite = escapeHtml(site);
    optionsHtml += `<option value="${escapedSite}" ${currentVal === site ? 'selected' : ''}>Site: ${escapedSite}</option>`;
  });
  filter.innerHTML = optionsHtml;
}

let currentGridDensity = localStorage.getItem('tv_grid_density') || 'default';

function applyGridDensity() {
  const grid = document.getElementById('device-grid');
  const btnDefault = document.getElementById('btn-density-default');
  const btnCompact = document.getElementById('btn-density-compact');

  if (grid) {
    if (currentGridDensity === 'compact') {
      grid.classList.add('compact-view');
      if (btnDefault) btnDefault.classList.remove('active');
      if (btnCompact) btnCompact.classList.add('active');
    } else {
      grid.classList.remove('compact-view');
      if (btnDefault) btnDefault.classList.add('active');
      if (btnCompact) btnCompact.classList.remove('active');
    }
  }
}

function setGridDensity(mode) {
  currentGridDensity = mode;
  localStorage.setItem('tv_grid_density', mode);
  applyGridDensity();
}

function formatCleanVideoName(filename) {
  if (!filename) return '';
  let clean = filename.replace(/^\d{10,14}_/, '');
  clean = clean.replace(/_/g, ' ');
  return clean;
}

function renderDevices() {
  const grid = document.getElementById('device-grid');
  const siteFilter = document.getElementById('site-filter').value;

  const filtered = devices.filter(d => siteFilter === 'all' || d.site === siteFilter);

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="card" style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
        No TV displays connected in this location yet.<br>
        <small>Open <code>http://&lt;SERVER_IP&gt;:8080/player.html</code> on a Raspberry Pi or Laptop connected to a TV.</small>
      </div>
    `;
    applyGridDensity();
    return;
  }

  grid.innerHTML = filtered.map(dev => {
    const safeId = sanitizeAttr(dev.id);
    const safeName = escapeHtml(dev.name);
    const safeSite = escapeHtml(dev.site);
    const safeIp = escapeHtml(dev.ip || 'Unknown');
    const chObj = channels.find(c => c.id === dev.currentChannel);
    const safeChName = escapeHtml(chObj ? chObj.name : dev.currentChannel);
    const safeLastSeen = escapeHtml(new Date(dev.lastSeen).toLocaleTimeString());

    let previewContent = '';
    if (!dev.online) {
      previewContent = `
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 6px; padding: 6px 8px; width: 100%;">
          <div style="font-weight: 600; font-size: 12px; color: #f87171;">Display Offline</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Channel: ${safeChName}</div>
        </div>
      `;
    } else if (dev.currentChannel === 'ch-live') {
      previewContent = `
        <div style="background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 6px; padding: 6px 8px; width: 100%;">
          <div style="font-weight: 700; font-size: 12px; color: #4ade80; display: flex; align-items: center; justify-content: center; gap: 6px;">
            <span style="width: 7px; height: 7px; border-radius: 50%; background: #4ade80; display: inline-block;"></span>
            Live Stream Feed
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">WebRTC Low Latency</div>
        </div>
      `;
    } else if (dev.currentChannel === 'ch-dashboard') {
      previewContent = `
        <div style="background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 6px; padding: 6px 8px; width: 100%;">
          <div style="font-weight: 700; font-size: 12px; color: #60a5fa;">Interactive Web Dashboard</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">URL Kiosk Mode</div>
        </div>
      `;
    } else {
      // ch-signage
      const hasVideo = !!dev.currentVideo;
      const cleanTitle = hasVideo ? escapeHtml(formatCleanVideoName(dev.currentVideo)) : null;
      const fullFilename = hasVideo ? escapeHtml(dev.currentVideo) : '';
      const videoNum = (typeof dev.currentVideoIndex === 'number' && dev.currentVideoIndex >= 0) ? (dev.currentVideoIndex + 1) : null;
      const totalVids = dev.totalVideos || null;

      if (hasVideo) {
        previewContent = `
          <div class="video-playing-indicator" style="background: rgba(6, 182, 212, 0.12); border: 1px solid rgba(6, 182, 212, 0.35); border-radius: 6px; padding: 6px 8px; width: 100%; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);" title="${fullFilename}">
            <div style="font-weight: 700; font-size: 11px; color: var(--accent-cyan); display: flex; align-items: center; justify-content: center; gap: 5px; text-transform: uppercase; letter-spacing: 0.5px;">
              <span class="equalizer">
                <span class="equalizer-bar"></span>
                <span class="equalizer-bar"></span>
                <span class="equalizer-bar"></span>
                <span class="equalizer-bar"></span>
              </span>
              Video ${videoNum ? videoNum : 1}${totalVids ? ' of ' + totalVids : ''}
            </div>
            <div style="font-weight: 600; font-size: 12px; color: #ffffff; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-shadow: 0 1px 4px rgba(0,0,0,0.8);">
              ${cleanTitle}
            </div>
          </div>
          <div class="preview-channel-name" style="font-size: 11px; color: var(--text-muted); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${safeChName}
          </div>
        `;
      } else {
        previewContent = `
          <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 8px; width: 100%;">
            <div class="preview-channel-name" style="font-weight: 600; font-size: 12px; color: #ffffff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${safeChName}
            </div>
            <div style="font-size: 11px; color: var(--accent-cyan); margin-top: 2px;">
              Digital Signage Playback
            </div>
          </div>
        `;
      }
    }

    return `
    <div class="tv-card" id="card-${safeId}">
      <!-- Card Top: Status, IP Pill, Quick Actions -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 6px; min-width: 0;">
          <span class="badge ${dev.online ? 'badge-green badge-pulse' : 'badge-red'} tv-status-badge" style="font-size: 10px; padding: 2px 7px;">
            ${dev.online ? 'ONLINE' : 'OFFLINE'}
          </span>
          <span class="tv-ip-badge" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle); padding: 2px 6px; border-radius: 4px;">
            ${safeIp}
          </span>
        </div>
        <div style="display: flex; gap: 5px; align-items: center; flex-shrink: 0;">
          <button onclick="reloadDevice('${safeId}')" class="btn btn-secondary btn-sm btn-reload-tv" title="Reload TV display browser" style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); padding: 2px 8px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path></svg>
            <span class="btn-reload-label">Reload</span>
          </button>
          <button onclick="removeDevice('${safeId}', '${safeName}')" class="btn-delete-tv" title="Delete TV display from dashboard" style="padding: 3px 6px; display: inline-flex; align-items: center; justify-content: center;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      </div>

      <!-- TV Identity: Full width name & site -->
      <div style="margin-bottom: 8px;">
        <div class="tv-title" onclick="editDeviceDetails('${safeId}')" style="cursor: pointer; font-size: 15px; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 6px;" title="Click to rename display">
          <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 90%;">${safeName}</span>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2" style="opacity: 0.6; flex-shrink: 0;"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
        </div>
        <div class="tv-meta" style="font-size: 11.5px; color: var(--text-muted); margin-top: 2px;">
          Location: <strong style="color: var(--text-secondary);">${safeSite}</strong>
          <span class="tv-compact-ip" style="display: none; font-family: var(--font-mono); color: var(--text-muted);"> &bull; ${safeIp}</span>
        </div>
      </div>

      <!-- Monitor Preview Bezel Box -->
      <div class="tv-preview-box">
        <div style="text-align: center; width: 100%; padding: 6px 10px; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%;">
          <div class="preview-status-label" style="font-size: 9.5px; text-transform: uppercase; letter-spacing: 1.2px; color: var(--accent-cyan); font-weight: 700; margin-bottom: 5px;">Currently Playing</div>
          ${previewContent}
          <div class="preview-last-seen" style="font-size: 10px; color: var(--text-muted); margin-top: 5px;">
            Last Seen: ${safeLastSeen}
          </div>
        </div>
      </div>

      <!-- Channel Output Select -->
      <div class="tv-channel-select" style="margin-top: auto; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.06);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <label style="font-size: 11px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Assign Channel:</label>
          <span style="font-size: 10px; color: var(--accent-cyan); font-family: var(--font-mono);">Active</span>
        </div>
        <select class="select" onchange="switchDeviceChannel('${safeId}', this.value)" style="cursor: pointer;">
          ${channels.map(ch => `
            <option value="${sanitizeAttr(ch.id)}" ${ch.id === dev.currentChannel ? 'selected' : ''}>
              ${escapeHtml(ch.name)}
            </option>
          `).join('')}
        </select>
      </div>
    </div>
  `;
  }).join('');

  applyGridDensity();
}

async function reloadDevice(deviceId) {
  try {
    const res = await fetch(`/api/devices/${deviceId}/reload`, { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      fetchDevices();
    } else {
      alert('Could not reload TV: ' + (data.error || 'Server error'));
    }
  } catch (err) {
    alert('Error sending reload signal: ' + err.message);
  }
}

async function reloadAllDevices() {
  if (!confirm('Reload all active TV screens? Displays will refresh their playback session.')) return;
  try {
    const res = await fetch('/api/devices/reload-all', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      alert(`Reload signal sent to ${data.count || 0} active TV displays.`);
      fetchDevices();
    }
  } catch (err) {
    alert('Error reloading TVs: ' + err.message);
  }
}

async function removeDevice(deviceId, deviceName) {
  if (!confirm(`Are you sure you want to remove "${deviceName}" from the display console?`)) return;
  try {
    const res = await fetch(`/api/devices/${deviceId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok && data.success) {
      fetchDevices();
    } else {
      alert('Failed to remove TV: ' + (data.error || 'Server error'));
    }
  } catch (err) {
    alert('Error removing TV: ' + err.message);
  }
}

async function pruneOfflineDevices() {
  if (!confirm('Are you sure you want to remove all offline or disconnected TV records? Active/online TVs will remain untouched.')) return;
  try {
    const res = await fetch('/api/devices/prune-offline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert(`Cleared ${data.prunedCount} offline TV display(s) from console.`);
      fetchDevices();
    } else {
      alert('Failed to clear offline devices: ' + (data.error || 'Server error'));
    }
  } catch (err) {
    alert('Error clearing offline devices: ' + err.message);
  }
}

async function switchDeviceChannel(deviceId, channelId) {
  try {
    await fetch(`/api/devices/${deviceId}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ currentChannel: channelId })
    });
    fetchDevices();
  } catch (err) {
    alert('Failed to switch channel: ' + err.message);
  }
}

async function broadcastGlobalChannel(channelId) {
  const siteFilter = document.getElementById('site-filter').value;
  const targetDesc = siteFilter === 'all' ? 'ALL TVs across ALL sites' : `all TVs in ${siteFilter}`;

  if (!confirm(`Are you sure you want to switch ${targetDesc} to this channel?`)) return;

  try {
    const res = await fetch('/api/broadcast/channel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        channelId,
        target: siteFilter === 'all' ? 'all' : 'site',
        site: siteFilter === 'all' ? null : siteFilter
      })
    });
    const result = await res.json();
    alert(`Successfully broadcast to ${result.updatedCount} active TV screen(s)!`);
    fetchDevices();
  } catch (err) {
    alert('Failed to broadcast channel: ' + err.message);
  }
}

async function editDeviceDetails(deviceId) {
  const dev = devices.find(d => d.id === deviceId);
  if (!dev) return;

  const newName = prompt('Enter friendly name for this TV display:', dev.name);
  if (!newName) return;

  const newSite = prompt('Enter Site/Location (e.g., Headquarters, Remote Site, Branch 2):', dev.site);
  if (!newSite) return;

  await fetch(`/api/devices/${deviceId}/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newName, site: newSite })
  });
  fetchDevices();
}

async function promptEmergencyAlert() {
  const msg = prompt('ENTER EMERGENCY ALERT MESSAGE (Displays in bold red banner across all TVs):', 'Fire Alarm Drill in progress. Please assemble at evacuation zone.');
  if (!msg) return;

  try {
    await fetch('/api/broadcast/alert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, severity: 'critical' })
    });
    fetchSystemStatus();
    alert('Emergency alert broadcasted to all screens!');
  } catch (err) {
    alert('Failed to trigger alert: ' + err.message);
  }
}

async function clearEmergencyAlert() {
  try {
    await fetch('/api/broadcast/clear-alert', { method: 'POST' });
    fetchSystemStatus();
    alert('Alert cleared from all TV displays.');
  } catch (err) {
    alert('Failed to clear alert: ' + err.message);
  }
}

async function fetchMedia() {
  try {
    const res = await fetch('/api/media');
    const data = await res.json();
    const list = document.getElementById('media-files-list');
    const badge = document.getElementById('playlist-badge');

    const media = data.media || [];
    const videos = media.filter(m => {
      const fn = m.filename.toLowerCase();
      return fn.endsWith('.mp4') || fn.endsWith('.webm') || fn.endsWith('.mkv') || fn.endsWith('.mov') || fn.endsWith('.m4v');
    });

    if (badge) {
      badge.textContent = `${videos.length} Video(s) in Loop`;
    }

    const kpiMedia = document.getElementById('kpi-media-count');
    if (kpiMedia) {
      const totalMb = (media.reduce((acc, m) => acc + (m.size || 0), 0) / (1024 * 1024)).toFixed(0);
      kpiMedia.textContent = `${videos.length} Videos (${totalMb} MB)`;
    }

    if (media.length === 0) {
      list.innerHTML = `<div style="font-size: 13px; color: var(--text-muted); text-align: center; padding: 20px;">No video files in continuous loop. Upload MP4/WebM videos above to start the 24/7 TV loop.</div>`;
      return;
    }

    list.innerHTML = media.map((m, idx) => {
      const safeFilename = escapeHtml(m.filename);
      const encodedFn = encodeURIComponent(m.filename);
      const cleanTitle = escapeHtml(formatCleanVideoName(m.filename));

      return `
      <div style="font-size: 12.5px; padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); display: flex; justify-content: space-between; align-items: center; background: ${idx % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent'}; border-radius: 6px; margin-bottom: 3px;">
        <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 55%; display: flex; align-items: center; gap: 8px;">
          <span style="font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); font-weight: 700; background: rgba(6, 182, 212, 0.12); padding: 2px 6px; border-radius: 4px;">#${idx + 1}</span>
          <span title="${safeFilename}" style="color: #ffffff; font-weight: 500;">${cleanTitle}</span>
        </div>
        <div style="display: flex; gap: 6px; align-items: center; flex-shrink: 0;">
          <span style="font-family: var(--font-mono); color: var(--text-muted); font-size: 11px; margin-right: 4px;">${(m.size / (1024*1024)).toFixed(1)} MB</span>
          <button onclick="syncAllTvsToVideo(${idx})" class="btn btn-secondary btn-sm" style="padding: 2px 7px; font-size: 11px; color: var(--accent-cyan); border-color: rgba(6, 182, 212, 0.3);" title="Sync all connected TVs to start playing this video">
            Play All
          </button>
          <button onclick="deleteMediaFile('${encodedFn}')" class="btn btn-secondary btn-sm" style="color: #f87171; border-color: rgba(239, 68, 68, 0.3); padding: 2px 7px; font-size: 11px;" title="Remove from loop">
            Delete
          </button>
        </div>
      </div>
    `;
    }).join('');
  } catch (err) {
    console.error('Error fetching media:', err);
  }
}

async function deleteMediaFile(encodedFilename) {
  if (!confirm('Are you sure you want to remove this video from the continuous loop?')) return;
  try {
    const res = await fetch(`/api/media/${encodedFilename}`, { method: 'DELETE' });
    if (res.ok) {
      fetchMedia();
    } else {
      alert('Failed to delete media file');
    }
  } catch (err) {
    alert('Error deleting file: ' + err.message);
  }
}

async function uploadMediaFiles() {
  const input = document.getElementById('media-upload-input');
  const btn = document.getElementById('btn-upload-media');
  if (!input.files || input.files.length === 0) {
    alert('Please select one or more video files to upload.');
    return;
  }

  const formData = new FormData();
  for (let i = 0; i < input.files.length; i++) {
    formData.append('files', input.files[i]);
  }

  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Uploading...';
  }

  try {
    const res = await fetch('/api/upload-media', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    alert(`Successfully uploaded ${data.uploaded.length} video(s)! All TVs will now loop them continuously.`);
    input.value = '';
    fetchMedia();
  } catch (err) {
    alert('Upload failed: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Upload Videos';
    }
  }
}

async function syncAllTvsToVideo(idx = 0) {
  try {
    const res = await fetch('/api/broadcast/sync-video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index: idx })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || `HTTP error ${res.status}`);
    }
    await fetchDevices();
    alert(`Synchronized all connected TV displays to video #${data.masterVideoIndex + 1}!`);
  } catch (err) {
    alert('Failed to sync video: ' + err.message);
  }
}

async function handleLogout() {
  if (confirm('Are you sure you want to sign out?')) {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {}
    localStorage.removeItem('tv_auth_token');
    window.location.href = '/login.html';
  }
}

async function runNetworkTvDetection() {
  const btn = document.getElementById('btn-detect-tvs');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Scanning Subnet...';
  }

  try {
    const res = await fetch('/api/tools/detect-tvs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();

    if (res.ok && data.success) {
      if (data.detectedCount === 0) {
        alert('Network Scan Complete: No Smart TVs detected on this subnet. Ensure TVs are powered ON and connected to the same Wi-Fi or LAN.');
      } else {
        const list = (data.results || []).map(r => `${r.name} (${r.ip}): ${r.status}`).join('\n');
        alert(`Discovered & Processed ${data.detectedCount} Smart TV(s):\n\n${list}\n\nDisplays are now launched.`);
        fetchDevices();
      }
    } else {
      alert('Network scan error: ' + (data.error || 'Server error'));
    }
  } catch (err) {
    alert('Failed to run network detection: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Scan & Auto-Connect Network TVs';
    }
  }
}
