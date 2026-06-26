"""
database.py
Handles all SQLite database setup and connections for Smart CGPA Planner.
"""

import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cgpa_planner.db")


def get_db_connection():
    """Returns a connection object with row access by column name."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates all required tables if they don't already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table - stores login credentials
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Semesters table - each user can have multiple semesters
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semesters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            semester_number INTEGER NOT NULL,
            sgpa REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, semester_number)
        )
    """)

    # Subjects table - each semester has multiple subjects with credits & grades
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semester_id INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            credits REAL NOT NULL,
            grade_point REAL NOT NULL,
            FOREIGN KEY (semester_id) REFERENCES semesters (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_NAME}")


if __name__ == "__main__":
    init_db()
