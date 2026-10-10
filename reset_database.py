"""Reset the database (keeps dataset intact)."""
import sys
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "server", "campus.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "server", "schema.sql")


def reset_database():
    if os.path.exists(DB_PATH):
        size_kb = os.path.getsize(DB_PATH) / 1024
        print(f"Found existing database ({size_kb:.1f} KB)")
        os.remove(DB_PATH)
        print("Deleted.")
    else:
        print("No existing database found.")

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.close()
    print("Database recreated with fresh schema.")
    print("Tables: hostels, rooms, students, cameras, gate_logs, unknown_logs, admin_users")


if __name__ == "__main__":
    confirm = input("Reset database? This will DELETE all logs, students, and cameras. (y/N): ")
    if confirm.lower() == "y":
        reset_database()
    else:
        print("Cancelled.")
