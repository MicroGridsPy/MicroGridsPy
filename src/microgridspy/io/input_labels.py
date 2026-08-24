from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml


def _read_yaml_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def renewable_labels_from_yaml(path: Path) -> Dict[str, List[str]]:
    payload = _read_yaml_optional(path)
    renewables = payload.get("renewables", None)
    if not isinstance(renewables, list):
        return {"resources": [], "conversion_technologies": []}

    resources: List[str] = []
    conversions: List[str] = []
    for i, item in enumerate(renewables):
        if not isinstance(item, dict):
            continue
        resources.append(str(item.get("resource", "") or f"Resource_{i+1}").strip() or f"Resource_{i+1}")
        conversions.append(
            str(item.get("conversion_technology", "") or f"Technology_{i+1}").strip() or f"Technology_{i+1}"
        )
    return {
        "resources": resources,
        "conversion_technologies": conversions,
    }


def component_labels_from_yaml(*, battery_path: Path, generator_path: Path) -> Dict[str, str]:
    battery_payload = _read_yaml_optional(battery_path)
    generator_payload = _read_yaml_optional(generator_path)

    battery = battery_payload.get("battery", {}) or {}
    generator = generator_payload.get("generator", {}) or {}
    fuel = generator_payload.get("fuel", {}) or {}

    return {
        "battery": str(battery.get("label", "Battery") or "Battery").strip() or "Battery",
        "generator": str(generator.get("label", "Generator") or "Generator").strip() or "Generator",
        "fuel": str(fuel.get("label", "Fuel") or "Fuel").strip() or "Fuel",
    }
