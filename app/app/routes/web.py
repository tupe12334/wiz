from flask import Blueprint, redirect, render_template, request

from app.services.auth import get_session_from_request
from app.services.reports import IncompleteModulesError, generate_report, get_onboarding_modules
from app.utils.db import get_db_connection

bp = Blueprint("web", __name__)


def current_user_or_none():
    return get_session_from_request()


@bp.route("/bot-detected")
def bot_detected():
    return render_template("bot_detected.html")


@bp.route("/")
def index():
    user = current_user_or_none()
    if user:
        return redirect("/dashboard")
    return redirect("/login")


@bp.route("/login")
def login_page():
    return render_template("login.html")


@bp.route("/logout")
def logout():
    resp = redirect("/login")
    resp.delete_cookie("session_id")
    return resp


@bp.route("/dashboard")
def dashboard():
    user = current_user_or_none()
    if not user:
        return redirect("/login")

    modules = get_onboarding_modules(user["id"])
    checklist_complete = all(m["completed"] for m in modules)

    return render_template(
        "dashboard.html",
        current_user=user,
        active_page="dashboard",
        checklist_complete=checklist_complete,
    )


@bp.route("/reports")
def reports():
    user = current_user_or_none()
    if not user:
        return redirect("/login")

    modules = get_onboarding_modules(user["id"])

    try:
        report_data = generate_report(user["id"])
        return render_template(
            "reports.html",
            current_user=user,
            active_page="reports",
            report=report_data,
            modules=report_data.get("modules", []),
            error=None,
            checklist_complete=True,
        )
    except IncompleteModulesError:
        return render_template(
            "reports.html",
            current_user=user,
            active_page="reports",
            report=None,
            modules=modules,
            error="incomplete",
            checklist_complete=False,
        )
    except Exception as e:
        return render_template(
            "reports.html",
            current_user=user,
            active_page="reports",
            report=None,
            modules=modules,
            error="data_error",
            traceback=f"{type(e).__name__}: {e}",
            checklist_complete=get_onboarding_modules(user["id"]),
        )


@bp.route("/data")
def data():
    user = current_user_or_none()
    if not user:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT sequence, category, value, encoded_char, source FROM report_data
        ORDER BY sequence DESC
        LIMIT 10"""
    )
    rows = cur.fetchall()
    recent_data = [
        {
            "sequence": r[0],
            "category": r[1],
            "value": r[2],
            "encoded_char": r[3],
            "source": r[4],
        }
        for r in rows
    ]
    cur.close()
    conn.close()

    return render_template(
        "data.html",
        current_user=user,
        active_page="data",
        recent_data=recent_data,
    )


@bp.route("/audit")
def audit():
    user = current_user_or_none()
    if not user:
        return redirect("/login")
    if user["role"] != "admin":
        return redirect("/dashboard")

    return render_template(
        "audit.html",
        current_user=user,
        active_page="audit",
    )


@bp.route("/admin")
def admin():
    user = current_user_or_none()
    if not user:
        return redirect("/login")
    if user["role"] != "admin":
        return redirect("/dashboard")

    return render_template(
        "admin.html",
        current_user=user,
        active_page="admin",
    )
