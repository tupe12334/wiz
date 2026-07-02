from flask import Blueprint, jsonify, make_response, request

from app.services.auth import authenticate_user, get_session_from_request

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    result, error = authenticate_user(username, password)

    if error:
        return jsonify({"error": error}), 401

    response = make_response(
        jsonify(
            {
                "message": "Login successful",
                "role": result["role"],
                "session_id": result["session_id"],
            }
        )
    )
    # Set cookie server-side (JavaScript cannot override HttpOnly cookies)
    response.set_cookie(
        "session_id",
        result["session_id"],
        max_age=86400,
        path="/",
        samesite="None",
        secure=True,
        httponly=False,  # Allow JS to read if needed
    )
    return response


@bp.route("/logout", methods=["POST"])
def logout():
    response = make_response(jsonify({"message": "Logged out"}))
    response.delete_cookie("session_id")
    return response
