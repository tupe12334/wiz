import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import requests as http_requests
from cryptography.fernet import Fernet
from flask import current_app, jsonify, request

from app.utils.db import get_db_connection

# Encrypted admin password - decryption key loaded from /etc/secrets/encryption-key
ENCRYPTED_ADMIN_PASSWORD = "gAAAAABpdzbFjN4YPqGNea2lBI7KyP9VziGBQhCMBwBuuahyNqv9xfV_718pDDiXjmxHvb71mb1z1drY7Qfpa5gtOo6RN740cVzIsp0SG1Xse4eIJHeg42m-D_Vcv7lxG8mCJDoGqEhQ"


def get_builtin_password():
    """Decrypt the admin password using the mounted encryption key."""
    try:
        with open("/etc/secrets/encryption-key", "r") as f:
            passphrase = f.read().strip()
        key = base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode()).digest())
        fernet = Fernet(key)
        return fernet.decrypt(ENCRYPTED_ADMIN_PASSWORD.encode()).decode()
    except Exception as e:
        current_app.logger.error(f"Failed to decrypt admin password: {e}")
        return None


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password_via_credential_store(password):
    """Hash password using the credential-store's secret pepper."""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as f:
            token = f.read().strip()
        resp = http_requests.post(
            f"{current_app.config['CREDENTIAL_STORE_API']}/hash-password",
            json={"password": password},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("hash")
    except Exception as e:
        current_app.logger.error(f"Credential store hash failed: {e}")
    return None


def get_session_from_request():
    # Check Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        session_id = auth_header[7:]
    else:
        # Fall back to cookie, then URL parameter (cookies blocked in iframes)
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = request.args.get("sid")

    if not session_id:
        return None

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT s.user_id, s.expires_at, u.username, u.role "
        "FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.id = %s",
        (session_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None
    user_id, expires_at, username, role = row
    if expires_at < datetime.now(timezone.utc):
        return None
    return {"id": user_id, "username": username, "role": role, "session_id": session_id}


def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_session_from_request()
        if not user:
            return jsonify({"error": "Login required"}), 401
        request.current_session = {"session_id": user["session_id"]}
        request.current_user = user
        return f(*args, **kwargs)

    return wrapper


def require_auth(f):
    """API variant of require_login - used by JSON endpoints."""
    return require_login(f)


def authenticate_user(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, password_hash, auth_type, role FROM users WHERE username = %s",
        (username,),
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return None, "Invalid credentials"

    user_id, stored_hash, auth_type, role = row

    if auth_type == "builtin":
        builtin_password = get_builtin_password()
        if not builtin_password or password != builtin_password:
            cur.close()
            conn.close()
            return None, "Invalid credentials"
    else:
        hashed = hash_password_via_credential_store(password)
        if not hashed or hashed != stored_hash:
            cur.close()
            conn.close()
            return None, "Invalid credentials"

    session_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=current_app.config["SESSION_DURATION_HOURS"]
    )
    cur.execute(
        "INSERT INTO sessions (id, user_id, expires_at) VALUES (%s, %s, %s)",
        (session_id, user_id, expires_at),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {"session_id": session_id, "role": role}, None
