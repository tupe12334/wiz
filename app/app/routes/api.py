import hmac
import hashlib
import secrets
import time
import traceback

import requests as http_requests
from flask import Blueprint, current_app, jsonify, request

from app.services.audit import analyze_burst_activity
from app.services.auth import (
    get_session_from_request,
    hash_password_via_credential_store,
    require_auth,
)
from app.services.reports import (
    IncompleteModulesError,
    add_report_entry,
    generate_report,
)
from app.utils.db import get_db_connection

bp = Blueprint("api", __name__)

# Shared secret used to sign the "you passed the slider captcha" token.
# Anyone who can reach /api/captcha/verify with a valid session gets a valid
# token back - the slider on the frontend never actually gets checked here.
CAPTCHA_SECRET = "wiznt-captcha-secret-do-not-hardcode-this-in-real-life"


def get_service_account_token():
    """Read the ServiceAccount token from the mounted secret."""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as f:
            return f.read().strip()
    except Exception as e:
        current_app.logger.error(f"Failed to read ServiceAccount token: {e}")
        return None


@bp.route("/health")
def health():
    return jsonify({"status": "ok"})


@bp.route("/")
def index():
    return jsonify(
        {
            "service": "OnBored API",
            "endpoints": [
                {"method": "POST", "path": "/api/login", "description": "Authenticate user"},
                {"method": "GET", "path": "/api/credentials", "description": "Get API credentials (admin only)"},
                {"method": "GET", "path": "/api/report", "description": "Generate analytics report"},
                {"method": "POST", "path": "/api/report/data", "description": "Add report data entry"},
                {"method": "GET", "path": "/health", "description": "Health check"},
            ],
        }
    )


@bp.route("/captcha/verify", methods=["POST"])
@require_auth
def verify_captcha():
    """Generate signed token after captcha completion."""
    session_id = request.current_session.get("session_id")
    timestamp = str(int(time.time()))

    # Create HMAC signature
    message = f"{session_id}:{timestamp}"
    signature = hmac.new(
        CAPTCHA_SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()

    token = f"{timestamp}:{signature}"
    return jsonify({"token": token})


@bp.route("/credentials", methods=["GET"])
@require_auth
def get_credentials():
    if request.current_user.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    # Verify captcha token
    captcha_token = request.headers.get("X-Captcha-Token")
    if not captcha_token:
        return (
            jsonify({"error": "Security verification required. Complete the slider."}),
            403,
        )

    try:
        timestamp, signature = captcha_token.split(":")
        # Check token age (5 min max)
        if int(time.time()) - int(timestamp) > 300:
            return (
                jsonify({"error": "Verification expired. Please complete slider again."}),
                403,
            )

        # Verify signature
        session_id = request.current_session.get("session_id")
        expected_msg = f"{session_id}:{timestamp}"
        expected_sig = hmac.new(
            CAPTCHA_SECRET.encode(), expected_msg.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return jsonify({"error": "Invalid verification token."}), 403
    except Exception:
        return jsonify({"error": "Invalid verification token format."}), 403

    token = get_service_account_token()
    if not token:
        return jsonify({"error": "Service authentication unavailable"}), 500

    cred_store_api = current_app.config["CREDENTIAL_STORE_API"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    try:
        response = http_requests.get(
            f"{cred_store_api}/credentials",
            headers=auth_headers,
            timeout=5,
        )
        if response.status_code == 200:
            return jsonify(response.json())
        return jsonify({"error": "Credential store error"}), response.status_code
    except http_requests.RequestException as e:
        return (
            jsonify({"error": "Cannot reach credential store", "details": str(e)}),
            503,
        )


@bp.route("/admin/create-account", methods=["POST"])
@require_auth
def create_account():
    if request.current_user.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    captcha_token = request.headers.get("X-Captcha-Token")
    if not captcha_token:
        return (
            jsonify({"error": "Security verification required. Complete the slider."}),
            403,
        )
    try:
        timestamp, signature = captcha_token.split(":")
        if int(time.time()) - int(timestamp) > 300:
            return (
                jsonify({"error": "Verification expired. Please complete slider again."}),
                403,
            )
        session_id = request.current_session.get("session_id")
        expected_msg = f"{session_id}:{timestamp}"
        expected_sig = hmac.new(
            CAPTCHA_SECRET.encode(), expected_msg.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return jsonify({"error": "Invalid verification token."}), 403
    except Exception:
        return jsonify({"error": "Invalid verification token format."}), 403

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    username = data.get("username", "").strip()
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    department = data.get("department", "").strip()
    title = data.get("title", "").strip()

    if not username or not full_name or not email:
        return jsonify({"error": "Username, full name, and email are required."}), 400

    # Generate a random password
    password = secrets.token_urlsafe(12)

    token = get_service_account_token()
    if not token:
        return jsonify({"error": "Service authentication unavailable"}), 500

    cred_store_api = current_app.config["CREDENTIAL_STORE_API"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Hash password via credential-store (uses a secret pepper only it knows)
    try:
        hash_resp = http_requests.post(
            f"{cred_store_api}/hash-password",
            json={"password": password},
            headers=auth_headers,
            timeout=5,
        )
        if hash_resp.status_code != 200:
            return jsonify({"error": "Cannot reach credential store"}), 503
        password_hash = hash_resp.json()["hash"]
    except http_requests.RequestException as e:
        return (
            jsonify({"error": "Cannot reach credential store", "details": str(e)}),
            503,
        )

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, auth_type, role, full_name, email, department, title) "
            "VALUES (%s, %s, 'standard', 'user', %s, %s, %s, %s) RETURNING id",
            (username, password_hash, full_name, email, department, title),
        )
        user_id = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO onboarding_modules (user_id, name, description, completed) "
            "SELECT %s, name, description, false FROM onboarding_modules WHERE user_id IS NULL",
            (user_id,),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        error_msg = str(e)
        cur.close()
        conn.close()
        if "duplicate key" in error_msg:
            return jsonify({"error": f"Username '{username}' already exists."}), 409
        return jsonify({"error": "Database error", "details": error_msg}), 500

    cur.close()
    conn.close()

    # Fetch provisioned credentials so the new hire has everything in one place
    cred_store_data = None
    try:
        cred_resp = http_requests.get(
            f"{cred_store_api}/credentials", headers=auth_headers, timeout=5
        )
        if cred_resp.status_code == 200:
            cred_store_data = cred_resp.json()
    except http_requests.RequestException:
        pass

    result = {
        "message": "Employee account created successfully.",
        "account": {
            "user_id": user_id,
            "username": username,
            "password": password,
            "full_name": full_name,
            "email": email,
            "department": department,
            "title": title,
            "role": "user",
        },
    }

    if cred_store_data:
        result["provisioned_credentials"] = cred_store_data.get("credentials", [])

    return jsonify(result), 201


@bp.route("/report", methods=["GET"])
@require_auth
def api_report():
    user_id = request.current_user.get("id")
    try:
        result = generate_report(user_id)
        return jsonify(result)
    except IncompleteModulesError as e:
        return (
            jsonify(
                {
                    "error": "Incomplete onboarding modules",
                    "modules": e.modules,
                }
            ),
            403,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "Report generation failed",
                    "traceback": traceback.format_exc(),
                    "type": type(e).__name__,
                }
            ),
            500,
        )


@bp.route("/report/data", methods=["POST"])
@require_auth
def api_report_data():
    data = request.get_json() or {}
    try:
        category = data["category"]
        value = int(data["value"])
        encoded_char = int(data["encoded_char"])
    except (KeyError, ValueError):
        return jsonify({"error": "category, value, encoded_char are required"}), 400

    sequence = add_report_entry(category, value, encoded_char)
    return jsonify({"message": "Entry added", "sequence": sequence}), 201


@bp.route("/audit/statistics", methods=["GET"])
@require_auth
def api_audit_statistics():
    if request.current_user.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    result = analyze_burst_activity()
    return jsonify(result)
