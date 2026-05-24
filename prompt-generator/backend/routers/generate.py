"""Router — POST /api/generate"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import GenerateRequest, GenerateResponse
from backend.services.hf_client import HFClientError
from backend.services.prompt_engine import generate_prompt

router = APIRouter(prefix="/api", tags=["generate"])


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a professional audio prompt",
    responses={
        200: {"description": "Prompt generated successfully"},
        400: {"description": "Invalid input"},
        500: {"description": "LLM or internal error"},
    },
)
def generate(request: GenerateRequest) -> GenerateResponse:
    """Generate a structured, professional audio prompt from a free-text description.

    Args:
        request: GenerateRequest payload.

    Returns:
        GenerateResponse with main prompt, variants, explanation, and quality score.
    """
    try:
        return generate_prompt(
            description=request.description,
            audio_type=request.type,
            tone=request.tone,
            duration=request.duration,
        )
    except HFClientError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
