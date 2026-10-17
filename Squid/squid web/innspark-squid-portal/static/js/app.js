// ==============================================================================
// INNSPIARK SECURE PROXY & LDAP PORTAL - FRONTEND JAVASCRIPT
// ==============================================================================

document.addEventListener("DOMContentLoaded", () => {
    // Global fetch interceptor for handling session timeout / 401
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
        const response = await originalFetch(...args);
        if (response.status === 401) {
            window.location.href = "/login";
        }
        return response;
    };

    // State Store
    let state = {
        users: [],
        whitelist: [],
        blacklist: [],
        logs: [],
        isLogStreaming: true,
        logStreamInterval: null
    };

    // DOM Elements
    const navItems = document.querySelectorAll(".nav-item");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const pageTitle = document.getElementById("page-title");
    
    // Status Elements
    const squidPill = document.getElementById("squid-status-pill");
    const ldapPill = document.getElementById("ldap-status-pill");

    // Metrics
    const metricUsers = document.getElementById("metric-users-count");
    const metricWhitelist = document.getElementById("metric-whitelist-count");
    const metricBlacklist = document.getElementById("metric-blacklist-count");
    const metricLogSize = document.getElementById("metric-log-size");

    // Modal Elements
    const userModal = document.getElementById("create-user-modal");
    const btnOpenUserModal = document.getElementById("btn-open-create-user-modal");
    const btnCloseUserModal = document.getElementById("btn-close-modal");
    const btnCancelUserModal = document.getElementById("btn-cancel-modal");
    const createUserForm = document.getElementById("create-user-form");

    // ACL Elements
    const whitelistBox = document.getElementById("whitelist-tags-box");
    const blacklistBox = document.getElementById("blacklist-tags-box");
    const inputNewWhitelist = document.getElementById("input-new-whitelist");
    const inputNewBlacklist = document.getElementById("input-new-blacklist");
    const btnAddWhitelist = document.getElementById("btn-add-whitelist");
    const btnAddBlacklist = document.getElementById("btn-add-blacklist");
    const btnSaveAcls = document.getElementById("btn-save-acls");

    // Logs Elements
    const logsTableBody = document.getElementById("logs-table-body");
    const logsFilterInput = document.getElementById("logs-filter-input");
    const logsLimitSelect = document.getElementById("logs-limit-select");
    const btnToggleLogRefresh = document.getElementById("btn-toggle-log-refresh");
    const logRefreshText = document.getElementById("log-refresh-text");
    const btnManualRefreshLogs = document.getElementById("btn-manual-refresh-logs");

    // Quick Action Buttons
    const btnQuickReload = document.getElementById("btn-quick-reload");
    const btnQuickAddUser = document.getElementById("btn-quick-add-user");
    const btnQuickSarg = document.getElementById("btn-quick-sarg");
    const btnTriggerSarg = document.getElementById("btn-trigger-sarg");
    const btnQuickViewLogs = document.getElementById("btn-quick-view-logs");

    // --------------------------------------------------------------------------
    // Toast Notification Helper
    // --------------------------------------------------------------------------
    function showToast(message, type = "success") {
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span>${type === "success" ? "✓" : "⚠"}</span>
            <span>${message}</span>
        `;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(40px)";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // --------------------------------------------------------------------------
    // Tab Navigation
    // --------------------------------------------------------------------------
    const tabTitles = {
        "tab-overview": "Dashboard Overview",
        "tab-users": "LDAP User Directory",
        "tab-acls": "Domain Whitelist & Blacklist Rules",
        "tab-logs": "Live Proxy Access Stream",
        "tab-sarg": "SARG Audit & Analytics Reports",
        "tab-system": "System Services & Health"
    };

    function switchTab(targetTabId) {
        navItems.forEach(item => item.classList.remove("active"));
        tabPanes.forEach(pane => pane.classList.remove("active"));

        const activeBtn = document.querySelector(`[data-tab="${targetTabId}"]`);
        const activePane = document.getElementById(targetTabId);

        if (activeBtn) activeBtn.classList.add("active");
        if (activePane) activePane.classList.add("active");

        if (tabTitles[targetTabId]) {
            pageTitle.textContent = tabTitles[targetTabId];
        }

        // Trigger tab-specific fetches
        if (targetTabId === "tab-users") loadUsers();
        if (targetTabId === "tab-acls") loadAcls();
        if (targetTabId === "tab-logs") loadLogs();
    }

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            switchTab(item.getAttribute("data-tab"));
        });
    });

    if (btnQuickAddUser) btnQuickAddUser.addEventListener("click", () => {
        switchTab("tab-users");
        openUserModal();
    });
    if (btnQuickViewLogs) btnQuickViewLogs.addEventListener("click", () => switchTab("tab-logs"));
    if (btnQuickSarg) btnQuickSarg.addEventListener("click", () => switchTab("tab-sarg"));

    // --------------------------------------------------------------------------
    // API: System & Health Status
    // --------------------------------------------------------------------------
    async function fetchSystemStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();

            // Squid status pill
            if (data.squid && data.squid.active) {
                squidPill.innerHTML = `
                    <span class="status-indicator online"></span>
                    <span class="status-label">Squid: Active (3128)</span>
                `;
            } else {
                squidPill.innerHTML = `
                    <span class="status-indicator offline"></span>
                    <span class="status-label">Squid: Inactive</span>
                `;
            }

            // LDAP status pill
            if (data.ldap && data.ldap.connected) {
                ldapPill.innerHTML = `
                    <span class="status-indicator online"></span>
                    <span class="status-label">LDAP: Online</span>
                `;
            } else {
                ldapPill.innerHTML = `
                    <span class="status-indicator offline"></span>
                    <span class="status-label">LDAP: Disconnected</span>
                `;
            }

            // Metric values
            if (data.counts) {
                metricWhitelist.textContent = data.counts.whitelisted_domains;
                metricBlacklist.textContent = data.counts.blacklisted_domains;
                
                // Format log size
                const bytes = data.counts.access_log_bytes;
                if (bytes < 1024) metricLogSize.textContent = bytes + " B";
                else if (bytes < 1024 * 1024) metricLogSize.textContent = (bytes / 1024).toFixed(1) + " KB";
                else metricLogSize.textContent = (bytes / (1024 * 1024)).toFixed(1) + " MB";
            }

            // System tab updates
            const sysSquid = document.getElementById("sys-squid-status");
            if (sysSquid) {
                sysSquid.textContent = data.squid.active ? "Active (Running)" : "Stopped";
            }
        } catch (err) {
            console.error("Status fetch error:", err);
        }
    }

    // --------------------------------------------------------------------------
    // API: LDAP User Management
    // --------------------------------------------------------------------------
    async function loadUsers() {
        const tbody = document.getElementById("users-table-body");
        tbody.innerHTML = `<tr><td colspan="6" class="text-center loading-row">Fetching LDAP accounts...</td></tr>`;

        try {
            const res = await fetch("/api/users");
            const data = await res.json();

            if (!data.success) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center loading-row" style="color:var(--status-danger)">Error: ${data.error}</td></tr>`;
                return;
            }

            state.users = data.users || [];
            metricUsers.textContent = state.users.length;
            renderUsersTable(state.users);
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center loading-row" style="color:var(--status-danger)">Failed to connect to LDAP backend.</td></tr>`;
        }
    }

    function renderUsersTable(userList) {
        const tbody = document.getElementById("users-table-body");
        tbody.innerHTML = "";

        if (userList.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center loading-row">No users found in directory.</td></tr>`;
            return;
        }

        userList.forEach(u => {
            const tr = document.createElement("tr");

            const proxyBadge = u.in_proxy_users 
                ? `<span class="badge badge-success">Permitted (proxy_users)</span>` 
                : `<span class="badge badge-muted">No Access</span>`;

            const adminBadge = u.in_proxy_admins 
                ? `<span class="badge badge-purple">Admin (proxy_admins)</span>` 
                : `<span class="badge badge-muted">Standard</span>`;

            tr.innerHTML = `
                <td><strong>${u.uid}</strong></td>
                <td>${u.cn || "-"}</td>
                <td>${u.mail || "-"}</td>
                <td>${proxyBadge}</td>
                <td>${adminBadge}</td>
                <td>
                    <button class="btn btn-secondary btn-sm btn-toggle-proxy" data-uid="${u.uid}" data-has="${u.in_proxy_users}">
                        ${u.in_proxy_users ? "Revoke Access" : "Grant Access"}
                    </button>
                    <button class="btn btn-danger btn-sm btn-delete-user" data-uid="${u.uid}">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Attach action handlers
        document.querySelectorAll(".btn-toggle-proxy").forEach(btn => {
            btn.addEventListener("click", () => toggleProxyGroup(btn.dataset.uid, btn.dataset.has === "true"));
        });

        document.querySelectorAll(".btn-delete-user").forEach(btn => {
            btn.addEventListener("click", () => deleteUser(btn.dataset.uid));
        });
    }

    async function toggleProxyGroup(uid, currentlyInGroup) {
        const action = currentlyInGroup ? "remove" : "add";
        try {
            const res = await fetch(`/api/users/${uid}/toggle-group`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ group_name: "proxy_users", action: action })
            });
            const data = await res.json();
            if (data.success) {
                showToast(data.message, "success");
                loadUsers();
            } else {
                showToast(data.error, "error");
            }
        } catch (err) {
            showToast("Failed to toggle proxy group.", "error");
        }
    }

    async function deleteUser(uid) {
        if (!confirm(`Are you sure you want to permanently delete LDAP user '${uid}'?`)) return;

        try {
            const res = await fetch(`/api/users/${uid}`, { method: "DELETE" });
            const data = await res.json();
            if (data.success) {
                showToast(data.message, "success");
                loadUsers();
            } else {
                showToast(data.error, "error");
            }
        } catch (err) {
            showToast("Failed to delete user.", "error");
        }
    }

    // Modal Open/Close
    function openUserModal() { userModal.classList.add("active"); }
    function closeUserModal() { 
        userModal.classList.remove("active");
        createUserForm.reset();
    }

    if (btnOpenUserModal) btnOpenUserModal.addEventListener("click", openUserModal);
    if (btnCloseUserModal) btnCloseUserModal.addEventListener("click", closeUserModal);
    if (btnCancelUserModal) btnCancelUserModal.addEventListener("click", closeUserModal);

    createUserForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            username: document.getElementById("input-username").value.trim(),
            first_name: document.getElementById("input-first-name").value.trim(),
            last_name: document.getElementById("input-last-name").value.trim(),
            email: document.getElementById("input-email").value.trim(),
            password: document.getElementById("input-password").value,
            is_proxy_user: document.getElementById("check-proxy-user").checked,
            is_proxy_admin: document.getElementById("check-proxy-admin").checked
        };

        try {
            const res = await fetch("/api/users", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                showToast(data.message, "success");
                closeUserModal();
                loadUsers();
            } else {
                showToast(data.error, "error");
            }
        } catch (err) {
            showToast("Network error creating user.", "error");
        }
    });

    // User Search Filter
    const userSearchInput = document.getElementById("user-search-input");
    if (userSearchInput) {
        userSearchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase();
            const filtered = state.users.filter(u => 
                u.uid.toLowerCase().includes(query) ||
                (u.cn && u.cn.toLowerCase().includes(query)) ||
                (u.mail && u.mail.toLowerCase().includes(query))
            );
            renderUsersTable(filtered);
        });
    }

    // --------------------------------------------------------------------------
    // API: Domain ACLs (Whitelist / Blacklist)
    // --------------------------------------------------------------------------
    async function loadAcls() {
        try {
            const res = await fetch("/api/acls");
            const data = await res.json();
            state.whitelist = data.whitelist || [];
            state.blacklist = data.blacklist || [];
            renderAclTags();
        } catch (err) {
            showToast("Failed to load ACL domain lists.", "error");
        }
    }

    function renderAclTags() {
        // Whitelist Box
        whitelistBox.innerHTML = "";
        state.whitelist.forEach(domain => {
            const pill = document.createElement("span");
            pill.className = "tag-pill";
            pill.innerHTML = `
                <span>${domain}</span>
                <span class="tag-remove-btn" data-type="whitelist" data-domain="${domain}">&times;</span>
            `;
            whitelistBox.appendChild(pill);
        });
        document.getElementById("whitelist-count-badge").textContent = state.whitelist.length;

        // Blacklist Box
        blacklistBox.innerHTML = "";
        state.blacklist.forEach(domain => {
            const pill = document.createElement("span");
            pill.className = "tag-pill";
            pill.innerHTML = `
                <span>${domain}</span>
                <span class="tag-remove-btn" data-type="blacklist" data-domain="${domain}">&times;</span>
            `;
            blacklistBox.appendChild(pill);
        });
        document.getElementById("blacklist-count-badge").textContent = state.blacklist.length;

        // Attach tag removal events
        document.querySelectorAll(".tag-remove-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const domain = btn.dataset.domain;
                if (btn.dataset.type === "whitelist") {
                    state.whitelist = state.whitelist.filter(d => d !== domain);
                } else {
                    state.blacklist = state.blacklist.filter(d => d !== domain);
                }
                renderAclTags();
            });
        });
    }

    function addAclTag(type, inputEl) {
        const domain = inputEl.value.trim().toLowerCase();
        if (!domain) return;
        if (type === "whitelist") {
            if (!state.whitelist.includes(domain)) state.whitelist.push(domain);
        } else {
            if (!state.blacklist.includes(domain)) state.blacklist.push(domain);
        }
        inputEl.value = "";
        renderAclTags();
    }

    btnAddWhitelist.addEventListener("click", () => addAclTag("whitelist", inputNewWhitelist));
    inputNewWhitelist.addEventListener("keydown", (e) => { if (e.key === "Enter") addAclTag("whitelist", inputNewWhitelist); });

    btnAddBlacklist.addEventListener("click", () => addAclTag("blacklist", inputNewBlacklist));
    inputNewBlacklist.addEventListener("keydown", (e) => { if (e.key === "Enter") addAclTag("blacklist", inputNewBlacklist); });

    btnSaveAcls.addEventListener("click", async () => {
        btnSaveAcls.disabled = true;
        btnSaveAcls.textContent = "Saving & Reloading Squid...";
        try {
            const res = await fetch("/api/acls", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    whitelist: state.whitelist,
                    blacklist: state.blacklist,
                    reload_squid: true
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast("ACLs saved and Squid reconfigured!", "success");
            } else {
                showToast(data.error || "Failed to reload Squid.", "error");
            }
        } catch (err) {
            showToast("Network error applying ACLs.", "error");
        } finally {
            btnSaveAcls.disabled = false;
            btnSaveAcls.textContent = "Save Rules & Reload Squid";
            fetchSystemStatus();
        }
    });

    // Quick reload
    btnQuickReload.addEventListener("click", async () => {
        btnQuickReload.disabled = true;
        try {
            const res = await fetch("/api/squid/reload", { method: "POST" });
            const data = await res.json();
            if (data.success) {
                showToast("Squid reconfigured successfully.", "success");
            } else {
                showToast(data.message || "Failed to reload Squid.", "error");
            }
        } catch (err) {
            showToast("Error reloading Squid.", "error");
        } finally {
            btnQuickReload.disabled = false;
            fetchSystemStatus();
        }
    });

    // --------------------------------------------------------------------------
    // API: Live Logs Streaming
    // --------------------------------------------------------------------------
    async function loadLogs() {
        const limit = logsLimitSelect.value || 50;
        try {
            const res = await fetch(`/api/logs?lines=${limit}`);
            const data = await res.json();
            if (data.success) {
                state.logs = data.logs || [];
                renderLogsTable(state.logs);
            }
        } catch (err) {
            console.error("Log fetch failed:", err);
        }
    }

    function renderLogsTable(logsList) {
        logsTableBody.innerHTML = "";
        if (logsList.length === 0) {
            logsTableBody.innerHTML = `<tr><td colspan="7" class="text-center loading-row">No log entries available.</td></tr>`;
            return;
        }

        logsList.forEach(log => {
            const tr = document.createElement("tr");

            // Format status code
            let statusBadgeClass = "badge-muted";
            if (log.status) {
                if (log.status.includes("200")) statusBadgeClass = "badge-success";
                else if (log.status.includes("403")) statusBadgeClass = "badge-danger";
                else if (log.status.includes("407")) statusBadgeClass = "badge-warning";
            }

            // Truncate long URLs
            const displayUrl = log.url && log.url.length > 50 ? log.url.substring(0, 50) + "..." : (log.url || "-");

            tr.innerHTML = `
                <td>${log.time || "-"}</td>
                <td>${log.ip || "-"}</td>
                <td><span class="badge ${statusBadgeClass}">${log.status || "-"}</span></td>
                <td>${log.method || "-"}</td>
                <td title="${log.url || ''}">${displayUrl}</td>
                <td><strong>${log.user || "-"}</strong></td>
                <td>${log.size || "-"} B</td>
            `;
            logsTableBody.appendChild(tr);
        });
    }

    // Filter Logs
    if (logsFilterInput) {
        logsFilterInput.addEventListener("input", (e) => {
            const q = e.target.value.toLowerCase();
            const filtered = state.logs.filter(l => 
                (l.ip && l.ip.includes(q)) ||
                (l.user && l.user.toLowerCase().includes(q)) ||
                (l.url && l.url.toLowerCase().includes(q)) ||
                (l.status && l.status.toLowerCase().includes(q))
            );
            renderLogsTable(filtered);
        });
    }

    // Toggle Stream Pause
    btnToggleLogRefresh.addEventListener("click", () => {
        state.isLogStreaming = !state.isLogStreaming;
        if (state.isLogStreaming) {
            logRefreshText.textContent = "Pause Stream";
            startLogStream();
            showToast("Log stream resumed.", "success");
        } else {
            logRefreshText.textContent = "Resume Stream";
            stopLogStream();
            showToast("Log stream paused.", "warning");
        }
    });

    btnManualRefreshLogs.addEventListener("click", loadLogs);

    function startLogStream() {
        if (state.logStreamInterval) clearInterval(state.logStreamInterval);
        state.logStreamInterval = setInterval(() => {
            // Only fetch if live logs tab is active
            if (document.getElementById("tab-logs").classList.contains("active")) {
                loadLogs();
            }
        }, 3000);
    }

    function stopLogStream() {
        if (state.logStreamInterval) clearInterval(state.logStreamInterval);
    }

    // --------------------------------------------------------------------------
    // API: SARG Report Generation
    // --------------------------------------------------------------------------
    async function triggerSargGeneration() {
        btnTriggerSarg.disabled = true;
        btnTriggerSarg.textContent = "Generating...";
        try {
            const res = await fetch("/api/sarg/generate", { method: "POST" });
            const data = await res.json();
            if (data.success) {
                showToast("SARG report refreshed successfully!", "success");
                // Reload iframe
                const iframe = document.getElementById("sarg-iframe");
                if (iframe) iframe.src = iframe.src;
            } else {
                showToast(data.error || "Failed to generate report.", "error");
            }
        } catch (err) {
            showToast("Error generating SARG report.", "error");
        } finally {
            btnTriggerSarg.disabled = false;
            btnTriggerSarg.textContent = "⚡ Generate Report Now";
        }
    }

    if (btnTriggerSarg) btnTriggerSarg.addEventListener("click", triggerSargGeneration);

    // --------------------------------------------------------------------------
    // Initialization
    // --------------------------------------------------------------------------
    fetchSystemStatus();
    loadUsers();
    loadAcls();
    startLogStream();

    // Periodic health poll every 10 seconds
    setInterval(fetchSystemStatus, 10000);
});
