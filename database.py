"""
database.py — SQLite session logging (stretch goal)
Logs every redaction session: timestamp + entity counts
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "redaction_log.db"


def init_db():
    """Create the sessions table if it doesn't already exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                source    TEXT    NOT NULL,
                counts    TEXT    NOT NULL,
                total     INTEGER NOT NULL
            )
        """)


def log_session(source: str, summary: dict):
    """
    Insert one log record.

    Args:
        source:  'upload' or 'paste'
        summary: dict of entity label → count
    """
    total = sum(summary.values())
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (timestamp, source, counts, total) VALUES (?,?,?,?)",
            (
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                source,
                json.dumps(summary),
                total,
            ),
        )


def get_recent_sessions(limit: int = 10) -> list[dict]:
    """Return the most recent `limit` sessions as a list of dicts."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, timestamp, source, counts, total "
            "FROM sessions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "source": r[2],
            "counts": json.loads(r[3]),
            "total": r[4],
        }
        for r in rows
    ]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn