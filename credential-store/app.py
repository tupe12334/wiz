import hashlib
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# In the real cluster this would be validated against the Kubernetes
# TokenReview API - only a pod's own mounted ServiceAccount token would
# pass. Here we simulate that by sharing one token file across the
# containers that are supposed to be "in-cluster" (app + shell), the
# same way a real ServiceAccount token gets auto-mounted into every pod
# in a namespace.
EXPECTED_TOKEN_FILE = os.environ.get(
    "EXPECTED_TOKEN_FILE", "/var/run/secrets/kubernetes.io/serviceaccount/token"
)
PEPPER = os.environ.get("CREDENTIAL_STORE_PEPPER", "wiznt-onboarding-pepper-2024")


def _read_expected_token():
    try:
        with open(EXPECTED_TOKEN_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def _authorized():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    provided = auth_header[7:]
    expected = _read_expected_token()
    return bool(expected) and provided == expected


@app.route("/")
def index():
    # Deliberately misleading: this message implies a NetworkPolicy is
    # doing the blocking. It isn't - it's this exact 401/200-regardless
    # response. Any pod that can reach this service over the network can
    # hit this root path fine; the real gate is the Bearer token check on
    # the endpoints below.
    return jsonify(
        {
            "note": "This is an internal service. Access restricted by NetworkPolicy.",
            "service": "Credential Store",
            "version": "1.0.0",
        }
    )


@app.route("/hash-password", methods=["POST"])
def hash_password():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    if not password:
        return jsonify({"error": "password required"}), 400

    hashed = hashlib.sha256((password + PEPPER).encode()).hexdigest()
    return jsonify({"hash": hashed})


@app.route("/credentials", methods=["GET"])
def credentials():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 401

    return jsonify(
        {
            "credentials": [
                {
                    "key": "partner_api_token",
                    "name": "DataSync Partners API Token",
                    "value": "FLAG{5_n3tw0rk_p0l1cy_byp4ss3d}",
                },
                {
                    "key": "email_smtp_password",
                    "name": "Wizn't Corporate SMTP Password",
                    "value": "smtp_Wiznt2024!",
                },
                {
                    "key": "backup_service_key",
                    "name": "SecureVault Backup API Key",
                    "value": "bkp_7f3a9c2e1d4b8f6c0a5e9d3b7c1f4a86",
                },
            ],
            "message": "Credentials retrieved successfully.",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
