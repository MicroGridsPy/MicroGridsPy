from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json

from core.io.utils import project_paths
from core.io.input_labels import renewable_labels_from_yaml, component_labels_from_yaml


@dataclass(frozen=True)
class CoreSets:
    project_name: str
    formulation: str
    system_type: str
    on_grid: bool
    allow_export: bool
    multi_scenario: bool
    scenarios: List[str]
    scenario_weights: List[float]
    years: List[str]
    capacity_expansion: bool
    steps: List[str]
    investment_steps_years: Optional[List[int]]
    n_sources: int
    conversion_technologies: List[str]
    resources: List[str]
    battery_label: str
    generator_label: str
    fuel_label: str


@dataclass(frozen=True)
class ManifestBundle:
    payload: Dict[str, Any]
    sets: CoreSets


def _safe_list(x: Any, default: List[Any]) -> List[Any]:
    return x if isinstance(x, list) else default


def _normalize_named_list(values: List[Any], *, n: int, prefix: str) -> List[str]:
    out = [str(v) for v in values[:n]]
    if len(out) < n:
        out += [f"{prefix}_{i+1}" for i in range(len(out), n)]
    return out


def _parse_years(formulation: str, start_year_label: Any, horizon_years: Any) -> List[str]:
    if formulation != "dynamic":
        return ["typical_year"]
    n = max(int(horizon_years or 1), 1)
    try:
        y0 = int(str(start_year_label).strip())
        return [str(y0 + i) for i in range(n)]
    except Exception:
        return [f"year_{i+1}" for i in range(n)]


def _parse_steps(formulation: str, capexp: bool, investment_steps_years: Any) -> List[str]:
    if formulation != "dynamic":
        return ["base"]
    if not capexp:
        return ["base"]
    years = investment_steps_years if isinstance(investment_steps_years, list) else []
    if len(years) == 0:
        return ["step_1"]
    return [f"step_{i+1}" for i in range(len(years))]


def read_manifest(project_name: str) -> ManifestBundle:
    paths = project_paths(project_name)
    payload = json.loads(paths.formulation_json.read_text(encoding="utf-8"))

    formulation = str(payload.get("core_formulation", "steady_state"))
    system_type = str(payload.get("system_type", "off_grid"))
    on_grid = bool(payload.get("on_grid", system_type == "on_grid"))
    allow_export = bool(payload.get("grid_allow_export", False))

    ms = payload.get("multi_scenario", {}) or {}
    multi_scenario = bool(ms.get("enabled", False))
    scenarios = _safe_list(ms.get("scenario_labels"), ["scenario_1"])
    weights = _safe_list(ms.get("scenario_weights"), [1.0])
    if not multi_scenario:
        scenarios = ["scenario_1"]
        weights = [1.0]

    years = _parse_years(formulation, payload.get("start_year_label", "typical_year"), payload.get("time_horizon_years", 1))
    capexp = bool(payload.get("capacity_expansion", False))
    inv_steps = payload.get("investment_steps_years", None)
    inv_steps_list = inv_steps if isinstance(inv_steps, list) else None
    steps = _parse_steps(formulation, capexp, inv_steps)

    syscfg = payload.get("system_configuration", {}) or {}
    n_sources = int(syscfg.get("n_sources", 1) or 1)
    renewable_labels = renewable_labels_from_yaml(paths.inputs_dir / "renewables.yaml")
    component_labels = component_labels_from_yaml(
        battery_path=paths.inputs_dir / "battery.yaml",
        generator_path=paths.inputs_dir / "generator.yaml",
    )
    conversion_technologies = _safe_list(
        renewable_labels.get("conversion_technologies"),
        _safe_list(syscfg.get("conversion_technologies"), [f"Technology_{i+1}" for i in range(n_sources)]),
    )
    resources = _safe_list(
        renewable_labels.get("resources"),
        _safe_list(syscfg.get("resources"), [f"Resource_{i+1}" for i in range(n_sources)]),
    )
    conversion_technologies = _normalize_named_list(conversion_technologies, n=n_sources, prefix="Technology")
    resources = _normalize_named_list(resources, n=n_sources, prefix="Resource")

    sets = CoreSets(
        project_name=project_name,
        formulation=formulation,
        system_type=system_type,
        on_grid=on_grid,
        allow_export=allow_export,
        multi_scenario=multi_scenario,
        scenarios=[str(s) for s in scenarios],
        scenario_weights=[float(w) for w in weights],
        years=[str(y) for y in years],
        capacity_expansion=capexp,
        steps=steps,
        investment_steps_years=inv_steps_list,
        n_sources=n_sources,
        conversion_technologies=conversion_technologies,
        resources=resources,
        battery_label=component_labels.get("battery", "Battery"),
        generator_label=component_labels.get("generator", "Generator"),
        fuel_label=component_labels.get("fuel", "Fuel"),
    )
    return ManifestBundle(payload=payload, sets=sets)

