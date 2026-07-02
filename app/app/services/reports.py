from app.utils.db import get_db_connection

# TODO: Make sure the keys are correct
XOR_KEYS = [0x42, 0x0A]  # BUG: second key should be 0x1F - fix before shipping


class IncompleteModulesError(Exception):
    """Raised when onboarding modules are not all completed."""

    def __init__(self, modules):
        self.modules = modules
        super().__init__("Incomplete onboarding modules")


def get_onboarding_modules(user_id=None):
    """Fetch onboarding modules for a specific user."""
    conn = get_db_connection()
    cur = conn.cursor()
    if user_id:
        cur.execute(
            "SELECT id, name, description, completed FROM onboarding_modules WHERE user_id = %s ORDER BY id",
            (user_id,),
        )
    else:
        cur.execute(
            "SELECT id, name, description, completed FROM onboarding_modules ORDER BY id"
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "description": r[2], "completed": r[3]}
        for r in rows
    ]


def generate_report(user_id=None):
    # Check onboarding modules first
    modules = get_onboarding_modules(user_id)
    incomplete = [m for m in modules if not m["completed"]]
    if incomplete:
        raise IncompleteModulesError(incomplete)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT sequence, category, value, encoded_char, source FROM report_data ORDER BY sequence"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    total = 0
    by_category = {}
    system_chars = []
    user_chars = []

    for row in rows:
        sequence, category, value, encoded_char, source = row
        total += value

        if category not in by_category:
            by_category[category] = 0
        by_category[category] += value

        key = XOR_KEYS[(sequence - 1) % len(XOR_KEYS)]
        decoded_char = chr(encoded_char ^ key)
        if source == "user":
            user_chars.append(decoded_char)
        else:
            system_chars.append(decoded_char)

    result = {
        "status": "success",
        "modules": modules,
        "total": total,
        "by_category": by_category,
        "record_count": len(rows),
        "checksum": "".join(system_chars),
    }

    if user_chars:
        result["user_checksum"] = "".join(user_chars)

    return result


def add_report_entry(category, value, encoded_char):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(sequence), 0) + 1 FROM report_data")
    next_seq = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO report_data (sequence, category, value, encoded_char, source) "
        "VALUES (%s, %s, %s, %s, 'user')",
        (next_seq, category, value, encoded_char),
    )
    conn.commit()
    cur.close()
    conn.close()
    return next_seq
