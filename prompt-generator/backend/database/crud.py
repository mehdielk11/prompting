"""CRUD operations — the only layer that touches SQLite directly."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from backend.database.db import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a plain dict and deserialise the tags field."""
    d = dict(row)
    if isinstance(d.get("tags"), str):
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
    return d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def create_prompt(title: str, content: str, type_: str, tags: list[str], score: float | None) -> dict:
    """Insert a new prompt and return the created row as a dict."""
    tags_json = json.dumps(tags)
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO prompts (title, content, type, tags, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, content, type_, tags_json, score, _now()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM prompts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_dict(row)


def get_prompt(prompt_id: int) -> dict | None:
    """Return a single prompt by ID, or None if not found."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_prompts(
    page: int = 1,
    page_size: int = 20,
    type_filter: str | None = None,
    min_score: float | None = None,
) -> tuple[list[dict], int]:
    """Return a paginated list of prompts and the total count.

    Args:
        page: 1-based page number.
        page_size: Number of items per page.
        type_filter: Optional audio type to filter by.
        min_score: Optional minimum score threshold.

    Returns:
        Tuple of (items, total_count).
    """
    conditions: list[str] = []
    params: list = []

    if type_filter:
        conditions.append("type = ?")
        params.append(type_filter)
    if min_score is not None:
        conditions.append("score >= ?")
        params.append(min_score)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size

    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM prompts {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM prompts {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return [_row_to_dict(r) for r in rows], total


def update_prompt(prompt_id: int, **fields) -> dict | None:
    """Update allowed fields on a prompt. Returns updated row or None."""
    allowed = {"title", "content", "type", "tags", "score"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_prompt(prompt_id)

    if "tags" in updates:
        updates["tags"] = json.dumps(updates["tags"])

    updates["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [prompt_id]

    with get_db() as conn:
        conn.execute(f"UPDATE prompts SET {set_clause} WHERE id = ?", values)
        conn.commit()
        row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()

    return _row_to_dict(row) if row else None


def delete_prompt(prompt_id: int) -> bool:
    """Delete a prompt by ID. Returns True if a row was deleted."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()
    return cursor.rowcount > 0


def search_prompts(query: str, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    """Full-text search on title and content using LIKE.

    Args:
        query: Search string.
        page: 1-based page number.
        page_size: Items per page.

    Returns:
        Tuple of (items, total_count).
    """
    pattern = f"%{query}%"
    offset = (page - 1) * page_size

    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM prompts WHERE title LIKE ? OR content LIKE ?",
            (pattern, pattern),
        ).fetchone()[0]
        rows = conn.execute(
            """
            SELECT * FROM prompts
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (pattern, pattern, page_size, offset),
        ).fetchall()

    return [_row_to_dict(r) for r in rows], total


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


def create_version(prompt_id: int, content: str, score: float | None) -> dict:
    """Snapshot the current content of a prompt as a new version."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO prompt_versions (prompt_id, content, score, created_at) VALUES (?, ?, ?, ?)",
            (prompt_id, content, score, _now()),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM prompt_versions WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


def get_versions(prompt_id: int) -> list[dict]:
    """Return all versions for a prompt, newest first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM prompt_versions WHERE prompt_id = ? ORDER BY created_at DESC",
            (prompt_id,),
        ).fetchall()
    return [dict(r) for r in rows]
