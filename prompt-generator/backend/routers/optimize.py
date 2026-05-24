"""Router — POST /api/optimize"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import OptimizeRequest, OptimizeResponse
from backend.services.hf_client import HFClientError
from backend.services.quality_scorer import optimize_prompt

router = APIRouter(prefix="/api", tags=["optimize"])


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Optimise an existing audio prompt",
    responses={
        200: {"description": "Prompt optimised successfully"},
        400: {"description": "Invalid input"},
        500: {"description": "LLM or internal error"},
    },
)
def optimize(request: OptimizeRequest) -> OptimizeResponse:
    """Improve an existing prompt according to the specified objective.

    Args:
        request: OptimizeRequest payload.

    Returns:
        OptimizeResponse with improved prompt, list of changes, and before/after scores.
    """
    try:
        return optimize_prompt(
            raw_prompt=request.raw_prompt,
            objective=request.objective,
            audio_type=request.type,
        )
    except HFClientError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
