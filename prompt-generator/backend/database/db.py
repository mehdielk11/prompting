"""SQLite connection management and schema initialisation."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./database/prompts.db")

_CREATE_PROMPTS = """
CREATE TABLE IF NOT EXISTS prompts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    type        TEXT,
    tags        TEXT    DEFAULT '[]',
    score       REAL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME
);
"""

_CREATE_VERSIONS = """
CREATE TABLE IF NOT EXISTS prompt_versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id   INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    content     TEXT    NOT NULL,
    score       REAL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def _ensure_dir(path: str) -> None:
    """Create parent directories for the DB file if they don't exist."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    _ensure_dir(DB_PATH)
    with get_db() as conn:
        conn.execute(_CREATE_PROMPTS)
        conn.execute(_CREATE_VERSIONS)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.commit()


@contextmanager
def get_db():
    """Yield a SQLite connection with row_factory set to Row.

    Usage::

        with get_db() as conn:
            rows = conn.execute("SELECT * FROM prompts").fetchall()
    """
    _ensure_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()
