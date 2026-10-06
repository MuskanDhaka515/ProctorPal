"""SQLite storage for bookings and staff escalations."""
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    course       TEXT NOT NULL,
    exam_date    TEXT NOT NULL,
    start_time   TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'booked',
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS escalations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    reason     TEXT NOT NULL,
    contact    TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def db_path() -> str:
    return os.getenv("PROCTORPAL_DB", "data/proctorpal.db")


def get_conn() -> sqlite3.Connection:
    path = db_path()
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
