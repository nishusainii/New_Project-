let localStream = null;
let peerConnection = null;
let isBroadcasting = false;
let selectedTarget = 'all';
let captureSource = 'screen'; // 'screen' or 'camera'
let presenterWakeLock = null;

const videoEl = document.getElementById('preview-video');
const noSignalPlaceholder = document.getElementById('no-signal-placeholder');
const onAirBadge = document.getElementById('on-air-badge');
const btnBroadcast = document.getElementById('btn-broadcast');
const streamStatusText = document.getElementById('stream-status-text');

async function acquirePresenterWakeLock() {
  try {
    if ('wakeLock' in navigator && !presenterWakeLock) {
      presenterWakeLock = await navigator.wakeLock.request('screen');
      presenterWakeLock.addEventListener('release', () => {
        presenterWakeLock = null;
      });
      console.log('[Presenter] Screen WakeLock acquired - screen lock is now disabled while broadcasting.');
    }
  } catch (err) {
    console.warn('[Presenter] WakeLock not available:', err.message);
  }
}

async function releasePresenterWakeLock() {
  try {
    if (presenterWakeLock) {
      await presenterWakeLock.release();
      presenterWakeLock = null;
      console.log('[Presenter] Screen WakeLock released.');
    }
  } catch (err) {}
}

async function startScreenCapture() {
  captureSource = 'screen';
  try {
    if (localStream) {
      localStream.getTracks().forEach(t => t.stop());
    }

    try {
      localStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          cursor: 'always',
          frameRate: { ideal: 30, max: 30 },
          width: { ideal: 1920, max: 1920 },
          height: { ideal: 1080, max: 1080 }
        },
        audio: true
      });
    } catch (audioErr) {
      console.warn('Audio capture not available, capturing video only:', audioErr);
      localStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          cursor: 'always',
          frameRate: { ideal: 30, max: 60 },
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        },
        audio: false
      });
    }

    handleStreamAttached('Screen Share Active');
  } catch (err) {
    if (err.name !== 'NotAllowedError') {
      alert('Error accessing screen: ' + err.message);
    }
  }
}

async function startCameraCapture() {
  captureSource = 'camera';
  try {
    if (localStream) {
      localStream.getTracks().forEach(t => t.stop());
    }

    localStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: true
    });

    handleStreamAttached('Camera & Mic Active');
  } catch (err) {
    alert('Error accessing camera: ' + err.message);
  }
}

function handleStreamAttached(label) {
  videoEl.srcObject = localStream;
  noSignalPlaceholder.style.display = 'none';
  btnBroadcast.disabled = false;
  streamStatusText.textContent = label;
  streamStatusText.style.color = 'var(--accent-cyan)';

  // If the OS forcibly ends the stream (screen lock, Win+L, etc.) or browser Stop Sharing pill
  localStream.getVideoTracks()[0].onended = () => {
    if (isBroadcasting && captureSource === 'screen') {
      // Screen lock killed the capture - immediately try to restart the screen capture
      // The screen is locked so getDisplayMedia will be queued and will fire once unlocked
      console.warn('[Presenter] Screen capture ended (screen lock or Stop Sharing). TVs held in standby. Re-launch capture when screen is unlocked.');
      streamStatusText.textContent = 'Screen locked - unlock to resume capture';
      streamStatusText.style.color = 'var(--accent-orange)';
      // Clean up old local stream; do NOT call stopBroadcast so TVs stay in ch-live
      if (localStream) {
        localStream.getTracks().forEach(t => t.stop());
        localStream = null;
      }
      videoEl.srcObject = null;
      btnBroadcast.disabled = false;
      btnBroadcast.textContent = 'Restart Screen Share';
      return;
    }
    if (isBroadcasting) {
      stopBroadcast();
    }
    stopLocalStream();
  };
}

function stopLocalStream() {
  if (localStream) {
    localStream.getTracks().forEach(t => t.stop());
    localStream = null;
  }
  videoEl.srcObject = null;
  noSignalPlaceholder.style.display = 'block';
  btnBroadcast.disabled = true;
  streamStatusText.textContent = 'Idle';
  streamStatusText.style.color = 'var(--text-muted)';
}

function updateTargetSelection() {
  const radios = document.getElementsByName('broadcast-target');
  for (const r of radios) {
    if (r.checked) {
      selectedTarget = r.value;
      break;
    }
  }
}

async function toggleBroadcast() {
  if (!isBroadcasting) {
    await startBroadcast();
  } else {
    await stopBroadcast();
  }
}

async function startBroadcast() {
  if (!localStream) return;

  btnBroadcast.disabled = true;
  btnBroadcast.textContent = '⏳ Connecting...';

  try {
    // 1. Determine WHIP URL (prefer same-origin proxy to eliminate mixed-content blocks)
    let whipUrl = '/webrtc/live/whip';
    const directWhipUrl = `http://${window.location.hostname}:8889/live/whip`;

    // 2. Setup WebRTC PeerConnection for WHIP ingest with STUN
    peerConnection = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
      ]
    });

    let whipSessionUrl = null;
    const queuedCandidates = [];

    const sendCandidate = (cand) => {
      if (!cand || !whipSessionUrl) return;
      fetch(whipSessionUrl, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/trickle-ice-sdpfrag' },
        body: `a=${cand.candidate}\r\n`
      }).catch(e => console.warn('[WHIP] Trickle ICE error:', e));
    };

    peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        if (whipSessionUrl) {
          sendCandidate(event.candidate);
        } else {
          queuedCandidates.push(event.candidate);
        }
      }
    };

    peerConnection.onconnectionstatechange = () => {
      console.log('[WebRTC Presenter] Connection state:', peerConnection.connectionState);
      if (peerConnection.connectionState === 'connected') {
        streamStatusText.textContent = 'Broadcasting Live to TVs';
        streamStatusText.style.color = 'var(--accent-green)';
      }
    };

    localStream.getTracks().forEach(track => {
      peerConnection.addTrack(track, localStream);
    });

    // Prioritize H.264 codec for Smart TV (LG WebOS) hardware decoder compatibility
    if ('RTCRtpSender' in window && 'getCapabilities' in RTCRtpSender) {
      try {
        const capabilities = RTCRtpSender.getCapabilities('video');
        if (capabilities && capabilities.codecs) {
          const h264Codecs = capabilities.codecs.filter(c => c.mimeType && c.mimeType.toLowerCase() === 'video/h264');
          const otherCodecs = capabilities.codecs.filter(c => !c.mimeType || c.mimeType.toLowerCase() !== 'video/h264');
          const sortedCodecs = [...h264Codecs, ...otherCodecs];
          for (const transceiver of peerConnection.getTransceivers()) {
            if (transceiver.sender && transceiver.sender.track && transceiver.sender.track.kind === 'video' && 'setCodecPreferences' in transceiver) {
              transceiver.setCodecPreferences(sortedCodecs);
              console.log('[WHIP] Prioritized H.264 video codec for Smart TV compatibility.');
            }
          }
        }
      } catch (codecErr) {
        console.warn('[WHIP] Could not apply codec preferences:', codecErr);
      }
    }

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    // Wait for initial ICE candidates (up to 800ms)
    await new Promise(resolve => {
      if (peerConnection.iceGatheringState === 'complete') {
        resolve();
      } else {
        const checkState = () => {
          if (peerConnection.iceGatheringState === 'complete') {
            peerConnection.removeEventListener('icegatheringstatechange', checkState);
            resolve();
          }
        };
        peerConnection.addEventListener('icegatheringstatechange', checkState);
        setTimeout(resolve, 800);
      }
    });

    // 3. Send SDP Offer to MediaMTX WHIP endpoint (try proxy first, then direct)
    let whipResponse = null;
    try {
      whipResponse = await fetch(whipUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: peerConnection.localDescription.sdp
      });
    } catch (e) {
      console.warn('[WHIP] Same-origin proxy failed, attempting direct port 8889...', e);
      try {
        whipResponse = await fetch(directWhipUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: peerConnection.localDescription.sdp
        });
      } catch (err2) {
        throw new Error('Streaming server is unreachable on both proxy and direct port 8889.');
      }
    }

    if (!whipResponse || !whipResponse.ok) {
      const errText = whipResponse ? await whipResponse.text() : 'No response';
      throw new Error(`MediaMTX WHIP publish rejected (${whipResponse ? whipResponse.status : 'error'}): ${errText}`);
    }

    whipSessionUrl = whipResponse.headers.get('Location') || whipUrl;
    if (whipSessionUrl.startsWith('/live') && !whipSessionUrl.startsWith('/webrtc')) {
      whipSessionUrl = '/webrtc' + whipSessionUrl;
    }

    // Flush any ICE candidates gathered during the offer exchange
    while (queuedCandidates.length > 0) {
      sendCandidate(queuedCandidates.shift());
    }

    const answerSdp = await whipResponse.text();
    await peerConnection.setRemoteDescription(new RTCSessionDescription({
      type: 'answer',
      sdp: answerSdp
    }));
    console.log('[WHIP] WebRTC broadcast connected successfully to MediaMTX!');

    // 4. Trigger Automatic TV Takeover via Central Server API
    const targetPayload = {
      channelId: 'ch-live',
      target: selectedTarget === 'all' ? 'all' : 'site',
      site: selectedTarget === 'HQ' ? 'Headquarters' : (selectedTarget === 'Remote' ? 'Remote Site' : null)
    };

    const bRes = await fetch('/api/broadcast/channel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(targetPayload)
    });
    const bData = await bRes.json();

    // 5. Update UI state
    isBroadcasting = true;
    onAirBadge.style.display = 'inline-flex';
    btnBroadcast.disabled = false;
    btnBroadcast.textContent = 'Stop Broadcast (Return TVs to Normal)';
    btnBroadcast.classList.remove('btn-primary');
    btnBroadcast.classList.add('btn-danger');

    streamStatusText.textContent = `Broadcasting Live to ${bData.updatedCount || 0} TV(s)`;
    streamStatusText.style.color = 'var(--accent-red)';
    document.getElementById('tvs-receiving-count').textContent = bData.updatedCount || 0;

    // Acquire WakeLock to prevent screen lock from killing the capture (Win+L, idle timeout)
    await acquirePresenterWakeLock();

  } catch (err) {
    console.error('Broadcast failed:', err);
    alert('Failed to start broadcast: ' + err.message);
    btnBroadcast.disabled = false;
    btnBroadcast.textContent = 'Start Live Broadcast';
  }
}

async function stopBroadcast() {
  btnBroadcast.disabled = true;
  btnBroadcast.textContent = 'Stopping...';

  try {
    // 1. Tell all TVs to automatically return to normal digital signage
    await fetch('/api/broadcast/channel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        channelId: 'ch-signage',
        target: selectedTarget === 'all' ? 'all' : 'site',
        site: selectedTarget === 'HQ' ? 'Headquarters' : (selectedTarget === 'Remote' ? 'Remote Site' : null)
      })
    });

    // 2. Close peer connection
    if (peerConnection) {
      peerConnection.close();
      peerConnection = null;
    }

    isBroadcasting = false;
    onAirBadge.style.display = 'none';
    btnBroadcast.disabled = false;
    btnBroadcast.textContent = 'Start Live Broadcast';
    btnBroadcast.classList.remove('btn-danger');
    btnBroadcast.classList.add('btn-primary');

    await releasePresenterWakeLock();
    streamStatusText.textContent = 'Stream Stopped (TVs reverted to Signage)';
    streamStatusText.style.color = 'var(--text-muted)';
  } catch (err) {
    alert('Error stopping broadcast: ' + err.message);
  }
}

async function handleLogout() {
  if (confirm('Are you sure you want to sign out?')) {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {}
    localStorage.removeItem('tv_auth_token');
    localStorage.removeItem('tv_user');
    window.location.href = '/login.html';
  }
}

// --- User Role & Media Library Management ---
let currentUser = null;
let mediaFiles = [];

document.addEventListener('DOMContentLoaded', () => {
  initPresenterUser();
  fetchMedia();
  setInterval(fetchMedia, 10000);
});

async function initPresenterUser() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated) {
        currentUser = data;
        const userBadge = document.getElementById('user-badge');
        const navAdmin = document.getElementById('nav-admin');
        if (userBadge) {
          userBadge.style.display = 'inline-flex';
          const roleLabel = data.role === 'admin' ? 'Admin' : 'Streamer';
          userBadge.textContent = `${roleLabel}: ${data.user}`;
          if (data.role === 'streamer') {
            userBadge.style.background = 'rgba(6, 182, 212, 0.2)';
            userBadge.style.color = '#38bdf8';
            userBadge.style.border = '1px solid rgba(6, 182, 212, 0.4)';
            if (navAdmin) navAdmin.style.display = 'none';
          } else {
            userBadge.style.background = 'rgba(16, 185, 129, 0.2)';
            userBadge.style.color = '#34d399';
            userBadge.style.border = '1px solid rgba(16, 185, 129, 0.4)';
          }
        }
      }
    }
  } catch (e) {
    console.warn('Could not retrieve user info:', e);
  }
}

async function fetchMedia() {
  try {
    const res = await fetch('/api/media');
    if (!res.ok) return;
    const data = await res.json();
    mediaFiles = data.media || [];
    renderMediaList();
  } catch (err) {
    console.error('Error fetching media playlist:', err);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function renderMediaList() {
  const container = document.getElementById('media-files-list');
  const badge = document.getElementById('playlist-badge');
  if (badge) {
    badge.textContent = `${mediaFiles.length} Video${mediaFiles.length === 1 ? '' : 's'} in Loop`;
  }
  if (!container) return;

  if (mediaFiles.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 24px; color: var(--text-muted); font-size: 13px;">
        No videos in the signage loop. Upload a video above to begin automated 24/7 signage.
      </div>
    `;
    return;
  }

  container.innerHTML = mediaFiles.map((m, idx) => {
    const sizeMb = (m.size / (1024 * 1024)).toFixed(1);
    const dateStr = m.updatedAt ? new Date(m.updatedAt).toLocaleDateString() : '';
    const safeName = escapeHtml(m.filename);
    return `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 9px 12px; margin-bottom: 6px; background: rgba(17, 24, 39, 0.7); border-radius: 8px; border: 1px solid var(--border-color);">
        <div style="display: flex; align-items: center; gap: 10px; overflow: hidden;">
          <span style="font-weight: 700; color: var(--accent-cyan); font-size: 12px; min-width: 24px;">#${idx + 1}</span>
          <div style="overflow: hidden;">
            <div style="font-size: 13px; font-weight: 600; color: var(--text-main); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${safeName}">
              ${safeName}
            </div>
            <div style="font-size: 11px; color: var(--text-muted);">
              ${sizeMb} MB &bull; ${dateStr}
            </div>
          </div>
        </div>
        <div style="display: flex; gap: 6px; flex-shrink: 0;">
          <button class="btn btn-secondary btn-sm" onclick="syncAllTvsToVideo(${idx})" style="font-size: 11px; padding: 4px 10px;" title="Play this video on all screens">
            Play on TVs
          </button>
          <button class="btn btn-danger btn-sm" onclick="deleteMediaFile('${encodeURIComponent(m.filename)}')" style="font-size: 11px; padding: 4px 10px;" title="Delete this video">
            Delete
          </button>
        </div>
      </div>
    `;
  }).join('');
}

async function uploadMediaFiles() {
  const input = document.getElementById('media-upload-input');
  const btn = document.getElementById('btn-upload-media');
  const status = document.getElementById('upload-status');
  if (!input.files || input.files.length === 0) {
    alert('Please select one or more video files (.mp4, .webm, .mkv) to upload.');
    return;
  }

  const formData = new FormData();
  for (let i = 0; i < input.files.length; i++) {
    formData.append('files', input.files[i]);
  }

  btn.disabled = true;
  btn.textContent = 'Uploading...';
  if (status) {
    status.style.display = 'inline';
    status.textContent = `Uploading ${input.files.length} file(s)...`;
  }

  try {
    const res = await fetch('/api/upload-media', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok && data.success) {
      input.value = '';
      if (status) {
        status.textContent = 'Upload complete!';
        setTimeout(() => { status.style.display = 'none'; }, 3000);
      }
      await fetchMedia();
      alert('Video(s) uploaded successfully! Added to continuous signage loop.');
    } else {
      alert('Upload failed: ' + (data.error || 'Server error'));
    }
  } catch (err) {
    alert('Upload error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Upload Videos to Loop';
  }
}

async function deleteMediaFile(encodedFilename) {
  const filename = decodeURIComponent(encodedFilename);
  if (!confirm(`Are you sure you want to delete "${filename}" from the signage loop?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/media/${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    });
    const data = await res.json();
    if (res.ok && data.success) {
      await fetchMedia();
    } else {
      alert('Failed to delete video: ' + (data.error || 'Server error'));
    }
  } catch (err) {
    alert('Delete error: ' + err.message);
  }
}

async function syncAllTvsToVideo(index) {
  try {
    const res = await fetch('/api/broadcast/sync-video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert(`Synchronized all connected TV displays to video #${index + 1}!`);
    } else {
      alert('Sync failed: ' + (data.error || 'Server error'));
    }
  } catch (err) {
    alert('Sync error: ' + err.message);
  }
}

async function revertAllToSignage() {
  try {
    const res = await fetch('/api/broadcast/channel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channelId: 'ch-signage', target: 'all' })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert(`Reverted ${data.updatedCount || 'all'} screen(s) to digital signage playlist.`);
    } else {
      alert('Command failed: ' + (data.error || 'Server error'));
    }
  } catch (err) {
    alert('Broadcast error: ' + err.message);
  }
}

