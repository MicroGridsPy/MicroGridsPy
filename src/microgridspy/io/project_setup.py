"""Headless project scaffolding: create a project and its input templates.

This module holds the project-creation logic that used to live only inside the
Streamlit ``Project Setup`` page, so it can be driven programmatically:

    import microgridspy as mgp
    paths = mgp.create_project("my_site", resources=["solar", "wind"])
    # fill paths.inputs_dir/load_demand.csv and resource_availability.csv, then:
    mgp.solve("my_site").results()

``create_project`` writes the input *templates* (headers + placeholder data);
the modeller still supplies the real load demand, resource availability, and
techno-economic parameters before solving.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from microgridspy.io.jsonio import write_json
from microgridspy.io.paths import ProjectPaths
from microgridspy.io.templates import TemplateSettings, write_templates
from microgridspy.io.utils import (
    ensure_project_structure,
    project_exists,
    project_paths,
    sanitize_project_name,
)

_STEADY = "steady_state"
_DYNAMIC = "dynamic"
_REQUIRED_INPUT_FILES = (
    "load_demand.csv",
    "resource_availability.csv",
    "renewables.yaml",
    "battery.yaml",
    "generator.yaml",
)


def build_formulation_payload(
    *,
    project_name: str,
    description: str = "",
    formulation: str = _STEADY,
    system_type: str = "off_grid",
    on_grid: bool = False,
    allow_export: bool = False,
    unit_commitment: bool = False,
    start_year_label: Optional[str] = "typical_year",
    time_horizon_years: Optional[int] = None,
    social_discount_rate: Optional[float] = None,
    capacity_expansion: bool = False,
    investment_steps_years: Optional[Sequence[int]] = None,
    multi_scenario_enabled: bool = False,
    n_scenarios: int = 1,
    scenario_labels: Sequence[str] = ("scenario_1",),
    scenario_weights: Sequence[float] = (1.0,),
    constraints_enforcement: str = "expected",
    min_renewable_penetration: float = 0.0,
    max_lost_load_fraction: float = 0.0,
    lost_load_cost_per_kwh: float = 0.0,
    land_availability_m2: Optional[float] = None,
    emission_cost_per_kgco2e: Optional[float] = 0.0,
    n_sources: int = 1,
    battery_loss_model: str = "constant_efficiency",
    battery_cycle_fade_enabled: bool = False,
    battery_calendar_fade_enabled: bool = False,
    generator_efficiency_model: str = "constant_efficiency",
    csv_delimiter: str = ",",
    csv_decimal: str = ".",
) -> dict:
    """Build the ``formulation.json`` payload for a project.

    This is the single source of truth for the formulation document; both the
    GUI and :func:`create_project` call it so the two stay in lock-step. All
    arguments have GUI-matching defaults, so a bare call yields a valid
    off-grid, steady-state, single-scenario configuration.
    """
    return {
        "project_name": project_name,
        "description": description,
        "module": "generation_planning",
        "created_at": datetime.now().isoformat() + "Z",
        "core_formulation": formulation,
        "system_type": system_type,
        "on_grid": on_grid,
        "grid_allow_export": allow_export,
        "unit_commitment": unit_commitment,
        "start_year_label": start_year_label,
        "time_horizon_years": time_horizon_years,
        "social_discount_rate": social_discount_rate,
        "capacity_expansion": capacity_expansion,
        "investment_steps_years": list(investment_steps_years) if investment_steps_years else None,
        "multi_scenario": {
            "enabled": multi_scenario_enabled,
            "n_scenarios": n_scenarios,
            "scenario_labels": list(scenario_labels),
            "scenario_weights": list(scenario_weights),
        },
        "optimization_constraints": {
            "enforcement": constraints_enforcement,
            "min_renewable_penetration": min_renewable_penetration,
            "max_lost_load_fraction": max_lost_load_fraction,
            "lost_load_cost_per_kwh": lost_load_cost_per_kwh,
            "land_availability_m2": land_availability_m2,
            "emission_cost_per_kgco2e": float(emission_cost_per_kgco2e or 0.0),
        },
        "system_configuration": {
            "n_sources": n_sources,
        },
        "battery_model": {
            "loss_model": str(battery_loss_model or "constant_efficiency"),
            "degradation_model": {
                "cycle_fade_enabled": bool(battery_cycle_fade_enabled),
                "calendar_fade_enabled": bool(battery_calendar_fade_enabled),
            },
        },
        "generator_model": {
            "efficiency_model": str(generator_efficiency_model or "constant_efficiency"),
        },
        "csv_format": {
            "delimiter": csv_delimiter,
            "decimal": csv_decimal,
        },
    }


def _normalize_scenarios(scenarios: "int | Sequence[str]") -> tuple[bool, int, list[str], list[float]]:
    """Turn a scenario count or label list into (enabled, n, labels, weights)."""
    if isinstance(scenarios, int):
        if scenarios <= 1:
            return False, 1, ["scenario_1"], [1.0]
        labels = [f"scenario_{i + 1}" for i in range(scenarios)]
        return True, scenarios, labels, [1.0 / scenarios] * scenarios
    labels = list(scenarios)
    n = len(labels)
    if n <= 1:
        return False, 1, labels or ["scenario_1"], [1.0]
    return True, n, labels, [1.0 / n] * n


def create_project(
    project_name: str,
    *,
    formulation: str = _STEADY,
    system_type: str = "off_grid",
    allow_export: bool = False,
    resources: Sequence[str] = ("Resource_1",),
    conversions: Optional[Sequence[str]] = None,
    scenarios: "int | Sequence[str]" = 1,
    horizon_years: Optional[int] = None,
    capacity_expansion: bool = False,
    investment_steps_years: Optional[Sequence[int]] = None,
    start_year_label: Optional[str] = None,
    battery_label: str = "Battery",
    generator_label: str = "Generator",
    fuel_label: str = "Fuel",
    csv_delimiter: str = ",",
    csv_decimal: str = ".",
    settings: Optional[TemplateSettings] = None,
    overwrite: bool = False,
) -> ProjectPaths:
    """Create a project folder, its ``formulation.json`` and input templates.

    Args:
        project_name: name of the project (sanitized to a filesystem-safe form).
        formulation: ``"steady_state"`` or ``"dynamic"``.
        system_type: ``"off_grid"`` or ``"on_grid"``.
        allow_export: whether grid export is permitted (on-grid only).
        resources: renewable resource labels, e.g. ``["solar", "wind"]``. Their
            count sets the number of renewable sources.
        conversions: conversion-technology labels; defaults to
            ``["Technology_1", ...]`` matching ``resources``.
        scenarios: number of stochastic scenarios, or an explicit list of labels.
            A single scenario disables the multi-scenario machinery.
        horizon_years: planning horizon (dynamic formulation only).
        capacity_expansion: enable staged capacity expansion (dynamic only).
        investment_steps_years: step durations, e.g. ``[5, 5, 5, 5]``.
        start_year_label: header for the first year; defaults to
            ``"typical_year"`` (steady-state) or ``"2026"`` (dynamic).
        battery_label, generator_label, fuel_label: component display names.
        csv_delimiter, csv_decimal: CSV formatting for the templates.
        settings: a fully-built :class:`TemplateSettings` for complete control;
            when given, the individual template arguments above are ignored.
        overwrite: overwrite existing input templates if the project exists.

    Returns:
        ProjectPaths: the resolved paths of the created project.

    Raises:
        FileExistsError: if the project already exists and ``overwrite`` is False.
    """
    name = sanitize_project_name(project_name)
    if not name:
        raise ValueError("project_name must not be empty after sanitization.")
    if project_exists(name) and not overwrite:
        raise FileExistsError(
            f"Project '{name}' already exists. Pass overwrite=True to regenerate its templates."
        )

    is_dynamic = formulation == _DYNAMIC
    resolved_start = start_year_label or ("2026" if is_dynamic else "typical_year")
    multi, n_scen, labels, weights = _normalize_scenarios(scenarios)
    res_labels = list(resources)
    conv_labels = list(conversions) if conversions else [f"Technology_{i + 1}" for i in range(len(res_labels))]

    paths = ensure_project_structure(name)

    payload = build_formulation_payload(
        project_name=name,
        formulation=formulation,
        system_type=system_type,
        on_grid=(system_type == "on_grid"),
        allow_export=allow_export,
        start_year_label=resolved_start,
        time_horizon_years=horizon_years if is_dynamic else None,
        capacity_expansion=capacity_expansion if is_dynamic else False,
        investment_steps_years=investment_steps_years if is_dynamic else None,
        multi_scenario_enabled=multi,
        n_scenarios=n_scen,
        scenario_labels=labels,
        scenario_weights=weights,
        n_sources=len(res_labels),
        csv_delimiter=csv_delimiter,
        csv_decimal=csv_decimal,
    )
    write_json(paths.formulation_json, payload)

    tpl = settings or TemplateSettings(
        formulation=formulation,
        system_type=system_type,
        allow_export=allow_export,
        multi_scenario=multi,
        n_scenarios=n_scen,
        scenario_labels=labels,
        scenario_weights=weights,
        start_year_label=resolved_start,
        horizon_years=horizon_years if is_dynamic else None,
        capacity_expansion=capacity_expansion if is_dynamic else False,
        investment_steps_years=investment_steps_years if is_dynamic else None,
        n_res_sources=len(res_labels),
        resource_labels=res_labels,
        conversion_labels=conv_labels,
        battery_label=battery_label,
        battery_loss_model="constant_efficiency",
        battery_cycle_fade_enabled=False,
        battery_calendar_fade_enabled=False,
        battery_efficiency_curve_csv="",
        battery_cycle_lifetime_to_eol_cycles=6000.0,
        battery_calendar_fade_curve_csv="",
        battery_calendar_time_increment_per_step=1.0,
        battery_end_of_life_soh=0.8,
        generator_label=generator_label,
        generator_efficiency_model="constant_efficiency",
        generator_efficiency_curve_csv="",
        fuel_label=fuel_label,
        csv_delimiter=csv_delimiter,
        csv_decimal=csv_decimal,
    )
    write_templates(paths, tpl, overwrite=overwrite)
    return paths


def validate_project(project_name: str) -> ProjectPaths:
    """Pre-flight check that a project has the inputs needed to solve.

    Verifies the project exists, its ``formulation.json`` is present and valid
    JSON, and the required input files are on disk - so problems surface before
    a long solve rather than midway through model building.

    Args:
        project_name: the project to check.

    Returns:
        ProjectPaths: the project's paths, if valid.

    Raises:
        InputValidationError: with a message describing the first problem found.
    """
    # Imported here to avoid a package-level import cycle with the model layer.
    from microgridspy.typical_year_model.model import InputValidationError

    name = sanitize_project_name(project_name)
    paths = project_paths(name)
    if not paths.root.exists():
        raise InputValidationError(f"Project '{name}' does not exist at {paths.root}.")
    if not paths.formulation_json.exists():
        raise InputValidationError(f"Missing formulation.json for project '{name}'.")
    try:
        json.loads(paths.formulation_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputValidationError(f"Invalid formulation.json for '{name}': {exc}") from exc
    missing = [f for f in _REQUIRED_INPUT_FILES if not (paths.inputs_dir / f).exists()]
    if missing:
        raise InputValidationError(
            f"Project '{name}' is missing required input files: {', '.join(missing)}."
        )
    return paths


def delete_project(project_name: str, *, missing_ok: bool = False) -> None:
    """Delete a project folder and everything in it.

    Args:
        project_name: the project to delete.
        missing_ok: if True, return quietly when the project does not exist;
            otherwise raise ``FileNotFoundError``.

    Raises:
        FileNotFoundError: if the project does not exist and ``missing_ok`` is False.
    """
    name = sanitize_project_name(project_name)
    root = project_paths(name).root
    if not root.exists():
        if missing_ok:
            return
        raise FileNotFoundError(f"Project '{name}' does not exist at {root}.")
    shutil.rmtree(root)


def copy_project(source: str, dest: str, *, overwrite: bool = False) -> ProjectPaths:
    """Copy a project to a new name within the same workspace.

    Args:
        source: the existing project to copy from.
        dest: the new project name.
        overwrite: replace ``dest`` if it already exists.

    Returns:
        ProjectPaths: the paths of the new project.

    Raises:
        FileNotFoundError: if ``source`` does not exist.
        FileExistsError: if ``dest`` exists and ``overwrite`` is False.
    """
    src_name = sanitize_project_name(source)
    dst_name = sanitize_project_name(dest)
    src_root = project_paths(src_name).root
    dst = project_paths(dst_name)
    if not src_root.exists():
        raise FileNotFoundError(f"Source project '{src_name}' does not exist at {src_root}.")
    if dst.root.exists():
        if not overwrite:
            raise FileExistsError(
                f"Project '{dst_name}' already exists. Pass overwrite=True to replace it."
            )
        shutil.rmtree(dst.root)
    shutil.copytree(src_root, dst.root)
    return dst


def rename_project(source: str, dest: str, *, overwrite: bool = False) -> ProjectPaths:
    """Rename a project (copy to the new name, then delete the old one).

    Args:
        source: the existing project name.
        dest: the new project name.
        overwrite: replace ``dest`` if it already exists.

    Returns:
        ProjectPaths: the paths of the renamed project.
    """
    dst = copy_project(source, dest, overwrite=overwrite)
    delete_project(source, missing_ok=True)
    return dst
