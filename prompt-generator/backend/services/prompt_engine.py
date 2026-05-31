"""Prompt generation engine — meta-prompting via Hugging Face LLM."""

from __future__ import annotations

from pathlib import Path

from backend.models.schemas import GenerateResponse
from backend.services.hf_client import get_hf_client
from backend.services.json_utils import parse_json_from_response
from backend.services.quality_scorer import score_prompt

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "prompts" / "templates"

_SYSTEM_PROMPT_BASE = """
You are a senior audio director and prompt engineer with 15+ years of experience directing \
voice talent, composing for picture, and designing sound for broadcast, streaming, and games. \
You have worked with ElevenLabs, Bark, MusicGen, AudioCraft, and professional studio pipelines.

Your task: transform a user's rough description into a HIGHLY SPECIFIC, PRODUCTION-READY \
audio generation prompt that a model or a real voice actor could execute without ambiguity.

DOMAIN KNOWLEDGE YOU MUST APPLY:
- Voiceover / TTS: specify mic proximity (close/mid/distant), breath control (natural/controlled/minimal), \
  room treatment (dry/slight room/reverb), emotional arc across the piece, exact WPM, \
  delivery nuances (rising inflection, falling cadence, punchy consonants, soft sibilants), \
  and any post-processing hints (EQ warmth, gentle compression).
- Music: specify key/mode if relevant, exact BPM, time signature, instrumentation with \
  articulation (e.g. "pizzicato strings", "breathy flute", "distorted Rhodes"), \
  dynamic arc (pp→ff build, constant groove, etc.), mix reference levels, and a concrete \
  artist/soundtrack reference the model can anchor to.
- SFX: specify the physical source material, recording environment (anechoic/room/outdoor), \
  layering strategy (sub-bass thud + mid crack + high transient), stereo width, \
  exact duration with attack/decay/sustain/release shape, and the emotional/narrative \
  function of the sound in context.

QUALITY STANDARDS:
- Be SPECIFIC: "warm, slightly breathy female voice, close-mic'd, minimal room" beats "warm female voice"
- Be TECHNICAL: include numbers (WPM, BPM, dB levels, Hz ranges, ms timings) where they add precision
- Be CONTEXTUAL: anchor the prompt to the real-world use case (broadcast TV, game engine, podcast, etc.)
- Be DIFFERENTIATED: the 2 variants must explore meaningfully different creative directions, \
  not just swap one adjective

Use the following type-specific template as a checklist of dimensions to cover:
{template}

CRITICAL OUTPUT RULES:
- "prompt" MUST be a single plain-text string — no nested JSON, no bullet points, no markdown
- "variants" MUST be an array of exactly 2 plain-text strings, each a genuinely different take
- "explanation" MUST be a plain-text string explaining the key creative and technical choices
- Do NOT use template field names as keys inside the strings

Output ONLY valid JSON, no markdown fences, no extra text:
{{
  "prompt": "<production-ready plain-text prompt>",
  "variants": ["<variant 1 — different creative direction>", "<variant 2 — different creative direction>"],
  "explanation": "<technical and creative rationale>"
}}
"""


def _load_template(audio_type: str) -> str:
    """Load the JSON template for the given audio type.

    Falls back to an empty dict string if the template file is missing.

    Args:
        audio_type: One of tts, music, sfx, voiceover.

    Returns:
        Pretty-printed JSON string of the template.
    """
    path = _TEMPLATES_DIR / f"{audio_type}.json"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "{}"


def _coerce_to_str(value: object) -> str:
    """Coerce a value to a plain string, flattening dicts/lists if the LLM misbehaves.

    Args:
        value: The raw value from the parsed LLM JSON — may be str, dict, or list.

    Returns:
        A human-readable string representation.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Flatten "key: value" pairs separated by ". "
        return ". ".join(f"{v}" for v in value.values() if v)
    if isinstance(value, list):
        return " | ".join(_coerce_to_str(item) for item in value)
    return str(value)


def _parse_json_from_response(text: str) -> dict:
    """Backwards-compatible alias for :func:`parse_json_from_response`."""
    return parse_json_from_response(text)


def generate_prompt(
    description: str,
    audio_type: str,
    tone: str,
    duration: str,
) -> GenerateResponse:
    """Generate a structured audio prompt from a free-text description.

    Args:
        description: User's informal description of the desired audio.
        audio_type: Target audio type (tts, music, sfx, voiceover).
        tone: Desired tone / style (e.g. professional, dramatic, neutral).
        duration: Estimated duration (short, medium, long).

    Returns:
        GenerateResponse with main prompt, two variants, explanation, and quality score.
    """
    client = get_hf_client()
    template_str = _load_template(audio_type)

    system_prompt = _SYSTEM_PROMPT_BASE.format(template=template_str)

    user_msg = (
        f"Audio type: {audio_type}\n"
        f"Tone / style: {tone}\n"
        f"Duration: {duration}\n"
        f"Description: {description}"
    )

    raw = client.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_msg,
        max_new_tokens=1200,
        temperature=0.7,
    )

    data = _parse_json_from_response(raw)

    main_prompt: str = _coerce_to_str(data.get("prompt", ""))
    raw_variants = data.get("variants", ["", ""])
    # Ensure exactly 2 string variants
    if not isinstance(raw_variants, list):
        raw_variants = [raw_variants, ""]
    while len(raw_variants) < 2:
        raw_variants.append("")
    variants: list[str] = [_coerce_to_str(v) for v in raw_variants[:2]]
    explanation: str = _coerce_to_str(data.get("explanation", ""))

    # Score the main prompt for quality feedback
    score_obj = score_prompt(main_prompt, audio_type)

    return GenerateResponse(
        prompt=main_prompt,
        variants=variants,
        explanation=explanation,
        score=score_obj.global_score,
    )
