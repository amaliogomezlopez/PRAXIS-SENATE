"""
Robust JSON parsing utilities for LLM responses
"""
import json
import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def extract_json(text: str) -> Optional[dict | list]:
    """
    Extract JSON from LLM responses that may contain thinking tags, markdown, extra text.

    Strategies:
    1. Direct parse (pure JSON)
    2. Remove thinking blocks, then find array-of-objects (subtasks) or any valid JSON
    3. Extract from ```json blocks
    4. Extract from ``` blocks
    """
    if not text:
        return None

    original = text.strip()

    # Strategy 1: Direct parse (pure JSON)
    try:
        return json.loads(original)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strategy 2: Remove thinking blocks
    text_no_thinking = re.sub(r'<think>', ' ', original)
    text_no_thinking = re.sub(r'</think>', ' ', text_no_thinking)

    # Find potential JSON arrays - look for [ followed by { (array of objects)
    # or just any [...] that is large enough to be a subtask list
    array_of_objs_pattern = r'(\[\s*\{[\s\S]*?\)\s*\])'

    candidates = []

    # Find all [...] positions
    for m in re.finditer(r'\[[\s\S]*?\]', text_no_thinking):
        start, end = m.start(), m.end()
        candidate = m.group()

        # Skip tiny arrays (less than 20 chars) - they're likely just incidental brackets
        if len(candidate) < 20:
            continue

        # Try to parse
        parsed = _try_parse(candidate)
        if parsed is None:
            # Try cleaned version
            cleaned = _clean_json_string(candidate)
            parsed = _try_parse(cleaned)

        if parsed is not None:
            # Score the candidate - prefer arrays of dicts with "description"
            score = 0
            if isinstance(parsed, list):
                score = len(parsed) * 10
                if all(isinstance(item, dict) for item in parsed):
                    score += 50
                    if any('description' in item for item in parsed):
                        score += 100
                elif all(isinstance(item, str) for item in parsed):
                    score -= 5  # Penalize string arrays
            candidates.append((score, -start, parsed))  # negative start = prefer earlier

    if candidates:
        # Return the highest-scoring candidate
        candidates.sort()
        return candidates[-1][2]

    # Strategy 3: Extract from ```json ... ``` blocks
    if "```json" in original:
        try:
            blocks = original.split("```json")
            for block in blocks[1:]:
                json_part = block.split("```")[0].strip()
                parsed = _try_parse(json_part)
                if parsed is not None:
                    return parsed
        except (IndexError, ValueError):
            pass

    # Strategy 4: Extract from ``` ... ``` blocks
    if "```" in original:
        try:
            blocks = original.split("```")
            for i in range(1, len(blocks), 2):
                content = blocks[i].strip()
                if content and (content.startswith('{') or content.startswith('[')):
                    parsed = _try_parse(content)
                    if parsed is not None:
                        return parsed
        except (IndexError, ValueError):
            pass

    logger.warning(f"Failed to extract JSON from text: {original[:200]}...")
    return None


def _try_parse(text: str) -> Optional[Any]:
    """Try to parse text as JSON, return None on failure."""
    if not text or not text.strip():
        return None
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, TypeError):
        return None


def _clean_json_string(text: str) -> str:
    """Clean common JSON formatting issues in LLM responses."""
    # Remove trailing commas
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    # Fix single quotes to double quotes (not escaped)
    text = re.sub(r"(?<!\\)'", '"', text)
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def safe_json_parse(text: str, default: Any = None) -> Any:
    """Safely parse JSON from text, returning default on failure."""
    result = extract_json(text)
    return result if result is not None else default


def extract_and_validate_json(
    text: str,
    schema: dict = None,
    required_fields: list = None
) -> Optional[dict]:
    """Extract JSON and optionally validate against a schema."""
    data = extract_json(text)
    if data is None:
        return None

    if not isinstance(data, dict):
        logger.warning(f"JSON is not a dict: {type(data)}")
        return None

    if required_fields:
        missing = [f for f in required_fields if f not in data]
        if missing:
            logger.warning(f"Missing required fields: {missing}")
            return None

    return data
