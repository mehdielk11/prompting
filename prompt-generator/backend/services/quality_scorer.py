"""Quality scoring service.

Evaluates a prompt on 5 weighted dimensions and returns a global score.
Also handles prompt optimisation via a diagnostic-driven feedback loop.
"""

from __future__ import annotations

import difflib
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

Also provide up to 3 short, actionable recommendations for improvement.

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
You are a senior audio director and prompt engineer with 15+ years of professional experience.
You will receive an audio generation prompt that has already been scored on 5 dimensions, \
along with the exact weaknesses and scorer recommendations.
Your task is to rewrite the prompt to specifically address every weakness identified.

OBJECTIVE DEFINITIONS:
- clarity: Eliminate all ambiguity. Every instruction must be unambiguous and directly actionable.
- precision: Add concrete technical parameters (exact WPM, BPM, Hz values, dB levels, ms timings, \
  mic distance, room RT60, compression ratios, etc.).
- creativity: Introduce specific, original, differentiating elements that make this prompt unique \
  and memorable — reference real artists, techniques, or sonic signatures.
- technical: Align fully with professional audio production standards (mic technique, signal chain, \
  post-processing, delivery nuances, mix context).

RULES:
- You MUST produce a prompt that is meaningfully different from and better than the original.
- Address EVERY recommendation listed in the diagnostic — do not skip any.
- For every dimension scoring below 85, make substantial, concrete improvements in that area.
- The rewritten prompt must be a single plain-text string (no JSON keys, no bullet points, no markdown).
- Do NOT simply rephrase — add real substance, real numbers, real specificity.
- The result must be longer and more detailed than the original unless the original is already verbose.

Respond ONLY with valid JSON, no markdown, no extra text:
{
  "optimized_prompt": "<rewritten plain-text prompt with all weaknesses addressed>",
  "changes": ["<specific change 1>", "<specific change 2>", "<specific change 3>"]
}
"""

_OPTIMIZE_RETRY_SUFFIX = """

CRITICAL — PREVIOUS ATTEMPT FAILED: The rewrite you produced scored LOWER than the original.
This is unacceptable. You must do substantially better this time.
- Pick the 2 weakest dimensions and add at least 3 concrete, measurable details to each.
- Add specific numbers (WPM, BPM, Hz, dB, ms) that were missing.
- Do not produce a shorter or vaguer prompt than the original.
- Make it unmistakably better — a professional audio director should immediately see the improvement.
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


def _compute_diff_changes(original: str, optimized: str) -> list[str]:
    """Derive a human-readable list of actual changes by comparing the two prompts.

    Uses token-level and numeric analysis to identify real additions and modifications.

    Args:
        original: The original prompt text.
        optimized: The optimized prompt text.

    Returns:
        List of up to 5 change descriptions derived from the actual text diff.
    """
    orig_words = set(original.lower().split())
    opt_words = set(optimized.lower().split())
    added = opt_words - orig_words
    removed = orig_words - opt_words

    changes: list[str] = []

    # Detect new numeric technical parameters
    orig_nums = set(re.findall(r'\d+(?:\.\d+)?', original))
    opt_nums = set(re.findall(r'\d+(?:\.\d+)?', optimized))
    new_nums = opt_nums - orig_nums
    if new_nums:
        changes.append(f"Added technical parameters: {', '.join(sorted(new_nums)[:6])}")

    # Detect length change
    orig_len = len(original.split())
    opt_len = len(optimized.split())
    if opt_len > orig_len + 5:
        changes.append(f"Expanded by {opt_len - orig_len} words with additional technical detail")
    elif opt_len < orig_len - 5:
        changes.append(f"Condensed by {orig_len - opt_len} words for clarity and directness")

    # Detect meaningful new content (words > 4 chars, alphabetic only)
    meaningful_additions = [w for w in added if len(w) > 4 and w.isalpha()][:5]
    if meaningful_additions:
        changes.append(f"Introduced new elements: {', '.join(meaningful_additions)}")

    # Detect removed vague terms replaced by specifics
    vague_terms = {"warm", "nice", "good", "great", "clear", "smooth", "natural", "subtle",
                   "soft", "gentle", "strong", "rich", "deep", "bright", "crisp"}
    removed_vague = removed & vague_terms
    if removed_vague:
        changes.append(
            f"Replaced vague descriptors ({', '.join(sorted(removed_vague))}) with specific parameters"
        )

    # Fallback: similarity-based summary
    if len(changes) < 2:
        ratio = difflib.SequenceMatcher(None, original, optimized).ratio()
        if ratio < 0.85:
            changes.append(f"Substantially restructured prompt (text similarity: {ratio:.0%})")
        else:
            changes.append("Refined wording and technical precision throughout")

    return changes[:5] if changes else ["Refined prompt based on diagnostic recommendations"]


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
    """Improve a prompt using a diagnostic-driven feedback loop.

    Strategy:
    1. Score the original → get exact dimension weaknesses + scorer recommendations.
    2. Build a targeted brief that tells the LLM precisely what to fix and why.
    3. Generate the optimized prompt.
    4. Score the result. If not better, retry with escalating pressure (max 3 attempts total).
    5. Return the best candidate found. Compute a real text diff for the changes list.

    Args:
        raw_prompt: The original prompt to optimise.
        objective: One of clarity, precision, creativity, technical.
        audio_type: Target audio type used for scoring context.

    Returns:
        OptimizeResponse with the improved prompt, real diff-derived changes, and before/after scores.
    """
    client = get_hf_client()

    # --- Step 1: Score the original and build the diagnostic brief ---
    score_before_obj = score_prompt(raw_prompt, audio_type)
    score_before = score_before_obj.global_score
    dims_before = score_before_obj.dimension_scores
    recommendations = score_before_obj.recommendations

    dim_report = (
        f"  - clarity:      {dims_before.clarity:.0f}/100\n"
        f"  - specificity:  {dims_before.specificity:.0f}/100\n"
        f"  - structure:    {dims_before.structure:.0f}/100\n"
        f"  - relevance:    {dims_before.relevance:.0f}/100\n"
        f"  - creativity:   {dims_before.creativity:.0f}/100"
    )

    weak_dims = [
        name for name, val in [
            ("clarity", dims_before.clarity),
            ("specificity", dims_before.specificity),
            ("structure", dims_before.structure),
            ("relevance", dims_before.relevance),
            ("creativity", dims_before.creativity),
        ]
        if val < 85
    ]

    rec_text = (
        "\n".join(f"  - {r}" for r in recommendations)
        if recommendations
        else "  - Push for more technical specificity and originality."
    )

    user_msg = (
        f"Audio type: {audio_type}\n"
        f"Optimisation objective: {objective}\n"
        f"Current global score: {score_before:.1f}/100\n\n"
        f"Dimension scores:\n{dim_report}\n\n"
        f"Dimensions that MUST be improved: "
        f"{', '.join(weak_dims) if weak_dims else 'all strong — push every dimension toward 100'}\n\n"
        f"Scorer recommendations (address ALL of these):\n{rec_text}\n\n"
        f"Original prompt:\n{raw_prompt}"
    )

    # --- Step 2: Generate with retry loop ---
    best_prompt = raw_prompt
    best_score_obj = score_before_obj
    system_prompt = _OPTIMIZE_SYSTEM_PROMPT

    for attempt in range(3):
        raw = client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_msg,
            max_new_tokens=900,
            temperature=0.65,
        )

        try:
            data = _parse_json_from_response(raw)
        except ValueError:
            system_prompt = _OPTIMIZE_SYSTEM_PROMPT + _OPTIMIZE_RETRY_SUFFIX
            continue

        candidate = data.get("optimized_prompt", "")
        if not isinstance(candidate, str) or len(candidate.strip()) < 20:
            system_prompt = _OPTIMIZE_SYSTEM_PROMPT + _OPTIMIZE_RETRY_SUFFIX
            continue

        candidate = candidate.strip()
        candidate_score_obj = score_prompt(candidate, audio_type)

        if candidate_score_obj.global_score > best_score_obj.global_score:
            best_prompt = candidate
            best_score_obj = candidate_score_obj
            break  # Genuine improvement found — stop

        # Not better — escalate pressure for next attempt
        system_prompt = _OPTIMIZE_SYSTEM_PROMPT + _OPTIMIZE_RETRY_SUFFIX

    # --- Step 3: Real diff-based changes ---
    changes = _compute_diff_changes(raw_prompt, best_prompt)

    return OptimizeResponse(
        optimized_prompt=best_prompt,
        changes=changes,
        score_before=score_before,
        score_after=best_score_obj.global_score,
        dimensions_before=dims_before,
        dimensions_after=best_score_obj.dimension_scores,
    )
