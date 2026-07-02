from app.utils.db import get_db_connection


def analyze_burst_activity():
    """Fetches audit statistics via the secure database function.
    The function has a 2-second timeout enforced at the database level.
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM analyze_burst_activity()")
        row = cur.fetchone()

        if row:
            status, total_users, total_bursts, top_users, flag = row
            return {
                "status": status,
                "total_users": total_users,
                "total_bursts": total_bursts,
                "top_users": top_users or [],
                "flag": flag,
            }
        return {"status": "error", "message": "No data returned"}
    finally:
        if cur:
            cur.close()
        conn.close()
