"""
Standalone script to (re-)create and seed the database.

Usage
-----
    python -m scripts.init_db

This removes any existing database file and creates a fresh one
with all tables and seed data from the assignment PDF.
"""

import os
import sys

# Ensure the project root is on sys.path so ``app`` can be imported
# when running as ``python -m scripts.init_db`` from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import DB_PATH, get_connection, init_db, seed_db


def main() -> None:
    """Create a fresh database with all seed data."""
    # Remove existing database so we start clean
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"Removed existing database: {DB_PATH}")

    # Ensure the data/ directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    try:
        init_db(conn)
        print("Created database tables.")

        seed_db(conn)

        # Quick verification
        candidates = conn.execute(
            "SELECT COUNT(*) AS cnt FROM candidates"
        ).fetchone()["cnt"]
        jobs = conn.execute(
            "SELECT COUNT(*) AS cnt FROM jobs"
        ).fetchone()["cnt"]
        skills = conn.execute(
            "SELECT COUNT(*) AS cnt FROM skills"
        ).fetchone()["cnt"]

        print(
            f"Seeded {candidates} candidates, {jobs} jobs, "
            f"{skills} unique skills."
        )
        print(f"Database created at: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
