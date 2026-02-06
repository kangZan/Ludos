"""Robust JSON extraction from LLM output."""

import json
import re


def extract_json(text: str) -> dict | None:
    """Extract JSON from LLM output, handling markdown code blocks and common issues.

    Tries multiple strategies:
    1. Direct JSON parse
    2. Extract from ```json ... ``` code blocks
    3. Extract from ``` ... ``` code blocks
    4. Find the first { ... } or [ ... ] block

    Returns:
        Parsed dict/list, or None if no valid JSON found.
    """
    text = text.strip()

    # Strategy 1: Direct parse
    result = _try_parse(text)
    if result is not None:
        return result

    # Strategy 2: ```json ... ``` code block
    match = re.search(r"```json\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        result = _try_parse(match.group(1).strip())
        if result is not None:
            return result

    # Strategy 3: ``` ... ``` code block
    match = re.search(r"```\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        result = _try_parse(match.group(1).strip())
        if result is not None:
            return result

    # Strategy 4: Find first { ... } block (balanced braces)
    result = _extract_balanced(text, "{", "}")
    if result is not None:
        return result

    # Strategy 5: Find first [ ... ] block
    return _extract_balanced(text, "[", "]")


def _try_parse(text: str) -> dict | None:
    """Attempt to parse JSON, handling common LLM formatting errors."""
    # Fix Chinese punctuation that LLMs sometimes produce
    text = text.replace("\uff0c", ",").replace("\u3001", ",")
    text = text.replace("\uff1a", ":").replace("\u201c", '"').replace("\u201d", '"')

    try:
        parsed = json.loads(text)
        if isinstance(parsed, (dict, list)):
            return parsed  # type: ignore[return-value]
    except json.JSONDecodeError:
        pass

    # Try fixing trailing commas
    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, (dict, list)):
            return parsed  # type: ignore[return-value]
    except json.JSONDecodeError:
        pass

    return None


def _extract_balanced(text: str, open_char: str, close_char: str) -> dict | None:
    """Extract a balanced bracket block from text."""
    start = text.find(open_char)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return _try_parse(text[start : i + 1])

    return None
