"""Router — POST /api/score"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import ScoreRequest, ScoreResponse
from backend.services.hf_client import HFClientError
from backend.services.quality_scorer import score_prompt

router = APIRouter(prefix="/api", tags=["score"])


@router.post(
    "/score",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Score the quality of an audio prompt",
    responses={
        200: {"description": "Scoring completed"},
        400: {"description": "Invalid input"},
        500: {"description": "LLM or internal error"},
    },
)
def score(request: ScoreRequest) -> ScoreResponse:
    """Evaluate a prompt on 5 quality dimensions and return a global score.

    Args:
        request: ScoreRequest payload.

    Returns:
        ScoreResponse with global score, per-dimension scores, and recommendations.
    """
    try:
        return score_prompt(prompt=request.prompt, audio_type=request.type)
    except HFClientError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
