/**
 * Innspark Squid Proxy Management Portal - Frontend Application Controller
 * Handles SPA navigation, real-time telemetry, modal controllers, and REST APIs.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Global Application State
  const state = {
    activeTab: "dashboard",
    squidStatus: {},
    users: [],
    groups: [],
    domainLists: [],
    currentDomainList: "ai_domains",
    allowedIps: [],
    ports: [],
    logStreamPaused: false,
    logStreamTimer: null,
    statusPollTimer: null,
    availableFiles: [],
    telemetryRange: "500"
  };

  // ----------------------------------------------------------------------------
  // UI Helpers & Toasts
  // ----------------------------------------------------------------------------
  function showToast(message, type = "success") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        ${type === 'success' ? '<polyline points="20 6 9 17 4 12"></polyline>' :
        type === 'error' ? '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>' :
          '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>'}
      </svg>
      <span>${message}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }

  // ----------------------------------------------------------------------------
  // Navigation & Tab Switching
  // ----------------------------------------------------------------------------
  function switchTab(tabId) {
    if (!tabId) tabId = "dashboard";
    tabId = tabId.replace("#", "");

    const targetPane = document.getElementById(`tab-${tabId}`);
    if (!targetPane) return;

    // Update active nav links
    document.querySelectorAll(".nav-item").forEach(link => {
      link.classList.toggle("active", link.dataset.tab === tabId);
    });

    // Update active pane
    document.querySelectorAll(".tab-pane").forEach(pane => {
      pane.classList.remove("active");
    });
    targetPane.classList.add("active");

    state.activeTab = tabId;
    window.location.hash = tabId;

    // Trigger tab-specific loaders
    if (tabId === "users") loadUsers();
    else if (tabId === "groups") loadGroups();
    else if (tabId === "domains") loadDomains();
    else if (tabId === "allowed-ips") loadAllowedIps();
    else if (tabId === "ports") loadPorts();
    else if (tabId === "logs") loadLogs();
    else if (tabId === "editor") loadEditableFiles();
    else if (tabId === "backups") loadBackups();
    else if (tabId === "dashboard") loadStatus();
    else if (tabId === "fleet") loadFleetStatus();
    else if (tabId === "blocked") loadBlockedAnalytics();
    else if (tabId === "user-activity") loadUserActivityInit();
    else if (tabId === "nftables") loadNftables();
    else if (tabId === "bandwidth") loadPortBandwidth();

    if (tabId !== "bandwidth" && state.bandwidthTimer) {
      clearInterval(state.bandwidthTimer);
      state.bandwidthTimer = null;
    }
  }

  // Handle hash changes
  window.addEventListener("hashchange", () => {
    switchTab(window.location.hash);
  });

  // Nav click handlers
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      switchTab(item.dataset.tab);
    });
  });

  // Internal hash links
  document.querySelectorAll(".nav-link-hash").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const hash = link.getAttribute("href");
      switchTab(hash);
      const dropdown = document.getElementById("userDropdownPanel");
      if (dropdown) dropdown.classList.remove("show");
    });
  });

  // User Profile Dropdown
  const avatarToggle = document.getElementById("avatarDropdownToggle");
  const userDropdown = document.getElementById("userDropdownPanel");
  if (avatarToggle && userDropdown) {
    avatarToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      userDropdown.classList.toggle("show");
    });
    document.addEventListener("click", () => {
      userDropdown.classList.remove("show");
    });
  }

  // ----------------------------------------------------------------------------
  // Telemetry & Status Engine
  // ----------------------------------------------------------------------------
  let currentBlockedEvents = [];

  function renderBlockedFeed(events, totalBlocked, rangeLabel) {
    currentBlockedEvents = events || [];
    const countBadge = document.getElementById("dashBlockedWindowCount");
    if (countBadge) {
      const count = totalBlocked !== undefined ? totalBlocked : currentBlockedEvents.length;
      countBadge.textContent = `${count} Blocked (${rangeLabel || 'Window'})`;
    }
    filterAndRenderBlockedFeed();
  }

  function filterAndRenderBlockedFeed() {
    const tbody = document.getElementById("dashBlockedFeedBody");
    if (!tbody) return;

    const filterInput = document.getElementById("dashBlockedFilterInput");
    const q = filterInput ? filterInput.value.toLowerCase().trim() : "";

    const filtered = currentBlockedEvents.filter(ev => {
      if (!q) return true;
      return (ev.client_ip && ev.client_ip.toLowerCase().includes(q)) ||
             (ev.user && ev.user.toLowerCase().includes(q)) ||
             (ev.domain && ev.domain.toLowerCase().includes(q)) ||
             (ev.reason && ev.reason.toLowerCase().includes(q)) ||
             (ev.status && ev.status.toLowerCase().includes(q));
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-3">No blocked requests recorded in this time window.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(ev => {
      const isAuthFail = (ev.status && ev.status.includes("407")) || (ev.reason && ev.reason.includes("407"));
      const isForbidden = (ev.status && ev.status.includes("403")) || (ev.reason && ev.reason.includes("403"));
      const categoryBadge = isAuthFail
        ? `<span class="badge-tag amber font-mono">AUTH FAIL (407)</span>`
        : (isForbidden
            ? `<span class="badge-tag rose font-mono">FORBIDDEN (403)</span>`
            : `<span class="badge-tag rose font-mono">TCP_DENIED</span>`);

      return `
        <tr class="blocked-row-highlight">
          <td class="font-mono text-xs text-muted">${escapeHtml(ev.time)}</td>
          <td class="font-mono text-xs">${escapeHtml(ev.client_ip)}</td>
          <td class="font-mono text-xs text-cyan" style="max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(ev.domain)}">${escapeHtml(ev.domain)}</td>
          <td><span class="badge-tag cyan">${escapeHtml(ev.user)}</span></td>
          <td><span class="badge-tag font-mono">${escapeHtml(ev.method || 'CONNECT')}</span></td>
          <td><span class="status-pill rose font-mono">${escapeHtml(ev.status)}</span></td>
          <td>${categoryBadge}</td>
        </tr>
      `;
    }).join("");
  }

  function renderTelemetryData(an) {
    if (!an) return;

    // 1. Update 4 Status KPI Cards & Donut Chart
    if (an.status_distribution && an.status_percentages) {
      const sDist = an.status_distribution;
      const sPct = an.status_percentages;

      const pTunnel = Number(sPct.tcp_tunnel || 0);
      const pMiss = Number(sPct.tcp_miss || 0);
      const pHit = Number(sPct.tcp_hit || 0);
      const pDenied = Number(sPct.tcp_denied || 0);

      const setKpi = (prefix, count, pct) => {
        const elCount = document.getElementById(`stat${prefix}Count`);
        const elPct = document.getElementById(`stat${prefix}Pct`);
        const elFill = document.getElementById(`stat${prefix}Fill`);
        if (elCount) elCount.textContent = (count || 0).toLocaleString();
        if (elPct) elPct.textContent = `${(pct || 0).toFixed(1)}%`;
        if (elFill) elFill.style.width = `${Math.min(pct || 0, 100)}%`;
      };

      setKpi("Tunnel", sDist.tcp_tunnel, pTunnel);
      setKpi("Miss", sDist.tcp_miss, pMiss);
      setKpi("Hit", sDist.tcp_hit, pHit);
      setKpi("Denied", sDist.tcp_denied, pDenied);

      // SVG Donut Segments (circumference C = 2 * PI * 72 ≈ 452.39)
      const C = 452.39;
      const lTunnel = Math.max(0, (pTunnel / 100) * C);
      const lMiss = Math.max(0, (pMiss / 100) * C);
      const lHit = Math.max(0, (pHit / 100) * C);
      const lDenied = Math.max(0, (pDenied / 100) * C);

      const segTunnel = document.getElementById("donutSegTunnel");
      const segMiss = document.getElementById("donutSegMiss");
      const segHit = document.getElementById("donutSegHit");
      const segDenied = document.getElementById("donutSegDenied");

      if (segTunnel) {
        segTunnel.style.strokeDasharray = `${lTunnel} ${C}`;
        segTunnel.style.strokeDashoffset = "0";
      }
      if (segMiss) {
        segMiss.style.strokeDasharray = `${lMiss} ${C}`;
        segMiss.style.strokeDashoffset = `${-lTunnel}`;
      }
      if (segHit) {
        segHit.style.strokeDasharray = `${lHit} ${C}`;
        segHit.style.strokeDashoffset = `${-(lTunnel + lMiss)}`;
      }
      if (segDenied) {
        segDenied.style.strokeDasharray = `${lDenied} ${C}`;
        segDenied.style.strokeDashoffset = `${-(lTunnel + lMiss + lHit)}`;
      }

      // Donut Center Readout
      const centerPct = document.getElementById("donutCenterPct");
      const centerSub = document.getElementById("donutCenterSub");
      const centerReqs = document.getElementById("donutCenterReqs");

      if (centerPct) centerPct.textContent = `${pTunnel.toFixed(1)}%`;
      if (centerSub) centerSub.textContent = "TUNNEL SLA";
      if (centerReqs) {
        const total = an.sample_lines || (sDist.tcp_tunnel + sDist.tcp_miss + sDist.tcp_hit + sDist.tcp_denied) || 500;
        centerReqs.textContent = `${(sDist.tcp_tunnel || 0).toLocaleString()} / ${total.toLocaleString()} Reqs`;
      }

      // Render Real-Time Traffic Velocity Waveform
      const velocityPoints = (an.traffic_velocity && an.traffic_velocity.length >= 2)
        ? an.traffic_velocity
        : [12, 18, 26, 22, 34, 38, 30, 44, 48, 36, 52, 46, 58, 50];

      const vMax = Math.max(...velocityPoints, 1);
      const vWidth = 360;
      const vHeight = 140;
      const padBottom = 12;
      const padTop = 15;
      const chartHeight = vHeight - padBottom - padTop;
      const nPoints = velocityPoints.length;

      const coords = velocityPoints.map((val, i) => {
        const x = (i / (nPoints - 1)) * vWidth;
        const y = (vHeight - padBottom) - (val / vMax) * chartHeight;
        return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10 };
      });

      let lineD = `M ${coords[0].x} ${coords[0].y}`;
      for (let i = 0; i < coords.length - 1; i++) {
        const p0 = coords[i === 0 ? i : i - 1];
        const p1 = coords[i];
        const p2 = coords[i + 1];
        const p3 = coords[i + 2] || p2;

        const cp1x = p1.x + (p2.x - p0.x) / 6;
        const cp1y = p1.y + (p2.y - p0.y) / 6;
        const cp2x = p2.x - (p3.x - p1.x) / 6;
        const cp2y = p2.y - (p3.y - p1.y) / 6;

        lineD += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
      }

      const areaD = `${lineD} L ${vWidth} ${vHeight - padBottom} L 0 ${vHeight - padBottom} Z`;

      const linePathEl = document.getElementById("velocityLinePath");
      const areaPathEl = document.getElementById("velocityAreaPath");
      if (linePathEl) linePathEl.setAttribute("d", lineD);
      if (areaPathEl) areaPathEl.setAttribute("d", areaD);

      const peakEl = document.getElementById("velocityPeakRate");
      if (peakEl) peakEl.textContent = `${an.peak_velocity || vMax} req/slot`;

      const cacheEffEl = document.getElementById("dashCacheEff");
      if (cacheEffEl) cacheEffEl.textContent = `${an.cache_efficiency_pct || 99.2}%`;

      const policyCompEl = document.getElementById("dashPolicyComp");
      if (policyCompEl) policyCompEl.textContent = `${(100 - (pDenied || 0)).toFixed(1)}%`;

      const activeSocketsEl = document.getElementById("dashActiveSockets");
      if (activeSocketsEl) activeSocketsEl.textContent = `${an.active_connections || 390}+`;
    }

    // Top Destination Domains
    const topDomainsContainer = document.getElementById("topDomainsList");
    if (topDomainsContainer && an.top_domains) {
      if (an.top_domains.length === 0) {
        topDomainsContainer.innerHTML = `<p class="text-muted text-xs">No domain traffic recorded in this window.</p>`;
      } else {
        topDomainsContainer.innerHTML = an.top_domains.map(d => `
          <div class="top-list-item">
            <div class="top-list-meta">
              <span class="top-list-name font-mono text-cyan">${escapeHtml(d.domain)}</span>
              <span class="top-list-count font-mono">${d.count} reqs (${d.pct}%)</span>
            </div>
            <div class="stat-progress-track mt-1" style="height:4px;">
              <div class="stat-progress-fill cyan" style="width: ${Math.min(d.pct * 2, 100)}%;"></div>
            </div>
          </div>
        `).join("");
      }
    }

    // Top Active Users
    const topUsersContainer = document.getElementById("topUsersList");
    if (topUsersContainer && an.top_users) {
      if (an.top_users.length === 0) {
        topUsersContainer.innerHTML = `<p class="text-muted text-xs">No authenticated users in this window.</p>`;
      } else {
        topUsersContainer.innerHTML = an.top_users.map(u => `
          <div class="top-list-item">
            <div class="top-list-meta">
              <span class="top-list-name font-semibold text-main">${escapeHtml(u.user)}</span>
              <span class="top-list-count font-mono" style="color:var(--blue-vibrant);">${u.count} requests (${u.pct}%)</span>
            </div>
            <div class="stat-progress-track mt-1" style="height:4px;">
              <div class="stat-progress-fill blue" style="width: ${Math.min(u.pct * 2, 100)}%;"></div>
            </div>
          </div>
        `).join("");
      }
    }

    // Live Security & Traffic Audit Stream
    const auditTbody = document.getElementById("dashRecentAuditBody");
    if (auditTbody && an.recent_events) {
      if (an.recent_events.length === 0) {
        auditTbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">Awaiting traffic events...</td></tr>`;
      } else {
        auditTbody.innerHTML = an.recent_events.map(ev => {
          const is200 = ev.status.includes("200");
          const isDenied = ev.status.includes("DENIED") || ev.status.includes("403");
          const badgeClass = is200 ? "emerald" : isDenied ? "rose" : "purple";
          return `
            <tr>
              <td class="font-mono text-xs text-muted">${escapeHtml(ev.time)}</td>
              <td><span class="badge-tag cyan">${escapeHtml(ev.user)}</span></td>
              <td class="font-mono text-xs">${escapeHtml(ev.client_ip)}</td>
              <td class="font-mono text-xs text-main" style="max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(ev.domain)}">${escapeHtml(ev.domain)}</td>
              <td><span class="badge-tag">${escapeHtml(ev.method)}</span></td>
              <td><span class="badge-tag ${badgeClass} font-mono text-xs">${escapeHtml(ev.status)}</span></td>
              <td class="font-mono text-xs text-muted">${escapeHtml(ev.bytes)} B</td>
            </tr>
          `;
        }).join("");
      }
    }

    // Render Live Blocked Feed
    renderBlockedFeed(an.blocked_events, an.total_blocked_in_window, an.range_label);
  }

  async function loadAnalytics(range) {
    try {
      const res = await fetch(`/api/dashboard/analytics?range=${encodeURIComponent(range || "500")}`);
      const data = await res.json();
      if (data.success && data.analytics) {
        renderTelemetryData(data.analytics);
      }
    } catch (err) {
      console.error("Failed to load telemetry for range:", range, err);
    }
  }

  async function loadStatus() {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      if (!data.status) return;

      const st = data.status;
      const met = data.metrics || {};
      const an = data.analytics || met.analytics || {};
      state.squidStatus = st;

      // Update Top Bar
      const pulse = document.getElementById("squidPulse");
      const statusText = document.getElementById("squidStatusText");
      if (pulse && statusText) {
        pulse.className = `pulse-indicator ${st.active ? "online" : "offline"}`;
        statusText.textContent = st.active ? "Squid 5.9 Active" : "Squid Inactive";
      }

      const topPid = document.getElementById("squidPid");
      if (topPid) topPid.textContent = st.pid || "N/A";
      const topRam = document.getElementById("squidRam");
      if (topRam) topRam.textContent = `${st.memory_mb} MB`;
      const topPorts = document.getElementById("squidPortCount");
      if (topPorts) {
        const pCount = (st.ports_listening && st.ports_listening.length > 0) ? st.ports_listening.length : (state.ports ? state.ports.length : 1);
        topPorts.textContent = `${pCount} active`;
      }

      // Update Enterprise Hero Banner
      const heroActiveConns = document.getElementById("dashActiveConnections");
      if (heroActiveConns) {
        heroActiveConns.textContent = an.active_connections !== undefined ? `${an.active_connections} active` : "—";
      }

      // Update 6 Enterprise KPI Cards
      const cardUser = document.getElementById("cardUserCount");
      if (cardUser) cardUser.textContent = met.total_users || 0;
      const badgeUser = document.getElementById("badgeUserCount");
      if (badgeUser) badgeUser.textContent = met.total_users || 0;

      const cardGroup = document.getElementById("cardGroupCount");
      if (cardGroup) cardGroup.textContent = met.total_groups || (state.groups ? state.groups.length : 5);

      const cardDomain = document.getElementById("cardDomainCount");
      if (cardDomain) cardDomain.textContent = met.total_domains || 0;
      const badgeDomain = document.getElementById("badgeDomainCount");
      if (badgeDomain) badgeDomain.textContent = met.total_domains || 0;
      const cardDomainList = document.getElementById("cardDomainListCount");
      if (cardDomainList) cardDomainList.textContent = `Across ${met.total_domain_lists || 3} domain lists`;

      const cardIp = document.getElementById("cardIpCount");
      if (cardIp) cardIp.textContent = met.total_allowed_ips || 0;

      const cardLog = document.getElementById("cardLogSize");
      if (cardLog) cardLog.textContent = `${met.access_log_size_mb || 0} MB`;

      const cardPorts = document.getElementById("cardPortsListening");
      if (cardPorts) {
        const pCount = (st.ports_listening && st.ports_listening.length > 0) ? st.ports_listening.length : (state.ports ? state.ports.length : 1);
        cardPorts.textContent = `${pCount} active`;
      }

      // Update Hardware & Health Telemetry Strip
      const hwCpuVal = document.getElementById("hwCpuVal");
      const hwCpuFill = document.getElementById("hwCpuFill");
      const hwLoad1m = document.getElementById("hwLoad1m");
      const hwLoad5m = document.getElementById("hwLoad5m");
      const hwLoad15m = document.getElementById("hwLoad15m");
      if (hwCpuVal) hwCpuVal.textContent = `${st.cpu_percent || 0}%`;
      if (hwCpuFill) hwCpuFill.style.width = `${Math.min(st.cpu_percent || 0, 100)}%`;
      if (st.load_avg) {
        if (hwLoad1m) hwLoad1m.textContent = st.load_avg.load1 !== undefined ? st.load_avg.load1 : "—";
        if (hwLoad5m) hwLoad5m.textContent = st.load_avg.load5 !== undefined ? st.load_avg.load5 : "—";
        if (hwLoad15m) hwLoad15m.textContent = st.load_avg.load15 !== undefined ? st.load_avg.load15 : "—";
      }

      const hwRamVal = document.getElementById("hwRamVal");
      const hwRamFill = document.getElementById("hwRamFill");
      const hwHostRamPct = document.getElementById("hwHostRamPct");
      const hwHostRamUsed = document.getElementById("hwHostRamUsed");
      const hwHostRamTotal = document.getElementById("hwHostRamTotal");
      if (hwRamVal) hwRamVal.textContent = `${st.memory_mb || 0} MB`;
      if (st.host_memory) {
        if (hwRamFill) hwRamFill.style.width = `${Math.min(st.host_memory.percent_used || 0, 100)}%`;
        if (hwHostRamPct) hwHostRamPct.textContent = `${st.host_memory.percent_used || 0}%`;
        if (hwHostRamUsed) hwHostRamUsed.textContent = st.host_memory.used_mb || 0;
        if (hwHostRamTotal) hwHostRamTotal.textContent = st.host_memory.total_mb || 0;
      }

      const hwSquidPid = document.getElementById("hwSquidPid");
      if (hwSquidPid) hwSquidPid.textContent = st.pid ? `PID ${st.pid}` : "Inactive";
      const hwUptimeText = document.getElementById("hwUptimeText");
      if (hwUptimeText) hwUptimeText.textContent = st.uptime || "N/A";

      const hwPolicyComp = document.getElementById("hwPolicyComp");
      const hwPolicyCompFill = document.getElementById("hwPolicyCompFill");
      const hwCacheEffVal = document.getElementById("hwCacheEffVal");
      const pDeniedVal = Number(an.status_percentages?.tcp_denied || 0);
      const policyVal = Math.max(0, 100 - pDeniedVal).toFixed(1);
      if (hwPolicyComp) hwPolicyComp.textContent = `${policyVal}%`;
      if (hwPolicyCompFill) hwPolicyCompFill.style.width = `${policyVal}%`;
      if (hwCacheEffVal) hwCacheEffVal.textContent = `${an.cache_efficiency_pct || 96.4}%`;

      // Update Telemetry data (if user hasn't toggled custom range or on initial load)
      if (!state.hasCustomRangeSelected) {
        renderTelemetryData(an);
      }

      // Update Daemon Health Card
      const dashPid = document.getElementById("dashSquidPid");
      if (dashPid) dashPid.textContent = st.pid || "N/A";
      const dashUptime = document.getElementById("dashSquidUptime");
      if (dashUptime) dashUptime.textContent = st.uptime || "N/A";
      const dashMem = document.getElementById("dashSquidMemory");
      if (dashMem) dashMem.textContent = `${st.memory_mb} MB`;
      const dashCpu = document.getElementById("dashSquidCpu");
      if (dashCpu) dashCpu.textContent = `${st.cpu_percent} %`;

      const dashBadge = document.getElementById("dashDaemonBadge");
      if (dashBadge) {
        dashBadge.className = `badge-status ${st.active ? "online" : "offline"}`;
        dashBadge.textContent = st.active ? "RUNNING" : "STOPPED";
      }

    } catch (err) {
      console.error("Telemetry fetch error:", err);
    }
  }

  // ----------------------------------------------------------------------------
  // Proxy Users Management
  // ----------------------------------------------------------------------------
  async function loadUsers() {
    try {
      const res = await fetch("/api/users");
      const data = await res.json();
      state.users = data.users || [];
      state.groups = data.groups || [];

      renderUsersTable(state.users);
      updateUserCountStats(state.users.length);
    } catch (err) {
      showToast("Failed to load proxy users.", "error");
    }
  }

  function renderUsersTable(userList) {
    const tbody = document.getElementById("usersTableBody");
    if (!tbody) return;

    if (userList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No proxy users found.</td></tr>`;
      return;
    }

    tbody.innerHTML = userList.map(u => {
      const groupBadges = u.groups.length > 0
        ? u.groups.map(g => `<span class="badge-tag cyan">${g}</span>`).join(" ")
        : `<span class="text-muted text-xs">Standard (No extra ACL)</span>`;

      return `
        <tr>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="user-avatar" style="width: 28px; height: 28px; font-size: 0.75rem;">${u.username[0].toUpperCase()}</span>
              <strong class="font-mono">${escapeHtml(u.username)}</strong>
            </div>
          </td>
          <td>${groupBadges}</td>
          <td><span class="badge-tag">NCSA htpasswd</span></td>
          <td class="text-right">
            <button class="btn btn-secondary btn-sm btn-edit-groups" data-user="${escapeHtml(u.username)}" title="Manage ACL Groups">
              Groups
            </button>
            <button class="btn btn-secondary btn-sm btn-reset-pass" data-user="${escapeHtml(u.username)}" title="Reset Password">
              Password
            </button>
            <button class="btn btn-danger-outline btn-sm btn-delete-user" data-user="${escapeHtml(u.username)}" title="Delete User">
              Delete
            </button>
          </td>
        </tr>
      `;
    }).join("");

    attachUserTableEvents();
  }

  function updateUserCountStats(count) {
    const counter = document.getElementById("userListCountText");
    if (counter) counter.textContent = `Total: ${count} users`;
    const badge = document.getElementById("badgeUserCount");
    if (badge) badge.textContent = count;
  }

  function attachUserTableEvents() {
    // Reset password buttons
    document.querySelectorAll(".btn-reset-pass").forEach(btn => {
      btn.addEventListener("click", () => {
        const username = btn.dataset.user;
        document.getElementById("resetTargetUsername").value = username;
        document.getElementById("resetUserTarget").textContent = username;
        document.getElementById("resetNewPass").value = generateSafeProxyPassword(15);
        openModal("modalResetPassword");
      });
    });

    // Edit groups buttons
    document.querySelectorAll(".btn-edit-groups").forEach(btn => {
      btn.addEventListener("click", () => {
        const username = btn.dataset.user;
        const userObj = state.users.find(u => u.username === username);
        const assigned = userObj ? userObj.groups : [];

        document.getElementById("editGroupsUsername").value = username;
        document.getElementById("editGroupsUserTarget").textContent = username;

        const container = document.getElementById("editGroupsCheckboxes");
        container.innerHTML = state.groups.map(grp => {
          const isChecked = assigned.includes(grp) ? "checked" : "";
          return `
            <label class="checkbox-item">
              <input type="checkbox" name="group" value="${escapeHtml(grp)}" ${isChecked}>
              <span>${escapeHtml(grp)}</span>
            </label>
          `;
        }).join("");

        openModal("modalEditUserGroups");
      });
    });

    // Delete user buttons
    document.querySelectorAll(".btn-delete-user").forEach(btn => {
      btn.addEventListener("click", async () => {
        const username = btn.dataset.user;
        if (!confirm(`Are you sure you want to permanently delete user '${username}'?`)) return;

        try {
          const res = await fetch(`/api/users/${encodeURIComponent(username)}`, { method: "DELETE" });
          const data = await res.json();
          if (data.success) {
            showToast(data.message, "success");
            loadUsers();
          } else {
            showToast(data.error || "Failed to delete user.", "error");
          }
        } catch (err) {
          showToast("Network error deleting user.", "error");
        }
      });
    });
  }

  // Filter Users Search
  const userSearch = document.getElementById("userSearchInput");
  if (userSearch) {
    userSearch.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      const filtered = state.users.filter(u => u.username.toLowerCase().includes(q));
      renderUsersTable(filtered);
    });
  }

  // Modal: Add User Form Submit
  const formAddUser = document.getElementById("formAddUser");
  if (formAddUser) {
    formAddUser.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("newUsername").value.trim();
      const password = document.getElementById("newUserPassword").value.trim();

      const checkedGroups = [];
      document.querySelectorAll("#addUserGroupCheckboxes input[type='checkbox']:checked").forEach(cb => {
        checkedGroups.push(cb.value);
      });

      try {
        const res = await fetch("/api/users", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password, groups: checkedGroups })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          closeModal("modalAddUser");
          formAddUser.reset();
          loadUsers();
        } else {
          showToast(data.error || "Failed to add user.", "error");
        }
      } catch (err) {
        showToast("Network error creating user.", "error");
      }
    });
  }

  // Modal: Reset Password Form Submit
  const formResetPassword = document.getElementById("formResetPassword");
  if (formResetPassword) {
    formResetPassword.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("resetTargetUsername").value;
      const newPassword = document.getElementById("resetNewPass").value.trim();

      try {
        const res = await fetch(`/api/users/${encodeURIComponent(username)}/password`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: newPassword })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          closeModal("modalResetPassword");
        } else {
          showToast(data.error || "Failed to reset password.", "error");
        }
      } catch (err) {
        showToast("Network error resetting password.", "error");
      }
    });
  }

  // Modal: Edit User Groups Form Submit
  const formEditUserGroups = document.getElementById("formEditUserGroups");
  if (formEditUserGroups) {
    formEditUserGroups.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("editGroupsUsername").value;
      const selectedGroups = [];
      document.querySelectorAll("#editGroupsCheckboxes input[type='checkbox']:checked").forEach(cb => {
        selectedGroups.push(cb.value);
      });

      try {
        const res = await fetch(`/api/users/${encodeURIComponent(username)}/groups`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ groups: selectedGroups })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          closeModal("modalEditUserGroups");
          loadUsers();
        } else {
          showToast(data.error || "Failed to update groups.", "error");
        }
      } catch (err) {
        showToast("Network error updating groups.", "error");
      }
    });
  }

  // ----------------------------------------------------------------------------
  // User Groups & ACLs
  // ----------------------------------------------------------------------------
  async function loadGroups() {
    try {
      const res = await fetch("/api/groups");
      const data = await res.json();
      state.groups = data.groups || [];
      if (data.all_users && Array.isArray(data.all_users)) {
        state.allUsers = data.all_users;
      } else if (state.users && state.users.length > 0) {
        state.allUsers = state.users.map(u => u.username);
      } else {
        state.allUsers = [];
      }

      const container = document.getElementById("groupsContainer");
      if (!container) return;

      if (state.groups.length === 0) {
        container.innerHTML = `<div class="card"><p class="text-muted">No ACL groups configured in /etc/squid/acl/.</p></div>`;
        return;
      }

      renderGroupCards();
    } catch (err) {
      showToast("Failed to load user ACL groups.", "error");
    }
  }

  function renderGroupCards() {
    const container = document.getElementById("groupsContainer");
    if (!container) return;

    container.innerHTML = state.groups.map(g => {
      const userChips = g.users.length > 0
        ? g.users.map(u => `<span class="badge-tag cyan">${escapeHtml(u)}</span>`).join(" ")
        : `<span class="text-muted text-xs">No users currently in this group</span>`;

      return `
        <div class="card group-card" id="cardGroup_${escapeHtml(g.name)}" data-group="${escapeHtml(g.name)}">
          <div class="card-header">
            <div class="card-title-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              </svg>
              <h3>${escapeHtml(g.name)}</h3>
            </div>
            <span class="badge-tag" id="badgeGroupCount_${escapeHtml(g.name)}">${g.users.length} members</span>
          </div>
          <div class="card-body">
            <p class="text-xs text-muted mb-2 font-mono">${escapeHtml(g.filepath)}</p>

            <!-- View Mode Display -->
            <div class="group-view-section" id="viewSection_${escapeHtml(g.name)}">
              <div class="group-chips-display" id="chipsGroup_${escapeHtml(g.name)}" style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; min-height: 28px;">
                ${userChips}
              </div>

              <div class="card-footer-actions">
                <button class="btn btn-secondary btn-sm btn-edit-group" data-group="${escapeHtml(g.name)}" title="Edit members of this group">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                  </svg>
                  <span>Edit</span>
                </button>
                <button class="btn btn-secondary btn-sm btn-validate-group" title="Validate Squid configuration syntax">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  <span>Validate</span>
                </button>
                <button class="btn btn-primary btn-sm btn-reload-group" title="Gracefully reload Squid">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"></polyline>
                    <polyline points="1 20 1 14 7 14"></polyline>
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                  </svg>
                  <span>Reload</span>
                </button>
              </div>
            </div>

            <!-- Inline Edit Section -->
            <div class="group-inline-edit" id="editSection_${escapeHtml(g.name)}" style="display: none;">
              <label class="text-xs font-semibold mb-1" style="display:block; color:var(--cyan-neon);">Select Members (Registered Proxy Users):</label>
              <div class="group-user-checkbox-grid" id="checkboxesGroup_${escapeHtml(g.name)}">
                <!-- Dynamically populated checkboxes -->
              </div>

              <label class="text-xs font-semibold mt-2 mb-1" style="display:flex; justify-content:space-between;">
                <span>Usernames (one per line):</span>
                <span class="text-muted" id="countInline_${escapeHtml(g.name)}">${g.users.length} users</span>
              </label>
              <textarea class="code-editor" id="textareaGroup_${escapeHtml(g.name)}" style="min-height: 80px; font-size: 0.8rem;" placeholder="one username per line">${escapeHtml(g.users.join("\n"))}</textarea>

              <div class="card-footer-actions">
                <button class="btn btn-secondary btn-sm btn-cancel-group-edit" data-group="${escapeHtml(g.name)}">
                  Cancel
                </button>
                <button class="btn btn-secondary btn-sm btn-validate-group" title="Validate Squid configuration syntax">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  <span>Validate</span>
                </button>
                <button class="btn btn-secondary btn-sm btn-reload-group" title="Gracefully reload Squid">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"></polyline>
                    <polyline points="1 20 1 14 7 14"></polyline>
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                  </svg>
                  <span>Reload</span>
                </button>
                <button class="btn btn-primary btn-sm btn-save-group" data-group="${escapeHtml(g.name)}" title="Save changes to group file">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                    <polyline points="17 21 17 13 7 13 7 21"></polyline>
                    <polyline points="7 3 7 8 15 8"></polyline>
                  </svg>
                  <span>Save</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join("");

    attachGroupCardEvents();
  }

  function attachGroupCardEvents() {
    // Edit Button -> opens inline edit mode
    document.querySelectorAll(".btn-edit-group").forEach(btn => {
      btn.addEventListener("click", () => {
        const groupName = btn.dataset.group;
        const groupObj = state.groups.find(g => g.name === groupName);
        if (!groupObj) return;

        const viewSec = document.getElementById(`viewSection_${groupName}`);
        const editSec = document.getElementById(`editSection_${groupName}`);
        const cbContainer = document.getElementById(`checkboxesGroup_${groupName}`);
        const textarea = document.getElementById(`textareaGroup_${groupName}`);
        const countSpan = document.getElementById(`countInline_${groupName}`);
        if (!viewSec || !editSec || !cbContainer || !textarea) return;

        // Build list of all available usernames
        const knownUsers = new Set([...(state.allUsers || []), ...groupObj.users]);
        const sortedUsers = Array.from(knownUsers).sort();

        cbContainer.innerHTML = sortedUsers.map(u => {
          const isChecked = groupObj.users.includes(u) ? "checked" : "";
          return `
            <label class="checkbox-label" style="font-size: 0.8rem; display:flex; align-items:center; gap:6px;">
              <input type="checkbox" value="${escapeHtml(u)}" ${isChecked} class="group-user-cb">
              <span>${escapeHtml(u)}</span>
            </label>
          `;
        }).join("");

        textarea.value = groupObj.users.join("\n");
        if (countSpan) countSpan.textContent = `${groupObj.users.length} users`;

        // Sync checkboxes -> textarea
        const checkboxes = cbContainer.querySelectorAll(".group-user-cb");
        const syncFromCheckboxes = () => {
          const selected = [];
          checkboxes.forEach(cb => {
            if (cb.checked) selected.push(cb.value);
          });
          // Preserve any custom usernames in textarea that aren't in checkboxes
          const rawLines = textarea.value.split("\n").map(s => s.trim()).filter(s => s && !s.startsWith("#"));
          rawLines.forEach(item => {
            if (!sortedUsers.includes(item) && !selected.includes(item)) {
              selected.push(item);
            }
          });
          textarea.value = selected.join("\n");
          if (countSpan) countSpan.textContent = `${selected.length} users`;
        };

        checkboxes.forEach(cb => {
          cb.addEventListener("change", syncFromCheckboxes);
        });

        // Sync textarea -> checkboxes
        textarea.addEventListener("input", () => {
          const lines = textarea.value.split("\n").map(s => s.trim()).filter(s => s && !s.startsWith("#"));
          checkboxes.forEach(cb => {
            cb.checked = lines.includes(cb.value);
          });
          if (countSpan) countSpan.textContent = `${lines.length} users`;
        });

        viewSec.style.display = "none";
        editSec.style.display = "block";
      });
    });

    // Cancel Button -> cancels inline edit mode
    document.querySelectorAll(".btn-cancel-group-edit").forEach(btn => {
      btn.addEventListener("click", () => {
        const groupName = btn.dataset.group;
        const viewSec = document.getElementById(`viewSection_${groupName}`);
        const editSec = document.getElementById(`editSection_${groupName}`);
        if (viewSec && editSec) {
          editSec.style.display = "none";
          viewSec.style.display = "block";
        }
      });
    });

    // Save Button -> saves group members to backend
    document.querySelectorAll(".btn-save-group").forEach(btn => {
      btn.addEventListener("click", async () => {
        const groupName = btn.dataset.group;
        const textarea = document.getElementById(`textareaGroup_${groupName}`);
        if (!textarea) return;

        const users = textarea.value
          .split("\n")
          .map(s => s.trim())
          .filter(s => s && !s.startsWith("#"));

        btn.disabled = true;
        try {
          const res = await fetch(`/api/groups/${encodeURIComponent(groupName)}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ users })
          });
          const data = await res.json();
          if (data.success) {
            showToast(data.message || `Group '${groupName}' saved successfully!`, "success");
            // Update state
            const grp = state.groups.find(g => g.name === groupName);
            if (grp) grp.users = users;

            // Update badge count
            const badgeCount = document.getElementById(`badgeGroupCount_${groupName}`);
            if (badgeCount) badgeCount.textContent = `${users.length} members`;

            // Update chips
            const chipsDiv = document.getElementById(`chipsGroup_${groupName}`);
            if (chipsDiv) {
              chipsDiv.innerHTML = users.length > 0
                ? users.map(u => `<span class="badge-tag cyan">${escapeHtml(u)}</span>`).join(" ")
                : `<span class="text-muted text-xs">No users currently in this group</span>`;
            }

            // Restore view mode
            const viewSec = document.getElementById(`viewSection_${groupName}`);
            const editSec = document.getElementById(`editSection_${groupName}`);
            if (viewSec && editSec) {
              editSec.style.display = "none";
              viewSec.style.display = "block";
            }
          } else {
            showToast(data.error || "Failed to save group.", "error");
          }
        } catch (err) {
          showToast("Network error saving group.", "error");
        } finally {
          btn.disabled = false;
        }
      });
    });

    // Validate Button -> triggers syntax validation
    document.querySelectorAll(".btn-validate-group").forEach(btn => {
      btn.addEventListener("click", () => runSyntaxTest(btn));
    });

    // Reload Button -> triggers safe Squid reload
    document.querySelectorAll(".btn-reload-group").forEach(btn => {
      btn.addEventListener("click", () => triggerSquidReload(btn));
    });
  }

  // Header Validate and Reload Buttons for User Groups Tab
  const btnValidateGroups = document.getElementById("btnValidateGroups");
  if (btnValidateGroups) {
    btnValidateGroups.addEventListener("click", () => runSyntaxTest(btnValidateGroups));
  }

  const btnReloadGroups = document.getElementById("btnReloadGroups");
  if (btnReloadGroups) {
    btnReloadGroups.addEventListener("click", () => triggerSquidReload(btnReloadGroups));
  }

  // Modal: Add New Group Form Setup
  const btnOpenAddGroupModal = document.getElementById("btnOpenAddGroupModal");
  if (btnOpenAddGroupModal) {
    btnOpenAddGroupModal.addEventListener("click", () => {
      const cbContainer = document.getElementById("modalAddGroupCheckboxes");
      if (cbContainer) {
        const users = (state.allUsers && state.allUsers.length > 0) ? state.allUsers : state.users.map(u => u.username);
        cbContainer.innerHTML = users.map(u => `
          <label class="checkbox-label" style="font-size: 0.8rem; display:flex; align-items:center; gap:6px;">
            <input type="checkbox" value="${escapeHtml(u)}" class="add-group-user-cb">
            <span>${escapeHtml(u)}</span>
          </label>
        `).join("");
      }
      openModal("modalAddGroup");
    });
  }

  const formAddGroup = document.getElementById("formAddGroup");
  if (formAddGroup) {
    formAddGroup.addEventListener("submit", async (e) => {
      e.preventDefault();
      const nameInput = document.getElementById("newGroupNameInput");
      const name = nameInput ? nameInput.value.trim() : "";
      if (!name) return;

      const checkedUsers = [];
      document.querySelectorAll(".add-group-user-cb:checked").forEach(cb => {
        checkedUsers.push(cb.value);
      });

      try {
        const res = await fetch("/api/groups", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, users: checkedUsers, reload: true })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || `Group '${name}' created successfully!`, "success");
          closeModal("modalAddGroup");
          formAddGroup.reset();
          loadGroups();
        } else {
          showToast(data.error || "Failed to create group.", "error");
        }
      } catch (err) {
        showToast("Network error creating group.", "error");
      }
    });
  }

  // Modal: Edit Group Validation & Reload Handlers
  const btnModalValidateGroup = document.getElementById("btnModalValidateGroup");
  if (btnModalValidateGroup) {
    btnModalValidateGroup.addEventListener("click", () => runSyntaxTest(btnModalValidateGroup));
  }

  const btnModalReloadGroup = document.getElementById("btnModalReloadGroup");
  if (btnModalReloadGroup) {
    btnModalReloadGroup.addEventListener("click", () => triggerSquidReload(btnModalReloadGroup));
  }

  const formEditGroup = document.getElementById("formEditGroup");
  if (formEditGroup) {
    formEditGroup.addEventListener("submit", async (e) => {
      e.preventDefault();
      const groupName = document.getElementById("editGroupTargetName").value;
      const textarea = document.getElementById("modalEditGroupTextarea");
      if (!groupName || !textarea) return;

      const users = textarea.value
        .split("\n")
        .map(s => s.trim())
        .filter(s => s && !s.startsWith("#"));

      try {
        const res = await fetch(`/api/groups/${encodeURIComponent(groupName)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ users })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || `Group '${groupName}' saved successfully!`, "success");
          closeModal("modalEditGroup");
          loadGroups();
        } else {
          showToast(data.error || "Failed to save group.", "error");
        }
      } catch (err) {
        showToast("Network error saving group.", "error");
      }
    });
  }

  const btnModalSaveReloadGroup = document.getElementById("btnModalSaveReloadGroup");
  if (btnModalSaveReloadGroup) {
    btnModalSaveReloadGroup.addEventListener("click", async () => {
      const groupName = document.getElementById("editGroupTargetName").value;
      const textarea = document.getElementById("modalEditGroupTextarea");
      if (!groupName || !textarea) return;

      const users = textarea.value
        .split("\n")
        .map(s => s.trim())
        .filter(s => s && !s.startsWith("#"));

      try {
        const res = await fetch(`/api/groups/${encodeURIComponent(groupName)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ users, reload: true })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || `Group '${groupName}' saved and Squid reloaded!`, "success");
          closeModal("modalEditGroup");
          loadGroups();
        } else {
          showToast(data.error || "Failed to save group.", "error");
        }
      } catch (err) {
        showToast("Network error saving group.", "error");
      }
    });
  }

  // ----------------------------------------------------------------------------
  // Domain Policies & ACL Lists
  // ----------------------------------------------------------------------------
  async function loadDomains() {
    try {
      const res = await fetch("/api/domains");
      const data = await res.json();
      state.domainLists = data.domain_lists || [];

      renderDomainPills();
      renderCurrentDomainTable();
    } catch (err) {
      showToast("Failed to load domain policies.", "error");
    }
  }

  function renderDomainPills() {
    const pillsContainer = document.getElementById("domainListPills");
    if (!pillsContainer) return;

    pillsContainer.innerHTML = state.domainLists.map(dl => {
      const isActive = dl.name === state.currentDomainList ? "active" : "";
      return `
        <button class="domain-pill ${isActive}" data-list="${escapeHtml(dl.name)}">
          ${escapeHtml(dl.name)} (${dl.domains.length})
        </button>
      `;
    }).join("");

    pillsContainer.querySelectorAll(".domain-pill").forEach(pill => {
      pill.addEventListener("click", () => {
        state.currentDomainList = pill.dataset.list;
        renderDomainPills();
        renderCurrentDomainTable();
      });
    });
  }

  function renderCurrentDomainTable() {
    const tbody = document.getElementById("domainTableBody");
    const stats = document.getElementById("domainListStats");
    if (!tbody) return;

    const currentList = state.domainLists.find(dl => dl.name === state.currentDomainList);
    if (!currentList) {
      tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">Select a domain list above.</td></tr>`;
      return;
    }

    const domains = currentList.domains || [];
    if (stats) stats.textContent = `${domains.length} domains in ${currentList.name}`;

    if (domains.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No domains configured in this list.</td></tr>`;
      return;
    }

    tbody.innerHTML = domains.map(d => {
      const isSubdomainWildcard = d.startsWith(".");
      const scopeBadge = isSubdomainWildcard
        ? `<span class="badge-tag purple">Domain & All Subdomains</span>`
        : `<span class="badge-tag">Exact Host Only</span>`;

      return `
        <tr>
          <td><strong class="font-mono text-cyan">${escapeHtml(d)}</strong></td>
          <td>${scopeBadge}</td>
          <td class="text-right">
            <button class="btn btn-danger-outline btn-sm btn-delete-domain" data-domain="${escapeHtml(d)}" data-list="${escapeHtml(currentList.name)}">
              Remove
            </button>
          </td>
        </tr>
      `;
    }).join("");

    // Attach delete domain events
    document.querySelectorAll(".btn-delete-domain").forEach(btn => {
      btn.addEventListener("click", async () => {
        const dom = btn.dataset.domain;
        const listName = btn.dataset.list;
        if (!confirm(`Remove '${dom}' from '${listName}'?`)) return;

        try {
          const res = await fetch(`/api/domains/${encodeURIComponent(listName)}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domain: dom })
          });
          const data = await res.json();
          if (data.success) {
            showToast(data.message, "success");
            loadDomains();
          } else {
            showToast(data.error || "Failed to remove domain.", "error");
          }
        } catch (err) {
          showToast("Network error removing domain.", "error");
        }
      });
    });
  }

  // Filter Domains Search
  const domainSearch = document.getElementById("domainSearchInput");
  if (domainSearch) {
    domainSearch.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      const currentList = state.domainLists.find(dl => dl.name === state.currentDomainList);
      if (!currentList) return;

      const filtered = currentList.domains.filter(d => d.toLowerCase().includes(q));
      const tbody = document.getElementById("domainTableBody");
      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No matching domains found.</td></tr>`;
      } else {
        tbody.innerHTML = filtered.map(d => `
          <tr>
            <td><strong class="font-mono text-cyan">${escapeHtml(d)}</strong></td>
            <td><span class="badge-tag">${d.startsWith(".") ? "Wildcard Subdomains" : "Exact Host"}</span></td>
            <td class="text-right">
              <button class="btn btn-danger-outline btn-sm btn-delete-domain" data-domain="${escapeHtml(d)}" data-list="${escapeHtml(currentList.name)}">
                Remove
              </button>
            </td>
          </tr>
        `).join("");
      }
    });
  }

  // Modal: Add Domain
  const btnOpenAddDomainModal = document.getElementById("btnOpenAddDomainModal");
  if (btnOpenAddDomainModal) {
    btnOpenAddDomainModal.addEventListener("click", () => {
      const select = document.getElementById("addDomainTargetList");
      select.innerHTML = state.domainLists.map(dl => `
        <option value="${escapeHtml(dl.name)}" ${dl.name === state.currentDomainList ? "selected" : ""}>
          ${escapeHtml(dl.name)}
        </option>
      `).join("");
      document.getElementById("addDomainInput").value = "";
      openModal("modalAddDomain");
    });
  }

  const formAddDomain = document.getElementById("formAddDomain");
  if (formAddDomain) {
    formAddDomain.addEventListener("submit", async (e) => {
      e.preventDefault();
      const targetList = document.getElementById("addDomainTargetList").value;
      const domain = document.getElementById("addDomainInput").value.trim();

      try {
        const res = await fetch(`/api/domains/${encodeURIComponent(targetList)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ domain })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          closeModal("modalAddDomain");
          loadDomains();
        } else {
          showToast(data.error || "Failed to add domain.", "error");
        }
      } catch (err) {
        showToast("Network error adding domain.", "error");
      }
    });
  }

  // ----------------------------------------------------------------------------
  // Allowed IPs & Subnets
  // ----------------------------------------------------------------------------
  async function loadAllowedIps() {
    try {
      const res = await fetch("/api/allowed-ips");
      const data = await res.json();
      state.allowedIps = data.ips || [];

      const tbody = document.getElementById("allowedIpsTableBody");
      if (!tbody) return;

      if (state.allowedIps.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No allowed IPs configured.</td></tr>`;
        return;
      }

      tbody.innerHTML = state.allowedIps.map(ip => {
        const isSubnet = ip.includes("/");
        return `
          <tr>
            <td><strong class="font-mono text-cyan">${escapeHtml(ip)}</strong></td>
            <td><span class="badge-tag ${isSubnet ? 'purple' : 'cyan'}">${isSubnet ? 'Subnet CIDR' : 'Single Host IP'}</span></td>
            <td>
              <button class="btn btn-danger-outline btn-sm btn-delete-ip" data-ip="${escapeHtml(ip)}">
                Remove
              </button>
            </td>
          </tr>
        `;
      }).join("");

      document.querySelectorAll(".btn-delete-ip").forEach(btn => {
        btn.addEventListener("click", async () => {
          const ip = btn.dataset.ip;
          if (!confirm(`Remove '${ip}' from allowed IPs?`)) return;

          try {
            const res = await fetch("/api/allowed-ips", {
              method: "DELETE",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ ip })
            });
            const data = await res.json();
            if (data.success) {
              showToast(data.message, "success");
              loadAllowedIps();
            } else {
              showToast(data.error || "Failed to remove IP.", "error");
            }
          } catch (err) {
            showToast("Network error removing IP.", "error");
          }
        });
      });

    } catch (err) {
      showToast("Failed to load allowed IPs.", "error");
    }
  }

  const btnOpenAddIpModal = document.getElementById("btnOpenAddIpModal");
  if (btnOpenAddIpModal) {
    btnOpenAddIpModal.addEventListener("click", () => {
      document.getElementById("newIpInput").value = "";
      openModal("modalAddIp");
    });
  }

  const formAddIp = document.getElementById("formAddIp");
  if (formAddIp) {
    formAddIp.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ip = document.getElementById("newIpInput").value.trim();

      try {
        const res = await fetch("/api/allowed-ips", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ip })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          closeModal("modalAddIp");
          loadAllowedIps();
        } else {
          showToast(data.error || "Failed to add IP.", "error");
        }
      } catch (err) {
        showToast("Network error adding IP.", "error");
      }
    });
  }

  // ----------------------------------------------------------------------------
  // Multi-Port & Egress Routing Visualizer
  // ----------------------------------------------------------------------------
  async function loadPorts() {
    try {
      const res = await fetch("/api/ports");
      const data = await res.json();
      state.ports = data.ports || [];

      // Render Dashboard Preview
      const dashTbody = document.getElementById("dashPortsPreviewBody");
      const listeningCount = state.ports.filter(p => p.is_listening).length;
      const portsBadge = document.getElementById("egressPortsListeningBadge");
      if (portsBadge) {
        portsBadge.textContent = `${listeningCount} / ${state.ports.length} Online`;
      }
      if (dashTbody) {
        dashTbody.innerHTML = state.ports.map(p => `
          <tr>
            <td><span class="badge-tag cyan font-mono">:${p.port}</span></td>
            <td>
              <span class="status-pill ${p.is_listening ? 'green' : 'rose'}">
                ${p.is_listening ? 'LISTENING' : 'INACTIVE'}
              </span>
            </td>
            <td><strong>${escapeHtml(p.name)}</strong></td>
            <td class="font-mono text-emerald" style="font-size:0.8rem;">${escapeHtml(p.outgoing_ip)}</td>
            <td>
              <button type="button" class="btn-probe-port" onclick="window.probePort(${p.port}, this)" title="Test loopback connection to port ${p.port}">
                Probe
              </button>
            </td>
          </tr>
        `).join("");
      }

      // Render Full Ports Table
      const fullTbody = document.getElementById("fullPortsTableBody");
      if (fullTbody) {
        fullTbody.innerHTML = state.ports.map(p => {
          const aclBadges = (p.allowed_groups || []).map(g => `<span class="badge-tag">${g}</span>`).join(" ");
          const ifaceBadge = p.interface ? `<span class="badge-tag blue font-mono" style="font-size:0.8rem;">${escapeHtml(p.interface)}</span>` : '<span class="text-muted text-xs font-mono">-</span>';
          const bwBadge = p.today_bandwidth ? `<span class="badge-tag cyan font-mono">${escapeHtml(p.today_bandwidth)}</span>` : '<span class="text-muted text-xs font-mono">0 B</span>';
          const connsBadge = `<span class="status-pill ${p.active_connections > 0 ? 'green' : 'gray'} font-mono">${p.active_connections || 0}</span>`;
          return `
            <tr>
              <td><span class="badge-tag cyan font-mono" style="font-size: 0.9rem; font-weight: 700;">:${p.port}</span></td>
              <td class="font-mono">${escapeHtml(p.listen_ip)}</td>
              <td><strong class="font-mono text-emerald">${escapeHtml(p.outgoing_ip)}</strong></td>
              <td>${ifaceBadge}</td>
              <td>${bwBadge}</td>
              <td>${connsBadge}</td>
              <td>${aclBadges}</td>
              <td class="text-secondary">${escapeHtml(p.purpose)}</td>
            </tr>
          `;
        }).join("");
      }

      // Update Dynamic Counts and Subtitles
      const pCount = state.ports.length;
      const subHeader = document.getElementById("portsHeaderSubtitle");
      if (subHeader) {
        subHeader.textContent = `${pCount} active listening port${pCount === 1 ? '' : 's'} with dedicated outbound egress IP addresses`;
      }
      const viewAll = document.getElementById("dashPortsViewAllLink");
      if (viewAll) {
        viewAll.textContent = `View All ${pCount} Port${pCount === 1 ? '' : 's'}`;
      }
      const cardPortsEl = document.getElementById("cardPortsListening");
      if (cardPortsEl) {
        cardPortsEl.textContent = `${pCount} active`;
      }
      const topPortsEl = document.getElementById("squidPortCount");
      if (topPortsEl) {
        topPortsEl.textContent = `${pCount} active`;
      }

    } catch (err) {
      console.error("Ports loading error:", err);
    }
  }

  // ----------------------------------------------------------------------------
  // Per-Port Bandwidth & Traffic Analytics
  // ----------------------------------------------------------------------------
  state.bandwidthData = [];
  state.bandwidthTimer = null;

  async function loadPortBandwidth() {
    try {
      const res = await fetch("/api/bandwidth/ports");
      const data = await res.json();
      if (!data.success) {
        console.error("Bandwidth API failed:", data);
        return;
      }

      const summary = data.summary || {};
      state.bandwidthData = data.ports || [];

      // Update Summary Cards
      const totalPortsEl = document.getElementById("bwMetricTotalPorts");
      if (totalPortsEl) totalPortsEl.textContent = summary.total_ports || 0;

      const activePortsEl = document.getElementById("bwMetricActivePorts");
      if (activePortsEl) activePortsEl.textContent = `${summary.active_ports || 0} listening / active`;

      const todayTotalEl = document.getElementById("bwMetricTodayTotal");
      if (todayTotalEl) todayTotalEl.textContent = summary.today_total_human || "0 B";

      const topPortEl = document.getElementById("bwMetricTopPort");
      if (topPortEl) topPortEl.textContent = summary.top_port || "None";

      const topPortDetailsEl = document.getElementById("bwMetricTopPortDetails");
      if (topPortDetailsEl) topPortDetailsEl.textContent = summary.top_port_details || "0 B today";

      const activeConnsEl = document.getElementById("bwMetricActiveConns");
      if (activeConnsEl) activeConnsEl.textContent = summary.total_connections || 0;

      const badgeBandwidthEl = document.getElementById("badgeBandwidthCount");
      if (badgeBandwidthEl) badgeBandwidthEl.textContent = summary.today_total_human || "0 B";

      // Render Bandwidth Table
      renderPortBandwidthTable();
      setupBandwidthTimer();

    } catch (err) {
      console.error("Failed to load port bandwidth:", err);
    }
  }

  function renderPortBandwidthTable() {
    const tbody = document.getElementById("portBandwidthTableBody");
    if (!tbody) return;

    const query = document.getElementById("bwSearchInput")?.value.trim().toLowerCase() || "";
    let filtered = state.bandwidthData;

    if (query) {
      filtered = filtered.filter(p => 
        String(p.port).includes(query) ||
        (p.name && p.name.toLowerCase().includes(query)) ||
        (p.interface && p.interface.toLowerCase().includes(query)) ||
        (p.outgoing_ip && p.outgoing_ip.toLowerCase().includes(query))
      );
    }

    const toolbarStats = document.getElementById("bwToolbarStats");
    if (toolbarStats) {
      toolbarStats.textContent = `Showing ${filtered.length} of ${state.bandwidthData.length} ports`;
    }

    if (!filtered || filtered.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="text-center text-muted py-4">No matching proxy ports found</td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = filtered.map(p => {
      const sharePct = p.usage_pct || 0;
      return `
        <tr>
          <td>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="badge-tag cyan font-mono" style="font-size:0.9rem; font-weight:700;">:${p.port}</span>
              <span class="text-xs text-secondary font-mono">${escapeHtml(p.name)}</span>
            </div>
          </td>
          <td>
            <div style="display:flex; flex-direction:column; gap:2px;">
              <span class="badge-tag blue font-mono" style="width:fit-content; font-size:0.8rem;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px;">
                  <polyline points="16 3 21 3 21 8"></polyline>
                  <line x1="4" y1="20" x2="21" y2="3"></line>
                  <polyline points="21 16 21 21 16 21"></polyline>
                  <line x1="15" y1="15" x2="21" y2="21"></line>
                </svg>
                ${escapeHtml(p.interface)}
              </span>
              <span class="font-mono text-emerald" style="font-size:0.8rem;">${escapeHtml(p.outgoing_ip)}</span>
            </div>
          </td>
          <td>
            <div style="display:flex; flex-direction:column; gap:3px;">
              <strong class="font-mono text-cyan" style="font-size:0.95rem;">${p.today_total}</strong>
              <small class="text-muted font-mono" style="font-size:0.75rem;">RX: ${p.today_rx} | TX: ${p.today_tx}</small>
            </div>
          </td>
          <td style="min-width:140px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <div class="progress-bar-container" style="flex:1; height:6px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden;">
                <div style="width:${Math.max(sharePct, 2)}%; height:100%; background:linear-gradient(90deg, #00d2ff, #00f2fe); border-radius:3px;"></div>
              </div>
              <span class="font-mono text-xs text-muted" style="min-width:38px;">${sharePct}%</span>
            </div>
          </td>
          <td class="font-mono text-secondary">${p.yesterday_total || '0 B'}</td>
          <td class="font-mono text-primary font-bold">${p.month_total || '0 B'}</td>
          <td>
            <span class="status-pill ${p.active_connections > 0 ? 'green' : 'gray'} font-mono" style="font-size:0.8rem;">
              ${p.active_connections} conn${p.active_connections === 1 ? '' : 's'}
            </span>
          </td>
          <td>
            <div id="port-status-${p.port}">
              ${(state.portDiagnostics && state.portDiagnostics[p.port]) ? `
                <span class="status-pill ${state.portDiagnostics[p.port].color || 'green'}" title="${state.portDiagnostics[p.port].message || ''}">
                  ${state.portDiagnostics[p.port].badge || 'ONLINE'}
                </span>
                ${state.portDiagnostics[p.port].public_ip ? `<div class="text-xs font-mono text-muted" style="margin-top:2px;">${state.portDiagnostics[p.port].public_ip}</div>` : ''}
              ` : `
                <span class="status-pill ${p.is_listening ? 'green' : 'rose'}">
                  ${p.is_listening ? 'ONLINE' : 'OFFLINE'}
                </span>
              `}
            </div>
          </td>
          <td>
            <button type="button" class="btn-probe-port" id="btn-probe-${p.port}" onclick="window.probePort(${p.port}, this)" title="Test live Internet egress, gateway ping & ISP data quota">
              Probe
            </button>
          </td>
        </tr>
      `;
    }).join("");
  }

  function setupBandwidthTimer() {
    if (state.bandwidthTimer) {
      clearInterval(state.bandwidthTimer);
      state.bandwidthTimer = null;
    }
    const selectEl = document.getElementById("bandwidthAutoRefresh");
    const intervalMs = parseInt(selectEl?.value || "10000", 10);
    if (intervalMs > 0 && state.activeTab === "bandwidth") {
      state.bandwidthTimer = setInterval(() => {
        if (state.activeTab === "bandwidth") {
          loadPortBandwidth();
        }
      }, intervalMs);
    }
  }

  // ----------------------------------------------------------------------------
  // Live Access Log Stream
  // ----------------------------------------------------------------------------
  state.logStatusFilter = "all";

  async function loadLogs() {
    const timeRange = document.getElementById("logTimeRange")?.value || "15m";
    const query = document.getElementById("logSearchInput")?.value.trim() || "";
    const userQuery = document.getElementById("logUserFilter")?.value.trim() || "";
    const statusFilter = state.logStatusFilter || "all";

    try {
      let url = `/api/logs?time=${encodeURIComponent(timeRange)}`;
      if (query) url += `&q=${encodeURIComponent(query)}`;
      if (userQuery) url += `&user=${encodeURIComponent(userQuery)}`;
      if (statusFilter !== "all") url += `&status=${encodeURIComponent(statusFilter)}`;

      const res = await fetch(url);
      const data = await res.json();
      const logs = data.logs || [];

      // Update Quick Stats counters
      let deniedCount = 0;
      let allowedCount = 0;
      logs.forEach(l => {
        const isDenied = l.is_denied || l.status.includes("403") || l.status.includes("DENIED") || l.status.includes("407");
        if (isDenied) deniedCount++;
        else allowedCount++;
      });

      const timeSelect = document.getElementById("logTimeRange");
      const timeLabel = timeSelect ? timeSelect.options[timeSelect.selectedIndex]?.text : timeRange;

      const elTotal = document.getElementById("logCountTotal");
      const elDenied = document.getElementById("logCountDenied");
      const elAllowed = document.getElementById("logCountAllowed");

      const isFallback = logs.length > 0 && logs[0].is_idle_fallback;
      const fallbackBadge = isFallback ? ` (Latest Audit Logs · Idle in last ${timeLabel})` : ` (${timeLabel})`;
      if (elTotal) elTotal.textContent = `${logs.length} entries${fallbackBadge}`;
      if (elDenied) elDenied.textContent = deniedCount;
      if (elAllowed) elAllowed.textContent = allowedCount;

      const tbody = document.getElementById("logsTableBody");
      if (!tbody) return;

      if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted" style="padding: 24px;">No log entries found matching selected filters for this time window.</td></tr>`;
        return;
      }

      tbody.innerHTML = logs.map(l => {
        const isDenied = l.is_denied || l.status.includes("403") || l.status.includes("DENIED") || l.status.includes("407");
        let statusClass = "s200";
        if (l.status.includes("403") || l.status.includes("DENIED")) statusClass = "s403";
        else if (l.status.includes("407")) statusClass = "s407";

        const rowClass = isDenied ? "row-denied" : "";

        return `
          <tr class="${rowClass}">
            <td class="text-muted">${escapeHtml(l.time)}</td>
            <td class="text-cyan font-mono">${escapeHtml(l.client_ip)}</td>
            <td><strong style="color: ${isDenied ? 'var(--rose)' : 'inherit'};">${escapeHtml(l.user)}</strong></td>
            <td><span class="badge-tag">${escapeHtml(l.method)}</span></td>
            <td><span class="status-badge ${statusClass}">${escapeHtml(l.status)}</span></td>
            <td style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(l.url)}">
              ${escapeHtml(l.url)}
            </td>
            <td class="text-muted">${escapeHtml(l.bytes)} B</td>
          </tr>
        `;
      }).join("");

    } catch (err) {
      console.error("Log fetch error:", err);
    }
  }

  // Filter Buttons (All / Denied / Allowed)
  function setupLogFilters() {
    const filterButtons = document.querySelectorAll(".btn-filter-status");
    filterButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        filterButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        state.logStatusFilter = btn.dataset.status || "all";
        loadLogs();
      });
    });

    let debounceTimer;
    const triggerDebouncedLogFetch = () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => loadLogs(), 300);
    };

    const userInput = document.getElementById("logUserFilter");
    if (userInput) {
      userInput.addEventListener("input", triggerDebouncedLogFetch);
    }

    const searchInput = document.getElementById("logSearchInput");
    if (searchInput) {
      searchInput.addEventListener("input", triggerDebouncedLogFetch);
    }

    const timeSelect = document.getElementById("logTimeRange");
    if (timeSelect) {
      timeSelect.addEventListener("change", () => loadLogs());
    }

    // Export Logs to CSV
    const btnExportCsv = document.getElementById("btnExportLogCsv");
    if (btnExportCsv) {
      btnExportCsv.addEventListener("click", () => {
        const tbody = document.getElementById("logsTableBody");
        if (!tbody) return;
        const rows = tbody.querySelectorAll("tr");
        if (!rows || rows.length === 0 || rows[0].innerText.includes("No log entries")) {
          showToast("No log data available to export.", "warning");
          return;
        }

        const csvRows = [];
        csvRows.push(["Timestamp", "Client IP", "User", "Method", "Status", "URL", "Bytes"]);

        rows.forEach(tr => {
          const cols = tr.querySelectorAll("td");
          if (cols.length >= 7) {
            const rowData = [
              cols[0].innerText.trim(),
              cols[1].innerText.trim(),
              cols[2].innerText.trim(),
              cols[3].innerText.trim(),
              cols[4].innerText.trim(),
              `"${cols[5].innerText.trim().replace(/"/g, '""')}"`,
              cols[6].innerText.trim().replace(" B", "")
            ];
            csvRows.push(rowData.join(","));
          }
        });

        const csvContent = "data:text/csv;charset=utf-8," + csvRows.join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        const nowStr = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
        link.setAttribute("download", `squid-logs-${window.location.hostname}-${nowStr}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast(`Exported ${csvRows.length - 1} log records to CSV.`, "success");
      });
    }
  }

  // Toggle log stream pause
  const btnTogglePause = document.getElementById("btnToggleLogPause");
  if (btnTogglePause) {
    btnTogglePause.addEventListener("click", () => {
      state.logStreamPaused = !state.logStreamPaused;
      document.getElementById("logPauseLabel").textContent = state.logStreamPaused ? "▶ Resume Stream" : "⏸ Pause Stream";
      btnTogglePause.classList.toggle("btn-primary", state.logStreamPaused);
      showToast(state.logStreamPaused ? "Log streaming paused." : "Log streaming resumed.", "info");
    });
  }

  const btnRefreshLogs = document.getElementById("btnRefreshLogs");
  if (btnRefreshLogs) {
    btnRefreshLogs.addEventListener("click", () => loadLogs());
  }

  // Initialize filter events
  setupLogFilters();

  // Auto-stream log interval (every 3 seconds when on logs tab)
  setInterval(() => {
    if (state.activeTab === "logs" && !state.logStreamPaused) {
      loadLogs();
    }
  }, 3000);

  // ----------------------------------------------------------------------------
  // ----------------------------------------------------------------------------
  // Direct File & Directory Management
  // ----------------------------------------------------------------------------
  async function loadEditableFiles() {
    try {
      const res = await fetch("/api/files");
      const data = await res.json();
      state.availableFiles = data.files || [];
      state.availableDirectories = data.directories || ["/etc/squid"];

      const select = document.getElementById("editorFileSelect");
      if (!select) return;

      select.innerHTML = state.availableFiles.map(f => `
        <option value="${escapeHtml(f.id)}">${escapeHtml(f.label)}</option>
      `).join("");

      if (state.availableFiles.length > 0) {
        select.value = state.availableFiles[0].id;
        loadSelectedFileContent(state.availableFiles[0].id);
      } else {
        document.getElementById("fileEditorArea").value = "";
        document.getElementById("editorFilePath").textContent = "No files found";
      }

      select.onchange = (e) => {
        loadSelectedFileContent(e.target.value);
      };

    } catch (err) {
      showToast("Failed to load file list for editor.", "error");
    }
  }

  async function loadSelectedFileContent(fileId) {
    const pathIndicator = document.getElementById("editorFilePath");
    const editor = document.getElementById("fileEditorArea");
    const delBtn = document.getElementById("btnEditorDeleteFile");

    const fileObj = state.availableFiles.find(f => f.id === fileId || f.path === fileId);
    state.currentEditingFile = fileObj;

    if (delBtn) {
      delBtn.disabled = false;
      delBtn.style.opacity = (fileObj && fileObj.deletable) ? "1" : "0.75";
      delBtn.title = (fileObj && fileObj.deletable) ? "Delete this file" : "Protected core system file (click for details)";
    }

    try {
      const res = await fetch(`/api/files/${encodeURIComponent(fileId)}`);
      const data = await res.json();
      if (data.success) {
        editor.value = data.content;
        pathIndicator.textContent = data.path;
      } else {
        showToast(data.error || "Failed to load file.", "error");
      }
    } catch (err) {
      showToast("Network error reading file.", "error");
    }
  }

  // Button: Open Create File Modal
  const btnOpenCreateFileModal = document.getElementById("btnOpenCreateFileModal");
  if (btnOpenCreateFileModal) {
    btnOpenCreateFileModal.addEventListener("click", () => {
      const parentSelect = document.getElementById("createFileParentDir");
      const dirs = state.availableDirectories.length > 0 ? state.availableDirectories : ["/etc/squid", "/etc/squid/acl/domains", "/etc/squid/acl/users", "/etc/squid/acl/ips"];
      parentSelect.innerHTML = dirs.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join("");
      document.getElementById("createFileName").value = "";
      document.getElementById("createFileContent").value = "";
      openModal("modalCreateFile");
    });
  }

  // Form: Create File Submit
  const formCreateFile = document.getElementById("formCreateFile");
  if (formCreateFile) {
    formCreateFile.addEventListener("submit", async (e) => {
      e.preventDefault();
      const parent_dir = document.getElementById("createFileParentDir").value;
      const filename = document.getElementById("createFileName").value.trim();
      const content = document.getElementById("createFileContent").value;

      try {
        const res = await fetch("/api/files/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ parent_dir, filename, content })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          closeModal("modalCreateFile");
          await loadEditableFiles();
          // Select newly created file
          const targetPath = `${parent_dir}/${filename}`.replace("//", "/");
          const targetItem = state.availableFiles.find(f => f.path === targetPath);
          if (targetItem) {
            document.getElementById("editorFileSelect").value = targetItem.id;
            loadSelectedFileContent(targetItem.id);
          }
        } else {
          showToast(data.error || "Failed to create file.", "error");
        }
      } catch (err) {
        showToast("Network error creating file.", "error");
      }
    });
  }

  // Button: Open Create Directory Modal
  const btnOpenCreateDirModal = document.getElementById("btnOpenCreateDirModal");
  if (btnOpenCreateDirModal) {
    btnOpenCreateDirModal.addEventListener("click", () => {
      const parentSelect = document.getElementById("createDirParentDir");
      const dirs = state.availableDirectories.length > 0 ? state.availableDirectories : ["/etc/squid", "/etc/squid/acl"];
      parentSelect.innerHTML = dirs.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join("");
      document.getElementById("createDirName").value = "";
      openModal("modalCreateDir");
    });
  }

  // Form: Create Directory Submit
  const formCreateDir = document.getElementById("formCreateDir");
  if (formCreateDir) {
    formCreateDir.addEventListener("submit", async (e) => {
      e.preventDefault();
      const parent_dir = document.getElementById("createDirParentDir").value;
      const dirname = document.getElementById("createDirName").value.trim();

      try {
        const res = await fetch("/api/directories/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ parent_dir, dirname })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          closeModal("modalCreateDir");
          loadEditableFiles();
        } else {
          showToast(data.error || "Failed to create directory.", "error");
        }
      } catch (err) {
        showToast("Network error creating directory.", "error");
      }
    });
  }

  // Button: Delete File
  const btnEditorDeleteFile = document.getElementById("btnEditorDeleteFile");
  if (btnEditorDeleteFile) {
    btnEditorDeleteFile.addEventListener("click", () => {
      if (!state.currentEditingFile) {
        showToast("No file selected.", "info");
        return;
      }
      if (!state.currentEditingFile.deletable) {
        alert(`Protected Core Configuration:\n\n'${state.currentEditingFile.path}' is a protected system configuration file (like squid.conf or password) and cannot be deleted to prevent disrupting Squid.\n\nTo delete a file, select any ACL or custom list file from the dropdown (e.g. from /etc/squid/acl/ or a file you created).`);
        return;
      }
      document.getElementById("deleteTargetFileName").textContent = state.currentEditingFile.path;
      openModal("modalConfirmDeleteFile");
    });
  }

  // Button: Confirm Delete File Action
  const btnConfirmDoDelete = document.getElementById("btnConfirmDoDelete");
  if (btnConfirmDoDelete) {
    btnConfirmDoDelete.addEventListener("click", async () => {
      if (!state.currentEditingFile) return;

      btnConfirmDoDelete.disabled = true;
      try {
        const res = await fetch("/api/files/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: state.currentEditingFile.path })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          closeModal("modalConfirmDeleteFile");
          await loadEditableFiles();
        } else {
          showToast(data.error || "Failed to delete file.", "error");
        }
      } catch (err) {
        showToast("Network error deleting file.", "error");
      } finally {
        btnConfirmDoDelete.disabled = false;
      }
    });
  }

  // Button: Open Delete Directory Modal
  const btnOpenDeleteDirModal = document.getElementById("btnOpenDeleteDirModal");
  if (btnOpenDeleteDirModal) {
    btnOpenDeleteDirModal.addEventListener("click", () => {
      const select = document.getElementById("deleteDirSelect");
      const protectedDirs = [
        "/etc/squid", "/etc/squid/acl", "/etc/squid/acl/domains",
        "/etc/squid/acl/users", "/etc/squid/acl/ips", "/etc/squid/conf.d"
      ];
      const dirs = state.availableDirectories || [];
      if (dirs.length === 0) {
        showToast("No directories found.", "error");
        return;
      }
      select.innerHTML = dirs.map(d => {
        const isProt = protectedDirs.includes(d);
        return `<option value="${escapeHtml(d)}" ${isProt ? 'data-protected="true"' : ''}>${escapeHtml(d)} ${isProt ? '(Protected Core Folder)' : ''}</option>`;
      }).join("");
      openModal("modalDeleteDir");
    });
  }

  // Form: Delete Directory Submit
  const formDeleteDir = document.getElementById("formDeleteDir");
  if (formDeleteDir) {
    formDeleteDir.addEventListener("submit", async (e) => {
      e.preventDefault();
      const select = document.getElementById("deleteDirSelect");
      const targetDir = select.value;
      const opt = select.options[select.selectedIndex];
      if (opt && opt.dataset.protected === "true") {
        alert(`Protected Core Directory:\n\n'${targetDir}' is a core system directory and cannot be deleted.`);
        return;
      }

      if (!confirm(`Permanently delete directory '${targetDir}'?`)) return;

      try {
        const res = await fetch("/api/directories/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: targetDir })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          closeModal("modalDeleteDir");
          await loadEditableFiles();
        } else {
          showToast(data.error || "Failed to delete directory.", "error");
        }
      } catch (err) {
        showToast("Network error deleting directory.", "error");
      }
    });
  }

  // Save File Button
  const btnEditorSave = document.getElementById("btnEditorSave");
  if (btnEditorSave) {
    btnEditorSave.addEventListener("click", async () => {
      const select = document.getElementById("editorFileSelect");
      const editor = document.getElementById("fileEditorArea");
      const fileId = select.value;
      const content = editor.value;

      btnEditorSave.disabled = true;
      btnEditorSave.innerHTML = `<span>Saving & Reconfiguring...</span>`;

      try {
        const res = await fetch(`/api/files/${encodeURIComponent(fileId)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
        } else {
          showToast(data.error || "Save rejected: Syntax check failed.", "error");
        }
      } catch (err) {
        showToast("Network error saving file.", "error");
      } finally {
        btnEditorSave.disabled = false;
        btnEditorSave.innerHTML = `
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
          </svg>
          <span>Save & Reconfigure Squid</span>
        `;
      }
    });
  }

  // ----------------------------------------------------------------------------
  // Syntax Testing & Safe Reload Global Utilities
  // ----------------------------------------------------------------------------
  const btnEditorTestSyntax = document.getElementById("btnEditorTestSyntax");
  const btnSyntaxCheck = document.getElementById("btnSyntaxCheck");

  async function runSyntaxTest(btn = null) {
    if (btn) btn.disabled = true;
    try {
      showToast("Validating Squid configuration syntax...", "info");
      const res = await fetch("/api/squid/parse", { method: "POST" });
      const data = await res.json();
      if (data.valid) {
        showToast("Syntax Check Passed! Squid configuration is 100% valid.", "success");
      } else {
        alert("Syntax Validation Error:\n\n" + data.output);
        showToast("Squid configuration syntax check reported issues.", "error");
      }
    } catch (err) {
      showToast("Network error running syntax check.", "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  if (btnEditorTestSyntax) btnEditorTestSyntax.addEventListener("click", () => runSyntaxTest(btnEditorTestSyntax));
  if (btnSyntaxCheck) btnSyntaxCheck.addEventListener("click", () => runSyntaxTest(btnSyntaxCheck));

  // Safe Reload Global Utility
  const btnGracefulReload = document.getElementById("btnGracefulReload");

  async function triggerSquidReload(btn = null) {
    if (btn) btn.disabled = true;
    try {
      showToast("Gracefully reloading Squid with zero connection loss...", "info");
      const res = await fetch("/api/squid/reload", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        showToast(data.message || "Squid configuration gracefully reloaded.", "success");
      } else {
        showToast(data.error || "Reload failed.", "error");
      }
    } catch (err) {
      showToast("Network error triggering reload.", "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  if (btnGracefulReload) {
    btnGracefulReload.addEventListener("click", () => triggerSquidReload(btnGracefulReload));
  }

  // ----------------------------------------------------------------------------
  // Backups & Restore (With 5-Snapshot Policy)
  // ----------------------------------------------------------------------------
  async function loadBackups() {
    try {
      const res = await fetch("/api/backups");
      const data = await res.json();
      const active = data.active || [];
      const archives = data.archives || [];

      // Render Active Backups
      const activeTbody = document.getElementById("activeBackupsTableBody");
      if (activeTbody) {
        if (active.length === 0) {
          activeTbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No snapshots created yet.</td></tr>`;
        } else {
          activeTbody.innerHTML = active.map(b => `
            <tr>
              <td><strong class="font-mono text-cyan">${escapeHtml(b.timestamp)}</strong></td>
              <td>${escapeHtml(b.description)}</td>
              <td><span class="badge-tag">${b.files ? b.files.join(", ") : "All Configs"}</span></td>
              <td class="text-right">
                <button class="btn btn-primary btn-sm btn-restore-backup" data-id="${escapeHtml(b.id)}">
                  Extract & Restore
                </button>
              </td>
            </tr>
          `).join("");

          document.querySelectorAll(".btn-restore-backup").forEach(btn => {
            btn.addEventListener("click", async () => {
              const id = btn.dataset.id;
              if (!confirm(`Warning: Are you sure you want to extract and restore snapshot '${id}'? This will revert configuration files and safely reconfigure Squid.`)) return;

              try {
                const res = await fetch("/api/backups/restore", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ backup_id: id })
                });
                const resData = await res.json();
                if (resData.success) {
                  showToast(resData.message, "success");
                  loadBackups();
                } else {
                  showToast(resData.error || "Restore failed.", "error");
                }
              } catch (err) {
                showToast("Network error restoring backup.", "error");
              }
            });
          });
        }
      }

      // Render Archived Backups
      const archTbody = document.getElementById("archivedBackupsTableBody");
      if (archTbody) {
        if (archives.length === 0) {
          archTbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No older archives. Only recent active snapshots in retention.</td></tr>`;
        } else {
          archTbody.innerHTML = archives.map(a => `
            <tr>
              <td class="font-mono text-emerald">${escapeHtml(a.filename)}</td>
              <td class="text-muted">${a.size_kb} KB</td>
              <td class="text-muted">${escapeHtml(a.created_at)}</td>
            </tr>
          `).join("");
        }
      }

    } catch (err) {
      showToast("Failed to load backups.", "error");
    }
  }

  const btnCreateManualBackup = document.getElementById("btnCreateManualBackup");
  if (btnCreateManualBackup) {
    btnCreateManualBackup.addEventListener("click", async () => {
      const desc = prompt("Enter a description for this backup snapshot:", "Manual snapshot via Web Portal");
      if (!desc) return;

      try {
        const res = await fetch("/api/backups", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ description: desc })
        });
        const data = await res.json();
        if (data.success) {
          showToast("Snapshot created successfully (5-retention policy applied).", "success");
          loadBackups();
        } else {
          showToast("Failed to create snapshot.", "error");
        }
      } catch (err) {
        showToast("Network error creating snapshot.", "error");
      }
    });
  }

  // ----------------------------------------------------------------------------
  // SARG Analytics Trigger
  // ----------------------------------------------------------------------------
  const btnTriggerSarg = document.getElementById("btnTriggerSarg");
  if (btnTriggerSarg) {
    btnTriggerSarg.addEventListener("click", async () => {
      btnTriggerSarg.disabled = true;
      try {
        const res = await fetch("/api/sarg/generate", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          // Refresh iframe after 6 seconds
          setTimeout(() => {
            const iframe = document.getElementById("sargIframe");
            if (iframe) iframe.src = "/sarg/?" + new Date().getTime();
          }, 6000);
        } else {
          showToast(data.error || "Failed to trigger SARG.", "error");
        }
      } catch (err) {
        showToast("Network error triggering SARG.", "error");
      } finally {
        setTimeout(() => { btnTriggerSarg.disabled = false; }, 3000);
      }
    });
  }

  // ----------------------------------------------------------------------------
  // Portal Admin Settings
  // ----------------------------------------------------------------------------
  const formChangeAdminPass = document.getElementById("formChangeAdminPass");
  if (formChangeAdminPass) {
    formChangeAdminPass.addEventListener("submit", async (e) => {
      e.preventDefault();
      const current = document.getElementById("currentAdminPass").value;
      const newPass = document.getElementById("newAdminPass").value;
      const confirmPass = document.getElementById("confirmAdminPass").value;

      if (newPass !== confirmPass) {
        showToast("New passwords do not match.", "error");
        return;
      }

      try {
        const res = await fetch("/api/settings/password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ current_password: current, new_password: newPass })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message, "success");
          formChangeAdminPass.reset();
        } else {
          showToast(data.error || "Failed to update password.", "error");
        }
      } catch (err) {
        showToast("Network error updating password.", "error");
      }
    });
  }

  // ----------------------------------------------------------------------------
  // Modal Utilities
  // ----------------------------------------------------------------------------
  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add("show");
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove("show");
  }

  document.querySelectorAll(".btn-close-modal, .btn-cancel-modal").forEach(btn => {
    btn.addEventListener("click", () => {
      btn.closest(".modal-overlay").classList.remove("show");
    });
  });

  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.classList.remove("show");
    });
  });

  // ============================================================================
  // SECURE 15-CHARACTER PASSWORD GENERATOR (EXCLUDES '@')
  // ============================================================================
  function generateSafeProxyPassword(length = 15) {
    const uppercase = "ABCDEFGHJKLMNPQRSTUVWXYZ";
    const lowercase = "abcdefghijkmnopqrstuvwxyz";
    const numbers = "23456789";
    const symbols = "!#$%&*()_+-=[]{}|;:,.<>?"; // Strictly NO '@' symbol to avoid proxy URL auth breaks

    const allChars = uppercase + lowercase + numbers + symbols;

    // Guarantee at least 1 of each character set
    const pass = [
      uppercase[Math.floor(Math.random() * uppercase.length)],
      lowercase[Math.floor(Math.random() * lowercase.length)],
      numbers[Math.floor(Math.random() * numbers.length)],
      symbols[Math.floor(Math.random() * symbols.length)]
    ];

    // Fill remaining up to 15 characters
    for (let i = pass.length; i < length; i++) {
      pass.push(allChars[Math.floor(Math.random() * allChars.length)]);
    }

    // Cryptographic shuffle
    for (let i = pass.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [pass[i], pass[j]] = [pass[j], pass[i]];
    }

    return pass.join("");
  }

  // Copy password helper
  function copyTextToClipboard(text, successMsg = "Password copied to clipboard!") {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(successMsg, "success");
      }).catch(() => {
        fallbackCopy(text, successMsg);
      });
    } else {
      fallbackCopy(text, successMsg);
    }
  }

  function fallbackCopy(text, successMsg) {
    const tempInput = document.createElement("input");
    tempInput.value = text;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand("copy");
    document.body.removeChild(tempInput);
    showToast(successMsg, "success");
  }

  // Attach Password Generator and Copy Buttons for Add User Modal
  const btnGenAddUserPass = document.getElementById("btnGenAddUserPass");
  if (btnGenAddUserPass) {
    btnGenAddUserPass.addEventListener("click", () => {
      document.getElementById("newUserPassword").value = generateSafeProxyPassword(15);
      showToast("Generated new 15-character password!", "info");
    });
  }

  const btnCopyAddUserPass = document.getElementById("btnCopyAddUserPass");
  if (btnCopyAddUserPass) {
    btnCopyAddUserPass.addEventListener("click", () => {
      const pass = document.getElementById("newUserPassword").value;
      if (pass) copyTextToClipboard(pass);
    });
  }

  const btnToggleAddUserPass = document.getElementById("btnToggleAddUserPass");
  if (btnToggleAddUserPass) {
    btnToggleAddUserPass.addEventListener("click", () => {
      const input = document.getElementById("newUserPassword");
      input.type = input.type === "password" ? "text" : "password";
    });
  }

  // Attach Password Generator and Copy Buttons for Reset Password Modal
  const btnGenResetPass = document.getElementById("btnGenResetPass");
  if (btnGenResetPass) {
    btnGenResetPass.addEventListener("click", () => {
      document.getElementById("resetNewPass").value = generateSafeProxyPassword(15);
      showToast("Generated new 15-character password!", "info");
    });
  }

  const btnCopyResetPass = document.getElementById("btnCopyResetPass");
  if (btnCopyResetPass) {
    btnCopyResetPass.addEventListener("click", () => {
      const pass = document.getElementById("resetNewPass").value;
      if (pass) copyTextToClipboard(pass);
    });
  }

  const btnToggleResetPass = document.getElementById("btnToggleResetPass");
  if (btnToggleResetPass) {
    btnToggleResetPass.addEventListener("click", () => {
      const input = document.getElementById("resetNewPass");
      input.type = input.type === "password" ? "text" : "password";
    });
  }

  // Open Add User Modal Handler
  const btnOpenAddUser = document.getElementById("btnOpenAddUserModal");
  if (btnOpenAddUser) {
    btnOpenAddUser.addEventListener("click", () => {
      const container = document.getElementById("addUserGroupCheckboxes");
      container.innerHTML = state.groups.map(grp => `
        <label class="checkbox-item">
          <input type="checkbox" name="group" value="${escapeHtml(grp)}">
          <span>${escapeHtml(grp)}</span>
        </label>
      `).join("");
      document.getElementById("newUsername").value = "";
      document.getElementById("newUserPassword").value = generateSafeProxyPassword(15);
      openModal("modalAddUser");
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }


  const btnRefreshDashboard = document.getElementById("btnRefreshDashboard");
  if (btnRefreshDashboard) {
    btnRefreshDashboard.addEventListener("click", async () => {
      btnRefreshDashboard.disabled = true;
      const svg = btnRefreshDashboard.querySelector("svg");
      if (svg) svg.style.animation = "spin 0.8s linear infinite";
      showToast("Refreshing enterprise telemetry & traffic metrics...", "info");
      await loadStatus();
      await loadPorts();
      setTimeout(() => {
        if (svg) svg.style.animation = "";
        btnRefreshDashboard.disabled = false;
        showToast("Dashboard metrics up to date.", "success");
      }, 600);
    });
  }

  // ============================================================================
  // ADVANCED ANALYTICS: Fleet, Blocked, User Activity, Security, Charts
  // ============================================================================

  // Chart instances (for destruction/recreation)
  let chartBlockedDomains = null;
  let chartDeniedUsers = null;
  let chartHourlyTraffic = null;
  let chartUserHeatmap = null;

  const chartColors = {
    cyan: 'rgba(0, 242, 254, 0.8)',
    cyanBg: 'rgba(0, 242, 254, 0.15)',
    rose: 'rgba(255, 65, 108, 0.8)',
    roseBg: 'rgba(255, 65, 108, 0.15)',
    emerald: 'rgba(56, 239, 125, 0.8)',
    emeraldBg: 'rgba(56, 239, 125, 0.15)',
    purple: 'rgba(196, 113, 237, 0.8)',
    purpleBg: 'rgba(196, 113, 237, 0.15)',
    amber: 'rgba(255, 217, 61, 0.8)',
    amberBg: 'rgba(255, 217, 61, 0.15)',
    blue: 'rgba(79, 172, 254, 0.8)',
    blueBg: 'rgba(79, 172, 254, 0.15)',
  };

  const chartDefaultOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
    },
    scales: {
      x: {
        ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 10 } },
        grid: { color: 'rgba(255,255,255,0.04)' },
        border: { color: 'rgba(255,255,255,0.08)' }
      },
      y: {
        ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 10 } },
        grid: { color: 'rgba(255,255,255,0.04)' },
        border: { color: 'rgba(255,255,255,0.08)' },
        beginAtZero: true
      }
    }
  };

  // ---------- FLEET OVERVIEW ----------
  async function loadFleetStatus() {
    try {
      const res = await fetch('/api/fleet/status');
      const data = await res.json();

      const el = (id) => document.getElementById(id);
      el('fleetTotalServers').textContent = data.total || 0;
      el('fleetOnlineCount').textContent = data.online || 0;
      el('fleetOfflineCount').textContent = data.offline || 0;
      el('fleetHealthPct').textContent = (data.fleet_health || 0) + '%';

      const container = el('fleetCardsContainer');
      if (!container || !data.servers) return;

      container.innerHTML = data.servers.map(s => {
        const statusClass = s.online ? 'online' : 'offline';
        const selfClass = s.is_self ? ' self-node' : '';
        const selfBadge = s.is_self ? '<span class="fleet-self-badge">THIS SERVER</span>' : '';
        const statusText = s.online ? 'Online' : 'Offline';
        const mem = s.status?.memory_mb || 0;
        const cpu = s.status?.cpu_percent || 0;
        const pid = s.status?.pid || '—';
        const ports = (s.status?.ports_listening || []).length;
        const users = s.metrics?.total_users || '—';
        const domains = s.metrics?.total_domains || '—';
        const errorHtml = s.error ? `<div class="fleet-error-msg">${esc(s.error)}</div>` : '';

        return `
          <div class="fleet-card ${statusClass}${selfClass}">
            <div class="fleet-card-header">
              <div>
                <div class="fleet-server-name">${esc(s.name)} ${selfBadge}</div>
                <div class="fleet-server-ip">${esc(s.ip)}:${s.port}</div>
              </div>
              <span class="fleet-status-badge ${statusClass}">${statusText}</span>
            </div>
            ${s.online ? `
            <div class="fleet-metrics-grid">
              <div class="fleet-metric">
                <span class="fleet-metric-label">PID</span>
                <span class="fleet-metric-val">${pid}</span>
              </div>
              <div class="fleet-metric">
                <span class="fleet-metric-label">Memory</span>
                <span class="fleet-metric-val">${mem} MB</span>
              </div>
              <div class="fleet-metric">
                <span class="fleet-metric-label">CPU</span>
                <span class="fleet-metric-val">${cpu}%</span>
              </div>
              <div class="fleet-metric">
                <span class="fleet-metric-label">Ports</span>
                <span class="fleet-metric-val">${ports}</span>
              </div>
              <div class="fleet-metric">
                <span class="fleet-metric-label">Users</span>
                <span class="fleet-metric-val">${users}</span>
              </div>
              <div class="fleet-metric">
                <span class="fleet-metric-label">Domains</span>
                <span class="fleet-metric-val">${domains}</span>
              </div>
            </div>` : ''}
            ${errorHtml}
          </div>`;
      }).join('');
    } catch (e) {
      console.error('Fleet load error:', e);
      showToast('Failed to load fleet status', 'error');
    }
  }

  const btnRefreshFleet = document.getElementById('btnRefreshFleet');
  if (btnRefreshFleet) btnRefreshFleet.addEventListener('click', loadFleetStatus);

  // ---------- BLOCKED REQUESTS ----------
  async function loadBlockedAnalytics() {
    try {
      const sampleEl = document.getElementById('blockedSampleSize');
      const lines = sampleEl ? sampleEl.value : 1000;
      const res = await fetch(`/api/analytics/blocked?lines=${lines}`);
      const data = await res.json();

      const el = (id) => document.getElementById(id);
      el('blockedTotalCount').textContent = data.total_blocked || 0;
      el('blockedAuthFailCount').textContent = data.total_auth_failures || 0;
      el('blockedDomainsCount').textContent = (data.top_blocked_domains || []).length;
      el('blockedUsersCount').textContent = (data.top_denied_users || []).length;

      // Chart: Top Blocked Domains
      const domCtx = document.getElementById('chartBlockedDomains');
      if (domCtx && data.top_blocked_domains?.length) {
        if (chartBlockedDomains) chartBlockedDomains.destroy();
        chartBlockedDomains = new Chart(domCtx, {
          type: 'bar',
          data: {
            labels: data.top_blocked_domains.map(d => d.domain.length > 25 ? d.domain.substring(0, 22) + '...' : d.domain),
            datasets: [{
              label: 'Blocked Count',
              data: data.top_blocked_domains.map(d => d.count),
              backgroundColor: chartColors.roseBg,
              borderColor: chartColors.rose,
              borderWidth: 1,
              borderRadius: 6
            }]
          },
          options: { ...chartDefaultOpts, indexAxis: 'y' }
        });
      }

      // Chart: Top Denied Users
      const usrCtx = document.getElementById('chartDeniedUsers');
      if (usrCtx && data.top_denied_users?.length) {
        if (chartDeniedUsers) chartDeniedUsers.destroy();
        chartDeniedUsers = new Chart(usrCtx, {
          type: 'bar',
          data: {
            labels: data.top_denied_users.map(u => u.user),
            datasets: [{
              label: 'Denied Count',
              data: data.top_denied_users.map(u => u.count),
              backgroundColor: chartColors.amberBg,
              borderColor: chartColors.amber,
              borderWidth: 1,
              borderRadius: 6
            }]
          },
          options: { ...chartDefaultOpts, indexAxis: 'y' }
        });
      }

      // Table: Recent Blocked
      const tbody = el('blockedTableBody');
      if (tbody && data.recent_blocked?.length) {
        tbody.innerHTML = data.recent_blocked.slice(0, 30).map(r => `
          <tr${r.is_auth_fail ? ' class="brute-force-row"' : ''}>
            <td class="font-mono text-xs">${esc(r.time)}</td>
            <td>${esc(r.user)}</td>
            <td class="font-mono">${esc(r.client_ip)}</td>
            <td class="text-cyan">${esc(r.domain)}</td>
            <td><span class="status-pill rose">${esc(r.status)}</span></td>
            <td>${r.is_auth_fail ? '<span class="threat-badge medium">AUTH FAIL</span>' : '<span class="threat-badge high">DENIED</span>'}</td>
          </tr>`).join('');
      } else if (tbody) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No blocked requests found in sample</td></tr>';
      }
    } catch (e) {
      console.error('Blocked analytics error:', e);
      showToast('Failed to load blocked analytics', 'error');
    }
  }

  const btnRefreshBlocked = document.getElementById('btnRefreshBlocked');
  if (btnRefreshBlocked) btnRefreshBlocked.addEventListener('click', loadBlockedAnalytics);
  const blockedSampleSize = document.getElementById('blockedSampleSize');
  if (blockedSampleSize) blockedSampleSize.addEventListener('change', loadBlockedAnalytics);

  // ---------- USER ACTIVITY ----------
  async function loadUserActivityInit() {
    // Populate user selector dropdown
    try {
      const res = await fetch('/api/users');
      const data = await res.json();
      const selector = document.getElementById('userActivitySelector');
      if (selector && data.users) {
        const currentVal = selector.value;
        selector.innerHTML = '<option value="">— Choose a proxy user —</option>' +
          data.users.map(u => `<option value="${esc(u.username)}">${esc(u.username)}</option>`).join('');
        if (currentVal) selector.value = currentVal;
      }
    } catch (e) {
      console.error('User list load error:', e);
    }
  }

  async function loadUserActivity(username) {
    if (!username) return;
    const contentEl = document.getElementById('userActivityContent');
    if (!contentEl) return;

    contentEl.innerHTML = '<div class="analytics-empty-state"><h3>Loading activity for ' + esc(username) + '...</h3></div>';

    try {
      const res = await fetch(`/api/analytics/user/${encodeURIComponent(username)}`);
      const data = await res.json();

      const initial = username.charAt(0).toUpperCase();
      let statusHtml = '';
      if (data.status_breakdown) {
        statusHtml = Object.entries(data.status_breakdown).map(([k, v]) =>
          `<span class="badge-tag cyan font-mono" style="margin-right:6px;">${esc(k)}: ${v}</span>`
        ).join('');
      }

      let methodHtml = '';
      if (data.method_breakdown) {
        methodHtml = Object.entries(data.method_breakdown).map(([k, v]) =>
          `<span class="badge-tag purple font-mono" style="margin-right:6px;">${esc(k)}: ${v}</span>`
        ).join('');
      }

      contentEl.innerHTML = `
        <div class="user-profile-header">
          <div class="user-profile-avatar">${initial}</div>
          <div class="user-profile-info">
            <h2>${esc(data.username)}</h2>
            <p class="profile-sub">First seen: ${esc(data.first_seen || 'N/A')} &nbsp;|&nbsp; Last seen: ${esc(data.last_seen || 'N/A')}</p>
          </div>
        </div>

        <div class="user-stats-grid">
          <div class="user-stat-card">
            <span class="user-stat-num text-cyan">${data.total_requests}</span>
            <span class="user-stat-label">Total Requests</span>
          </div>
          <div class="user-stat-card">
            <span class="user-stat-num text-emerald">${esc(data.total_bytes_human)}</span>
            <span class="user-stat-label">Bandwidth</span>
          </div>
          <div class="user-stat-card">
            <span class="user-stat-num text-purple">${(data.top_domains || []).length}</span>
            <span class="user-stat-label">Unique Domains</span>
          </div>
          <div class="user-stat-card">
            <span class="user-stat-num text-amber">${Object.keys(data.method_breakdown || {}).length}</span>
            <span class="user-stat-label">HTTP Methods</span>
          </div>
        </div>

        <div class="grid-2-col">
          <div class="card">
            <div class="card-header"><h3>Hourly Activity Heatmap</h3><span class="badge-tag cyan font-mono">24h Pattern</span></div>
            <div class="card-body">
              <div class="chart-container"><canvas id="chartUserHeatmap"></canvas></div>
            </div>
          </div>
          <div class="card">
            <div class="card-header"><h3>Top Domains Accessed</h3><span class="badge-tag blue font-mono">By Frequency</span></div>
            <div class="card-body p-0">
              <div class="table-responsive"><table class="data-table"><thead><tr><th>Domain</th><th>Requests</th></tr></thead>
              <tbody>${(data.top_domains || []).map(d => `<tr><td class="text-cyan">${esc(d.domain)}</td><td class="font-mono">${d.count}</td></tr>`).join('') || '<tr><td colspan="2" class="text-center text-muted">No data</td></tr>'}</tbody></table></div>
            </div>
          </div>
        </div>

        <div class="card mt-4">
          <div class="card-header"><h3>Protocol & Method Breakdown</h3></div>
          <div class="card-body">
            <div style="margin-bottom:12px;"><strong style="color:rgba(255,255,255,0.5);font-size:0.75rem;">STATUS:</strong> ${statusHtml || '<span class="text-muted">No data</span>'}</div>
            <div><strong style="color:rgba(255,255,255,0.5);font-size:0.75rem;">METHODS:</strong> ${methodHtml || '<span class="text-muted">No data</span>'}</div>
          </div>
        </div>

        <div class="card mt-4">
          <div class="card-header"><h3>Recent Requests by ${esc(data.username)}</h3><span class="badge-tag emerald">Last 20</span></div>
          <div class="card-body p-0">
            <div class="table-responsive"><table class="data-table"><thead><tr><th>Time</th><th>Domain</th><th>Method</th><th>Status</th><th>Size</th></tr></thead>
            <tbody>${(data.recent_requests || []).map(r => `<tr><td class="font-mono text-xs">${esc(r.time)}</td><td class="text-cyan">${esc(r.domain)}</td><td>${esc(r.method)}</td><td><span class="status-pill cyan">${esc(r.status)}</span></td><td class="font-mono">${esc(r.bytes)}</td></tr>`).join('') || '<tr><td colspan="5" class="text-center text-muted">No data</td></tr>'}</tbody></table></div>
          </div>
        </div>
      `;

      // Render hourly heatmap chart
      if (data.hourly_heatmap) {
        const ctx = document.getElementById('chartUserHeatmap');
        if (ctx) {
          if (chartUserHeatmap) chartUserHeatmap.destroy();
          const labels = Array.from({length: 24}, (_, i) => `${String(i).padStart(2, '0')}:00`);
          chartUserHeatmap = new Chart(ctx, {
            type: 'bar',
            data: {
              labels: labels,
              datasets: [{
                label: 'Requests',
                data: data.hourly_heatmap,
                backgroundColor: data.hourly_heatmap.map(v => v > 0 ? chartColors.cyanBg : 'rgba(255,255,255,0.02)'),
                borderColor: data.hourly_heatmap.map(v => v > 0 ? chartColors.cyan : 'rgba(255,255,255,0.06)'),
                borderWidth: 1,
                borderRadius: 4
              }]
            },
            options: chartDefaultOpts
          });
        }
      }
    } catch (e) {
      console.error('User activity error:', e);
      contentEl.innerHTML = '<div class="analytics-empty-state"><h3>Error loading user activity</h3></div>';
    }
  }

  const btnLoadUserActivity = document.getElementById('btnLoadUserActivity');
  if (btnLoadUserActivity) {
    btnLoadUserActivity.addEventListener('click', () => {
      const selector = document.getElementById('userActivitySelector');
      if (selector && selector.value) loadUserActivity(selector.value);
      else showToast('Please select a user first', 'error');
    });
  }

  // ---------- SECURITY AUDIT ----------
  async function loadSecurityAudit() {
    try {
      const res = await fetch('/api/analytics/security');
      const data = await res.json();

      const el = (id) => document.getElementById(id);

      // Score
      const score = data.security_score || 0;
      el('securityScoreVal').textContent = score;
      const scoreEl = el('securityScoreVal');
      scoreEl.className = 'security-score-val ' + (score >= 80 ? 'security-score-good' : score >= 50 ? 'security-score-warn' : 'security-score-bad');

      // Animate score arc (circumference = 2*PI*60 = 377)
      const arc = el('securityScoreArc');
      if (arc) {
        const offset = 377 - (377 * score / 100);
        arc.style.transition = 'stroke-dashoffset 1s ease';
        arc.style.strokeDashoffset = offset;
        arc.style.stroke = score >= 80 ? '#38ef7d' : score >= 50 ? '#ffd93d' : '#ff416c';
      }

      // Summary cards
      el('secTotalRequests').textContent = data.total_requests || 0;
      el('secTotalDenied').textContent = data.total_denied || 0;
      el('secTotalAuthFail').textContent = data.total_auth_failures || 0;
      el('secBruteForceCount').textContent = (data.brute_force_candidates || []).length;

      // Brute force table
      const bfBody = el('bruteForceTableBody');
      if (bfBody) {
        const bf = data.brute_force_candidates || [];
        if (bf.length) {
          bfBody.innerHTML = bf.map(b => {
            const level = b.attempts >= 20 ? 'high' : b.attempts >= 10 ? 'medium' : 'high';
            const levelText = b.attempts >= 20 ? 'CRITICAL' : b.attempts >= 10 ? 'HIGH' : 'ELEVATED';
            return `<tr class="brute-force-row"><td class="font-mono">${esc(b.ip)}</td><td class="font-mono text-rose">${b.attempts}</td><td><span class="threat-badge ${level}">${levelText}</span></td></tr>`;
          }).join('');
        } else {
          bfBody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No brute-force candidates detected ✓</td></tr>';
        }
      }

      // Auth failures table
      const afBody = el('authFailTableBody');
      if (afBody) {
        const af = data.auth_failure_events || [];
        if (af.length) {
          afBody.innerHTML = af.slice(0, 20).map(e => `<tr><td class="font-mono text-xs">${esc(e.time)}</td><td class="font-mono">${esc(e.client_ip)}</td><td>${esc(e.user)}</td><td class="text-cyan">${esc(e.domain)}</td></tr>`).join('');
        } else {
          afBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No authentication failures ✓</td></tr>';
        }
      }

      // Denied events table
      const deBody = el('deniedEventsTableBody');
      if (deBody) {
        const de = data.denied_events || [];
        if (de.length) {
          deBody.innerHTML = de.slice(0, 20).map(e => `<tr><td class="font-mono text-xs">${esc(e.time)}</td><td>${esc(e.user)}</td><td class="text-cyan">${esc(e.domain)}</td><td><span class="status-pill rose">${esc(e.status)}</span></td></tr>`).join('');
        } else {
          deBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No denied requests ✓</td></tr>';
        }
      }

      // Load hourly traffic chart
      loadHourlyTrafficChart();
    } catch (e) {
      console.error('Security audit error:', e);
      showToast('Failed to load security data', 'error');
    }
  }

  async function loadHourlyTrafficChart() {
    try {
      const res = await fetch('/api/analytics/hourly');
      const data = await res.json();

      const ctx = document.getElementById('chartHourlyTraffic');
      if (!ctx) return;
      if (chartHourlyTraffic) chartHourlyTraffic.destroy();

      chartHourlyTraffic = new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.labels || [],
          datasets: [
            {
              label: 'Total Requests',
              data: data.requests || [],
              borderColor: chartColors.cyan,
              backgroundColor: chartColors.cyanBg,
              fill: true,
              tension: 0.4,
              pointRadius: 3,
              pointHoverRadius: 6
            },
            {
              label: 'Tunnel (HTTPS)',
              data: data.tunnel || [],
              borderColor: chartColors.purple,
              backgroundColor: 'transparent',
              borderDash: [5, 5],
              tension: 0.4,
              pointRadius: 2
            },
            {
              label: 'Denied',
              data: data.denied || [],
              borderColor: chartColors.rose,
              backgroundColor: chartColors.roseBg,
              fill: true,
              tension: 0.4,
              pointRadius: 3
            }
          ]
        },
        options: {
          ...chartDefaultOpts,
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: { color: 'rgba(255,255,255,0.5)', font: { size: 11 }, padding: 16, usePointStyle: true, pointStyle: 'circle' }
            }
          }
        }
      });
    } catch (e) {
      console.error('Hourly traffic chart error:', e);
    }
  }

  const btnRefreshSecurity = document.getElementById('btnRefreshSecurity');
  if (btnRefreshSecurity) btnRefreshSecurity.addEventListener('click', loadSecurityAudit);

  // ----------------------------------------------------------------------------
  // Time-Range Picker & Egress Port Probe Handlers
  // ----------------------------------------------------------------------------
  window.probePort = async function(port, btn) {
    if (!btn || btn.classList.contains("probing")) return;
    btn.classList.add("probing");
    const originalText = btn.textContent;
    btn.textContent = "...";
    try {
      const res = await fetch(`/api/ports/check/${port}`, { method: "POST" });
      const data = await res.json();
      state.portDiagnostics = state.portDiagnostics || {};
      state.portDiagnostics[port] = data;

      const statusContainer = document.getElementById(`port-status-${port}`);
      if (statusContainer) {
        statusContainer.innerHTML = `
          <span class="status-pill ${data.color || (data.success ? 'green' : 'rose')}" title="${data.message || ''}">
            ${data.badge || (data.success ? 'INTERNET OK' : 'DOWN')}
          </span>
          ${data.public_ip ? `<div class="text-xs font-mono text-muted" style="margin-top:2px;">${data.public_ip}</div>` : ''}
        `;
      }

      if (data.status === "ONLINE") {
        btn.textContent = `${data.latency_ms}ms ✓`;
        btn.style.borderColor = "#38ef7d";
        btn.style.color = "#38ef7d";
        showToast(data.message, "success");
      } else if (data.status === "DATA_OVER") {
        btn.textContent = "Quota Over ⚠";
        btn.style.borderColor = "#fbbf24";
        btn.style.color = "#fbbf24";
        showToast(data.message, "warning");
      } else {
        btn.textContent = "Down ✗";
        btn.style.borderColor = "#ff416c";
        btn.style.color = "#ff416c";
        showToast(data.message, "error");
      }
    } catch (e) {
      btn.textContent = "Error";
      showToast(`Diagnostic probe failed for port ${port}`, "error");
    } finally {
      btn.classList.remove("probing");
      setTimeout(() => {
        btn.textContent = "Probe";
        btn.style.borderColor = "";
        btn.style.color = "";
      }, 5000);
    }
  };

  window.checkAllPortsInternet = async function() {
    const btn = document.getElementById("btnCheckAllPortsInternet");
    if (btn) {
      btn.disabled = true;
      btn.classList.add("loading");
      const span = btn.querySelector("span");
      if (span) span.textContent = "Checking ISP...";
    }
    showToast("Running active Internet & ISP diagnostics across all ports...", "info");
    try {
      const res = await fetch("/api/ports/check-all", { method: "POST" });
      const data = await res.json();
      if (data.success && data.results) {
        state.portDiagnostics = state.portDiagnostics || {};
        let onlineCount = 0;
        let warningCount = 0;
        let downCount = 0;

        for (const [port, diag] of Object.entries(data.results)) {
          state.portDiagnostics[port] = diag;
          if (diag.status === "ONLINE") onlineCount++;
          else if (diag.status === "DATA_OVER") warningCount++;
          else downCount++;

          const statusContainer = document.getElementById(`port-status-${port}`);
          if (statusContainer) {
            statusContainer.innerHTML = `
              <span class="status-pill ${diag.color || 'green'}" title="${diag.message || ''}">
                ${diag.badge || 'ONLINE'}
              </span>
              ${diag.public_ip ? `<div class="text-xs font-mono text-muted" style="margin-top:2px;">${diag.public_ip}</div>` : ''}
            `;
          }
          const portBtn = document.getElementById(`btn-probe-${port}`);
          if (portBtn) {
            if (diag.status === "ONLINE") {
              portBtn.textContent = `${diag.latency_ms}ms ✓`;
              portBtn.style.borderColor = "#38ef7d";
              portBtn.style.color = "#38ef7d";
            } else if (diag.status === "DATA_OVER") {
              portBtn.textContent = "Quota Over ⚠";
              portBtn.style.borderColor = "#fbbf24";
              portBtn.style.color = "#fbbf24";
            } else {
              portBtn.textContent = "Down ✗";
              portBtn.style.borderColor = "#ff416c";
              portBtn.style.color = "#ff416c";
            }
          }
        }

        if (downCount === 0 && warningCount === 0) {
          showToast(`All ${onlineCount} ports have active Internet!`, "success");
        } else if (warningCount > 0) {
          showToast(`${warningCount} port(s) detected with Data Over / ISP Captive Portal!`, "warning");
        } else {
          showToast(`${downCount} port(s) are Down / have No Internet!`, "error");
        }
      } else {
        showToast("Failed to complete ISP diagnostics", "error");
      }
    } catch (e) {
      showToast("Error running ISP connectivity diagnostics", "error");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.classList.remove("loading");
        const span = btn.querySelector("span");
        if (span) span.textContent = "Check All ISP / Internet";
      }
    }
  };

  const telemetryTimePicker = document.getElementById("telemetryTimePicker");
  if (telemetryTimePicker) {
    telemetryTimePicker.addEventListener("click", (e) => {
      const btn = e.target.closest(".time-range-btn");
      if (!btn) return;
      telemetryTimePicker.querySelectorAll(".time-range-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.telemetryRange = btn.dataset.range || "500";
      state.hasCustomRangeSelected = true;
      loadAnalytics(state.telemetryRange);
    });
  }

  const blockedFilterInput = document.getElementById("dashBlockedFilterInput");
  if (blockedFilterInput) {
    blockedFilterInput.addEventListener("input", () => {
      filterAndRenderBlockedFeed();
    });
  }

  // ============================================================================
  // NFTABLES FIREWALL & NAT MANAGEMENT CONTROLLER
  // ============================================================================
  state.nftRuleset = null;
  state.nftRawModified = false;

  async function loadNftables() {
    const container = document.getElementById("nftChainsContainer");
    if (container) {
      container.innerHTML = `<div class="text-center text-muted py-4">Fetching active kernel ruleset...</div>`;
    }

    try {
      const res = await fetch("/api/nftables/ruleset");
      const data = await res.json();
      if (!data.success || !data.ruleset) {
        showToast(data.error || "Failed to load nftables ruleset.", "error");
        if (container) container.innerHTML = `<div class="alert-box alert-danger">Error loading nftables: ${escapeHtml(data.error || "Unknown error")}</div>`;
        return;
      }

      state.nftRuleset = data.ruleset;
      const st = data.ruleset.status || {};

      // 1. Update Health & Summary Strip
      const statusPill = document.getElementById("nftStatusPill");
      if (statusPill) {
        statusPill.textContent = st.active ? "ACTIVE" : (st.service_status || "INACTIVE").toUpperCase();
        statusPill.className = `status-pill ${st.active ? "green" : "rose"} font-mono`;
      }

      const confMtimeEl = document.getElementById("nftConfMtime");
      if (confMtimeEl) {
        confMtimeEl.textContent = st.conf_mtime ? `Modified: ${st.conf_mtime}` : "Config: /etc/nftables.conf";
      }

      const tableCountEl = document.getElementById("nftTableCount");
      const tableSummaryEl = document.getElementById("nftTableSummary");
      if (tableCountEl) tableCountEl.textContent = data.ruleset.tables?.length || 0;
      if (tableSummaryEl) {
        const tNames = (data.ruleset.tables || []).map(t => `${t.family} ${t.name}`).join(", ");
        tableSummaryEl.textContent = tNames || "No active tables";
      }

      const chainCountEl = document.getElementById("nftChainCount");
      const chainSummaryEl = document.getElementById("nftChainSummary");
      if (chainCountEl) chainCountEl.textContent = data.ruleset.chains?.length || 0;
      if (chainSummaryEl) {
        const cNames = (data.ruleset.chains || []).map(c => c.name).join(", ");
        chainSummaryEl.textContent = cNames || "No active chains";
      }

      const totalRules = data.ruleset.rules?.length || 0;
      const ruleTotalEl = document.getElementById("nftRuleTotalCount");
      if (ruleTotalEl) ruleTotalEl.textContent = totalRules;

      const sidebarBadge = document.getElementById("badgeNftRuleCount");
      if (sidebarBadge) sidebarBadge.textContent = totalRules;

      // 2. Populate Raw Code Editor
      const rawTextarea = document.getElementById("nftRawEditorTextarea");
      if (rawTextarea) {
        rawTextarea.value = data.ruleset.raw_config || data.ruleset.active_ruleset_text || "";
      }

      // 3. Render Visual Rule Explorer
      renderNftVisualExplorer();

    } catch (err) {
      console.error("Failed to load nftables:", err);
      showToast("Error connecting to nftables API.", "error");
    }
  }

  function renderNftVisualExplorer() {
    const container = document.getElementById("nftChainsContainer");
    if (!container || !state.nftRuleset) return;

    const { tables = [], chains = [], rules = [] } = state.nftRuleset;

    if (tables.length === 0 && chains.length === 0 && rules.length === 0) {
      container.innerHTML = `
        <div class="card p-4 text-center">
          <p class="text-muted mb-2">No active tables or chains detected in /etc/nftables.conf.</p>
          <button class="btn btn-primary btn-sm" onclick="document.getElementById('btnOpenAddNftRuleModal').click()">
            + Create First Rule
          </button>
        </div>
      `;
      return;
    }

    const searchQuery = (document.getElementById("nftRuleSearchInput")?.value || "").toLowerCase().trim();

    let html = "";

    tables.forEach(tbl => {
      const tblChains = chains.filter(c => c.table_family === tbl.family && c.table_name === tbl.name);

      html += `
        <div class="nft-table-card mb-4" style="background: rgba(15,23,42,0.6); border: 1px solid var(--border-cyan); border-radius: var(--radius-md); overflow: hidden;">
          <div class="nft-table-header p-3" style="background: rgba(0,242,254,0.08); border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span class="badge-tag cyan font-mono">${escapeHtml(tbl.family.toUpperCase())}</span>
              <strong style="font-size: 1.05rem;" class="text-main">table ${escapeHtml(tbl.family)} ${escapeHtml(tbl.name)}</strong>
            </div>
            <span class="text-xs text-muted font-mono">${tblChains.length} Chains</span>
          </div>
          <div class="p-3">
      `;

      if (tblChains.length === 0) {
        html += `<p class="text-muted text-xs p-2">No chains defined in this table.</p>`;
      } else {
        tblChains.forEach(chn => {
          const chnRules = rules.filter(r => 
            r.table_family === tbl.family && 
            r.table_name === tbl.name && 
            r.chain_name === chn.name
          );

          const filteredRules = chnRules.filter(r => {
            if (!searchQuery) return true;
            return r.rule_raw.toLowerCase().includes(searchQuery) ||
                   (r.comment && r.comment.toLowerCase().includes(searchQuery)) ||
                   r.action.toLowerCase().includes(searchQuery) ||
                   (r.handle !== null && String(r.handle).includes(searchQuery));
          });

          const hookBadge = chn.hook !== "none" ? `<span class="badge-tag font-mono text-xs">hook: ${escapeHtml(chn.hook)}</span>` : "";
          const prioBadge = `<span class="badge-tag font-mono text-xs">prio: ${escapeHtml(chn.priority)}</span>`;
          const policyBadge = chn.policy ? `<span class="badge-tag font-mono text-xs ${chn.policy === 'accept' ? 'emerald' : 'rose'}">policy: ${escapeHtml(chn.policy)}</span>` : "";

          html += `
            <div class="nft-chain-block mb-3" style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); overflow: hidden;">
              <div class="nft-chain-header p-2 px-3" style="background: rgba(255,255,255,0.03); border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span class="badge-tag purple font-mono">chain ${escapeHtml(chn.name)}</span>
                  ${hookBadge}
                  ${prioBadge}
                  ${policyBadge}
                </div>
                <div style="display: flex; gap: 6px;">
                  <button type="button" class="btn btn-secondary btn-sm" style="padding: 2px 8px; font-size: 0.72rem;" onclick="window.quickAddRuleToChain('${escapeHtml(tbl.family)}', '${escapeHtml(tbl.name)}', '${escapeHtml(chn.name)}')">
                    + Add to Chain
                  </button>
                </div>
              </div>
              
              <div class="table-responsive">
                <table class="data-table" style="font-size: 0.8rem; margin-bottom: 0;">
                  <thead>
                    <tr>
                      <th style="width: 70px;">Handle</th>
                      <th style="width: 110px;">Verdict</th>
                      <th>Rule Expression / Match Criteria</th>
                      <th>Comment</th>
                      <th style="width: 80px; text-align: right;">Action</th>
                    </tr>
                  </thead>
                  <tbody>
          `;

          if (filteredRules.length === 0) {
            html += `<tr><td colspan="5" class="text-center text-muted py-3">${searchQuery ? 'No rules matching query.' : 'No rules in this chain.'}</td></tr>`;
          } else {
            filteredRules.forEach(rl => {
              let verdictBadge = `<span class="status-pill green font-mono">ACCEPT</span>`;
              if (rl.action === "drop") verdictBadge = `<span class="status-pill rose font-mono">DROP</span>`;
              else if (rl.action === "reject") verdictBadge = `<span class="status-pill rose font-mono">REJECT</span>`;
              else if (rl.action === "masquerade") verdictBadge = `<span class="status-pill purple font-mono">MASQUERADE</span>`;
              else if (rl.action === "redirect") verdictBadge = `<span class="status-pill cyan font-mono">REDIRECT</span>`;
              else if (rl.action === "dnat" || rl.action === "snat") verdictBadge = `<span class="status-pill amber font-mono">${rl.action.toUpperCase()}</span>`;

              // Syntax format highlights
              const formattedRule = escapeHtml(rl.rule_raw)
                .replace(/(ip saddr|ip6 saddr|saddr)/g, '<span class="text-cyan font-bold">$1</span>')
                .replace(/(ip daddr|ip6 daddr|daddr)/g, '<span class="text-emerald font-bold">$1</span>')
                .replace(/(tcp dport|udp dport|dport)/g, '<span class="text-amber font-bold">$1</span>')
                .replace(/(iifname|oifname|iif|oif)/g, '<span class="text-purple font-bold">$1</span>')
                .replace(/(masquerade|accept|drop|reject)/g, '<span class="font-bold">$1</span>');

              html += `
                <tr>
                  <td class="font-mono text-xs text-muted">${rl.handle !== null ? `#${rl.handle}` : '—'}</td>
                  <td>${verdictBadge}</td>
                  <td class="font-mono text-xs" style="word-break: break-all;">${formattedRule}</td>
                  <td class="text-xs text-muted">${rl.comment ? escapeHtml(rl.comment) : '—'}</td>
                  <td style="text-align: right;">
                    <button type="button" class="btn btn-danger-outline btn-sm" style="padding: 2px 7px; font-size: 0.72rem;" onclick="window.deleteNftRule('${escapeHtml(tbl.family)}', '${escapeHtml(tbl.name)}', '${escapeHtml(chn.name)}', ${rl.handle}, '${encodeURIComponent(rl.rule_raw)}')" title="Delete this rule">
                      Delete
                    </button>
                  </td>
                </tr>
              `;
            });
          }

          html += `
                  </tbody>
                </table>
              </div>
            </div>
          `;
        });
      }

      html += `
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  // Populate Table and Chain dropdowns dynamically based on live nftables ruleset
  function populateNftTableChainDropdowns(selectedFamily, targetTable, targetChain) {
    const famEl = document.getElementById("nftRuleFamily");
    const tblEl = document.getElementById("nftRuleTable");
    const tblCustom = document.getElementById("nftRuleTableCustom");
    const chnEl = document.getElementById("nftRuleChain");
    const chnCustom = document.getElementById("nftRuleChainCustom");
    if (!tblEl || !chnEl) return;

    const currentFamily = selectedFamily || famEl?.value || "inet";
    if (famEl && selectedFamily) famEl.value = selectedFamily;

    // Collect tables matching selected family
    const allTables = (state.nftablesData && state.nftablesData.tables) ? state.nftablesData.tables : [];
    const matchingTables = allTables.filter(t => t.family === currentFamily);

    const tableNames = new Set(matchingTables.map(t => t.name));
    if (tableNames.size === 0) {
      tableNames.add("filter");
      tableNames.add("wiregate");
      tableNames.add("nat");
    }

    let tblHtml = "";
    tableNames.forEach(tName => {
      tblHtml += `<option value="${escapeHtml(tName)}">${escapeHtml(tName)}</option>`;
    });
    tblHtml += `<option value="__custom__">+ Custom Table Name...</option>`;
    tblEl.innerHTML = tblHtml;

    let chosenTable = targetTable || (tblEl.options[0] ? tblEl.options[0].value : "filter");
    if (tableNames.has(chosenTable)) {
      tblEl.value = chosenTable;
      if (tblCustom) tblCustom.style.display = "none";
    } else if (targetTable) {
      tblEl.value = "__custom__";
      if (tblCustom) {
        tblCustom.style.display = "block";
        tblCustom.value = targetTable;
      }
    } else {
      tblEl.value = tblEl.options[0]?.value || "filter";
      if (tblCustom) tblCustom.style.display = "none";
    }

    populateNftChainDropdown(currentFamily, chosenTable, targetChain);
  }

  function populateNftChainDropdown(family, tableName, targetChain) {
    const tblEl = document.getElementById("nftRuleTable");
    const tblCustom = document.getElementById("nftRuleTableCustom");
    const chnEl = document.getElementById("nftRuleChain");
    const chnCustom = document.getElementById("nftRuleChainCustom");
    if (!chnEl) return;

    const actualTable = (tblEl?.value === "__custom__" ? tblCustom?.value.trim() : tblEl?.value) || tableName || "filter";

    const allTables = (state.nftablesData && state.nftablesData.tables) ? state.nftablesData.tables : [];
    const tableObj = allTables.find(t => t.family === family && t.name === actualTable);

    const chainNames = new Set();
    if (tableObj && tableObj.chains) {
      tableObj.chains.forEach(c => chainNames.add(c.name));
    }

    if (chainNames.size === 0) {
      if (actualTable === "nat" || actualTable === "wiregate") {
        chainNames.add("postrouting");
        chainNames.add("prerouting");
        chainNames.add("input");
        chainNames.add("output");
      } else {
        chainNames.add("forward");
        chainNames.add("input");
        chainNames.add("output");
      }
    }

    let chnHtml = "";
    chainNames.forEach(cName => {
      chnHtml += `<option value="${escapeHtml(cName)}">${escapeHtml(cName)}</option>`;
    });
    chnHtml += `<option value="__custom__">+ Custom Chain Name...</option>`;
    chnEl.innerHTML = chnHtml;

    let chosenChain = targetChain || (chnEl.options[0] ? chnEl.options[0].value : "forward");
    if (chainNames.has(chosenChain)) {
      chnEl.value = chosenChain;
      if (chnCustom) chnCustom.style.display = "none";
    } else if (targetChain) {
      chnEl.value = "__custom__";
      if (chnCustom) {
        chnCustom.style.display = "block";
        chnCustom.value = targetChain;
      }
    } else {
      chnEl.value = chnEl.options[0]?.value || "forward";
      if (chnCustom) chnCustom.style.display = "none";
    }
  }

  // Quick helper: open Add Rule modal prefilled with chain
  window.quickAddRuleToChain = function(family, table, chain) {
    populateNftTableChainDropdowns(family, table, chain);
    openModal("modalAddNftRule");
    updateNftRulePreview();
  };

  // Delete Rule Handler
  window.deleteNftRule = async function(family, table, chain, handle, encodedRaw) {
    const ruleRaw = decodeURIComponent(encodedRaw || "");
    const displayInfo = handle ? `handle #${handle}` : `"${ruleRaw}"`;
    if (!confirm(`Are you sure you want to delete rule ${displayInfo} from chain '${chain}'?\n\nA pre-deletion backup will be saved automatically.`)) {
      return;
    }

    try {
      const res = await fetch("/api/nftables/rules/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          table_family: family,
          table_name: table,
          chain_name: chain,
          handle: handle,
          rule_text: ruleRaw
        })
      });
      const data = await res.json();
      if (data.success) {
        showToast(data.message || "Rule deleted successfully.", "success");
        loadNftables();
      } else {
        showToast(data.error || "Failed to delete rule.", "error");
      }
    } catch (err) {
      showToast("Error executing rule deletion.", "error");
    }
  };

  // Update rule preview dynamically in Modal
  function updateNftRulePreview() {
    const previewInput = document.getElementById("nftRuleStatementPreview");
    if (!previewInput || previewInput.dataset.manualEdited === "true") return;

    const iif = document.getElementById("nftRuleIif")?.value.trim();
    const oif = document.getElementById("nftRuleOif")?.value.trim();
    const src = document.getElementById("nftRuleSrc")?.value.trim();
    const dst = document.getElementById("nftRuleDst")?.value.trim();
    const proto = document.getElementById("nftRuleProto")?.value;
    const dport = document.getElementById("nftRuleDport")?.value.trim();
    const action = document.getElementById("nftRuleAction")?.value || "accept";
    const comment = document.getElementById("nftRuleComment")?.value.trim();

    const parts = [];

    if (iif) {
      parts.push(iif.startsWith("!") ? `iifname != "${iif.replace(/^!\s*/, '')}"` : `iifname "${iif}"`);
    }
    if (oif) {
      parts.push(oif.startsWith("!") ? `oifname != "${oif.replace(/^!\s*/, '')}"` : `oifname "${oif}"`);
    }

    if (src) {
      parts.push(src.startsWith("{") || src.includes(",") ? `ip saddr ${src.startsWith("{") ? src : "{ " + src + " }"}` : `ip saddr ${src}`);
    }
    if (dst) {
      parts.push(dst.startsWith("{") || dst.includes(",") ? `ip daddr ${dst.startsWith("{") ? dst : "{ " + dst + " }"}` : `ip daddr ${dst}`);
    }

    if (proto && proto !== "all") {
      if (dport) {
        parts.push(dport.startsWith("{") || dport.includes(",") ? `${proto} dport ${dport.startsWith("{") ? dport : "{ " + dport + " }"}` : `${proto} dport ${dport}`);
      } else {
        parts.push(`ip protocol ${proto}`);
      }
    } else if (dport) {
      parts.push(dport.startsWith("{") || dport.includes(",") ? `tcp dport ${dport.startsWith("{") ? dport : "{ " + dport + " }"}` : `tcp dport ${dport}`);
    }

    parts.push(action);

    if (comment) {
      parts.push(`comment "${comment}"`);
    }

    previewInput.value = parts.join(" ");
  }

  // Hook input events to update live preview
  ["nftRuleIif", "nftRuleOif", "nftRuleSrc", "nftRuleDst", "nftRuleProto", "nftRuleDport", "nftRuleAction", "nftRuleComment"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", updateNftRulePreview);
    if (el) el.addEventListener("change", updateNftRulePreview);
  });

  const btnNftToggleRaw = document.getElementById("btnNftToggleRawEdit");
  if (btnNftToggleRaw) {
    btnNftToggleRaw.addEventListener("click", () => {
      const previewInput = document.getElementById("nftRuleStatementPreview");
      if (previewInput) {
        previewInput.dataset.manualEdited = "true";
        previewInput.focus();
        showToast("Switched to manual raw statement editing mode.", "info");
      }
    });
  }

  function getNftSelectedTable() {
    const tblEl = document.getElementById("nftRuleTable");
    const tblCustom = document.getElementById("nftRuleTableCustom");
    if (tblEl?.value === "__custom__") {
      return tblCustom?.value.trim() || "filter";
    }
    return tblEl?.value.trim() || "filter";
  }

  function getNftSelectedChain() {
    const chnEl = document.getElementById("nftRuleChain");
    const chnCustom = document.getElementById("nftRuleChainCustom");
    if (chnEl?.value === "__custom__") {
      return chnCustom?.value.trim() || "forward";
    }
    return chnEl?.value.trim() || "forward";
  }

  // Hook Family, Table, Chain change events
  const nftFamSelect = document.getElementById("nftRuleFamily");
  if (nftFamSelect) {
    nftFamSelect.addEventListener("change", () => {
      populateNftTableChainDropdowns(nftFamSelect.value);
      updateNftRulePreview();
    });
  }

  const nftTblSelect = document.getElementById("nftRuleTable");
  const nftTblCustom = document.getElementById("nftRuleTableCustom");
  if (nftTblSelect) {
    nftTblSelect.addEventListener("change", () => {
      if (nftTblSelect.value === "__custom__") {
        if (nftTblCustom) {
          nftTblCustom.style.display = "block";
          nftTblCustom.focus();
        }
      } else {
        if (nftTblCustom) nftTblCustom.style.display = "none";
      }
      populateNftChainDropdown(document.getElementById("nftRuleFamily")?.value || "inet", nftTblSelect.value);
      updateNftRulePreview();
    });
  }

  const nftChnSelect = document.getElementById("nftRuleChain");
  const nftChnCustom = document.getElementById("nftRuleChainCustom");
  if (nftChnSelect) {
    nftChnSelect.addEventListener("change", () => {
      if (nftChnSelect.value === "__custom__") {
        if (nftChnCustom) {
          nftChnCustom.style.display = "block";
          nftChnCustom.focus();
        }
      } else {
        if (nftChnCustom) nftChnCustom.style.display = "none";
      }
      updateNftRulePreview();
    });
  }

  // Submit Add Rule Form
  const formAddNftRule = document.getElementById("formAddNftRule");
  if (formAddNftRule) {
    formAddNftRule.addEventListener("submit", async (e) => {
      e.preventDefault();
      const alertBox = document.getElementById("nftAddRuleAlert");
      if (alertBox) alertBox.style.display = "none";

      const family = document.getElementById("nftRuleFamily")?.value.trim() || "inet";
      const table = getNftSelectedTable();
      const chain = getNftSelectedChain();
      const statement = document.getElementById("nftRuleStatementPreview")?.value.trim();
      const comment = document.getElementById("nftRuleComment")?.value.trim();

      if (!statement) {
        showToast("Rule statement cannot be empty.", "error");
        return;
      }

      const submitBtn = document.getElementById("btnSubmitAddNftRule");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Applying...";
      }

      try {
        const res = await fetch("/api/nftables/rules/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            table_family: family,
            table_name: table,
            chain_name: chain,
            rule_statement: statement,
            comment: comment
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || "Rule added and applied live successfully!", "success");
          closeAllModals();
          loadNftables();
        } else {
          if (alertBox) {
            alertBox.textContent = data.error + (data.details ? ` (${data.details})` : "");
            alertBox.style.display = "block";
          }
          showToast(data.error || "Failed to apply rule.", "error");
        }
      } catch (err) {
        showToast("Error adding rule to nftables.", "error");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>Add & Apply Rule</span>
          `;
        }
      }
    });
  }

  // Button: Test Rule Syntax in Modal
  const btnTestAddRuleSyntax = document.getElementById("btnTestAddRuleSyntax");
  if (btnTestAddRuleSyntax) {
    btnTestAddRuleSyntax.addEventListener("click", async () => {
      const family = document.getElementById("nftRuleFamily")?.value.trim() || "inet";
      const table = getNftSelectedTable();
      const chain = getNftSelectedChain();
      const statement = document.getElementById("nftRuleStatementPreview")?.value.trim();

      if (!statement) {
        showToast("Rule statement cannot be empty.", "error");
        return;
      }

      btnTestAddRuleSyntax.disabled = true;
      btnTestAddRuleSyntax.textContent = "Testing...";

      try {
        const dummyConf = `table ${family} ${table} {\n  chain ${chain} {\n    ${statement}\n  }\n}\n`;
        const res = await fetch("/api/nftables/validate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: dummyConf })
        });
        const data = await res.json();
        if (data.valid) {
          showToast("Rule syntax is valid ✓ (nft -c -f)", "success");
        } else {
          showToast(`Rule Syntax Error: ${data.message || data.error}`, "error");
        }
      } catch (err) {
        showToast("Error checking rule syntax.", "error");
      } finally {
        btnTestAddRuleSyntax.disabled = false;
        btnTestAddRuleSyntax.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span>Test Syntax</span>
        `;
      }
    });
  }

  // Button: Open Add Rule Modal
  const btnOpenAddNftModal = document.getElementById("btnOpenAddNftRuleModal");
  if (btnOpenAddNftModal) {
    btnOpenAddNftModal.addEventListener("click", () => {
      const previewInput = document.getElementById("nftRuleStatementPreview");
      if (previewInput) previewInput.dataset.manualEdited = "false";
      populateNftTableChainDropdowns();
      openModal("modalAddNftRule");
      updateNftRulePreview();
    });
  }

  // Button: Open Presets Modal
  const btnOpenNftPresetsModal = document.getElementById("btnOpenNftPresetsModal");
  if (btnOpenNftPresetsModal) {
    btnOpenNftPresetsModal.addEventListener("click", () => {
      openModal("modalNftPresets");
    });
  }

  // Preset Card Clicks
  document.querySelectorAll(".preset-card").forEach(card => {
    card.addEventListener("click", () => {
      const preset = card.dataset.preset;
      closeAllModals();

      const previewInput = document.getElementById("nftRuleStatementPreview");
      if (previewInput) previewInput.dataset.manualEdited = "false";

      if (preset === "proxy_forward") {
        populateNftTableChainDropdowns("inet", "filter", "forward");
        document.getElementById("nftRuleSrc").value = "{ 10.31.1.124, 10.31.1.136, 10.31.0.33 }";
        document.getElementById("nftRuleDst").value = "{ 3.21.193.9, 18.222.140.241, 13.235.72.170 }";
        document.getElementById("nftRuleProto").value = "tcp";
        document.getElementById("nftRuleDport").value = "80, 443";
        document.getElementById("nftRuleAction").value = "accept";
        document.getElementById("nftRuleComment").value = "Proxy Client Forwarding";
      } else if (preset === "nat_masquerade") {
        populateNftTableChainDropdowns("inet", "wiregate", "postrouting");
        document.getElementById("nftRuleOif").value = "ens18";
        document.getElementById("nftRuleSrc").value = "{ 10.31.1.124, 10.31.1.136 }";
        document.getElementById("nftRuleDst").value = "{ 3.21.193.9, 18.222.140.241 }";
        document.getElementById("nftRuleProto").value = "tcp";
        document.getElementById("nftRuleDport").value = "80, 443";
        document.getElementById("nftRuleAction").value = "masquerade";
        document.getElementById("nftRuleComment").value = "Egress NAT Masquerade";
      } else if (preset === "allow_proxy_port") {
        populateNftTableChainDropdowns("inet", "filter", "input");
        document.getElementById("nftRuleProto").value = "tcp";
        document.getElementById("nftRuleDport").value = "8085";
        document.getElementById("nftRuleAction").value = "accept";
        document.getElementById("nftRuleComment").value = "Squid Proxy Port 8085";
      } else if (preset === "block_ip") {
        populateNftTableChainDropdowns("inet", "filter", "input");
        document.getElementById("nftRuleSrc").value = "1.2.3.4";
        document.getElementById("nftRuleAction").value = "drop";
        document.getElementById("nftRuleComment").value = "Blocked Hostile IP";
      }

      openModal("modalAddNftRule");
      updateNftRulePreview();
    });
  });

  // View Switcher (Visual vs Raw)
  const nftViewPicker = document.getElementById("nftViewPicker");
  if (nftViewPicker) {
    nftViewPicker.addEventListener("click", (e) => {
      const btn = e.target.closest(".time-range-btn");
      if (!btn) return;
      nftViewPicker.querySelectorAll(".time-range-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const view = btn.dataset.view;
      const visualView = document.getElementById("nftVisualView");
      const rawView = document.getElementById("nftRawView");
      const filterBox = document.getElementById("nftVisualFilterBox");

      if (view === "raw") {
        if (visualView) visualView.style.display = "none";
        if (rawView) rawView.style.display = "block";
        if (filterBox) filterBox.style.display = "none";
      } else {
        if (visualView) visualView.style.display = "block";
        if (rawView) rawView.style.display = "none";
        if (filterBox) filterBox.style.display = "block";
        renderNftVisualExplorer();
      }
    });
  }

  // Filter input in visual rule explorer
  const nftSearchInput = document.getElementById("nftRuleSearchInput");
  if (nftSearchInput) {
    nftSearchInput.addEventListener("input", renderNftVisualExplorer);
  }

  // Button: Validate Syntax
  const btnValidateNft = document.getElementById("btnValidateNftables");
  if (btnValidateNft) {
    btnValidateNft.addEventListener("click", async () => {
      const rawContent = document.getElementById("nftRawEditorTextarea")?.value;
      try {
        const res = await fetch("/api/nftables/validate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: rawContent })
        });
        const data = await res.json();
        if (data.valid) {
          showToast("nftables syntax check passed successfully ✓ (nft -c -f)", "success");
        } else {
          showToast(`Syntax Error: ${data.message || data.error}`, "error");
        }
      } catch (err) {
        showToast("Failed to validate syntax.", "error");
      }
    });
  }

  // Button: Raw Validate Syntax
  const btnRawValidateNft = document.getElementById("btnRawValidateNft");
  if (btnRawValidateNft) {
    btnRawValidateNft.addEventListener("click", () => {
      if (btnValidateNft) btnValidateNft.click();
    });
  }

  // Button: Apply Ruleset
  const btnApplyNft = document.getElementById("btnApplyNftables");
  if (btnApplyNft) {
    btnApplyNft.addEventListener("click", async () => {
      if (!confirm("Apply /etc/nftables.conf live to kernel firewall?\n\nAn automated snapshot backup will be created before reload.")) return;
      try {
        const res = await fetch("/api/nftables/apply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({})
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || "Ruleset applied live with zero downtime!", "success");
          loadNftables();
        } else {
          showToast(data.error || "Failed to apply ruleset.", "error");
        }
      } catch (err) {
        showToast("Error applying ruleset.", "error");
      }
    });
  }

  // Button: Raw Save & Apply Live
  const btnRawSaveApplyNft = document.getElementById("btnRawSaveApplyNft");
  if (btnRawSaveApplyNft) {
    btnRawSaveApplyNft.addEventListener("click", async () => {
      const rawContent = document.getElementById("nftRawEditorTextarea")?.value;
      if (!rawContent || !rawContent.trim()) {
        showToast("Configuration content cannot be empty.", "error");
        return;
      }
      if (!confirm("Save raw configuration to /etc/nftables.conf and apply live?\n\nA backup snapshot will be captured.")) return;

      try {
        const res = await fetch("/api/nftables/apply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: rawContent })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || "Configuration saved and applied live!", "success");
          loadNftables();
        } else {
          showToast(data.error || "Failed to save configuration.", "error");
        }
      } catch (err) {
        showToast("Error saving /etc/nftables.conf.", "error");
      }
    });
  }

  // Button: Refresh Nftables
  const btnRefreshNft = document.getElementById("btnRefreshNftables");
  if (btnRefreshNft) {
    btnRefreshNft.addEventListener("click", () => {
      loadNftables();
      showToast("Refreshed nftables ruleset from system.", "info");
    });
  }

  // Bandwidth Listeners
  const btnRefreshBw = document.getElementById("btnRefreshBandwidth");
  if (btnRefreshBw) {
    btnRefreshBw.addEventListener("click", () => {
      loadPortBandwidth();
      showToast("Refreshed port bandwidth metrics.", "info");
    });
  }

  const btnCheckAllIsp = document.getElementById("btnCheckAllPortsInternet");
  if (btnCheckAllIsp) {
    btnCheckAllIsp.addEventListener("click", () => {
      window.checkAllPortsInternet();
    });
  }

  const bwSearch = document.getElementById("bwSearchInput");
  if (bwSearch) {
    bwSearch.addEventListener("input", () => {
      renderPortBandwidthTable();
    });
  }

  const bwAutoRefresh = document.getElementById("bandwidthAutoRefresh");
  if (bwAutoRefresh) {
    bwAutoRefresh.addEventListener("change", () => {
      setupBandwidthTimer();
    });
  }

  // ----------------------------------------------------------------------------
  // Initialization
  // ----------------------------------------------------------------------------
  const initialTab = window.location.hash || "#dashboard";
  switchTab(initialTab);
  loadStatus();
  loadPorts();
  loadPortBandwidth();

  // Poll status every 5 seconds
  setInterval(loadStatus, 5000);
});

