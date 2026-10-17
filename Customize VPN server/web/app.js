// ========================================================
// SSL VPN Web Management Portal JavaScript Logic
// ========================================================

const API = {
  session: '/api/session',
  login: '/api/login',
  logout: '/api/logout',
  status: '/api/status',
  users: '/api/users',
  toggleUser: '/api/users/toggle',
  deleteUser: (username) => `/api/users/${encodeURIComponent(username)}`,
  logs: '/api/logs'
};

let authToken = localStorage.getItem('sslvpn_token') || null;
let currentUsername = localStorage.getItem('sslvpn_user') || 'admin';
let logInterval = null;

// Initialize app on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  checkSession();
});

function getHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
}

// --------------------------------------------------------
// Navigation & Views
// --------------------------------------------------------
function switchView(viewName) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById(`${viewName}-view`);
  if (target) {
    target.classList.add('active');
  }

  if (viewName === 'dashboard') {
    loadStatus();
    loadUsers();
    startLogStream();
  } else {
    stopLogStream();
  }
}

function switchTab(tabName) {
  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabName);
  });
  document.querySelectorAll('.tab-content').forEach(c => {
    c.classList.toggle('active', c.id === `tab-${tabName}`);
  });

  if (tabName === 'logs') {
    loadLogs();
  } else if (tabName === 'users') {
    loadUsers();
  } else if (tabName === 'overview') {
    loadStatus();
  }
}

// --------------------------------------------------------
// Event Listeners
// --------------------------------------------------------
function setupEventListeners() {
  // Login Form
  const loginForm = document.getElementById('login-form');
  loginForm.addEventListener('submit', handleLogin);

  // Toggle Password Visibility in Login
  const togglePassBtn = document.getElementById('toggle-password');
  togglePassBtn.addEventListener('click', () => {
    const passInput = document.getElementById('password');
    const isPass = passInput.type === 'password';
    passInput.type = isPass ? 'text' : 'password';
  });

  // Logout Button
  const logoutBtn = document.getElementById('logout-btn');
  logoutBtn.addEventListener('click', handleLogout);

  // Tab Navigation
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  // Refresh Buttons
  document.getElementById('btn-refresh-status').addEventListener('click', loadStatus);
  document.getElementById('btn-refresh-logs').addEventListener('click', loadLogs);

  // Auto Refresh Logs Checkbox
  const autoLogs = document.getElementById('auto-refresh-logs');
  autoLogs.addEventListener('change', () => {
    if (autoLogs.checked) {
      startLogStream();
    } else {
      stopLogStream();
    }
  });

  // Add User Modal
  const addUserBtn = document.getElementById('btn-open-add-user');
  const modal = document.getElementById('add-user-modal');
  const closeBtn = document.getElementById('modal-close-btn');
  const cancelBtn = document.getElementById('modal-cancel-btn');
  const addUserForm = document.getElementById('add-user-form');
  const genPwBtn = document.getElementById('modal-gen-pw-btn');

  addUserBtn.addEventListener('click', () => {
    modal.classList.remove('hidden');
    document.getElementById('modal-alert').classList.add('hidden');
    addUserForm.reset();
    document.getElementById('new-subnets').value = '0.0.0.0/0';
    document.getElementById('new-bandwidth').value = '0';
  });

  const closeModal = () => modal.classList.add('hidden');
  closeBtn.addEventListener('click', closeModal);
  cancelBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  genPwBtn.addEventListener('click', () => {
    const chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789#@!';
    let pass = '';
    for (let i = 0; i < 14; i++) {
      pass += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const passInput = document.getElementById('new-password');
    passInput.type = 'text';
    passInput.value = pass;
  });

  addUserForm.addEventListener('submit', handleAddUser);

  // Copy Buttons
  setupCopyBtn('btn-copy-quick-cli', 'quick-cli-code');
  setupCopyBtn('btn-copy-quick-docker', 'quick-docker-code');
  setupCopyBtn('btn-copy-logs', 'terminal-logs');
}

function setupCopyBtn(btnId, targetId) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.addEventListener('click', () => {
    const text = document.getElementById(targetId).innerText;
    navigator.clipboard.writeText(text).then(() => {
      const original = btn.innerHTML;
      btn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none"><polyline points="20 6 9 17 4 12"></polyline></svg><span>Copied!</span>`;
      setTimeout(() => { btn.innerHTML = original; }, 2000);
    });
  });
}

// --------------------------------------------------------
// Authentication
// --------------------------------------------------------
async function checkSession() {
  if (!authToken) {
    switchView('login');
    return;
  }

  try {
    const res = await fetch(API.session, { headers: getHeaders() });
    if (res.ok) {
      const data = await res.json();
      currentUsername = data.username || 'admin';
      updateUserDisplay();
      switchView('dashboard');
    } else {
      localStorage.removeItem('sslvpn_token');
      authToken = null;
      switchView('login');
    }
  } catch (err) {
    switchView('login');
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const alertBox = document.getElementById('login-alert');
  alertBox.classList.add('hidden');

  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const submitBtn = document.getElementById('login-submit-btn');

  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span>Verifying credentials...</span>';

  try {
    const res = await fetch(API.login, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (res.ok && data.token) {
      authToken = data.token;
      currentUsername = data.username || username;
      localStorage.setItem('sslvpn_token', authToken);
      localStorage.setItem('sslvpn_user', currentUsername);
      updateUserDisplay();
      switchView('dashboard');
    } else {
      alertBox.className = 'alert-banner error';
      alertBox.textContent = data.error || 'Invalid username or password';
      alertBox.classList.remove('hidden');
    }
  } catch (err) {
    alertBox.className = 'alert-banner error';
    alertBox.textContent = 'Server connection failed. Please check that the portal is running.';
    alertBox.classList.remove('hidden');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span>Sign In to Dashboard</span><svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>`;
  }
}

async function handleLogout() {
  try {
    await fetch(API.logout, { method: 'POST', headers: getHeaders() });
  } catch (err) {
    // Ignore error
  }
  authToken = null;
  localStorage.removeItem('sslvpn_token');
  localStorage.removeItem('sslvpn_user');
  switchView('login');
}

function updateUserDisplay() {
  document.getElementById('display-username').textContent = currentUsername;
  const initials = currentUsername.substring(0, 2).toUpperCase();
  document.getElementById('user-avatar-initials').textContent = initials;
}

// --------------------------------------------------------
// Data Loading: Status
// --------------------------------------------------------
async function loadStatus() {
  try {
    const res = await fetch(API.status, { headers: getHeaders() });
    if (res.status === 401) {
      handleLogout();
      return;
    }
    const data = await res.json();

    // Global & KPI
    const isRunning = data.container && data.container.status && data.container.status.toLowerCase().includes('up');
    const statusText = isRunning ? 'Server Online (Port 443)' : 'Container Offline';
    const statusBadge = document.getElementById('global-status-badge');
    statusBadge.className = isRunning ? 'server-status-badge online' : 'server-status-badge offline';
    document.getElementById('global-status-text').textContent = statusText;

    document.getElementById('kpi-status').textContent = isRunning ? 'Healthy' : 'Stopped';
    document.getElementById('kpi-port').textContent = `${data.server.host || '0.0.0.0'}:${data.server.port || 443}`;
    document.getElementById('kpi-subnet').textContent = data.network.vpn_subnet || '10.8.0.0/24';
    document.getElementById('kpi-server-ip').textContent = `Gateway IP: ${data.network.server_ip || '10.8.0.1'}`;
    document.getElementById('kpi-users-count').textContent = data.users_count || 1;

    // Spec table
    document.getElementById('spec-ip-pool').textContent = `${data.network.ip_pool_start || '10.8.0.10'} → ${data.network.ip_pool_end || '10.8.0.250'}`;
    document.getElementById('spec-mtu').textContent = `${data.network.mtu || 1400} bytes`;
    document.getElementById('spec-dns').textContent = (data.network.dns_servers || ['8.8.8.8']).join(', ');
    document.getElementById('spec-auth-mode').textContent = data.security.auth_mode || 'password';
    document.getElementById('spec-max-clients').textContent = data.session.max_clients || 50;
    document.getElementById('spec-idle-timeout').textContent = `${data.session.idle_timeout_seconds || 300}s`;

    // Sidebar TUN mode
    const isMock = data.tun_mock !== false;
    document.getElementById('sidebar-tun-mode').textContent = isMock ? 'MOCK TUN (Safe)' : 'REAL KERNEL TUN';
  } catch (err) {
    console.error('Error loading status:', err);
  }
}

// --------------------------------------------------------
// Data Loading: Users
// --------------------------------------------------------
async function loadUsers() {
  try {
    const res = await fetch(API.users, { headers: getHeaders() });
    if (res.status === 401) {
      handleLogout();
      return;
    }
    const data = await res.json();
    const tbody = document.getElementById('users-table-body');
    tbody.innerHTML = '';

    const users = data.users || {};
    const usernames = Object.keys(users);

    if (usernames.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4">No users configured.</td></tr>';
      return;
    }

    usernames.forEach(name => {
      const u = users[name];
      const isEnabled = u.enabled !== false;
      const subnets = (u.allowed_subnets || ['0.0.0.0/0']).join(', ');
      const bw = u.bandwidth_kbps > 0 ? `${u.bandwidth_kbps} kbps` : 'Unlimited';
      const vpnIp = u.vpn_ip || 'Auto-assign pool';

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${escapeHtml(name)}</strong></td>
        <td>
          <span class="badge-pill ${isEnabled ? 'badge-active' : 'badge-disabled'}">
            ${isEnabled ? 'Active' : 'Disabled'}
          </span>
        </td>
        <td><code>${escapeHtml(vpnIp)}</code></td>
        <td><code>${escapeHtml(subnets)}</code></td>
        <td>${escapeHtml(bw)}</td>
        <td class="text-right">
          <button class="btn btn-secondary btn-sm" onclick="toggleUserStatus('${escapeHtml(name)}')">
            ${isEnabled ? 'Disable' : 'Enable'}
          </button>
          ${name !== 'admin' ? `
            <button class="btn btn-danger btn-sm" style="margin-left: 0.5rem;" onclick="deleteUser('${escapeHtml(name)}')">
              Delete
            </button>
          ` : ''}
        </td>
      `;
      tbody.appendChild(tr);
    });

    document.getElementById('kpi-users-count').textContent = usernames.length;
  } catch (err) {
    console.error('Error loading users:', err);
  }
}

// --------------------------------------------------------
// User Management Actions
// --------------------------------------------------------
async function handleAddUser(e) {
  e.preventDefault();
  const alertBox = document.getElementById('modal-alert');
  alertBox.classList.add('hidden');

  const username = document.getElementById('new-username').value.trim();
  const password = document.getElementById('new-password').value;
  const vpn_ip = document.getElementById('new-vpn-ip').value.trim() || null;
  const bandwidth_kbps = parseInt(document.getElementById('new-bandwidth').value || 0, 10);
  const subnetsStr = document.getElementById('new-subnets').value.trim();
  const allowed_subnets = subnetsStr ? subnetsStr.split(',').map(s => s.trim()).filter(Boolean) : ['0.0.0.0/0'];

  const submitBtn = document.getElementById('modal-submit-btn');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Saving...';

  try {
    const res = await fetch(API.users, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        username,
        password,
        vpn_ip,
        bandwidth_kbps,
        allowed_subnets
      })
    });

    const data = await res.json();
    if (res.ok) {
      document.getElementById('add-user-modal').classList.add('hidden');
      loadUsers();
    } else {
      alertBox.className = 'alert-banner error';
      alertBox.textContent = data.error || 'Failed to add user';
      alertBox.classList.remove('hidden');
    }
  } catch (err) {
    alertBox.className = 'alert-banner error';
    alertBox.textContent = 'Failed to connect to server';
    alertBox.classList.remove('hidden');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Save User';
  }
}

async function toggleUserStatus(username) {
  try {
    const res = await fetch(API.toggleUser, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ username })
    });
    if (res.ok) {
      loadUsers();
    }
  } catch (err) {
    console.error('Error toggling user:', err);
  }
}

async function deleteUser(username) {
  if (!confirm(`Are you sure you want to delete user "${username}"?`)) return;

  try {
    const res = await fetch(API.deleteUser(username), {
      method: 'DELETE',
      headers: getHeaders()
    });
    if (res.ok) {
      loadUsers();
    }
  } catch (err) {
    console.error('Error deleting user:', err);
  }
}

// --------------------------------------------------------
// Logs Stream
// --------------------------------------------------------
async function loadLogs() {
  try {
    const res = await fetch(API.logs, { headers: getHeaders() });
    if (res.ok) {
      const data = await res.json();
      const terminal = document.getElementById('terminal-logs');
      terminal.textContent = data.logs || 'No logs available.';
      terminal.scrollTop = terminal.scrollHeight;
    }
  } catch (err) {
    console.error('Error fetching logs:', err);
  }
}

function startLogStream() {
  stopLogStream();
  loadLogs();
  logInterval = setInterval(() => {
    const auto = document.getElementById('auto-refresh-logs');
    if (auto && auto.checked) {
      loadLogs();
    }
  }, 3000);
}

function stopLogStream() {
  if (logInterval) {
    clearInterval(logInterval);
    logInterval = null;
  }
}

// Utility
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
