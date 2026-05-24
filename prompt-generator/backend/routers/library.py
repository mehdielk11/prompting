"""Router — CRUD + search for /api/library"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from backend.database import crud
from backend.models.schemas import (
    PromptCreate,
    PromptListResponse,
    PromptOut,
    PromptUpdate,
    PromptVersionOut,
)

router = APIRouter(prefix="/api/library", tags=["library"])


def _prompt_or_404(prompt_id: int) -> dict:
    """Fetch a prompt by ID or raise 404."""
    row = crud.get_prompt(prompt_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prompt {prompt_id} not found.")
    return row


# ---------------------------------------------------------------------------
# List & search
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=PromptListResponse,
    summary="List prompts (paginated)",
    responses={200: {"description": "Paginated list of prompts"}},
)
def list_prompts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None, description="Filter by audio type"),
    min_score: float | None = Query(None, ge=0, le=100, description="Minimum quality score"),
) -> PromptListResponse:
    """Return a paginated list of saved prompts with optional filters."""
    items, total = crud.list_prompts(page=page, page_size=page_size, type_filter=type, min_score=min_score)
    return PromptListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/search",
    response_model=PromptListResponse,
    summary="Full-text search across title and content",
)
def search_prompts(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PromptListResponse:
    """Search prompts by title or content using a LIKE query."""
    items, total = crud.search_prompts(query=q, page=page, page_size=page_size)
    return PromptListResponse(items=items, total=total, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Single prompt CRUD
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PromptOut,
    status_code=status.HTTP_201_CREATED,
    summary="Save a new prompt to the library",
)
def create_prompt(payload: PromptCreate) -> PromptOut:
    """Create and persist a new prompt."""
    row = crud.create_prompt(
        title=payload.title,
        content=payload.content,
        type_=payload.type,
        tags=payload.tags,
        score=payload.score,
    )
    return PromptOut(**row)


@router.get(
    "/{prompt_id}",
    response_model=PromptOut,
    summary="Get a single prompt by ID",
)
def get_prompt(prompt_id: int) -> PromptOut:
    """Return a single prompt by its ID."""
    return PromptOut(**_prompt_or_404(prompt_id))


@router.put(
    "/{prompt_id}",
    response_model=PromptOut,
    summary="Update a prompt",
)
def update_prompt(prompt_id: int, payload: PromptUpdate) -> PromptOut:
    """Partially update a prompt. Only provided fields are changed.

    A version snapshot is created automatically before the update.
    """
    existing = _prompt_or_404(prompt_id)
    # Snapshot current state before overwriting
    crud.create_version(
        prompt_id=prompt_id,
        content=existing["content"],
        score=existing.get("score"),
    )
    updated = crud.update_prompt(
        prompt_id,
        title=payload.title,
        content=payload.content,
        type=payload.type,
        tags=payload.tags,
        score=payload.score,
    )
    return PromptOut(**updated)


@router.delete(
    "/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prompt",
)
def delete_prompt(prompt_id: int) -> None:
    """Permanently delete a prompt and all its versions."""
    _prompt_or_404(prompt_id)
    crud.delete_prompt(prompt_id)


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


@router.get(
    "/{prompt_id}/versions",
    response_model=list[PromptVersionOut],
    summary="Get version history for a prompt",
)
def get_versions(prompt_id: int) -> list[PromptVersionOut]:
    """Return all historical versions of a prompt, newest first."""
    _prompt_or_404(prompt_id)
    rows = crud.get_versions(prompt_id)
    return [PromptVersionOut(**r) for r in rows]


# ---------------------------------------------------------------------------
# Duplicate
# ---------------------------------------------------------------------------


@router.post(
    "/{prompt_id}/duplicate",
    response_model=PromptOut,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate a prompt",
)
def duplicate_prompt(prompt_id: int) -> PromptOut:
    """Create a copy of an existing prompt with '(copy)' appended to the title."""
    source = _prompt_or_404(prompt_id)
    row = crud.create_prompt(
        title=f"{source['title']} (copy)",
        content=source["content"],
        type_=source["type"],
        tags=source["tags"],
        score=source.get("score"),
    )
    return PromptOut(**row)
