"""Quality scoring service.

Evaluates a prompt on 5 weighted dimensions and returns a global score.
Also handles prompt optimisation (score before/after).
"""

from __future__ import annotations

import json
import re

from backend.models.schemas import DimensionScores, OptimizeResponse, ScoreResponse
from backend.services.hf_client import get_hf_client

# Dimension weights must sum to 1.0
_WEIGHTS: dict[str, float] = {
    "clarity": 0.25,
    "specificity": 0.25,
    "structure": 0.20,
    "relevance": 0.20,
    "creativity": 0.10,
}

_SCORE_SYSTEM_PROMPT = """
You are an expert evaluator of audio generation prompts.
Score the given prompt on each of the following dimensions from 0 to 100:
- clarity: Is the prompt unambiguous and easy to understand?
- specificity: Does it contain useful technical details?
- structure: Does it follow a recognised audio prompt template?
- relevance: Is it well-adapted to the target audio type?
- creativity: Does it include differentiating or original elements?

Also provide up to 3 short recommendations for improvement.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{
  "clarity": <number>,
  "specificity": <number>,
  "structure": <number>,
  "relevance": <number>,
  "creativity": <number>,
  "recommendations": ["...", "..."]
}
"""

_OPTIMIZE_SYSTEM_PROMPT = """
You are an expert prompt engineer specialised in audio generation prompts.
Your task is to improve the given prompt according to the specified objective.

Objectives:
- clarity: Make the prompt unambiguous and easy to parse.
- precision: Add missing technical details and parameters.
- creativity: Introduce original, differentiating elements.
- technical: Align with professional audio production standards.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{
  "optimized_prompt": "...",
  "changes": ["change 1", "change 2", "change 3"]
}
"""


def _parse_json_from_response(text: str) -> dict:
    """Extract the first JSON object from a model response string.

    Args:
        text: Raw model output that may contain surrounding text.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If no valid JSON object is found.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:200]}")
    return json.loads(match.group())


def score_prompt(prompt: str, audio_type: str) -> ScoreResponse:
    """Evaluate a prompt and return a structured quality score.

    Args:
        prompt: The audio generation prompt to evaluate.
        audio_type: Target audio type (tts, music, sfx, voiceover).

    Returns:
        ScoreResponse with global score, per-dimension scores, and recommendations.
    """
    client = get_hf_client()
    user_msg = f"Audio type: {audio_type}\n\nPrompt to evaluate:\n{prompt}"
    raw = client.generate_text(
        system_prompt=_SCORE_SYSTEM_PROMPT,
        user_prompt=user_msg,
        max_new_tokens=400,
        temperature=0.2,
    )

    data = _parse_json_from_response(raw)

    dims = DimensionScores(
        clarity=float(data.get("clarity", 50)),
        specificity=float(data.get("specificity", 50)),
        structure=float(data.get("structure", 50)),
        relevance=float(data.get("relevance", 50)),
        creativity=float(data.get("creativity", 50)),
    )

    global_score = round(
        dims.clarity * _WEIGHTS["clarity"]
        + dims.specificity * _WEIGHTS["specificity"]
        + dims.structure * _WEIGHTS["structure"]
        + dims.relevance * _WEIGHTS["relevance"]
        + dims.creativity * _WEIGHTS["creativity"],
        1,
    )

    recommendations: list[str] = data.get("recommendations", [])

    return ScoreResponse(
        global_score=global_score,
        dimension_scores=dims,
        recommendations=recommendations,
    )


def optimize_prompt(raw_prompt: str, objective: str, audio_type: str = "tts") -> OptimizeResponse:
    """Improve a prompt according to the given objective.

    Args:
        raw_prompt: The original prompt to optimise.
        objective: One of clarity, precision, creativity, technical.
        audio_type: Target audio type used for scoring context (tts, music, sfx, voiceover).

    Returns:
        OptimizeResponse with the improved prompt, list of changes, and before/after scores.
    """
    client = get_hf_client()

    # Score the original prompt with the correct audio type
    score_before_obj = score_prompt(raw_prompt, audio_type)
    score_before = score_before_obj.global_score

    user_msg = f"Objective: {objective}\n\nOriginal prompt:\n{raw_prompt}"
    raw = client.generate_text(
        system_prompt=_OPTIMIZE_SYSTEM_PROMPT,
        user_prompt=user_msg,
        max_new_tokens=600,
        temperature=0.5,
    )

    data = _parse_json_from_response(raw)
    optimized = data.get("optimized_prompt", raw_prompt)
    changes: list[str] = data.get("changes", [])

    score_after_obj = score_prompt(optimized, audio_type)
    score_after = score_after_obj.global_score

    return OptimizeResponse(
        optimized_prompt=optimized,
        changes=changes,
        score_before=score_before,
        score_after=score_after,
    )
