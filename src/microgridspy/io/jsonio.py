"""Reading and writing the JSON and YAML files that make up a project."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from microgridspy.errors import InputValidationError


def ensure_parent_dir(path: Path) -> None:
    """Ensure the parent directory for a file path exists."""
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    """Write a JSON payload to the specified file path."""
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def read_json(path: Path) -> dict[str, Any]:
    """Read a required JSON file, raising `InputValidationError` if it is unusable."""
    if not path.exists():
        raise InputValidationError(f"Missing required file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise InputValidationError(f"Cannot parse JSON: {path}\nerror: {exc}") from exc


def read_yaml(path: Path) -> dict[str, Any]:
    """Read a required YAML file, raising `InputValidationError` if it is unusable."""
    if not path.exists():
        raise InputValidationError(f"Missing required file: {path}")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise InputValidationError(f"Cannot parse YAML: {path}\nerror: {exc}") from exc


def read_yaml_optional(path: Path) -> dict[str, Any]:
    """Read an optional YAML file, returning ``{}`` if it is missing or unreadable.

    Used for files that only carry presentation metadata (display labels), where a
    malformed file should degrade to defaults rather than stop a run.
    """
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}
