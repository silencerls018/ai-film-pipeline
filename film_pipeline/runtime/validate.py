from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def load_schema(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_against_schema(instance: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    messages: list[str] = []
    for err in errors:
        loc = ".".join(str(p) for p in err.path) or "<root>"
        messages.append(f"{loc}: {err.message}")
    return messages
