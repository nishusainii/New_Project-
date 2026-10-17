let socket = null;
let peerConnection = null;
let currentMode = 'signage';
let mediamtxConfig = null;

// Video Playlist State
let videoPlaylist = [];
let currentVideoIndex = 0;

// Network stall recovery state
let videoErrorRetryCount = 0;
let videoErrorRetryTimer = null;
const VIDEO_ERROR_MAX_RETRIES = 10;
const VIDEO_ERROR_RETRY_BASE_MS = 2000;

// Persistent Device Identification
function getDeviceId() {
  const urlParams = new URLSearchParams(window.location.search);
  let id = urlParams.get('id');
  if (!id) {
    id = localStorage.getItem('tv_device_id');
  }
  if (!id) {
    id = `tv-${Math.random().toString(36).substring(2, 8)}`;
    localStorage.setItem('tv_device_id', id);
  }
  return id;
}

const deviceId = getDeviceId();
const urlParams = new URLSearchParams(window.location.search);
const initialSite = urlParams.get('site') || 'Headquarters';
const initialName = urlParams.get('name') || `TV Display (${deviceId.substring(0, 6)})`;

// Register Service Worker for offline video caching (survives laptop sleep/network drop)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/tv-sw.js').then(reg => {
    console.log('[SW] Registered:', reg.scope);
    // Listen for pre-cache complete confirmation
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'PRECACHE_COMPLETE') {
        console.log('[SW] All media files are now cached locally on this TV.');
      }
    });
  }).catch(err => {
    console.warn('[SW] Service Worker registration failed:', err.message);
  });
}

// Seamless Master Loop State
let seamlessLoopData = null;
let isSeamlessMode = false;


// DOM Elements
const liveContainer = document.getElementById('live-container');
const liveVideo = document.getElementById('live-video');
const playlistContainer = document.getElementById('playlist-container');
const playlistVideo = document.getElementById('playlist-video');
const playlistClock = document.getElementById('playlist-clock');
const signageContainer = document.getElementById('signage-container');
const dashboardContainer = document.getElementById('dashboard-container');
const dashboardIframe = document.getElementById('dashboard-iframe');
const emergencyBanner = document.getElementById('emergency-banner');
const emergencyMessage = document.getElementById('emergency-message');
const hudId = document.getElementById('hud-id');
const autoplayOverlay = document.getElementById('autoplay-overlay');

function showAutoplayOverlay() {
  if (autoplayOverlay) autoplayOverlay.style.display = 'block';
}

function hideAutoplayOverlay() {
  if (autoplayOverlay) autoplayOverlay.style.display = 'none';
}

function unlockAutoplay() {
  hideAutoplayOverlay();
  if (playlistVideo && playlistVideo.paused && videoPlaylist && videoPlaylist.length > 0) {
    playlistVideo.muted = true;
    playlistVideo.play().catch(() => {});
  }
}

window.addEventListener('click', unlockAutoplay);
window.addEventListener('keydown', unlockAutoplay);
window.addEventListener('touchstart', unlockAutoplay);
if (autoplayOverlay) {
  autoplayOverlay.addEventListener('click', unlockAutoplay);
}

hudId.textContent = `TV ID: ${deviceId} | ${initialSite}`;

// Initialize Clocks
function updateClock() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString();
  document.getElementById('clock-time').textContent = timeStr;
  if (playlistClock) playlistClock.textContent = timeStr;
  document.getElementById('clock-date').textContent = now.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric'
  });
}
setInterval(updateClock, 1000);
updateClock();

// Digital Signage Slides Carousel
const slides = [
  {
    title: 'Central Multi-Site TV Network',
    text: 'Connected via secure Site-to-Site VPN. Instant low-latency live streaming & corporate announcements ready.'
  },
  {
    title: 'Daily Operations & Standup Broadcasts',
    text: 'Broadcast laptop screens, presentations, and town halls across all branch offices with one click.'
  },
  {
    title: 'Security & Enterprise Telemetry',
    text: 'Automated failover and zero-downtime display control powered by lightweight open-source microservices.'
  }
];

let slideIdx = 0;
function rotateSlide() {
  if (currentMode !== 'signage' || (videoPlaylist && videoPlaylist.length > 0)) return;
  slideIdx = (slideIdx + 1) % slides.length;
  const slide = slides[slideIdx];
  const titleEl = document.getElementById('slide-title');
  const textEl = document.getElementById('slide-text');

  titleEl.style.opacity = '0';
  textEl.style.opacity = '0';

  setTimeout(() => {
    titleEl.textContent = slide.title;
    textEl.textContent = slide.text;
    titleEl.style.opacity = '1';
    textEl.style.opacity = '1';
  }, 400);
}
setInterval(rotateSlide, 15000);

// --- Continuous Video Playlist Loop Engine ---
async function loadVideoPlaylist() {
  try {
    const res = await fetch('/api/media');
    const data = await res.json();
    const media = data.media || [];

    // Check for seamless loop support from server
    if (data.seamlessLoop && data.seamlessLoop.enabled && data.seamlessLoop.chapters && data.seamlessLoop.chapters.length > 0) {
      seamlessLoopData = data.seamlessLoop;
      isSeamlessMode = true;
      console.log(`[SeamlessLoop] Active with ${seamlessLoopData.chapters.length} chapter(s), duration: ${seamlessLoopData.totalDuration}s`);
    } else {
      seamlessLoopData = null;
      isSeamlessMode = false;
    }

    // Filter only video formats for fallback playlist
    videoPlaylist = media.filter(m => {
      const fn = m.filename.toLowerCase();
      return fn.endsWith('.mp4') || fn.endsWith('.webm') || fn.endsWith('.mkv') || fn.endsWith('.mov') || fn.endsWith('.m4v');
    });

    console.log(`[Playlist] Loaded ${videoPlaylist.length} individual video(s). Seamless mode: ${isSeamlessMode}`);

    // Tell Service Worker to pre-cache all media files into local browser storage
    // This ensures video plays from local cache even if laptop server goes offline/sleeps
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      const urlsToCache = [];
      if (isSeamlessMode && seamlessLoopData && seamlessLoopData.url) {
        urlsToCache.push(seamlessLoopData.url);
      }
      videoPlaylist.forEach(v => urlsToCache.push(v.url));
      if (urlsToCache.length > 0) {
        navigator.serviceWorker.controller.postMessage({
          type: 'PRECACHE_MEDIA',
          urls: urlsToCache
        });
        console.log(`[SW] Requested pre-cache of ${urlsToCache.length} media file(s).`);
      }
    }

    if (currentMode === 'signage') {
      showSignage();
    }
    sendPlaybackStatus();
  } catch (err) {
    console.error('Failed to load video playlist:', err);
  }
}

function sendPlaybackStatus() {
  if (socket && socket.readyState === WebSocket.OPEN) {
    let currentVideo = null;
    let videoIndex = -1;
    let totalVideos = 0;

    if (currentMode === 'signage') {
      if (isSeamlessMode && seamlessLoopData && seamlessLoopData.chapters && seamlessLoopData.chapters.length > 0) {
        const chs = seamlessLoopData.chapters;
        const idx = (currentVideoIndex >= 0 && currentVideoIndex < chs.length) ? currentVideoIndex : 0;
        currentVideo = chs[idx].filename;
        videoIndex = idx;
        totalVideos = chs.length;
      } else if (videoPlaylist && videoPlaylist.length > 0) {
        if (videoPlaylist[currentVideoIndex]) {
          currentVideo = videoPlaylist[currentVideoIndex].filename;
        }
        videoIndex = currentVideoIndex;
        totalVideos = videoPlaylist.length;
      }
    }

    socket.send(JSON.stringify({
      type: 'PLAYBACK_STATUS',
      mode: currentMode,
      currentVideo: currentVideo,
      currentVideoIndex: videoIndex,
      totalVideos: totalVideos
    }));
  }
}

function playCurrentVideo() {
  // Approach 2: Broadcast-Grade Seamless Master Loop
  if (isSeamlessMode && seamlessLoopData) {
    if (playlistContainer) playlistContainer.style.display = 'block';
    if (signageContainer) signageContainer.style.display = 'none';

    if (!playlistVideo.src || !playlistVideo.src.includes(seamlessLoopData.url)) {
      console.log(`[SeamlessLoop] Initializing seamless loop: ${seamlessLoopData.url}`);
      playlistVideo.src = seamlessLoopData.url;
      playlistVideo.loop = true;
      playlistVideo.muted = true;
      playlistVideo.defaultMuted = true;
      playlistVideo.setAttribute('muted', '');
      playlistVideo.setAttribute('playsinline', '');
      playlistVideo.preload = 'auto';

      playlistVideo.play().then(() => {
        hideAutoplayOverlay();
        sendPlaybackStatus();
      }).catch(e => {
        console.warn('[Autoplay] Browser policy prevented automated playback:', e);
        showAutoplayOverlay();
      });
    } else if (playlistVideo.paused) {
      playlistVideo.play().catch(() => {});
    }

    sendPlaybackStatus();
    return;
  }

  // Fallback: Individual video playlist
  if (!videoPlaylist || videoPlaylist.length === 0) {
    if (playlistContainer) playlistContainer.style.display = 'none';
    if (signageContainer) signageContainer.style.display = 'flex';
    sendPlaybackStatus();
    return;
  }

  if (playlistContainer) playlistContainer.style.display = 'block';
  if (signageContainer) signageContainer.style.display = 'none';

  if (currentVideoIndex >= videoPlaylist.length) {
    currentVideoIndex = 0;
  }

  const video = videoPlaylist[currentVideoIndex];
  console.log(`[Playlist] Playing video (${currentVideoIndex + 1}/${videoPlaylist.length}): ${video.filename}`);

  playlistVideo.loop = false;
  playlistVideo.src = video.url;
  playlistVideo.muted = true;
  playlistVideo.defaultMuted = true;
  playlistVideo.setAttribute('muted', '');
  playlistVideo.setAttribute('playsinline', '');

  const playPromise = playlistVideo.play();
  if (playPromise !== undefined) {
    playPromise.then(() => {
      hideAutoplayOverlay();
      sendPlaybackStatus();
    }).catch(e => {
      console.warn('[Autoplay] Browser policy prevented automated playback:', e);
      showAutoplayOverlay();
    });
  }

  sendPlaybackStatus();
}

function advanceVideo() {
  if (isSeamlessMode && seamlessLoopData && seamlessLoopData.chapters && seamlessLoopData.chapters.length > 0) {
    const chs = seamlessLoopData.chapters;
    currentVideoIndex = (currentVideoIndex + 1) % chs.length;
    playlistVideo.currentTime = chs[currentVideoIndex].startTime;
    sendPlaybackStatus();
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: 'VIDEO_ADVANCE',
        nextIndex: currentVideoIndex,
        currentVideo: chs[currentVideoIndex].filename,
        totalVideos: chs.length
      }));
    }
    return;
  }

  if (!videoPlaylist || videoPlaylist.length === 0) return;
  currentVideoIndex = (currentVideoIndex + 1) % videoPlaylist.length;
  playCurrentVideo();

  if (socket && socket.readyState === WebSocket.OPEN) {
    const currentVid = (videoPlaylist && videoPlaylist[currentVideoIndex]) ? videoPlaylist[currentVideoIndex].filename : null;
    socket.send(JSON.stringify({
      type: 'VIDEO_ADVANCE',
      nextIndex: currentVideoIndex,
      currentVideo: currentVid,
      totalVideos: videoPlaylist.length
    }));
  }
}

if (playlistVideo) {
  // Continuous real-time chapter detection for seamless broadcast mode
  playlistVideo.addEventListener('timeupdate', () => {
    if (!isSeamlessMode || !seamlessLoopData || !seamlessLoopData.chapters || seamlessLoopData.chapters.length === 0) return;
    const ct = playlistVideo.currentTime;
    const chs = seamlessLoopData.chapters;

    let activeIdx = chs.findIndex(c => ct >= c.startTime && ct < c.endTime);
    if (activeIdx === -1) {
      activeIdx = ct >= (seamlessLoopData.totalDuration - 0.5) ? (chs.length - 1) : 0;
    }

    if (activeIdx !== currentVideoIndex && activeIdx >= 0 && activeIdx < chs.length) {
      currentVideoIndex = activeIdx;
      console.log(`[SeamlessLoop] Chapter transitioned to (${currentVideoIndex + 1}/${chs.length}): ${chs[currentVideoIndex].displayName}`);
      sendPlaybackStatus();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: 'VIDEO_ADVANCE',
          nextIndex: currentVideoIndex,
          currentVideo: chs[currentVideoIndex].filename,
          totalVideos: chs.length
        }));
      }
    }
  });

  playlistVideo.onended = () => {
    if (isSeamlessMode) {
      // Loop attribute handles wrap-around internally; if onended fires, immediately restart frame 0
      playlistVideo.currentTime = 0;
      playlistVideo.play().catch(() => {});
      return;
    }
    console.log('[Playlist] Video ended, advancing to next in continuous loop...');
    advanceVideo();
  };

  playlistVideo.onerror = (e) => {
    console.error('[Playlist] Video load error, advancing to next video in 1 second...', e);
    setTimeout(advanceVideo, 1000);
  };
}

// WebSocket Connection to Central Controller
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/control`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log('[WS] Connected to Central Hub. Registering...');
    let currentVid = null;
    let vidIdx = -1;
    let totVids = 0;
    if (currentMode === 'signage' && videoPlaylist && videoPlaylist.length > 0) {
      if (videoPlaylist[currentVideoIndex]) {
        currentVid = videoPlaylist[currentVideoIndex].filename;
      }
      vidIdx = currentVideoIndex;
      totVids = videoPlaylist.length;
    }
    socket.send(JSON.stringify({
      type: 'REGISTER',
      id: deviceId,
      name: initialName,
      site: initialSite,
      mode: currentMode,
      currentVideo: currentVid,
      currentVideoIndex: vidIdx,
      totalVideos: totVids
    }));
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleServerMessage(data);
    } catch (e) {
      console.error('[WS] Parse error:', e);
    }
  };

  socket.onclose = () => {
    console.warn('[WS] Connection lost. Retrying in 3 seconds...');
    setTimeout(connectWebSocket, 3000);
  };

  socket.onerror = (err) => {
    console.error('[WS] Socket error:', err);
    socket.close();
  };
}

// Handle Incoming Server Commands
function handleServerMessage(data) {
  console.log('[WS Command Received]:', data.type, data);

  if (data.type === 'REGISTRATION_SUCCESS') {
    if (data.device) {
      document.getElementById('display-site-title').textContent = data.device.site || 'CiSAI Network Display';
      document.getElementById('display-location-name').textContent = data.device.name || 'Display Screen';
      hudId.textContent = `TV ID: ${deviceId} | ${data.device.site} (${data.device.name})`;
    }
    if (typeof data.masterVideoIndex === 'number' && videoPlaylist && videoPlaylist.length > 0) {
      console.log('[Sync] Aligning with master playlist video index:', data.masterVideoIndex);
      currentVideoIndex = data.masterVideoIndex % videoPlaylist.length;
    }
    if (data.currentChannel) {
      applyChannel(data.currentChannel);
    }
    if (data.alert) {
      showAlert(data.alert.message);
    }
  }

function executeSyncVideo(idx) {
  currentMode = 'signage';
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }
  if (liveContainer) liveContainer.style.display = 'none';
  if (dashboardContainer) dashboardContainer.style.display = 'none';
  if (signageContainer) signageContainer.style.display = 'none';
  if (playlistContainer) playlistContainer.style.display = 'block';

  if (isSeamlessMode && seamlessLoopData && seamlessLoopData.chapters && seamlessLoopData.chapters.length > 0) {
    const chs = seamlessLoopData.chapters;
    const targetIdx = idx % chs.length;
    currentVideoIndex = targetIdx;
    console.log(`[Sync] Master synchronized to chapter ${currentVideoIndex + 1}: ${chs[currentVideoIndex].displayName}`);

    if (!playlistVideo.src || !playlistVideo.src.includes(seamlessLoopData.url)) {
      playlistVideo.src = seamlessLoopData.url;
      playlistVideo.loop = true;
      playlistVideo.muted = true;
      playlistVideo.defaultMuted = true;
    }
    playlistVideo.currentTime = chs[targetIdx].startTime;
    playlistVideo.play().then(() => {
      hideAutoplayOverlay();
      sendPlaybackStatus();
    }).catch(() => showAutoplayOverlay());
    sendPlaybackStatus();
    return;
  }

  if (!videoPlaylist || videoPlaylist.length === 0) return;
  currentVideoIndex = idx % videoPlaylist.length;
  const video = videoPlaylist[currentVideoIndex];
  console.log(`[Sync] Master synchronized to Video ${currentVideoIndex + 1}: ${video.filename}`);

  playlistVideo.loop = false;
  playlistVideo.src = video.url;
  playlistVideo.currentTime = 0;
  playlistVideo.muted = true;
  playlistVideo.defaultMuted = true;
  playlistVideo.setAttribute('muted', '');
  playlistVideo.setAttribute('playsinline', '');

  playlistVideo.play().then(() => {
    hideAutoplayOverlay();
    sendPlaybackStatus();
  }).catch(e => {
    console.warn('[Autoplay] Browser policy prevented automated playback on sync:', e);
    showAutoplayOverlay();
  });
  sendPlaybackStatus();
}

  if (data.type === 'SYNC_VIDEO') {
    const idx = (typeof data.index === 'number') ? data.index : 0;
    console.log('[Sync] Received SYNC_VIDEO command for video index:', idx);
    if (!videoPlaylist || videoPlaylist.length === 0) {
      loadVideoPlaylist().then(() => executeSyncVideo(idx));
    } else {
      executeSyncVideo(idx);
    }
  }

  if (data.type === 'SWITCH_CHANNEL') {
    applyChannel(data.channel);
  }

  if (data.type === 'PLAYLIST_UPDATED') {
    console.log('[WS] Playlist updated on server. Refreshing continuous loop...');
    loadVideoPlaylist();
  }

  if (data.type === 'EMERGENCY_ALERT') {
    showAlert(data.alert ? data.alert.message : 'EMERGENCY ALERT');
  }

  if (data.type === 'CLEAR_ALERT') {
    hideAlert();
  }

  if (data.type === 'RELOAD_PLAYER') {
    location.reload();
  }
}

// Channel Switcher
function applyChannel(channel) {
  if (!channel) return;
  console.log('Switching to channel:', channel.id, channel.type);

  if (channel.type === 'webrtc') {
    startLiveStream(channel.streamKey || 'live');
  } else if (channel.type === 'url') {
    showDashboard(channel.url);
  } else {
    showSignage();
  }
}

// Live Stream Handling (WebRTC WHEP via MediaMTX)
let liveRetryTimer = null;

async function startLiveStream(streamKey) {
  currentMode = 'live';
  streamKey = streamKey || 'live';

  if (playlistContainer) {
    playlistContainer.style.display = 'none';
    if (playlistVideo) playlistVideo.pause();
  }
  signageContainer.style.display = 'none';
  dashboardContainer.style.display = 'none';
  liveContainer.style.display = 'block';

  // Add or get standby indicator inside live container
  let liveStandby = document.getElementById('live-standby-msg');
  if (!liveStandby) {
    liveStandby = document.createElement('div');
    liveStandby.id = 'live-standby-msg';
    liveStandby.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: #94a3b8; font-size: 18px; font-weight: 500; letter-spacing: 0.5px; z-index: 5; pointer-events: none;';
    liveStandby.innerHTML = '<div style="font-size: 13px; color: #38bdf8; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px;">Live Channel Armed</div>Connecting to live stream...';
    liveContainer.appendChild(liveStandby);
  }
  liveStandby.style.display = 'block';

  // Clear any existing retry timer
  if (liveRetryTimer) {
    clearTimeout(liveRetryTimer);
    liveRetryTimer = null;
  }

  // Cleanup existing WebRTC stream
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }

  try {
    peerConnection = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
      ]
    });

    let whepSessionUrl = null;
    const queuedPlayerCandidates = [];

    const sendPlayerCandidate = (cand) => {
      if (!cand || !whepSessionUrl) return;
      fetch(whepSessionUrl, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/trickle-ice-sdpfrag' },
        body: `a=${cand.candidate}\r\n`
      }).catch(e => {});
    };

    peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        if (whepSessionUrl) {
          sendPlayerCandidate(event.candidate);
        } else {
          queuedPlayerCandidates.push(event.candidate);
        }
      }
    };

    peerConnection.ontrack = (event) => {
      if (liveVideo.srcObject !== event.streams[0]) {
        console.log('[WebRTC] Stream track received! Playing video...');
        if (liveStandby) liveStandby.style.display = 'none';
        
        liveVideo.removeAttribute('src'); // Ensure HLS fallback src is cleared
        liveVideo.load(); // Force browser decoder reset
        
        liveVideo.muted = true;
        liveVideo.defaultMuted = true;
        liveVideo.setAttribute('muted', '');
        liveVideo.setAttribute('playsinline', '');
        liveVideo.srcObject = event.streams[0];
        
        const playPromise = liveVideo.play();
        if (playPromise !== undefined) {
          playPromise.catch(e => {
            console.warn('[WebRTC] Autoplay prevented, retrying muted:', e);
            liveVideo.muted = true;
            liveVideo.play().catch(() => {});
          });
        }
      }
    };

    peerConnection.onconnectionstatechange = () => {
      console.log('[WebRTC] Connection state:', peerConnection.connectionState);
      if (peerConnection.connectionState === 'failed' || peerConnection.connectionState === 'disconnected') {
        if (currentMode === 'live') {
          console.warn('[WebRTC] Connection failed, attempting HLS fallback...');
          startHlsStream(streamKey);
        }
      }
    };

    // WHEP receiver requires creating a receive-only offer
    peerConnection.addTransceiver('video', { direction: 'recvonly' });
    peerConnection.addTransceiver('audio', { direction: 'recvonly' });

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    // Wait for initial ICE candidates (up to 800ms)
    await new Promise(resolve => {
      if (peerConnection.iceGatheringState === 'complete') resolve();
      else {
        const handler = () => {
          if (peerConnection.iceGatheringState === 'complete') {
            peerConnection.removeEventListener('icegatheringstatechange', handler);
            resolve();
          }
        };
        peerConnection.addEventListener('icegatheringstatechange', handler);
        setTimeout(resolve, 800);
      }
    });

    const whepUrl = `/webrtc/${streamKey}/whep`;
    const directWhepUrl = `http://${window.location.hostname}:8889/${streamKey}/whep`;

    let res = null;
    try {
      res = await fetch(whepUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: peerConnection.localDescription.sdp
      });
    } catch (errProxy) {
      console.warn('[WHEP] Proxy fetch failed, trying direct port 8889...', errProxy);
      try {
        res = await fetch(directWhepUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: peerConnection.localDescription.sdp
        });
      } catch (errDirect) {}
    }

    if (res && res.ok) {
      whepSessionUrl = res.headers.get('Location') || whepUrl;
      if (whepSessionUrl.startsWith('/live') && !whepSessionUrl.startsWith('/webrtc')) {
        whepSessionUrl = '/webrtc' + whepSessionUrl;
      }
      while (queuedPlayerCandidates.length > 0) {
        sendPlayerCandidate(queuedPlayerCandidates.shift());
      }
      const answer = await res.text();
      await peerConnection.setRemoteDescription(new RTCSessionDescription({
        type: 'answer',
        sdp: answer
      }));
      console.log('[WHEP] Remote description applied. Waiting for video tracks...');
    } else {
      console.log('[WHEP] Stream not publishing yet. Standing by and retrying in 2.5s...');
      if (liveStandby) {
        liveStandby.innerHTML = '<div style="font-size: 13px; color: #38bdf8; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px;">Live Broadcast Channel</div>Waiting for presenter video feed...';
        liveStandby.style.display = 'block';
      }
      liveRetryTimer = setTimeout(() => {
        if (currentMode === 'live') startLiveStream(streamKey);
      }, 2500);
    }

    sendPlaybackStatus();
  } catch (err) {
    console.error('Failed to connect to live stream:', err);
    if (liveStandby) {
      liveStandby.innerHTML = '<div style="font-size: 13px; color: #ef4444; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px;">Connection Notice</div>Retrying connection...';
    }
    liveRetryTimer = setTimeout(() => {
      if (currentMode === 'live') startLiveStream(streamKey);
    }, 3000);
  }
}

function startHlsStream(streamKey) {
  currentMode = 'live';
  console.log('[Live] Activating HLS stream for Smart TV stability...');
  
  if (playlistContainer) {
    playlistContainer.style.display = 'none';
    if (playlistVideo) playlistVideo.pause();
  }
  if (dashboardContainer) dashboardContainer.style.display = 'none';
  if (liveContainer) liveContainer.style.display = 'flex';

  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }
  
  if (liveStandby) {
    liveStandby.innerHTML = '<div style="font-size: 13px; color: #38bdf8; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px;">Live Channel Armed</div>Waiting for broadcaster...';
    liveStandby.style.display = 'block';
  }

  const hlsUrl = `/hls/${streamKey || 'live'}/index.m3u8`;
  liveVideo.srcObject = null;
  liveVideo.muted = true;
  liveVideo.defaultMuted = true;
  liveVideo.setAttribute('muted', '');
  liveVideo.setAttribute('playsinline', '');
  
  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(hlsUrl);
    hls.attachMedia(liveVideo);
    hls.on(Hls.Events.MANIFEST_PARSED, function() {
      liveVideo.play().then(() => {
        if (liveStandby) liveStandby.style.display = 'none';
        console.log('[Live] HLS stream playback started via hls.js.');
      }).catch(e => {
        console.warn('[Live] HLS playback pending stream availability:', e);
        if (liveStandby) {
          liveStandby.innerHTML = '<div style="font-size: 13px; color: #eab308; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px;">Waiting for Stream</div>The presenter has not started yet...';
          liveStandby.style.display = 'block';
        }
      });
    });
    hls.on(Hls.Events.ERROR, function(event, data) {
      if (data.fatal) {
        liveRetryTimer = setTimeout(() => {
          if (currentMode === 'live') startHlsStream(streamKey);
        }, 3000);
      }
    });
  } else if (liveVideo.canPlayType('application/vnd.apple.mpegurl')) {
    liveVideo.src = hlsUrl;
    liveVideo.addEventListener('loadedmetadata', function() {
      liveVideo.play().then(() => {
        if (liveStandby) liveStandby.style.display = 'none';
        console.log('[Live] HLS stream playback started natively.');
      }).catch(e => {
        liveRetryTimer = setTimeout(() => {
          if (currentMode === 'live') startHlsStream(streamKey);
        }, 3000);
      });
    });
  } else {
    console.error('[Live] HLS is not supported on this browser.');
  }
}

function showSignage() {
  currentMode = 'signage';
  if (liveRetryTimer) {
    clearTimeout(liveRetryTimer);
    liveRetryTimer = null;
  }
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }
  if (liveVideo) {
    liveVideo.pause();
    liveVideo.src = '';
    liveVideo.srcObject = null;
  }
  liveContainer.style.display = 'none';
  dashboardContainer.style.display = 'none';

  // Check if continuous video playlist has videos
  if (videoPlaylist && videoPlaylist.length > 0) {
    signageContainer.style.display = 'none';
    if (playlistContainer) playlistContainer.style.display = 'block';
    if (!playlistVideo.src || playlistVideo.paused) {
      playCurrentVideo();
    }
  } else {
    if (playlistContainer) playlistContainer.style.display = 'none';
    signageContainer.style.display = 'flex';
  }
  sendPlaybackStatus();
}

function showDashboard(url) {
  currentMode = 'url';
  if (liveRetryTimer) {
    clearTimeout(liveRetryTimer);
    liveRetryTimer = null;
  }
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }
  if (liveVideo) {
    liveVideo.pause();
    liveVideo.src = '';
    liveVideo.srcObject = null;
  }
  if (playlistContainer) {
    playlistContainer.style.display = 'none';
    if (playlistVideo) playlistVideo.pause();
  }
  liveContainer.style.display = 'none';
  signageContainer.style.display = 'none';
  dashboardContainer.style.display = 'block';
  if (url) dashboardIframe.src = url;
  sendPlaybackStatus();
}

function showAlert(msg) {
  emergencyMessage.textContent = msg;
  emergencyBanner.style.display = 'flex';
}

function hideAlert() {
  emergencyBanner.style.display = 'none';
}

// Heartbeat Loop (every 10s)
setInterval(() => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    let currentVid = null;
    let vidIdx = -1;
    let totVids = 0;
    if (currentMode === 'signage') {
      if (isSeamlessMode && seamlessLoopData && seamlessLoopData.chapters && seamlessLoopData.chapters.length > 0) {
        const chs = seamlessLoopData.chapters;
        const idx = (currentVideoIndex >= 0 && currentVideoIndex < chs.length) ? currentVideoIndex : 0;
        currentVid = chs[idx].filename;
        vidIdx = idx;
        totVids = chs.length;
      } else if (videoPlaylist && videoPlaylist.length > 0) {
        if (videoPlaylist[currentVideoIndex]) {
          currentVid = videoPlaylist[currentVideoIndex].filename;
        }
        vidIdx = currentVideoIndex;
        totVids = videoPlaylist.length;
      }
    }
    socket.send(JSON.stringify({
      type: 'HEARTBEAT',
      mode: currentMode,
      currentVideo: currentVid,
      currentVideoIndex: vidIdx,
      totalVideos: totVids
    }));
  }
}, 10000);

// Double-click full screen toggle
function toggleFullScreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen().catch(() => {});
  }
}

// Screen WakeLock to prevent TV display from sleeping/turning off
let wakeLock = null;
async function requestWakeLock() {
  try {
    if ('wakeLock' in navigator) {
      wakeLock = await navigator.wakeLock.request('screen');
      console.log('[Power] Screen WakeLock acquired successfully.');
      wakeLock.addEventListener('release', () => {
        console.log('[Power] Screen WakeLock was released.');
      });
    }
  } catch (err) {
    console.warn('[Power] WakeLock error:', err.message);
  }
}

// Re-acquire WakeLock and resume video when screen or tab becomes visible
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    requestWakeLock();
    if (currentMode === 'signage' && playlistVideo && playlistVideo.paused) {
      console.log('[Power] Screen became visible, resuming video playback...');
      playlistVideo.play().catch(() => {});
    }
  }
});

// ============================================================
// Comprehensive Video Stall & Network-Drop Recovery System
// Handles: laptop sleep, WiFi drop, server restart, Docker pause
// ============================================================

function scheduleVideoRetry(reason) {
  if (currentMode !== 'signage') return;
  if (videoErrorRetryTimer) return; // already scheduled

  if (videoErrorRetryCount >= VIDEO_ERROR_MAX_RETRIES) {
    console.warn('[Recovery] Max retries reached. Reloading playlist from scratch...');
    videoErrorRetryCount = 0;
    loadVideoPlaylist();
    return;
  }

  // Exponential backoff: 2s, 4s, 8s, 16s ... capped at 30s
  const delay = Math.min(VIDEO_ERROR_RETRY_BASE_MS * Math.pow(2, videoErrorRetryCount), 30000);
  videoErrorRetryCount++;
  console.warn(`[Recovery] ${reason} - retry ${videoErrorRetryCount}/${VIDEO_ERROR_MAX_RETRIES} in ${delay}ms...`);

  videoErrorRetryTimer = setTimeout(() => {
    videoErrorRetryTimer = null;
    if (currentMode !== 'signage') return;

    const rememberedTime = playlistVideo.currentTime || 0;
    const currentSrc = playlistVideo.src;

    if (!currentSrc) {
      playCurrentVideo();
      return;
    }

    // Re-assign same src to force browser to re-request from server (or Service Worker cache)
    playlistVideo.src = '';
    playlistVideo.load();
    playlistVideo.src = currentSrc;
    playlistVideo.muted = true;
    playlistVideo.defaultMuted = true;

    playlistVideo.addEventListener('canplay', function resume() {
      playlistVideo.removeEventListener('canplay', resume);
      // Seek back to where we were (only valid for seamless loop, not individual clips)
      if (isSeamlessMode && rememberedTime > 0) {
        playlistVideo.currentTime = rememberedTime;
      }
      playlistVideo.play().then(() => {
        videoErrorRetryCount = 0; // reset on success
        console.log('[Recovery] Video playback resumed successfully.');
      }).catch(() => scheduleVideoRetry('play() rejected after src reload'));
    }, { once: true });

    // If canplay doesn't fire in 10s (server still down), retry again
    setTimeout(() => {
      if (playlistVideo.paused && currentMode === 'signage') {
        scheduleVideoRetry('canplay timeout after src reload');
      }
    }, 10000);
  }, delay);
}

if (playlistVideo) {
  // Network error (server unreachable, HTTP error response)
  playlistVideo.addEventListener('error', (e) => {
    if (currentMode !== 'signage') return;
    const code = playlistVideo.error ? playlistVideo.error.code : 'unknown';
    // MediaError.MEDIA_ERR_NETWORK = 2, MEDIA_ERR_SRC_NOT_SUPPORTED = 4
    if (code === 2 || code === 4 || code === 'unknown') {
      console.error('[Recovery] Network error on video (code=' + code + '). Server may be offline.');
      scheduleVideoRetry('network error code=' + code);
    } else {
      // Other error (bad codec etc) - just advance to next
      console.warn('[Recovery] Video decode/source error (code=' + code + '). Advancing...');
      if (!isSeamlessMode) advanceVideo();
    }
  });

  // Video stalled (server stopped sending bytes - typical of laptop sleep)
  playlistVideo.addEventListener('stalled', () => {
    if (currentMode !== 'signage') return;
    console.warn('[Recovery] Video stalled - server may have paused or gone to sleep.');
    scheduleVideoRetry('stalled event');
  });

  // Buffering exhausted (waiting for more data from server)
  playlistVideo.addEventListener('waiting', () => {
    if (currentMode !== 'signage') return;
    // Waiting is normal during initial load; only act if we've already been playing
    if (playlistVideo.currentTime > 1) {
      console.warn('[Recovery] Video waiting (buffer underrun). Server may be slow/offline.');
      // Give it 8 seconds to recover naturally before retrying
      if (!videoErrorRetryTimer) {
        videoErrorRetryTimer = setTimeout(() => {
          videoErrorRetryTimer = null;
          if (playlistVideo.paused && currentMode === 'signage') {
            scheduleVideoRetry('persistent buffer underrun');
          }
        }, 8000);
      }
    }
  });

  // Successful data flow - reset error counter
  playlistVideo.addEventListener('playing', () => {
    if (videoErrorRetryCount > 0) {
      console.log('[Recovery] Video playing again. Resetting error counter.');
      videoErrorRetryCount = 0;
    }
    if (videoErrorRetryTimer) {
      clearTimeout(videoErrorRetryTimer);
      videoErrorRetryTimer = null;
    }
  });

  // Auto-resume unexpected pause (e.g., from visibility change)
  playlistVideo.addEventListener('pause', () => {
    if (currentMode === 'signage' && playlistContainer && playlistContainer.style.display !== 'none') {
      setTimeout(() => {
        if (playlistVideo.paused && currentMode === 'signage') {
          console.log('[Watchdog] Unexpected pause. Auto-resuming...');
          playlistVideo.play().catch(() => scheduleVideoRetry('auto-resume after pause failed'));
        }
      }, 1500);
    }
  });
}

// Playback Stall Watchdog: every 15s checks playback is advancing
let lastObservedTime = -1;
let stallCount = 0;
setInterval(() => {
  if (currentMode === 'signage' && playlistVideo && playlistVideo.src) {
    if (playlistVideo.paused) {
      if (!videoErrorRetryTimer) {
        console.log('[Watchdog] Video paused in signage mode. Kicking playback...');
        playlistVideo.play().catch(() => scheduleVideoRetry('watchdog kick failed'));
      }
    } else if (playlistVideo.currentTime === lastObservedTime && playlistVideo.duration > 0) {
      stallCount++;
      if (stallCount >= 2) {
        console.warn('[Watchdog] Video frozen at', lastObservedTime, 's. Triggering recovery...');
        stallCount = 0;
        if (!videoErrorRetryTimer) {
          scheduleVideoRetry('playback frozen (same currentTime for 30s)');
        }
      }
    } else {
      lastObservedTime = playlistVideo.currentTime;
      stallCount = 0;
    }
  }
}, 15000);

// Network online event: resume immediately when laptop wakes up from sleep
window.addEventListener('online', () => {
  console.log('[Network] Connection restored. Resuming video...');
  if (videoErrorRetryTimer) {
    clearTimeout(videoErrorRetryTimer);
    videoErrorRetryTimer = null;
  }
  videoErrorRetryCount = 0;
  if (currentMode === 'signage' && playlistVideo && playlistVideo.paused) {
    scheduleVideoRetry('network came back online');
  }
});

// Initial playlist fetch, WakeLock and WebSocket startup
requestWakeLock();
loadVideoPlaylist().then(() => {
  connectWebSocket();
}).catch(() => {
  connectWebSocket();
});

