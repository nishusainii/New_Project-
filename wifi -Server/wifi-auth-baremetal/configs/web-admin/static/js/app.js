// Innspark Wi-Fi & LDAP Manager Client JavaScript

let allUsers = [];

document.addEventListener("DOMContentLoaded", () => {
  fetchServerStatus();
  loadUsers();

  // Search filter
  document.getElementById("user-search-input").addEventListener("input", (e) => {
    filterUsers(e.target.value);
  });
});

// 1. Fetch Server Status
async function fetchServerStatus() {
  try {
    const res = await fetch("/api/status");
    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }
    const data = await res.json();
    if (data.ldap_online) {
      document.getElementById("ldap-host-badge").innerText = data.ldap_host;
      document.getElementById("base-dn-badge").innerText = data.base_dn;
    } else {
      const pill = document.getElementById("ldap-status-pill");
      pill.querySelector(".indicator-dot").className = "indicator-dot offline";
      pill.querySelector("strong").innerText = "Offline";
    }
  } catch (err) {
    console.error("Status fetch failed:", err);
  }
}

// 2. Fetch Users
async function loadUsers() {
  const tbody = document.getElementById("users-table-body");
  try {
    const res = await fetch("/api/users");
    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }
    const data = await res.json();

    if (!data.success) {
      tbody.innerHTML = `<tr><td colspan="6" class="loading-cell" style="color: #f43f5e;">Failed to load users: ${data.error}</td></tr>`;
      return;
    }

    allUsers = data.users || [];
    renderUsersTable(allUsers);
    updateKpis(allUsers);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading-cell" style="color: #f43f5e;">Network error connecting to API: ${err.message}</td></tr>`;
  }
}

// 3. Render Table
function renderUsersTable(users) {
  const tbody = document.getElementById("users-table-body");
  if (users.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">No employee accounts found matching your query.</td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(user => {
    const initials = (user.cn || user.uid)
      .split(" ")
      .map(n => n[0])
      .join("")
      .substring(0, 2)
      .toUpperCase();

    const wifiBadge = user.wifi_authorized
      ? `<span class="badge-pill authorized">● Active (wifi-users)</span>`
      : `<span class="badge-pill revoked">○ Revoked</span>`;

    const toggleBtnText = user.wifi_authorized ? "Revoke Wi-Fi" : "Grant Wi-Fi";
    const toggleAction = user.wifi_authorized ? false : true;

    return `
      <tr>
        <td>
          <div class="user-cell">
            <div class="user-avatar">${initials}</div>
            <div>
              <div class="user-name">${escapeHtml(user.cn)}</div>
              <div style="font-size: 0.75rem; color: #64748b;">${escapeHtml(user.sn)}</div>
            </div>
          </div>
        </td>
        <td><span class="username-tag">${escapeHtml(user.uid)}</span></td>
        <td><span class="email-tag">${escapeHtml(user.mail)}</span></td>
        <td><span style="font-family: 'Fira Code', monospace; font-size: 0.8rem; color: #94a3b8;">${user.uidNumber}</span></td>
        <td>${wifiBadge}</td>
        <td>
          <div class="action-cluster">
            <button class="action-btn btn-key" onclick="openResetPasswordModal('${escapeHtml(user.uid)}', '${escapeHtml(user.cn)}')">
              🔑 Password
            </button>
            <button class="action-btn btn-toggle" onclick="toggleWifiAccess('${escapeHtml(user.uid)}', ${toggleAction})">
              📶 ${toggleBtnText}
            </button>
            <button class="action-btn" onclick="openTestForUser('${escapeHtml(user.uid)}')">
              🧪 Test
            </button>
            <button class="action-btn btn-del" onclick="deleteUser('${escapeHtml(user.uid)}')">
              🗑️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

// 4. Update KPIs
function updateKpis(users) {
  document.getElementById("kpi-total-users").innerText = users.length;
  const wifiCount = users.filter(u => u.wifi_authorized).length;
  document.getElementById("kpi-wifi-users").innerText = `${wifiCount} / ${users.length}`;
}

// 5. Filter Users
function filterUsers(query) {
  const q = query.trim().toLowerCase();
  if (!q) {
    renderUsersTable(allUsers);
    return;
  }
  const filtered = allUsers.filter(u => 
    u.uid.toLowerCase().includes(q) ||
    (u.cn && u.cn.toLowerCase().includes(q)) ||
    (u.mail && u.mail.toLowerCase().includes(q))
  );
  renderUsersTable(filtered);
}

// 6. Modal Controls
function openModal(id) {
  document.getElementById(id).classList.add("active");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("active");
}

function openAddUserModal() {
  document.getElementById("add-user-form").reset();
  document.getElementById("add-password").value = "WifiPassword2026!";
  openModal("add-user-modal");
}

function suggestUsername() {
  const first = document.getElementById("add-givenName").value.trim().toLowerCase();
  const last = document.getElementById("add-sn").value.trim().toLowerCase();
  const uidInput = document.getElementById("add-uid");
  const mailInput = document.getElementById("add-mail");

  if (first && last) {
    const suggested = `${first}.${last}`.replace(/[^a-z0-9.]/g, "");
    uidInput.value = suggested;
    mailInput.value = `${suggested}@innspark.in`;
  }
}

function generateRandomPassword(targetId) {
  const upper = "ABCDEFGHJKLMNPQRSTUVWXYZ";
  const lower = "abcdefghijkmnopqrstuvwxyz";
  const numbers = "23456789";
  const symbols = "@#%*";
  
  let pwd = "";
  pwd += upper.charAt(Math.floor(Math.random() * upper.length));
  pwd += lower.charAt(Math.floor(Math.random() * lower.length));
  pwd += numbers.charAt(Math.floor(Math.random() * numbers.length));
  pwd += symbols.charAt(Math.floor(Math.random() * symbols.length));

  const all = upper + lower + numbers + symbols;
  for (let i = 0; i < 10; i++) {
    pwd += all.charAt(Math.floor(Math.random() * all.length));
  }

  // Shuffle
  pwd = pwd.split("").sort(() => 0.5 - Math.random()).join("");
  pwd = "Inn#" + pwd; // Professional prefix
  document.getElementById(targetId).value = pwd;
}

// Global reference to recently created user for instant testing
let lastCreatedUser = null;

// 7. Create User Handler
async function handleCreateUser(e) {
  e.preventDefault();
  const btn = document.getElementById("add-user-submit-btn");
  btn.disabled = true;
  btn.innerText = "Creating...";

  const payload = {
    givenName: document.getElementById("add-givenName").value.trim(),
    sn: document.getElementById("add-sn").value.trim(),
    uid: document.getElementById("add-uid").value.trim(),
    mail: document.getElementById("add-mail").value.trim(),
    password: document.getElementById("add-password").value.trim(),
    wifi_authorized: document.getElementById("add-wifi-auth").checked
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
      closeModal("add-user-modal");
      loadUsers();
      showCreatedUserModal(payload.uid, payload.password, payload.wifi_authorized);
    } else {
      showToast(data.error || "Failed to create employee", "error");
    }
  } catch (err) {
    showToast("Network error: " + err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerText = "Create Employee";
  }
}

function showCreatedUserModal(uid, password, wifiAuthorized) {
  lastCreatedUser = { uid, password };
  document.getElementById("created-uid-val").innerText = uid;
  document.getElementById("created-pwd-val").innerText = password;
  const badge = document.getElementById("created-wifi-val");
  if (wifiAuthorized) {
    badge.className = "badge-pill authorized";
    badge.innerText = "Active (cn=wifi-users)";
  } else {
    badge.className = "badge-pill revoked";
    badge.innerText = "Revoked";
  }
  openModal("user-created-modal");
}

function testCreatedUserImmediately() {
  closeModal("user-created-modal");
  if (!lastCreatedUser) return;
  openTestAuthModal();
  document.getElementById("test-username").value = lastCreatedUser.uid;
  document.getElementById("test-password").value = lastCreatedUser.password;
  document.getElementById("test-auth-btn").click();
}

// 8. Reset Password Handlers
function openResetPasswordModal(uid, name) {
  document.getElementById("reset-uid").value = uid;
  document.getElementById("reset-user-display").innerText = `${name} (${uid})`;
  document.getElementById("reset-password").value = "WifiPassword2026!";
  openModal("password-modal");
}

async function handleResetPassword(e) {
  e.preventDefault();
  const uid = document.getElementById("reset-uid").value;
  const newPassword = document.getElementById("reset-password").value.trim();
  const btn = document.getElementById("reset-submit-btn");
  btn.disabled = true;
  btn.innerText = "Updating...";

  try {
    const res = await fetch(`/api/users/${encodeURIComponent(uid)}/password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: newPassword })
    });
    const data = await res.json();

    if (data.success) {
      showToast(data.message, "success");
      closeModal("password-modal");
    } else {
      showToast(data.error || "Failed to update password", "error");
    }
  } catch (err) {
    showToast("Network error: " + err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerText = "Update Password";
  }
}

// 9. Toggle Wi-Fi Access
async function toggleWifiAccess(uid, enable) {
  try {
    const res = await fetch(`/api/users/${encodeURIComponent(uid)}/toggle-wifi`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enable })
    });
    const data = await res.json();

    if (data.success) {
      showToast(data.message, "info");
      loadUsers();
    } else {
      showToast(data.error || "Failed to toggle Wi-Fi access", "error");
    }
  } catch (err) {
    showToast("Network error: " + err.message, "error");
  }
}

// 10. Delete User
async function deleteUser(uid) {
  if (!confirm(`Are you sure you want to permanently delete user '${uid}' from OpenLDAP?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/users/${encodeURIComponent(uid)}`, {
      method: "DELETE"
    });
    const data = await res.json();

    if (data.success) {
      showToast(data.message, "info");
      loadUsers();
    } else {
      showToast(data.error || "Failed to delete user", "error");
    }
  } catch (err) {
    showToast("Network error: " + err.message, "error");
  }
}

// 11. Test Auth Tool
function openTestAuthModal() {
  document.getElementById("test-auth-form").reset();
  document.getElementById("test-result-box").style.display = "none";
  openModal("test-auth-modal");
}

function openTestForUser(uid) {
  openTestAuthModal();
  document.getElementById("test-username").value = uid;
  document.getElementById("test-password").value = "WifiPassword2026!";
}

async function handleTestAuth(e) {
  e.preventDefault();
  const username = document.getElementById("test-username").value.trim();
  const password = document.getElementById("test-password").value;
  const btn = document.getElementById("test-auth-btn");
  const resultBox = document.getElementById("test-result-box");

  btn.disabled = true;
  btn.innerText = "Testing Bind...";
  resultBox.style.display = "none";

  try {
    const res = await fetch("/api/test-auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();

    resultBox.style.display = "block";
    if (data.authenticated) {
      resultBox.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
      resultBox.style.border = "1px solid #10b981";
      resultBox.style.color = "#6ee7b7";
      resultBox.innerHTML = `
        <strong>✔ AUTHENTICATION SUCCESS (Access-Accept)</strong><br>
        DN: ${data.user_dn}<br>
        Wi-Fi Group Status: ${data.wifi_authorized ? 'Authorized (Member of cn=wifi-users)' : 'WARNING: Not in Wi-Fi group!'}<br>
        Message: ${data.message}
      `;
    } else {
      resultBox.style.backgroundColor = "rgba(244, 63, 94, 0.15)";
      resultBox.style.border = "1px solid #f43f5e";
      resultBox.style.color = "#fda4af";
      resultBox.innerHTML = `
        <strong>✖ AUTHENTICATION FAILED (Access-Reject)</strong><br>
        DN: ${data.user_dn}<br>
        Message: ${data.message}
      `;
    }
  } catch (err) {
    resultBox.style.display = "block";
    resultBox.style.backgroundColor = "rgba(244, 63, 94, 0.15)";
    resultBox.style.border = "1px solid #f43f5e";
    resultBox.style.color = "#fda4af";
    resultBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.innerText = "Execute Test";
  }
}

// 12. Toast Notification Helper
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast-msg ${type}`;
  
  const icon = type === "success" ? "✔" : type === "error" ? "✖" : "ℹ";
  toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, m => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[m]);
}

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const eyeOpen = btn.querySelector(".eye-open");
  const eyeClosed = btn.querySelector(".eye-closed");
  if (input.type === "password") {
    input.type = "text";
    if (eyeOpen) eyeOpen.style.display = "none";
    if (eyeClosed) eyeClosed.style.display = "block";
  } else {
    input.type = "password";
    if (eyeOpen) eyeOpen.style.display = "block";
    if (eyeClosed) eyeClosed.style.display = "none";
  }
}
