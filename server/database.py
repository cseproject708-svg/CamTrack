import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "campus.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    _seed_defaults(conn)
    conn.commit()
    conn.close()


def _seed_defaults(conn):
    """Insert minimal default rows so the frontend isn't empty on first run."""
    import hashlib
    import secrets

    # Hostels
    if conn.execute("SELECT COUNT(*) AS c FROM hostels").fetchone()["c"] == 0:
        conn.execute("INSERT INTO hostels (name, address) VALUES (?, ?)", ("A-block", "Main Campus"))
        conn.execute("INSERT INTO hostels (name, address) VALUES (?, ?)", ("B-block", "Main Campus"))

    # Rooms (depend on hostels above)
    if conn.execute("SELECT COUNT(*) AS c FROM rooms").fetchone()["c"] == 0:
        hostels = conn.execute("SELECT id FROM hostels ORDER BY id").fetchall()
        for h in hostels:
            for rn in ("101", "102"):
                conn.execute(
                    "INSERT INTO rooms (hostel_id, room_number, capacity) VALUES (?, ?, ?)",
                    (h["id"], rn, 2),
                )

    # Cameras
    if conn.execute("SELECT COUNT(*) AS c FROM cameras").fetchone()["c"] == 0:
        conn.execute(
            "INSERT INTO cameras (name, location, is_active) VALUES (?, ?, 1)",
            ("Camera 1", "Main Gate"),
        )

    # Default admin (admin/admin123) if none exists
    if conn.execute("SELECT COUNT(*) AS c FROM admin_users").fetchone()["c"] == 0:
        salt = secrets.token_hex(16)
        pw_hash = hashlib.sha256(f"{salt}admin123".encode()).hexdigest()
        conn.execute(
            "INSERT INTO admin_users (username, password_hash, full_name) VALUES (?, ?, ?)",
            ("admin", f"{salt}${pw_hash}", "System Administrator"),
        )


def reset_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
