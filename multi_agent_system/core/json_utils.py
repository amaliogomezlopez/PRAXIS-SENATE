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
    Extract JSON from LLM response text that may contain markdown, extra text, or be malformed.

    Tries multiple strategies:
    1. Direct parse (if valid JSON)
    2. Extract from ```json ... ``` blocks
    3. Extract from ``` ... ``` blocks
    4. Extract first { ... } or [ ... ] using regex
    5. Return None if all fail

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON object/array or None if extraction failed
    """
    if not text:
        return None

    text = text.strip()

    # Strategy 1: Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strategy 2: Extract from ```json ... ``` blocks
    try:
        if "```json" in text:
            blocks = text.split("```json")
            for block in blocks[1:]:  # Skip text before first ```
                json_part = block.split("```")[0].strip()
                if json_part:
                    return json.loads(json_part)
    except (json.JSONDecodeError, IndexError, TypeError):
        pass

    # Strategy 3: Extract from ``` ... ``` blocks
    try:
        if "```" in text:
            blocks = text.split("```")
            for i in range(1, len(blocks), 2):  # Odd indices are content
                content = blocks[i].strip()
                if content and (content.startswith('{') or content.startswith('[')):
                    try:
                        return json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        continue
    except (IndexError, TypeError):
        pass

    # Strategy 4: Regex extraction for first JSON object or array
    try:
        # Match {...} or [...]
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if match:
            json_str = match.group(1)
            # Clean up common issues
            json_str = _clean_json_string(json_str)
            return json.loads(json_str)
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    logger.warning(f"Failed to extract JSON from text: {text[:200]}...")
    return None


def _clean_json_string(text: str) -> str:
    """Clean common JSON formatting issues in LLM responses"""
    # Remove trailing commas
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Fix single quotes to double quotes (basic cases only)
    # Be careful not to break strings that contain quotes
    text = re.sub(r"(?<!\\)'", '"', text)

    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    return text


def safe_json_parse(text: str, default: Any = None) -> Any:
    """
    Safely parse JSON from text, returning default on failure.

    Args:
        text: Text to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    result = extract_json(text)
    if result is not None:
        return result
    return default


def extract_and_validate_json(
    text: str,
    schema: dict = None,
    required_fields: list = None
) -> Optional[dict]:
    """
    Extract JSON and optionally validate against a schema.

    Args:
        text: Raw LLM response
        schema: Optional JSON schema to validate against
        required_fields: List of required field names

    Returns:
        Validated JSON dict or None
    """
    data = extract_json(text)
    if data is None:
        return None

    # Basic type check
    if not isinstance(data, dict):
        logger.warning(f"JSON is not a dict: {type(data)}")
        return None

    # Check required fields
    if required_fields:
        missing = [f for f in required_fields if f not in data]
        if missing:
            logger.warning(f"Missing required fields: {missing}")
            return None

    # Schema validation could be added here with jsonschema library
    # if schema:
    #     from jsonschema import validate, ValidationError
    #     try:
    #         validate(instance=data, schema=schema)
    #     except ValidationError as e:
    #         logger.warning(f"Schema validation failed: {e}")
    #         return None

    return data
