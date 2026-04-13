from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from core.io.utils import project_paths


FAMILY_FALLBACK_PREFIX = {
    "renewable": "Renewable technology",
    "battery": "Storage technology",
    "generator": "Backup technology",
    "fuel": "Fuel",
}


def _read_yaml_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_step_key(step: object) -> str:
    text = str(step).strip()
    lower = text.lower().replace(" ", "")
    if lower.startswith("step_"):
        return lower.split("step_", 1)[1]
    if lower.startswith("step"):
        return lower.split("step", 1)[1]
    return text


def _sanitize_label_map(raw: object) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for key, value in raw.items():
        label = str(value or "").strip()
        if label:
            out[_normalize_step_key(key)] = label
    return out


def _sanitize_nested_step_map(raw: object) -> Dict[str, Dict[str, str]]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, str]] = {}
    for step, value in raw.items():
        if not isinstance(value, dict):
            continue
        step_key = _normalize_step_key(step)
        step_map: Dict[str, str] = {}
        for subkey, label in value.items():
            text = str(label or "").strip()
            if text:
                step_map[str(subkey)] = text
        if step_map:
            out[step_key] = step_map
    return out


def load_multi_year_vintage_labels(project_name: str) -> Dict[str, Dict[str, str]]:
    paths = project_paths(project_name)
    renewables_meta = (_read_yaml_optional(paths.inputs_dir / "renewables.yaml").get("meta", {}) or {})
    battery_meta = (_read_yaml_optional(paths.inputs_dir / "battery.yaml").get("meta", {}) or {})
    generator_meta = (_read_yaml_optional(paths.inputs_dir / "generator.yaml").get("meta", {}) or {})

    renewables_labels = (renewables_meta.get("labels", {}) or {})
    battery_labels = (battery_meta.get("labels", {}) or {})
    generator_labels = (generator_meta.get("labels", {}) or {})

    return {
        "renewable": _sanitize_nested_step_map(renewables_labels.get("renewable_vintage_by_step")),
        "battery": _sanitize_label_map(battery_labels.get("battery_vintage_by_step")),
        "generator": _sanitize_label_map(generator_labels.get("generator_vintage_by_step")),
        "fuel": _sanitize_label_map(generator_labels.get("fuel_vintage_by_step")),
    }


def fallback_vintage_label(family: str, step: object) -> str:
    prefix = FAMILY_FALLBACK_PREFIX.get(str(family), "Vintage")
    step_text = _normalize_step_key(step)
    return f"{prefix} {step_text}"


def vintage_label_for_step(
    *,
    labels: Dict[str, Dict[str, str]],
    family: str,
    step: object,
    resource: Optional[object] = None,
) -> str:
    family_map = labels.get(str(family), {}) if isinstance(labels, dict) else {}
    normalized = _normalize_step_key(step)
    if family == "renewable" and isinstance(family_map, dict):
        step_map = family_map.get(normalized, {})
        if isinstance(step_map, dict) and resource is not None:
            resource_key = str(resource)
            if resource_key in step_map:
                return step_map[resource_key]
        if isinstance(step_map, dict) and "__default__" in step_map:
            return step_map["__default__"]
    if normalized in family_map:
        return family_map[normalized]
    if "base" in family_map:
        return family_map["base"]
    return fallback_vintage_label(str(family), normalized)

def vintage_display_for_step(
    *,
    labels: Dict[str, Dict[str, str]],
    family: str,
    step: object,
    resource: Optional[object] = None,
) -> str:
    return f"{vintage_label_for_step(labels=labels, family=family, step=step, resource=resource)} (step {_normalize_step_key(step)})"
