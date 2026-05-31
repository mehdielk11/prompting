"""Shared utilities for parsing JSON from LLM responses.

LLMs occasionally produce truncated, prefixed, or suffixed output around the
expected JSON object. The functions in this module extract and, if needed,
repair JSON in a defensive manner so the rest of the pipeline does not crash
on transient model misbehaviour.
"""

from __future__ import annotations

import json


def _repair_truncated_json(text: str) -> str:
    """Best-effort repair of a JSON object truncated mid-stream.

    Walks the input character by character tracking string state, escapes,
    and bracket depth. If the input ends inside a string or with unclosed
    brackets, it appends the minimum sequence of characters to make it
    parseable.

    Args:
        text: A string that starts with ``{`` but may be truncated.

    Returns:
        A best-effort balanced JSON string. The result is not guaranteed to
        parse, but it is far more likely to than the raw truncated input.
    """
    in_string = False
    escape = False
    stack: list[str] = []

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()

    repaired = text
    # Close an unterminated string
    if in_string:
        repaired += '"'
    # Close any open brackets in reverse order
    while stack:
        opener = stack.pop()
        repaired += "}" if opener == "{" else "]"
    return repaired


def parse_json_from_response(text: str) -> dict:
    """Extract the first JSON object from a model response, with repair fallback.

    Strategy:
    1. Find the first ``{`` and extract everything from there.
    2. Try ``json.loads`` directly.
    3. If that fails, try greedy slice up to the last ``}`` (handles trailing prose).
    4. Otherwise attempt to repair a truncated JSON by closing dangling strings
       and brackets, then retry.

    Args:
        text: Raw model output.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If no JSON object can be extracted even after repair.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in model response: {text[:200]}")

    candidate = text[start:]

    # First try: parse as-is
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Second try: greedy to last closing brace (handles trailing prose)
    last_brace = candidate.rfind("}")
    if last_brace != -1:
        try:
            return json.loads(candidate[: last_brace + 1])
        except json.JSONDecodeError:
            pass

    # Third try: best-effort repair of truncated JSON
    repaired = _repair_truncated_json(candidate)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"No valid JSON object found in model response (truncated or malformed): {text[:200]}"
        ) from exc
