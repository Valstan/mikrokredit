import os
import sqlite3
from datetime import date
from typing import Optional

DB_FILENAME = os.environ.get("MIKROKREDIT_DB", "mikrokredit.db")


def get_db_path() -> str:
    return os.path.abspath(DB_FILENAME)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    # Ensure FK constraints work
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
    except Exception:
        pass
    return conn


def _ensure_is_paid_column(conn: sqlite3.Connection) -> None:
    try:
        cols = conn.execute("PRAGMA table_info(loans)").fetchall()
        names = {c[1] for c in cols}
        if "is_paid" not in names:
            conn.execute("ALTER TABLE loans ADD COLUMN is_paid INTEGER NOT NULL DEFAULT 0;")
    except sqlite3.OperationalError:
        # Older SQLite variants might raise if ALTER cannot run; ignore
        pass


def _ensure_org_name_column(conn: sqlite3.Connection) -> None:
    try:
        cols = conn.execute("PRAGMA table_info(loans)").fetchall()
        names = {c[1] for c in cols}
        if "org_name" not in names:
            conn.execute("ALTER TABLE loans ADD COLUMN org_name TEXT;")
    except sqlite3.OperationalError:
        pass


def init_db() -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website TEXT NOT NULL,
                loan_date TEXT NOT NULL,
                amount_borrowed REAL NOT NULL,
                amount_due REAL NOT NULL,
                due_date TEXT NOT NULL,
                risky_org INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                payment_methods TEXT,
                reminded_pre_due INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        _ensure_is_paid_column(conn)
        _ensure_org_name_column(conn)
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_loans_due_date ON loans(due_date);
            """
        )

        # Installments schedule per loan
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS installments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL,
                due_date TEXT NOT NULL,
                amount REAL NOT NULL,
                paid INTEGER NOT NULL DEFAULT 0,
                paid_date TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_installments_loan_due
            ON installments(loan_id, due_date);
            """
        )
        conn.commit()

        # Ensure created_at default for existing rows (if table existed before)
        cur.execute("UPDATE loans SET created_at = ? WHERE created_at IS NULL OR created_at = ''", (date.today().isoformat(),))
        cur.execute("UPDATE installments SET created_at = ? WHERE created_at IS NULL OR created_at = ''", (date.today().isoformat(),))
        conn.commit()
