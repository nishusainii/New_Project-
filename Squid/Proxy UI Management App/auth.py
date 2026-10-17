"""
Innspark Squid Proxy Management Portal - Authentication & Security
"""

import os
import json
import time
from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
import config

# In-memory brute-force rate limiter: {ip: [timestamps]}
LOGIN_ATTEMPTS = {}
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes lockout

def init_admin_creds():
    """Initializes admin credentials if they don't already exist."""
    if not os.path.exists(config.ADMIN_CREDS_FILE):
        default_data = {
            "username": config.DEFAULT_ADMIN_USER,
            "password_hash": generate_password_hash(config.DEFAULT_ADMIN_PASS, method="pbkdf2:sha256"),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(config.ADMIN_CREDS_FILE, "w") as f:
            json.dump(default_data, f, indent=2)
        return default_data
    else:
        with open(config.ADMIN_CREDS_FILE, "r") as f:
            return json.load(f)

def is_rate_limited(ip):
    """Checks if the client IP is currently rate-limited."""
    now = time.time()
    attempts = LOGIN_ATTEMPTS.get(ip, [])
    # Filter attempts within the lockout window
    recent = [t for t in attempts if now - t < LOCKOUT_SECONDS]
    LOGIN_ATTEMPTS[ip] = recent
    return len(recent) >= MAX_ATTEMPTS

def record_failed_attempt(ip):
    """Records a failed login attempt for the client IP."""
    now = time.time()
    attempts = LOGIN_ATTEMPTS.get(ip, [])
    attempts.append(now)
    LOGIN_ATTEMPTS[ip] = attempts

def clear_failed_attempts(ip):
    """Clears failed login attempts after a successful login."""
    if ip in LOGIN_ATTEMPTS:
        del LOGIN_ATTEMPTS[ip]

def verify_credentials(username, password, client_ip):
    """Verifies username and password against the admin credentials file."""
    if is_rate_limited(client_ip):
        return False, "Too many failed login attempts. Please wait 5 minutes."

    creds = init_admin_creds()
    if username == creds.get("username") and check_password_hash(creds.get("password_hash"), password):
        clear_failed_attempts(client_ip)
        return True, "Login successful"
    
    record_failed_attempt(client_ip)
    remaining = MAX_ATTEMPTS - len(LOGIN_ATTEMPTS.get(client_ip, []))
    if remaining > 0:
        return False, f"Invalid username or password. ({remaining} attempts remaining)"
    else:
        return False, "Invalid credentials. Account temporarily locked for 5 minutes."

def update_admin_password(old_password, new_password):
    """Updates the admin password after verifying the old password."""
    creds = init_admin_creds()
    if not check_password_hash(creds.get("password_hash"), old_password):
        return False, "Current password is incorrect."
    
    if len(new_password) < 4:
        return False, "New password must be at least 4 characters long."
    
    creds["password_hash"] = generate_password_hash(new_password, method="pbkdf2:sha256")
    creds["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(config.ADMIN_CREDS_FILE, "w") as f:
        json.dump(creds, f, indent=2)
    
    return True, "Password updated successfully."

def login_required(f):
    """Decorator to require an active admin session for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required", "logged_in": False}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated_function
