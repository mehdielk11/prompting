"""Router — POST /api/export"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.database import crud
from backend.models.schemas import ExportRequest

router = APIRouter(prefix="/api", tags=["export"])


def _build_json_export(prompts: list[dict]) -> str:
    """Serialise prompts to the standard JSON export format."""
    payload = {
        "export_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "prompts": [
            {
                "id": p["id"],
                "title": p["title"],
                "content": p["content"],
                "type": p["type"],
                "score": p.get("score"),
                "tags": p.get("tags", []),
                "created_at": p.get("created_at"),
            }
            for p in prompts
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _build_markdown_export(prompts: list[dict]) -> str:
    """Serialise prompts to the standard Markdown export format."""
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    lines: list[str] = [
        "# Bibliothèque de Prompts Audio",
        f"**Exporté le** : {today}",
        "",
    ]
    for p in prompts:
        tags_str = ", ".join(p.get("tags", []))
        score_str = f"{p['score']}/100" if p.get("score") is not None else "N/A"
        lines += [
            "---",
            "",
            f"## {p['title']}",
            f"**Type** : {p['type']} | **Score** : {score_str} | **Tags** : {tags_str}",
            "",
            p["content"],
            "",
        ]
    return "\n".join(lines)


@router.post(
    "/export",
    summary="Export prompts as JSON or Markdown",
    responses={
        200: {"description": "File download"},
        400: {"description": "Invalid request"},
        404: {"description": "One or more prompt IDs not found"},
    },
)
def export_prompts(request: ExportRequest) -> StreamingResponse:
    """Export a selection of prompts as a downloadable file.

    Args:
        request: ExportRequest with list of IDs and desired format.

    Returns:
        StreamingResponse with the file content and appropriate headers.
    """
    prompts: list[dict] = []
    missing: list[int] = []

    for pid in request.ids:
        row = crud.get_prompt(pid)
        if row is None:
            missing.append(pid)
        else:
            prompts.append(row)

    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt IDs not found: {missing}",
        )

    if request.format == "json":
        content = _build_json_export(prompts)
        media_type = "application/json"
        filename = "prompts_export.json"
    else:
        content = _build_markdown_export(prompts)
        media_type = "text/markdown"
        filename = "prompts_export.md"

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
