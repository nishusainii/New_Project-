import base64
import hashlib
import os
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from app.core.config import APP_SECRET

ph = PasswordHasher()

# Derived 32-byte key for Fernet symmetric encryption of private keys
_derived_key = base64.urlsafe_b64encode(hashlib.sha256(APP_SECRET.encode()).digest())
cipher = Fernet(_derived_key)

def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return ph.hash(password)

def verify_password(hash_str: str, password: str) -> bool:
    """Verify a password against an Argon2 hash."""
    try:
        return ph.verify(hash_str, password)
    except (VerifyMismatchError, Exception):
        return False

def is_wireguard_key(key: str) -> bool:
    """Validate if a string is a standard 32-byte Base64-encoded WireGuard key."""
    if not key or not isinstance(key, str):
        return False
    k = key.strip()
    if len(k) != 44:
        return False
    try:
        decoded = base64.b64decode(k.encode("ascii"))
        return len(decoded) == 32
    except Exception:
        return False

def encrypt_key(plain_key: str) -> str:
    """Encrypt sensitive keys before storing in SQLite."""
    if not plain_key:
        return ""
    # Don't double encrypt if already a Fernet token
    if plain_key.startswith("gAAAAA"):
        return plain_key
    try:
        return cipher.encrypt(plain_key.encode()).decode()
    except Exception:
        return plain_key

def decrypt_key(encrypted_key: str) -> str:
    """Decrypt sensitive keys when rendering configurations. Never returns invalid Fernet tokens."""
    if not encrypted_key:
        return ""
    # If already a valid plaintext WireGuard key, return directly
    if is_wireguard_key(encrypted_key):
        return encrypted_key.strip()

    # If it is an encrypted Fernet token, attempt decryption
    if encrypted_key.startswith("gAAAAA"):
        try:
            dec = cipher.decrypt(encrypted_key.encode()).decode()
            if is_wireguard_key(dec):
                return dec.strip()
        except Exception:
            pass

        # Decryption failed (e.g. APP_SECRET changed). Try reading plaintext key from /etc/wireguard/wg0.conf
        try:
            from app.core.config import WG_CONFIG_PATH
            if os.path.exists(WG_CONFIG_PATH):
                with open(WG_CONFIG_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().lower().startswith("privatekey"):
                            candidate = line.split("=", 1)[1].strip()
                            if is_wireguard_key(candidate):
                                return candidate
        except Exception:
            pass

        # Return empty string rather than an invalid token that breaks WireGuard tools
        return ""

    return encrypted_key.strip()

def generate_csrf_token() -> str:
    """Generate a secure cryptographically random CSRF token."""
    return secrets.token_hex(32)

def validate_csrf(session_token: str, form_token: str) -> bool:
    """Constant-time comparison of CSRF tokens."""
    if not session_token or not form_token:
        return False
    return secrets.compare_digest(session_token, form_token)
