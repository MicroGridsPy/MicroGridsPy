from __future__ import annotations

from pathlib import Path

from microgridspy.io.jsonio import read_yaml_optional


def renewable_labels_from_yaml(path: Path) -> dict[str, list[str]]:
    payload = read_yaml_optional(path)
    renewables = payload.get("renewables", None)
    if not isinstance(renewables, list):
        return {"resources": [], "conversion_technologies": []}

    resources: list[str] = []
    conversions: list[str] = []
    for i, item in enumerate(renewables):
        if not isinstance(item, dict):
            continue
        resources.append(
            str(item.get("resource", "") or f"Resource_{i + 1}").strip() or f"Resource_{i + 1}"
        )
        conversions.append(
            str(item.get("conversion_technology", "") or f"Technology_{i + 1}").strip()
            or f"Technology_{i + 1}"
        )
    return {
        "resources": resources,
        "conversion_technologies": conversions,
    }
