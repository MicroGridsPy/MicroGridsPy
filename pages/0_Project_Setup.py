# generation_planning/pages/project_setup.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple, Literal, Optional

import pandas as pd
import streamlit as st

from core.data_pipeline.utils import normalize_weights
from core.io.utils import (
    ensure_project_structure,
    project_exists,
    project_paths,
    sanitize_project_name,
)
from core.io.jsonio import write_json
from core.io.templates import TemplateSettings, write_templates

# =============================================================================
# Session keys and UI constants
# =============================================================================
K = {
    "formulation": "gp_formulation",
    "is_dynamic": "gp_is_dynamic",
    "system_type": "gp_system_type",
    "on_grid": "gp_on_grid",
    "allow_export": "gp_grid_allow_export",

    # sizing / structure
    "unit_commitment": "gp_unit_commitment",  # bool (discrete units)
    "cap_expansion": "gp_use_capacity_expansion",  # bool

    # dynamic horizon / discounting
    "start_year_label": "gp_start_year_label",  # str
    "horizon_years": "gp_horizon_years",  # int
    "discount_pct": "gp_social_discount_pct",  # float (%)

    # capacity expansion step table (variable step durations)
    "investment_steps": "gp_investment_steps_df",  # pd.DataFrame (step_idx, duration_years)
    "investment_steps_n": "gp_investment_steps_n",  # int

    # uncertainty modelling
    "uncertainty_mode": "gp_uncertainty_mode",  # "single" | "multi"
    "use_multiscenario": "gp_use_multiscenario",  # derived
    "n_scenarios": "gp_n_scenarios",  # int
    "scenario_labels": "gp_scenario_labels",  # list[str]
    "scenario_weights": "gp_scenario_weights",  # list[float]

    # constraints
    "constraints_enforcement": "gp_constraints_enforcement",  # str
    "min_res_penetration_pct": "gp_min_res_penetration_pct",  # float (%)
    "max_lost_load_fraction_pct": "gp_max_lost_load_fraction_pct",  # float (%)
    "lost_load_cost_per_kwh": "gp_lost_load_cost_per_kWh",  # float
    "land_availability_m2": "gp_land_availability_m2",  # float | None
    "land_limit_enabled": "gp_land_limit_enabled",  # bool
    "emission_cost_per_kgco2e": "gp_emission_cost_per_kgco2e",  # float
    "include_carbon_cost": "gp_include_carbon_cost",  # bool

    # renewables naming
    "n_res_sources": "gp_n_res_sources",  # int
    "res_conversion_labels": "gp_res_conversion_labels",  # list[str]
    "res_resource_labels": "gp_res_resource_labels",  # list[str]

    # component labels
    "battery_label": "gp_battery_label",  # str
    "battery_loss_model": "gp_battery_loss_model",  # str
    "battery_efficiency_curve_csv": "gp_battery_efficiency_curve_csv",  # str
    "battery_cycle_fade_enabled": "gp_battery_cycle_fade_enabled",  # bool
    "battery_cycle_lifetime_to_eol_cycles": "gp_battery_cycle_lifetime_to_eol_cycles",  # float
    "battery_calendar_fade_enabled": "gp_battery_calendar_fade_enabled",  # bool
    "battery_calendar_fade_curve_csv": "gp_battery_calendar_fade_curve_csv",  # str
    "battery_calendar_time_increment": "gp_battery_calendar_time_increment",  # float
    "battery_end_of_life_soh": "gp_battery_end_of_life_soh",  # float
    "generator_label": "gp_generator_label",  # str
    "generator_efficiency_model": "gp_generator_efficiency_model",  # str
    "generator_efficiency_curve_csv": "gp_generator_efficiency_curve_csv",  # str
    "fuel_label": "gp_fuel_label",  # str

    # metadata
    "project_name": "gp_project_name",
    "project_desc": "gp_project_description",
    # cross-page
    "active_project": "active_project",
}

FORMULATION_OPTIONS = ["steady_state", "dynamic"]
SYSTEM_OPTIONS = ["off_grid", "on_grid"]
UNCERTAINTY_OPTIONS = ["single", "multi"]
SIZING_OPTIONS = ["continuous", "discrete"]
CONSTRAINT_ENFORCEMENT_OPTIONS = ["expected", "scenario_wise"]

ProjectAction = Literal["create", "load"]


# =============================================================================
# Page-level configuration container (manifest snapshot)
# =============================================================================
@dataclass(frozen=True)
class PageConfig:
    formulation: str
    system_type: str
    on_grid: bool
    allow_export: bool

    # sizing / structure
    discrete_unit_sizing: bool

    # dynamic horizon / discounting
    start_year_label: str | None
    horizon_years: int | None
    social_discount_rate: float | None  # decimal (e.g. 0.05)
    capacity_expansion: bool
    investment_steps: List[int] | None  # list of step durations (years)

    # uncertainty
    multi_scenario: bool
    n_scenarios: int
    scenario_labels: List[str]
    scenario_weights: List[float]

    # constraints
    constraints_enforcement: str
    min_res_penetration: float
    max_lost_load_fraction: float
    lost_load_cost_per_kwh: float
    land_availability_m2: float | None
    emission_cost_per_kgco2e: float | None

    # renewables naming
    n_res_sources: int
    res_conversion_labels: List[str]
    res_resource_labels: List[str]

    # component labels
    battery_label: str
    battery_loss_model: str
    battery_efficiency_curve_csv: str
    battery_cycle_fade_enabled: bool
    battery_cycle_lifetime_to_eol_cycles: float
    battery_calendar_fade_enabled: bool
    battery_calendar_fade_curve_csv: str
    battery_calendar_time_increment_per_step: float
    battery_end_of_life_soh: float
    generator_label: str
    generator_efficiency_model: str
    generator_efficiency_curve_csv: str
    fuel_label: str
    renewable_vintage_labels_by_step: Dict[str, Dict[str, str]]
    battery_vintage_labels_by_step: Dict[str, str]
    generator_vintage_labels_by_step: Dict[str, str]
    fuel_vintage_labels_by_step: Dict[str, str]


def _battery_endogenous_degradation_enabled(cfg: PageConfig) -> bool:
    return (
        str(cfg.formulation or "").strip().lower() == "dynamic"
        and str(cfg.battery_loss_model or "").strip().lower() == "convex_loss_epigraph"
        and (bool(cfg.battery_cycle_fade_enabled) or bool(cfg.battery_calendar_fade_enabled))
    )


def _battery_cycle_fade_active(cfg: PageConfig) -> bool:
    return _battery_endogenous_degradation_enabled(cfg) and bool(cfg.battery_cycle_fade_enabled)


def _battery_calendar_fade_active(cfg: PageConfig) -> bool:
    return _battery_endogenous_degradation_enabled(cfg) and bool(cfg.battery_calendar_fade_enabled)


# =============================================================================
# Defaults
# =============================================================================
def _default_investment_steps_df(n_steps: int = 4, default_duration: int = 5) -> pd.DataFrame:
    return pd.DataFrame(
        {"Step": list(range(1, n_steps + 1)), "Duration [years]": [default_duration] * n_steps}
    )


def init_session_state_defaults() -> None:
    defaults: Dict[str, object] = {
        # core
        K["formulation"]: "steady_state",
        K["is_dynamic"]: False,
        K["system_type"]: "off_grid",
        K["on_grid"]: False,
        K["allow_export"]: False,

        # sizing
        K["unit_commitment"]: False,

        # dynamic horizon / discounting
        K["cap_expansion"]: False,
        K["start_year_label"]: str(datetime.now().year),
        K["horizon_years"]: 20,
        K["discount_pct"]: 5.0,

        # capacity expansion table
        K["investment_steps_n"]: 4,

        # uncertainty
        K["uncertainty_mode"]: "single",
        K["use_multiscenario"]: False,
        K["n_scenarios"]: 2,
        K["scenario_labels"]: ["scenario_1", "scenario_2"],
        K["scenario_weights"]: [0.5, 0.5],

        # constraints
        K["constraints_enforcement"]: "expected",
        K["min_res_penetration_pct"]: 0.0,
        K["max_lost_load_fraction_pct"]: 0.0,
        K["lost_load_cost_per_kwh"]: 0.0,
        K["land_availability_m2"]: None,
        K["land_limit_enabled"]: False,
        K["emission_cost_per_kgco2e"]: 0.0,
        K["include_carbon_cost"]: False,

        # renewables naming
        K["n_res_sources"]: 1,
        K["res_conversion_labels"]: ["Technology_1"],
        K["res_resource_labels"]: ["Resource_1"],

        # component labels
        K["battery_label"]: "Battery",
        K["battery_loss_model"]: "constant_efficiency",
        K["battery_efficiency_curve_csv"]: "battery_efficiency_curve.csv",
        K["battery_cycle_fade_enabled"]: False,
        K["battery_cycle_lifetime_to_eol_cycles"]: 6000.0,
        K["battery_calendar_fade_enabled"]: False,
        K["battery_calendar_fade_curve_csv"]: "battery_calendar_fade_curve.csv",
        K["battery_calendar_time_increment"]: 1.0,
        K["battery_end_of_life_soh"]: 0.8,
        K["generator_label"]: "Generator",
        K["generator_efficiency_model"]: "constant_efficiency",
        K["generator_efficiency_curve_csv"]: "generator_efficiency_curve.csv",
        K["fuel_label"]: "Fuel",

        # metadata
        K["project_name"]: "",
        K["project_desc"]: "",
    }

    for key, value in defaults.items():
        if key not in st.session_state or st.session_state[key] is None:
            st.session_state[key] = value


# =============================================================================
# Persistence
# =============================================================================
def write_formulation_file(*, project_name: str, project_description: str, cfg: PageConfig) -> None:
    degradation_supported = cfg.formulation == "dynamic"
    battery_cycle_fade_active = _battery_cycle_fade_active(cfg) if degradation_supported else False
    battery_calendar_fade_active = _battery_calendar_fade_active(cfg) if degradation_supported else False
    payload = {
        "project_name": project_name,
        "description": project_description,
        "module": "generation_planning",
        "created_at": datetime.now().isoformat() + "Z",
        "core_formulation": cfg.formulation,
        "system_type": cfg.system_type,
        "on_grid": cfg.on_grid,
        "grid_allow_export": cfg.allow_export,
        "unit_commitment": cfg.discrete_unit_sizing,
        "start_year_label": cfg.start_year_label,
        "time_horizon_years": cfg.horizon_years,
        "social_discount_rate": cfg.social_discount_rate,
        "capacity_expansion": cfg.capacity_expansion,
        "investment_steps_years": cfg.investment_steps,
        "multi_scenario": {
            "enabled": cfg.multi_scenario,
            "n_scenarios": cfg.n_scenarios,
            "scenario_labels": cfg.scenario_labels,
            "scenario_weights": cfg.scenario_weights,
        },
        "optimization_constraints": {
            "enforcement": cfg.constraints_enforcement,
            "min_renewable_penetration": cfg.min_res_penetration,
            "max_lost_load_fraction": cfg.max_lost_load_fraction,
            "lost_load_cost_per_kwh": cfg.lost_load_cost_per_kwh,
            "land_availability_m2": cfg.land_availability_m2,
            "emission_cost_per_kgco2e": float(cfg.emission_cost_per_kgco2e or 0.0),
        },
        "system_configuration": {
            "n_sources": cfg.n_res_sources,
        },
        "battery_model": {
            "loss_model": str(cfg.battery_loss_model or "constant_efficiency"),
            "degradation_model": {
                "cycle_fade_enabled": battery_cycle_fade_active,
                "calendar_fade_enabled": battery_calendar_fade_active,
            },
        },
        "generator_model": {
            "efficiency_model": str(cfg.generator_efficiency_model or "constant_efficiency"),
        },
    }

    paths = project_paths(project_name)
    try:
        write_json(paths.formulation_json, payload)
    except Exception as exc:
        st.warning(f"Project initialized, but failed to write `{paths.formulation_json.name}`: {exc}")


def _activate_project(project_name: str):
    """Store the selected project in session state and return its resolved paths."""
    st.session_state[K["active_project"]] = project_name
    paths = project_paths(project_name)
    st.session_state["project_path"] = str(paths.root)
    return paths


def create_or_overwrite_project(*, project_name: str, project_description: str, cfg: PageConfig) -> None:
    """
    Always generates/overwrites templates based on cfg.
    - If project does not exist: create it.
    - If project exists: overwrite templates (WARNING should be shown in UI).
    """
    if not project_name:
        st.error("Please provide a project name before continuing.")
        return

    ensure_project_structure(project_name)
    paths = _activate_project(project_name)

    # Always rewrite formulation.json to match current UI config
    write_formulation_file(project_name=project_name, project_description=project_description, cfg=cfg)

    tpl_settings = TemplateSettings(
        formulation=cfg.formulation,
        system_type=cfg.system_type,
        allow_export=cfg.allow_export,
        multi_scenario=cfg.multi_scenario,
        n_scenarios=cfg.n_scenarios if cfg.multi_scenario else 1,
        scenario_labels=cfg.scenario_labels if cfg.multi_scenario else ["scenario_1"],
        scenario_weights=cfg.scenario_weights if cfg.multi_scenario else [1.0],
        start_year_label=cfg.start_year_label or "typical_year",
        horizon_years=cfg.horizon_years,
        capacity_expansion=cfg.capacity_expansion,
        investment_steps_years=cfg.investment_steps,
        n_res_sources=cfg.n_res_sources,
        conversion_labels=cfg.res_conversion_labels,
        resource_labels=cfg.res_resource_labels,
        battery_label=cfg.battery_label,
        battery_loss_model=cfg.battery_loss_model,
        battery_cycle_fade_enabled=cfg.battery_cycle_fade_enabled,
        battery_calendar_fade_enabled=cfg.battery_calendar_fade_enabled,
        battery_efficiency_curve_csv=cfg.battery_efficiency_curve_csv,
        battery_cycle_lifetime_to_eol_cycles=cfg.battery_cycle_lifetime_to_eol_cycles,
        battery_calendar_fade_curve_csv=cfg.battery_calendar_fade_curve_csv,
        battery_calendar_time_increment_per_step=cfg.battery_calendar_time_increment_per_step,
        battery_end_of_life_soh=cfg.battery_end_of_life_soh,
        generator_label=cfg.generator_label,
        generator_efficiency_model=cfg.generator_efficiency_model,
        generator_efficiency_curve_csv=cfg.generator_efficiency_curve_csv,
        fuel_label=cfg.fuel_label,
        renewable_vintage_labels_by_step=cfg.renewable_vintage_labels_by_step,
        battery_vintage_labels_by_step=cfg.battery_vintage_labels_by_step,
        generator_vintage_labels_by_step=cfg.generator_vintage_labels_by_step,
        fuel_vintage_labels_by_step=cfg.fuel_vintage_labels_by_step,
    )

    # IMPORTANT: in this simplified UX, "create" overwrites if exists
    write_templates(paths, tpl_settings, overwrite=True)

    st.success(f"Project initialized at: {paths.root}")
    st.success("Input templates are ready (and were overwritten if the project already existed).")


def load_project(*, project_name: str) -> None:
    if not project_name:
        st.error("Select a project to load.")
        return
    if not project_exists(project_name):
        st.error("Selected project does not exist.")
        return

    paths = _activate_project(project_name)
    st.success(f"Project loaded: {paths.root}")
    st.info("No files were modified. Proceed to fill/validate/run using the existing project inputs.")


# =============================================================================
# UI helpers
# =============================================================================
def _ensure_res_label_lists_length(n: int) -> None:
    conv = st.session_state.get(K["res_conversion_labels"])
    res = st.session_state.get(K["res_resource_labels"])
    if not isinstance(conv, list):
        conv = []
    if not isinstance(res, list):
        res = []

    if len(conv) < n:
        conv += [f"Technology_{i+1}" for i in range(len(conv), n)]
    if len(res) < n:
        res += [f"Resource_{i+1}" for i in range(len(res), n)]
    if len(conv) > n:
        conv = conv[:n]
    if len(res) > n:
        res = res[:n]

    st.session_state[K["res_conversion_labels"]] = conv
    st.session_state[K["res_resource_labels"]] = res


def _ensure_scenario_labels_length(n: int) -> None:
    labels = st.session_state.get(K["scenario_labels"])
    if not isinstance(labels, list):
        labels = []
    if len(labels) < n:
        labels = labels + [f"scenario_{i+1}" for i in range(len(labels), n)]
    if len(labels) > n:
        labels = labels[:n]
    st.session_state[K["scenario_labels"]] = labels


def _scenario_weight_rounding_tolerance(n_scenarios: int, *, step: float) -> float:
    """Allow small rounding leftovers from UI granularity, then normalize on save."""
    return max(1e-6, 0.5 * float(step) * max(1, int(n_scenarios)))


def _normalize_csv_filename(raw: str, default: str) -> str:
    value = str(raw or "").strip()
    if not value:
        value = default
    if not value.lower().endswith(".csv"):
        value = f"{value}.csv"
    return value


def _coerce_investment_df(df: pd.DataFrame, n_steps: int) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return _default_investment_steps_df(n_steps=n_steps)

    cols = list(df.columns)
    if "Step" not in cols or "Duration [years]" not in cols:
        df = _default_investment_steps_df(n_steps=n_steps)

    df = df[["Step", "Duration [years]"]].copy()
    df["Step"] = range(1, len(df) + 1)

    if len(df) < n_steps:
        last = int(df["Duration [years]"].iloc[-1] if len(df) else 5)
        add = _default_investment_steps_df(n_steps=n_steps - len(df), default_duration=last)
        add["Step"] = range(len(df) + 1, n_steps + 1)
        df = pd.concat([df, add], ignore_index=True)
    elif len(df) > n_steps:
        df = df.iloc[:n_steps].copy()
        df["Step"] = range(1, n_steps + 1)

    return df


def _list_existing_projects() -> List[str]:
    try:
        probe = project_paths("___probe___").root
        projects_dir = probe.parent
        if not projects_dir.exists():
            return []
        names = [p.name for p in projects_dir.iterdir() if p.is_dir()]
        names.sort()
        return names
    except Exception:
        return []


# =============================================================================
# Configuration sections (kept as in your script)
# =============================================================================
def render_formulation_section() -> Tuple[str, bool, str | None, int | None, float | None, bool, List[int] | None]:
    st.subheader("Model formulation")

    formulation = st.radio(
        "Planning mode:",
        options=FORMULATION_OPTIONS,
        index=(0 if st.session_state[K["formulation"]] == "steady_state" else 1),
        format_func=lambda v: ("Typical-year formulation" if v == "steady_state" else "Multi-year formulation"),
        help=(
            "Typical-year: one representative year (faster), steady-state interpretation.\n"
            "Multi-year: explicit intertemporal horizon, discounting, and optional capacity expansion."
        ),
        key="gp_formulation_radio",
    )
    st.session_state[K["formulation"]] = formulation
    is_dynamic = (formulation == "dynamic")
    st.session_state[K["is_dynamic"]] = is_dynamic

    if not is_dynamic:
        st.info("Typical-year formulation enabled. A single representative year is used for sizing and operation.")
        st.session_state[K["cap_expansion"]] = False
        return formulation, False, "typical_year", None, None, False, None

    st.info(
        "Multi-year formulation enabled. Configure the planning horizon and the discount rate "
        "used to compute discounted costs over time."
    )

    st.markdown("**Time horizon & discounting**")
    col1, col2 = st.columns(2)
    with col1:
        start_year_default = st.session_state.get(K["start_year_label"], str(datetime.now().year))
        try:
            start_year_default_int = int(str(start_year_default).strip())
        except Exception:
            start_year_default_int = int(datetime.now().year)
        start_year = int(
            st.number_input(
            "Project start year",
            min_value=1,
            step=1,
            value=start_year_default_int,
            help=(
                "First modeled calendar year. Multi-year projects currently require integer year labels; "
                "this value is used directly in the year coordinate and in generated time-series headers."
            ),
            key="gp_start_year_label_input",
            )
        )
        st.session_state[K["start_year_label"]] = str(start_year)

    with col2:
        horizon_years = int(
            st.number_input(
                "Project time horizon [years]",
                min_value=1,
                step=1,
                value=int(st.session_state[K["horizon_years"]]),
                help="Length of the intertemporal planning horizon used for discounting and (optionally) capacity expansion.",
                key="gp_horizon_years_input",
            )
        )
        st.session_state[K["horizon_years"]] = horizon_years

    discount_pct = float(
        st.number_input(
            "Social discount rate [%]",
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            format="%.2f",
            value=float(st.session_state[K["discount_pct"]]),
            help="Used to discount future costs in the objective (e.g., NPC).",
            key="gp_discount_pct_input",
        )
    )
    st.session_state[K["discount_pct"]] = discount_pct
    discount_rate_dec = discount_pct / 100.0

    cap_expansion = st.checkbox(
        "Allow capacity expansion over time",
        value=bool(st.session_state[K["cap_expansion"]]),
        help="If enabled, the model can invest at multiple steps. This increases model size and solve time.",
        key="gp_cap_expansion_checkbox",
    )
    st.session_state[K["cap_expansion"]] = bool(cap_expansion)

    if not cap_expansion:
        return formulation, True, str(start_year), horizon_years, discount_rate_dec, False, None

    st.info(
        "Shared-technology capacity expansion is used: future expansion can add more capacity over time, but the "
        "technology family remains the same and technical parameters stay shared across investment steps."
    )

    st.markdown("**Investment steps**")
    st.caption(
        "Define the duration of each investment step. Steps do not need to be equal. "
        "The model will use these steps for investment timing and discounting."
    )

    n_steps = int(
        st.number_input(
            "Number of investment steps",
            min_value=1,
            max_value=50,
            step=1,
            value=int(st.session_state.get(K["investment_steps_n"], 4)),
            help="More steps increase flexibility but also increase problem size.",
            key="gp_investment_steps_n_input",
        )
    )
    st.session_state[K["investment_steps_n"]] = n_steps

    df_prev = st.session_state.get(K["investment_steps"])
    df = _coerce_investment_df(df_prev, n_steps=n_steps)

    edited = st.data_editor(
        df,
        hide_index=True,
        disabled=["Step"],
        column_config={
            "Duration [years]": st.column_config.NumberColumn(
                "Duration [years]",
                min_value=1,
                step=1,
                help="Length of each investment step (years).",
            )
        },
        key="gp_investment_steps_editor",
    )

    edited["Duration [years]"] = edited["Duration [years]"].fillna(1).astype(int).clip(lower=1)
    edited["Step"] = range(1, len(edited) + 1)
    st.session_state[K["investment_steps"]] = edited

    step_years_list = edited["Duration [years]"].astype(int).tolist()
    total_years = int(sum(step_years_list))

    if total_years != horizon_years:
        st.warning(
            f"The sum of investment step durations must match the project horizon.\n\n"
            f"- Horizon: **{horizon_years}** years\n"
            f"- Sum of step durations: **{total_years}** years\n\n"
            "Adjust the table so that the total matches the horizon."
        )
        st.stop()

    st.caption(f"Total duration: **{total_years}** years across **{n_steps}** steps.")
    return formulation, True, str(start_year), horizon_years, discount_rate_dec, True, step_years_list


def render_externalities_section() -> Optional[float]:
    include_carbon_cost = st.checkbox(
        "Include carbon emission cost within the objective function",
        value=bool(st.session_state.get(K["include_carbon_cost"], False)),
        help=(
            "If enabled, the cost of carbon emissions (per kg CO₂e) will be included "
            "in the objective function when computing discounted costs over time."
        ),
        key="gp_include_carbon_checkbox",
    )
    st.session_state[K["include_carbon_cost"]] = bool(include_carbon_cost)
    if include_carbon_cost:
        carbon_cost_per_kgco2e = float(
            st.number_input(
                "Carbon emission cost (per kgCO₂e)",
                min_value=0.0,
                step=0.01,
                value=float(st.session_state.get(K["emission_cost_per_kgco2e"], 0.0)),
                key="gp_carbon_cost_input",
            )
        )
        st.session_state[K["emission_cost_per_kgco2e"]] = carbon_cost_per_kgco2e
        st.info("Carbon emission cost will be included in the objective function and affect sizing decisions.")
        return carbon_cost_per_kgco2e

    st.session_state[K["emission_cost_per_kgco2e"]] = 0.0
    return None


def render_uncertainty_section() -> Tuple[bool, int, List[str], List[float]]:
    st.subheader("Uncertainty modelling")

    mode = st.radio(
        "Modelling uncertainties:",
        options=UNCERTAINTY_OPTIONS,
        index=0 if st.session_state[K["uncertainty_mode"]] == "single" else 1,
        format_func=lambda v: (
            "Single scenario (deterministic time series)"
            if v == "single"
            else "Multi-scenarios (expected cost across scenarios)"
        ),
        help=(
            "Single scenario uses one set of time series.\n"
            "Multi-scenarios replicates operation per scenario and minimizes expected total cost."
        ),
        key="gp_uncertainty_mode_radio",
    )
    st.session_state[K["uncertainty_mode"]] = mode

    multi = (mode == "multi")
    st.session_state[K["use_multiscenario"]] = multi

    if not multi:
        st.info("Single scenario selected. Templates will include scenario_1 with weight 1.0.")
        st.session_state[K["n_scenarios"]] = 1
        st.session_state[K["scenario_weights"]] = [1.0]
        st.session_state[K["scenario_labels"]] = ["scenario_1"]
        return False, 1, ["scenario_1"], [1.0]

    st.info("Multi-scenarios selected. Define each scenario label and weight (weights must sum to 1.0).")

    prev_n_scen = int(st.session_state.get(K["n_scenarios"], 2))
    n_scen = int(
        st.number_input(
            "Number of scenarios",
            min_value=2,
            max_value=24,
            step=1,
            value=max(2, int(st.session_state.get(K["n_scenarios"], 2))),
            help="Operational variables and time series inputs will be replicated per scenario.",
            key="gp_n_scenarios_input",
        )
    )
    st.session_state[K["n_scenarios"]] = n_scen

    _ensure_scenario_labels_length(n_scen)

    current_w = st.session_state.get(K["scenario_weights"])
    if (not isinstance(current_w, list)) or (len(current_w) != n_scen) or (prev_n_scen != n_scen):
        current_w = normalize_weights([], n_scen)

    labels = st.session_state[K["scenario_labels"]]
    weight_step = 0.001

    st.markdown("**Scenarios** (labels + weights; weights must sum to 1.0)")

    tmp_labels: List[str] = []
    tmp_weights: List[float] = []

    for i in range(n_scen):
        c1, c2 = st.columns([2, 1])
        with c1:
            lab = st.text_input(
                f"Scenario {i+1} label",
                value=str(labels[i]),
                help="Used for file naming, plots and results tables.",
                key=f"gp_scen_label_{i}",
            )
        with c2:
            w = st.number_input(
                "Weight",
                min_value=0.0,
                max_value=1.0,
                value=float(current_w[i]),
                step=weight_step,
                format="%.3f",
                key=f"gp_scen_weight_{i}",
                help="Scenario probability (must sum to 1.0 across all scenarios).",
            )

        lab = lab.strip() if lab.strip() else f"scenario_{i+1}"
        tmp_labels.append(lab)
        tmp_weights.append(float(w))

    total_w = sum(tmp_weights)
    rounding_tol = _scenario_weight_rounding_tolerance(n_scen, step=weight_step)
    if abs(total_w - 1.0) > rounding_tol:
        st.warning(f"Scenario weights must sum to 1.0 (current sum = {total_w:.3f}).")
        st.stop()

    normalized_weights = normalize_weights(tmp_weights, n_scen)
    normalized_total = sum(normalized_weights)

    duplicate_labels = sorted({label for label in tmp_labels if tmp_labels.count(label) > 1})
    if duplicate_labels:
        st.warning(
            "Scenario labels must be unique. Duplicate labels found: "
            + ", ".join(duplicate_labels)
        )
        st.stop()

    st.session_state[K["scenario_labels"]] = tmp_labels
    st.session_state[K["scenario_weights"]] = normalized_weights
    if abs(total_w - 1.0) > 1e-6:
        st.caption(
            f"Entered weight sum: {total_w:.3f}. Saved weights are normalized to sum exactly to {normalized_total:.3f}."
        )
    else:
        st.caption(f"Sum of weights: {normalized_total:.3f}")

    return True, n_scen, tmp_labels, normalized_weights


def render_system_section() -> Tuple[
    str,
    bool,
    bool,
    bool,
    int,
    List[str],
    List[str],
    str,
    str,
    str,
    bool,
    float,
    bool,
    str,
    float,
    float,
    str,
    str,
    str,
    str,
]:
    st.subheader("System configuration")

    system_type = st.radio(
        "System type:",
        options=SYSTEM_OPTIONS,
        index=(0 if st.session_state[K["system_type"]] == "off_grid" else 1),
        format_func=lambda v: "Off-grid (isolated)" if v == "off_grid" else "On-grid (weakly-connected)",
        help=(
            "Off-grid: demand must be met entirely with local resources.\n"
            "On-grid: grid imports (and optional exports) can be used subject to constraints/outages."
        ),
        key="gp_system_type_radio",
    )
    st.session_state[K["system_type"]] = system_type
    on_grid = (system_type == "on_grid")
    st.session_state[K["on_grid"]] = on_grid

    allow_export = False
    if on_grid:
        allow_export = st.checkbox(
            "Allow export to grid",
            value=bool(st.session_state[K["allow_export"]]),
            help="If enabled, surplus electricity may be exported to the grid (revenue may apply).",
            key="gp_allow_export_checkbox",
        )
        st.session_state[K["allow_export"]] = bool(allow_export)
    else:
        st.session_state[K["allow_export"]] = False

    sizing_mode = st.radio(
        "Sizing approach:",
        options=SIZING_OPTIONS,
        index=1 if bool(st.session_state[K["unit_commitment"]]) else 0,
        format_func=lambda v: (
            "Continuous sizing"
            if v == "continuous"
            else "Discrete unit sizing by nominal capacity"
        ),
        help=(
            "Continuous sizing treats capacity as a continuous decision variable.\n"
            "Discrete units sizes capacity in integer multiples of a nominal unit."
        ),
        key="gp_sizing_mode_radio",
    )
    discrete_sizing = (sizing_mode == "discrete")
    st.session_state[K["unit_commitment"]] = discrete_sizing

    st.markdown("**Renewable sources**")
    st.caption("Define the renewable source/resource names and the associated conversion technology labels.")

    n_res = int(
        st.number_input(
            "Number of renewable sources",
            min_value=1,
            max_value=20,
            step=1,
            value=int(st.session_state.get(K["n_res_sources"], 1)),
            key="gp_n_res_sources_input",
        )
    )
    st.session_state[K["n_res_sources"]] = n_res
    _ensure_res_label_lists_length(n_res)
    current_conv = list(st.session_state.get(K["res_conversion_labels"], []))
    current_res = list(st.session_state.get(K["res_resource_labels"], []))
    updated_conv: List[str] = []
    updated_res: List[str] = []
    for i in range(n_res):
        col1, col2 = st.columns(2)
        with col1:
            res_name = st.text_input(
                f"Source {i+1} resource label",
                value=str(current_res[i]),
                key=f"gp_res_resource_label_{i}",
            ).strip()
        with col2:
            conv_name = st.text_input(
                f"Source {i+1} technology label",
                value=str(current_conv[i]),
                key=f"gp_res_conversion_label_{i}",
            ).strip()
        updated_res.append(res_name or f"Resource_{i+1}")
        updated_conv.append(conv_name or f"Technology_{i+1}")
    st.session_state[K["res_conversion_labels"]] = updated_conv
    st.session_state[K["res_resource_labels"]] = updated_res

    duplicate_resources = sorted({label for label in updated_res if updated_res.count(label) > 1})
    if duplicate_resources:
        st.warning(
            "Renewable resource labels must be unique. Duplicate labels found: "
            + ", ".join(duplicate_resources)
        )
        st.stop()

    st.markdown("**Storage and backup components**")
    battery_label = st.text_input(
        "Storage component label",
        value=str(st.session_state.get(K["battery_label"], "Battery")),
        key="gp_battery_label_input",
    ).strip() or "Battery"
    st.session_state[K["battery_label"]] = battery_label
    battery_efficiency_curve_csv = _normalize_csv_filename(
        str(st.session_state.get(K["battery_efficiency_curve_csv"], "battery_efficiency_curve.csv")),
        "battery_efficiency_curve.csv",
    )
    cycle_fade_enabled = bool(st.session_state.get(K["battery_cycle_fade_enabled"], False))
    cycle_lifetime_to_eol_cycles = float(st.session_state.get(K["battery_cycle_lifetime_to_eol_cycles"], 6000.0))
    calendar_fade_enabled = bool(st.session_state.get(K["battery_calendar_fade_enabled"], False))
    battery_calendar_fade_curve_csv = _normalize_csv_filename(
        str(st.session_state.get(K["battery_calendar_fade_curve_csv"], "battery_calendar_fade_curve.csv")),
        "battery_calendar_fade_curve.csv",
    )
    battery_calendar_time_increment_per_step = float(st.session_state.get(K["battery_calendar_time_increment"], 1.0))
    battery_end_of_life_soh = float(st.session_state.get(K["battery_end_of_life_soh"], 0.8))
    battery_loss_model = str(st.session_state.get(K["battery_loss_model"], "constant_efficiency"))
    degradation_supported = str(st.session_state.get(K["formulation"], "steady_state")) == "dynamic"

    with st.expander("Storage system modeling and degradation", expanded=False):
        main_col, _ = st.columns([1.35, 0.65])
        with main_col:
            battery_loss_model = st.radio(
                "Battery conversion-loss model",
                options=["constant_efficiency", "convex_loss_epigraph"],
                index=0 if battery_loss_model == "constant_efficiency" else 1,
                format_func=lambda v: (
                    "Constant efficiency"
                    if v == "constant_efficiency"
                    else "Convex loss epigraph"
                ),
                help=(
                    "Constant efficiency keeps the current battery model unchanged. "
                    "Convex loss epigraph enables the advanced AC/DC loss formulation and requires "
                    "a battery efficiency-curve CSV. The scalar efficiencies in battery.yaml remain "
                    "the full-load baseline; the CSV provides the normalized curve shape."
                ),
                horizontal=True,
                key="gp_battery_loss_model_radio",
            )
            st.session_state[K["battery_loss_model"]] = battery_loss_model
            if battery_loss_model == "convex_loss_epigraph":
                eff_col1, eff_col2 = st.columns([0.9, 1.05])
                with eff_col1:
                    battery_efficiency_curve_csv = _normalize_csv_filename(
                        st.text_input(
                            "Battery efficiency curve CSV",
                            value=battery_efficiency_curve_csv,
                            help="Template/example file generated under the project inputs folder. Preferred semantics: normalized multipliers around the battery.yaml full-load efficiencies.",
                            key="gp_battery_eff_curve_csv_input",
                        ),
                        "battery_efficiency_curve.csv",
                    )
                    st.session_state[K["battery_efficiency_curve_csv"]] = battery_efficiency_curve_csv

        if not degradation_supported:
            cycle_fade_enabled = False
            calendar_fade_enabled = False
            st.session_state[K["battery_cycle_fade_enabled"]] = False
            st.session_state[K["battery_calendar_fade_enabled"]] = False
            st.info("Battery degradation is available only in the dynamic multi-year formulation. In steady_state typical-year projects, only the optional battery loss model is used.")
        elif battery_loss_model != "convex_loss_epigraph":
            cycle_fade_enabled = False
            calendar_fade_enabled = False
            st.session_state[K["battery_cycle_fade_enabled"]] = False
            st.session_state[K["battery_calendar_fade_enabled"]] = False
            st.info("Enable `Convex loss epigraph` above to unlock the advanced multi-year battery degradation surrogate, including cycle fade, calendar fade, and degraded usable-capacity tracking.")
        else:
            with main_col:
                col1, col2 = st.columns([0.9, 1.05])
                with col1:
                    cycle_fade_enabled = st.checkbox(
                        "Enable cycle fade",
                        value=bool(st.session_state.get(K["battery_cycle_fade_enabled"], False)),
                        help="Adds throughput-based degradation using the internal DC-side battery powers.",
                        key="gp_battery_cycle_fade_enabled_checkbox",
                    )
                    st.session_state[K["battery_cycle_fade_enabled"]] = cycle_fade_enabled
                    cycle_lifetime_to_eol_cycles = float(
                        st.number_input(
                            "Cycle lifetime to end of life [cycles]",
                            min_value=1.0,
                            step=100.0,
                            format="%.0f",
                            value=float(st.session_state.get(K["battery_cycle_lifetime_to_eol_cycles"], 6000.0)),
                            disabled=not cycle_fade_enabled,
                            help="Full-equivalent cycle life used together with battery.yaml depth_of_discharge and the end-of-life SoH target to derive the internal cycle-fade coefficient automatically.",
                            key="gp_battery_cycle_lifetime_to_eol_cycles_input",
                        )
                    )
                    st.session_state[K["battery_cycle_lifetime_to_eol_cycles"]] = cycle_lifetime_to_eol_cycles

                    calendar_fade_enabled = st.checkbox(
                        "Enable calendar fade",
                        value=bool(st.session_state.get(K["battery_calendar_fade_enabled"], False)),
                        help="Adds a yearly average-SoC-dependent calendar-ageing term using a user-provided CSV curve in the linear battery degradation surrogate.",
                        key="gp_battery_calendar_fade_enabled_checkbox",
                    )
                    st.session_state[K["battery_calendar_fade_enabled"]] = calendar_fade_enabled
                    cal_col1, cal_col2 = st.columns([1.35, 0.85])
                    with cal_col1:
                        battery_calendar_fade_curve_csv = _normalize_csv_filename(
                            st.text_input(
                                "Calendar fade curve CSV",
                                value=battery_calendar_fade_curve_csv,
                                help="Template/example file generated under the project inputs folder.",
                                disabled=not calendar_fade_enabled,
                                key="gp_battery_calendar_curve_csv_input",
                            ),
                            "battery_calendar_fade_curve.csv",
                        )
                        st.session_state[K["battery_calendar_fade_curve_csv"]] = battery_calendar_fade_curve_csv
                    with cal_col2:
                        battery_calendar_time_increment_per_step = float(
                            st.number_input(
                                "Calendar time increment per year",
                                min_value=0.0,
                                step=0.1,
                                format="%.3f",
                                value=float(st.session_state.get(K["battery_calendar_time_increment"], 1.0)),
                                disabled=not calendar_fade_enabled,
                                help="Constant calendar-ageing increment applied at each modeled year in the yearly average-SoC calendar-fade term.",
                                key="gp_battery_calendar_time_increment_input",
                            )
                        )
                        st.session_state[K["battery_calendar_time_increment"]] = battery_calendar_time_increment_per_step
                soh_enabled = cycle_fade_enabled or calendar_fade_enabled
                if cycle_fade_enabled and not calendar_fade_enabled:
                    st.info(
                        "With cycle fade only, `battery.yaml -> battery.technical.capacity_degradation_rate_per_year` remains active if provided. "
                        "If calendar fade is enabled, that exogenous annual term is ignored to avoid double-counting background ageing."
                    )
                elif calendar_fade_enabled:
                    st.info(
                        "When calendar fade is enabled, `battery.yaml -> battery.technical.capacity_degradation_rate_per_year` is ignored to avoid double-counting background ageing."
                    )
                battery_end_of_life_soh = float(
                    st.number_input(
                        "Battery end-of-life SoH [-]",
                        min_value=0.01,
                        max_value=1.0,
                        step=0.01,
                        format="%.2f",
                        value=float(st.session_state.get(K["battery_end_of_life_soh"], 0.8)),
                        disabled=not soh_enabled,
                        help="Health threshold used to calibrate the degradation inputs and compare simulated ageing against calendar_lifetime_years in Results.",
                        key="gp_battery_end_of_life_soh_input",
                    )
                )
                st.session_state[K["battery_end_of_life_soh"]] = battery_end_of_life_soh

    generator_label = st.text_input(
        "Backup component label",
        value=str(st.session_state.get(K["generator_label"], "Generator")),
        key="gp_generator_label_input",
    ).strip() or "Generator"
    st.session_state[K["generator_label"]] = generator_label
    with st.expander("Backup system efficiency modeling", expanded=False):
        generator_efficiency_model = str(st.session_state.get(K["generator_efficiency_model"], "constant_efficiency"))
        generator_efficiency_curve_csv = _normalize_csv_filename(
            str(st.session_state.get(K["generator_efficiency_curve_csv"], "generator_efficiency_curve.csv")),
            "generator_efficiency_curve.csv",
        )
        generator_efficiency_model = st.radio(
            "Generator efficiency model",
            options=["constant_efficiency", "efficiency_curve"],
            index=0 if generator_efficiency_model == "constant_efficiency" else 1,
            format_func=lambda v: (
                "Constant efficiency in partial load"
                if v == "constant_efficiency"
                else "Efficiency curve"
            ),
            help=(
                "Constant efficiency keeps the generator at nominal full-load efficiency for all operating points. "
                "Efficiency curve activates the partial-load efficiency curve. The scalar nominal full-load efficiency "
                "in generator.yaml remains the baseline; the CSV provides the normalized part-load shape."
            ),
            horizontal=True,
            key="gp_generator_efficiency_model_radio",
        )
        st.session_state[K["generator_efficiency_model"]] = generator_efficiency_model
        if generator_efficiency_model == "efficiency_curve":
            generator_efficiency_curve_csv = _normalize_csv_filename(
                st.text_input(
                    "Generator efficiency curve CSV",
                    value=generator_efficiency_curve_csv,
                    help="Template/example file generated under the project inputs folder. Preferred semantics: normalized multipliers around the generator.yaml nominal full-load efficiency.",
                    key="gp_generator_eff_curve_csv_input",
                ),
                "generator_efficiency_curve.csv",
            )
            st.session_state[K["generator_efficiency_curve_csv"]] = generator_efficiency_curve_csv
            st.caption("Generated example file")
            st.caption(f"`inputs/{generator_efficiency_curve_csv}`")

    generator_efficiency_model = str(st.session_state.get(K["generator_efficiency_model"], "constant_efficiency"))
    generator_efficiency_curve_csv = _normalize_csv_filename(
        str(st.session_state.get(K["generator_efficiency_curve_csv"], "generator_efficiency_curve.csv")),
        "generator_efficiency_curve.csv",
    )

    fuel_label = st.text_input(
        "Fuel label",
        value=str(st.session_state.get(K["fuel_label"], "Fuel")),
        key="gp_fuel_label_input",
    ).strip() or "Fuel"
    st.session_state[K["fuel_label"]] = fuel_label

    return (
        system_type,
        on_grid,
        bool(st.session_state[K["allow_export"]]),
        discrete_sizing,
        n_res,
        updated_conv,
        updated_res,
        battery_label,
        battery_loss_model,
        battery_efficiency_curve_csv,
        cycle_fade_enabled,
        cycle_lifetime_to_eol_cycles,
        calendar_fade_enabled,
        battery_calendar_fade_curve_csv,
        battery_calendar_time_increment_per_step,
        battery_end_of_life_soh,
        generator_label,
        generator_efficiency_model,
        generator_efficiency_curve_csv,
        fuel_label,
    )


def render_constraints_section() -> Tuple[str, float, float, float, float | None]:
    st.markdown("**Optimization constraints**")
    with st.expander("⚙️ System constraints", expanded=True):
        land_limit_enabled = st.checkbox(
            "Enforce land limit for renewables",
            value=bool(st.session_state.get(K["land_limit_enabled"], False)),
            help="If disabled, land availability is left unconstrained.",
            key="gp_land_limit_enabled_checkbox",
        )
        st.session_state[K["land_limit_enabled"]] = bool(land_limit_enabled)

        if land_limit_enabled:
            land = float(
                st.number_input(
                    "Maximum land availability for renewables [m²]",
                    min_value=0.0,
                    step=10.0,
                    value=float(st.session_state.get(K["land_availability_m2"], 0.0) or 0.0),
                    key="gp_land_input",
                )
            )
            st.session_state[K["land_availability_m2"]] = land
        else:
            land = None
            st.session_state[K["land_availability_m2"]] = None
        use_multiscenario = bool(st.session_state.get(K["use_multiscenario"], False))
        if use_multiscenario:
            enforcement = st.selectbox(
                "Constraint enforcement across scenarios",
                options=CONSTRAINT_ENFORCEMENT_OPTIONS,
                index=0 if st.session_state.get(K["constraints_enforcement"], "expected") == "expected" else 1,
                key="gp_constraints_enforcement_select",
            )
        else:
            enforcement = "scenario_wise"
        st.session_state[K["constraints_enforcement"]] = enforcement

        min_res_pct = float(
            st.number_input(
                "Minimum renewable penetration over project [%]",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                value=float(st.session_state[K["min_res_penetration_pct"]]),
                key="gp_min_res_pct_input",
            )
        )
        st.session_state[K["min_res_penetration_pct"]] = min_res_pct
        min_res = min_res_pct / 100.0

        max_ll_pct = float(
            st.number_input(
                "Maximum lost load fraction over project [%]",
                min_value=0.0,
                max_value=100.0,
                step=0.5,
                value=float(st.session_state[K["max_lost_load_fraction_pct"]]),
                key="gp_max_ll_pct_input",
            )
        )
        st.session_state[K["max_lost_load_fraction_pct"]] = max_ll_pct
        max_ll = max_ll_pct / 100.0

        if max_ll_pct > 0.0:
            lolc = float(
                st.number_input(
                    "Social cost of lost load (per kWh unmet)",
                    min_value=0.0,
                    step=0.01,
                    value=float(st.session_state[K["lost_load_cost_per_kwh"]]),
                    key="gp_lolc_input",
                )
            )
            st.session_state[K["lost_load_cost_per_kwh"]] = lolc
        else:
            lolc = 0.0
            st.session_state[K["lost_load_cost_per_kwh"]] = 0.0

    return enforcement, min_res, max_ll, lolc, land


# =============================================================================
# Page entrypoint
# =============================================================================
def render_project_setup_page() -> None:
    init_session_state_defaults()

    st.title("Project Setup")
    st.markdown(
        "Configure your planning model, generate a project folder with input templates, "
        "then fill the files externally and come back to validate/run the model."
    )

    st.subheader("Project")
    tab_create, tab_load = st.tabs(["Create", "Load"])

    with tab_create:
        st.caption(
            "Create a project folder and generate input templates from the current settings shown on this page."
        )

        # Project name
        project_name = st.text_input(
            "Project name",
            value=str(st.session_state.get(K["project_name"], "")),
            placeholder="e.g. project_1",
            key="gp_create_project_name",
        )
        project_name = sanitize_project_name(project_name)
        st.session_state[K["project_name"]] = project_name

        if project_name and project_exists(project_name):
            st.warning(
                "This project **already exists**. Continuing will **overwrite** the generated files in "
                "`inputs/` using the current settings shown on this page."
            )

        # Project description
        desc = st.text_area(
            "Short description",
            value=str(st.session_state.get(K["project_desc"], "")),
            placeholder="Brief context and objective of this project.",
            key="gp_project_desc_text",
        )
        st.session_state[K["project_desc"]] = desc.strip()

        # Configuration sections appear only after a project name is provided
        if not project_name:
            st.info("Please provide a project name to configure the model and generate templates.")
        else:
            st.markdown("---")
            (
                formulation,
                is_dynamic,
                start_year,
                horizon_years,
                dr_dec,
                cap_exp,
                investment_steps,
            ) = render_formulation_section()
            em_cost = render_externalities_section()

            st.markdown("---")
            (
                system_type,
                on_grid,
                allow_export,
                discrete_sizing,
                n_res,
                conv_labels,
                resource_labels,
                battery_label,
                battery_loss_model,
                battery_efficiency_curve_csv,
                battery_cycle_fade_enabled,
                battery_cycle_lifetime_to_eol_cycles,
                battery_calendar_fade_enabled,
                battery_calendar_fade_curve_csv,
                battery_calendar_time_increment_per_step,
                battery_end_of_life_soh,
                generator_label,
                generator_efficiency_model,
                generator_efficiency_curve_csv,
                fuel_label,
            ) = render_system_section()

            st.markdown("---")
            multi, n_scen, scen_labels, weights = render_uncertainty_section()

            st.markdown("---")
            enforcement, min_res, max_ll, lolc, land = render_constraints_section()

            renewable_vintage_labels_by_step: Dict[str, Dict[str, str]] = {}
            battery_vintage_labels_by_step: Dict[str, str] = {}
            generator_vintage_labels_by_step: Dict[str, str] = {}
            fuel_vintage_labels_by_step: Dict[str, str] = {}

            cfg = PageConfig(
                formulation=formulation,
                system_type=system_type,
                on_grid=on_grid,
                allow_export=allow_export,
                discrete_unit_sizing=discrete_sizing,
                start_year_label=start_year,
                horizon_years=horizon_years,
                social_discount_rate=dr_dec,
                capacity_expansion=cap_exp,
                investment_steps=investment_steps,
                multi_scenario=multi,
                n_scenarios=n_scen,
                scenario_labels=scen_labels,
                scenario_weights=weights,
                constraints_enforcement=enforcement,
                min_res_penetration=min_res,
                max_lost_load_fraction=max_ll,
                lost_load_cost_per_kwh=lolc,
                land_availability_m2=land,
                emission_cost_per_kgco2e=em_cost,
                n_res_sources=n_res,
                res_conversion_labels=conv_labels,
                res_resource_labels=resource_labels,
                battery_label=battery_label,
                battery_loss_model=battery_loss_model,
                battery_efficiency_curve_csv=battery_efficiency_curve_csv,
                battery_cycle_fade_enabled=battery_cycle_fade_enabled,
                battery_cycle_lifetime_to_eol_cycles=battery_cycle_lifetime_to_eol_cycles,
                battery_calendar_fade_enabled=battery_calendar_fade_enabled,
                battery_calendar_fade_curve_csv=battery_calendar_fade_curve_csv,
                battery_calendar_time_increment_per_step=battery_calendar_time_increment_per_step,
                battery_end_of_life_soh=battery_end_of_life_soh,
                generator_label=generator_label,
                generator_efficiency_model=generator_efficiency_model,
                generator_efficiency_curve_csv=generator_efficiency_curve_csv,
                fuel_label=fuel_label,
                renewable_vintage_labels_by_step=renewable_vintage_labels_by_step,
                battery_vintage_labels_by_step=battery_vintage_labels_by_step,
                generator_vintage_labels_by_step=generator_vintage_labels_by_step,
                fuel_vintage_labels_by_step=fuel_vintage_labels_by_step,
            )

            st.markdown("---")
            # Optional UX: change label if overwriting an existing project
            btn_label = "Overwrite templates" if project_exists(project_name) else "Initialize project and generate templates"

            if st.button(btn_label, type="primary", key="gp_create_confirm"):
                create_or_overwrite_project(
                    project_name=project_name,
                    project_description=st.session_state[K["project_desc"]],
                    cfg=cfg,
                )


    with tab_load:
        st.caption(
            "Set an existing project as active without modifying any files. This action does not "
            "repopulate the form from the project's saved inputs."
        )
        existing = _list_existing_projects()

        if not existing:
            st.warning("No existing projects found. Create a new project using the form above.")
            st.info(
                "The selected project will be set as **active**. No templates will be overwritten, "
                "and the current form values will remain unchanged."
            )
            st.button("Load project", type="primary", key="gp_load_confirm", disabled=True)
        else:
            pick = st.selectbox(
                "Select an existing project",
                options=existing,
                index=0,
                key="gp_load_project_select",
            )
            pick = sanitize_project_name(pick)
            st.session_state[K["project_name"]] = pick

            st.info(
                "The selected project will be set as **active**. No templates will be overwritten, "
                "and the current form values will remain unchanged."
            )

            if st.button("Load project", type="primary", key="gp_load_confirm"):
                load_project(project_name=pick)

render_project_setup_page()

