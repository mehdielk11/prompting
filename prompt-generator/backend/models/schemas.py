"""Pydantic schemas — single source of truth for all API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enums / literals
# ---------------------------------------------------------------------------

AudioType = Literal["tts", "music", "sfx", "voiceover"]
ExportFormat = Literal["json", "markdown"]
OptimizeObjective = Literal["clarity", "precision", "creativity", "technical"]
AudioTone = Literal[
    "professional", "neutral", "dramatic", "warm", "energetic", "calm", "playful",
    "authoritative", "friendly", "serious", "humorous", "inspirational",
]


# ---------------------------------------------------------------------------
# F1 — Generate
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    """Input for prompt generation."""

    description: str = Field(..., min_length=10, description="Free-text description of the desired audio content.")
    type: AudioType = Field(..., description="Target audio type.")
    tone: AudioTone = Field(..., description="Tone / style (e.g. dramatic, neutral, professional).")
    duration: Literal["short", "medium", "long"] = Field(
        ..., description="Estimated duration: short (<30s), medium, long (>2min)."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "description": "Corporate e-learning introduction for a software product",
                "type": "tts",
                "tone": "professional",
                "duration": "short",
            }
        }
    }


class GenerateResponse(BaseModel):
    """Output of prompt generation."""

    prompt: str = Field(..., description="Main optimised prompt.")
    variants: list[str] = Field(..., description="Two alternative variants.")
    explanation: str = Field(..., description="Explanation of structural choices.")
    score: float = Field(..., ge=0, le=100, description="Quality score 0–100.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "Female voice, mid-30s, neutral French accent...",
                "variants": ["Variant A...", "Variant B..."],
                "explanation": "Structured around voice profile, tone, and pace...",
                "score": 82.5,
            }
        }
    }


# ---------------------------------------------------------------------------
# F2 — Optimize
# ---------------------------------------------------------------------------


class OptimizeRequest(BaseModel):
    """Input for prompt optimisation."""

    raw_prompt: str = Field(..., min_length=10, description="Existing prompt to improve.")
    objective: OptimizeObjective = Field(..., description="Optimisation objective.")
    type: AudioType = Field(default="tts", description="Target audio type (used for scoring context).")

    model_config = {
        "json_schema_extra": {
            "example": {
                "raw_prompt": "A calm female voice reading a story.",
                "objective": "precision",
                "type": "tts",
            }
        }
    }


class OptimizeResponse(BaseModel):
    """Output of prompt optimisation."""

    optimized_prompt: str
    changes: list[str] = Field(..., description="Actual diff-derived list of improvements made.")
    score_before: float = Field(..., ge=0, le=100)
    score_after: float = Field(..., ge=0, le=100)
    dimensions_before: DimensionScores | None = Field(default=None, description="Per-dimension scores before optimisation.")
    dimensions_after: DimensionScores | None = Field(default=None, description="Per-dimension scores after optimisation.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "optimized_prompt": "Female voice, late-20s, warm and calm tone...",
                "changes": ["Added voice age range", "Specified pace at 115 wpm"],
                "score_before": 45.0,
                "score_after": 78.0,
                "dimensions_before": {"clarity": 50.0, "specificity": 40.0, "structure": 45.0, "relevance": 50.0, "creativity": 30.0},
                "dimensions_after": {"clarity": 80.0, "specificity": 75.0, "structure": 78.0, "relevance": 80.0, "creativity": 70.0},
            }
        }
    }


# ---------------------------------------------------------------------------
# F3 — Score
# ---------------------------------------------------------------------------


class DimensionScores(BaseModel):
    """Per-dimension quality scores (each 0–100)."""

    clarity: float = Field(..., ge=0, le=100)
    specificity: float = Field(..., ge=0, le=100)
    structure: float = Field(..., ge=0, le=100)
    relevance: float = Field(..., ge=0, le=100)
    creativity: float = Field(..., ge=0, le=100)


class ScoreRequest(BaseModel):
    """Input for quality scoring."""

    prompt: str = Field(..., min_length=5)
    type: AudioType

    model_config = {
        "json_schema_extra": {
            "example": {"prompt": "Female voice, mid-30s, neutral French accent...", "type": "tts"}
        }
    }


class ScoreResponse(BaseModel):
    """Output of quality scoring."""

    global_score: float = Field(..., ge=0, le=100)
    dimension_scores: DimensionScores
    recommendations: list[str] = Field(..., description="Improvement suggestions.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "global_score": 72.0,
                "dimension_scores": {
                    "clarity": 80.0,
                    "specificity": 70.0,
                    "structure": 75.0,
                    "relevance": 65.0,
                    "creativity": 55.0,
                },
                "recommendations": ["Add more technical parameters", "Specify target platform"],
            }
        }
    }


# ---------------------------------------------------------------------------
# F4 — Library (CRUD)
# ---------------------------------------------------------------------------


class PromptCreate(BaseModel):
    """Payload to create a new prompt in the library."""

    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=5)
    type: AudioType
    tags: list[str] = Field(default_factory=list)
    score: float | None = Field(default=None, ge=0, le=100)


class PromptUpdate(BaseModel):
    """Partial update payload — all fields optional."""

    title: str | None = Field(default=None, min_length=2, max_length=200)
    content: str | None = Field(default=None, min_length=5)
    type: AudioType | None = None
    tags: list[str] | None = None
    score: float | None = Field(default=None, ge=0, le=100)


class PromptOut(BaseModel):
    """Full prompt representation returned by the API."""

    id: int
    title: str
    content: str
    type: AudioType
    tags: list[str]
    score: float | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class PromptListResponse(BaseModel):
    """Paginated list of prompts."""

    items: list[PromptOut]
    total: int
    page: int
    page_size: int


class PromptVersionOut(BaseModel):
    """A single historical version of a prompt."""

    id: int
    prompt_id: int
    content: str
    score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# F5 — Export
# ---------------------------------------------------------------------------


class ExportRequest(BaseModel):
    """Request to export one or more prompts."""

    ids: list[int] = Field(..., min_length=1, description="IDs of prompts to export.")
    format: ExportFormat = Field(..., description="Output format: json or markdown.")

    model_config = {
        "json_schema_extra": {
            "example": {"ids": [1, 2, 3], "format": "json"}
        }
    }
