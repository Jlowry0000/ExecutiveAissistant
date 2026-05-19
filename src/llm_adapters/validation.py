import json
from typing import Any


class LLMValidationError(ValueError):
    pass


def validate_llm_json_output(content: str, expected_keys: list[str] | None = None) -> dict[str, Any]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise LLMValidationError(f"LLM response is not valid JSON: {e}")

    if not isinstance(data, dict):
        raise LLMValidationError(f"LLM response must be a JSON object, got {type(data).__name__}")

    for key, value in data.items():
        if isinstance(value, str):
            for char in value:
                if ord(char) < 32 and char not in ("\n", "\r", "\t"):
                    raise LLMValidationError(f"Control character (0x{ord(char):02x}) in field '{key}'")

    if expected_keys:
        missing = [k for k in expected_keys if k not in data]
        if missing:
            raise LLMValidationError(f"LLM response missing expected keys: {missing}")

    return data
