from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import json

import pandas as pd
import xarray as xr

from core.export.common import get_bundle_formulation, get_var_solution as _get_var_solution_common
from core.export.results_bundle import ResultsBundle, build_results_bundle
from core.data_pipeline.loader import load_project_dataset
from core.io.utils import project_paths
from core.multi_year_model.sets import initialize_sets as initialize_multi_year_sets
from core.typical_year_model.sets import initialize_sets as initialize_typical_year_sets
from core.export.typical_year_results import (
    TypicalYearResults,
    build_typical_year_results,
    build_typical_year_results_from_tables,
    build_dispatch_timeseries_table,
    build_energy_balance_table,
    export_typical_year_results,
    export_typical_year_results_package,
)
from core.export.multi_year_results import (
    MultiYearResults,
    build_dispatch_timeseries_table_multi_year,
    build_energy_balance_table_multi_year,
    build_multi_year_results,
    build_multi_year_results_from_tables,
    export_multi_year_results,
    export_multi_year_results_package,
)


def _resolve_typical_year_results_dir(project_name: str) -> Optional[Path]:
    paths = project_paths(project_name)
    candidates = [paths.results_dir / "typical_year", paths.results_dir]
    required = {
        "dispatch_timeseries.csv",
        "energy_balance.csv",
        "design_summary.csv",
        "kpis.csv",
    }
    for directory in candidates:
        if directory.exists() and all((directory / name).exists() for name in required):
            return directory
    return None


def load_typical_year_results_from_files(project_name: str) -> Optional[TypicalYearResults]:
    paths = project_paths(project_name)
    if not paths.formulation_json.exists():
        return None

    try:
        formulation = json.loads(paths.formulation_json.read_text(encoding="utf-8"))
    except Exception:
        return None

    if str(formulation.get("core_formulation", "steady_state")).strip() != "steady_state":
        return None

    results_dir = _resolve_typical_year_results_dir(project_name)
    if results_dir is None:
        return None

    sets = initialize_typical_year_sets(project_name)
    data = load_project_dataset(project_name, sets, mode="typical_year")

    optional_frames: Dict[str, pd.DataFrame] = {}
    optional_files = {
        "upfront_df": "upfront_investment.csv",
        "expected_cost_components_df": "expected_cost_components.csv",
        "expected_fixed_om_df": "expected_fixed_om.csv",
        "annuities_df": "annuities.csv",
        "embodied_df": "embodied_externalities.csv",
        "scenario_variable_costs_df": "scenario_variable_costs.csv",
        "scenario_emissions_df": "scenario_emissions.csv",
        "scenario_total_operating_costs_df": "scenario_total_operating_costs.csv",
    }
    for key, filename in optional_files.items():
        path = results_dir / filename
        if path.exists():
            optional_frames[key] = pd.read_csv(path)

    return build_typical_year_results_from_tables(
        project_name=project_name,
        data=data,
        dispatch_df=pd.read_csv(results_dir / "dispatch_timeseries.csv"),
        energy_balance_df=pd.read_csv(results_dir / "energy_balance.csv"),
        design_summary_df=pd.read_csv(results_dir / "design_summary.csv"),
        kpis_df=pd.read_csv(results_dir / "kpis.csv"),
        results_dir=results_dir,
        source="files",
        **optional_frames,
    )


def _resolve_multi_year_results_dir(project_name: str) -> Optional[Path]:
    paths = project_paths(project_name)
    candidates = [paths.results_dir]
    required = {
        "dispatch_timeseries.csv",
        "energy_balance.csv",
        "design_by_step.csv",
        "kpis_yearly.csv",
        "cashflows_discounted.csv",
        "scenario_costs_yearly.csv",
    }
    for directory in candidates:
        if directory.exists() and all((directory / name).exists() for name in required):
            return directory
    return None


def load_multi_year_results_from_files(project_name: str) -> Optional[MultiYearResults]:
    paths = project_paths(project_name)
    if not paths.formulation_json.exists():
        return None

    try:
        formulation = json.loads(paths.formulation_json.read_text(encoding="utf-8"))
    except Exception:
        return None

    if str(formulation.get("core_formulation", "steady_state")).strip() != "dynamic":
        return None

    results_dir = _resolve_multi_year_results_dir(project_name)
    if results_dir is None:
        return None

    sets = initialize_multi_year_sets(project_name)
    data = load_project_dataset(project_name, sets, mode="multi_year")

    optional_frames: Dict[str, pd.DataFrame] = {}
    optional_files = {
        "renewable_inverter_design_by_step_df": "renewable_inverter_design_by_step.csv",
        "battery_inverter_design_by_step_df": "battery_inverter_design_by_step.csv",
        "inverter_capacity_by_year_df": "inverter_capacity_by_year.csv",
        "inverter_metrics_yearly_df": "inverter_metrics_yearly.csv",
        "capacity_by_year_df": "capacity_by_year.csv",
        "investment_summary_df": "investment_summary.csv",
        "yearly_expected_df": "yearly_expected.csv",
        "reporting_summary_df": "reporting_summary.csv",
    }
    for key, filename in optional_files.items():
        path = results_dir / filename
        if path.exists():
            optional_frames[key] = pd.read_csv(path)

    return build_multi_year_results_from_tables(
        project_name=project_name,
        data=data,
        sets=sets,
        dispatch_df=pd.read_csv(results_dir / "dispatch_timeseries.csv"),
        energy_balance_df=pd.read_csv(results_dir / "energy_balance.csv"),
        design_by_step_df=pd.read_csv(results_dir / "design_by_step.csv"),
        kpis_yearly_df=pd.read_csv(results_dir / "kpis_yearly.csv"),
        cashflows_discounted_df=pd.read_csv(results_dir / "cashflows_discounted.csv"),
        scenario_costs_yearly_df=pd.read_csv(results_dir / "scenario_costs_yearly.csv"),
        results_dir=results_dir,
        source="files",
        metadata={"project_name": project_name, "formulation": "dynamic"},
        **optional_frames,
    )


def _dataset_project_name(data: Any) -> Optional[str]:
    if not isinstance(data, xr.Dataset):
        return None
    settings = (data.attrs or {}).get("settings", {})
    if not isinstance(settings, dict):
        return None
    raw = settings.get("project_name", None)
    return str(raw) if raw is not None else None


def get_results_bundle_from_session(session_state: Mapping[str, Any], *, active_project: str | None = None) -> Optional[ResultsBundle]:
    raw = session_state.get("gp_results_bundle")
    if isinstance(raw, ResultsBundle):
        if active_project is not None and _dataset_project_name(raw.data) not in {None, active_project}:
            return None
        model_obj = session_state.get("gp_model_obj")
        model_sol = getattr(getattr(model_obj, "model", None), "solution", None)
        if isinstance(model_sol, xr.Dataset):
            raw.solution = model_sol
        return raw

    data = session_state.get("gp_data")
    vars_dict = session_state.get("gp_vars")
    if not isinstance(data, xr.Dataset) or not isinstance(vars_dict, dict):
        return None
    if active_project is not None and _dataset_project_name(data) not in {None, active_project}:
        return None

    return build_results_bundle(
        sets=session_state.get("gp_sets"),
        data=data,
        vars=vars_dict,
        model_obj=session_state.get("gp_model_obj"),
        solution=session_state.get("gp_solution"),
        solution_summary=session_state.get("gp_solution_summary"),
        solver=None,
    )


def get_typical_year_results_from_session(
    session_state: Mapping[str, Any],
    *,
    active_project: str | None = None,
) -> Optional[TypicalYearResults]:
    raw = session_state.get("gp_typical_year_results")
    if isinstance(raw, TypicalYearResults):
        raw_project = str(raw.metadata.get("project_name") or raw.project_name)
        if active_project is not None and raw_project not in {None, "", active_project}:
            return None
        return raw

    data = session_state.get("gp_data")
    vars_dict = session_state.get("gp_vars")
    if not isinstance(data, xr.Dataset) or not isinstance(vars_dict, dict):
        return None
    if str(((data.attrs or {}).get("settings", {}) or {}).get("formulation", "steady_state")) != "steady_state":
        return None
    if active_project is not None and _dataset_project_name(data) not in {None, active_project}:
        return None

    # Legacy compatibility fallback while migrating old session-state payloads.
    summary = session_state.get("gp_solution_summary")
    objective_value = summary.get("objective_value") if isinstance(summary, dict) else None
    status = summary.get("status") if isinstance(summary, dict) else None
    return build_typical_year_results(
        project_name=str(active_project or _dataset_project_name(data) or ""),
        data=data,
        vars=vars_dict,
        solution=session_state.get("gp_solution") if isinstance(session_state.get("gp_solution"), xr.Dataset) else None,
        objective_value=objective_value,
        status=status,
        solver=None,
        results_dir=None,
        source="session_legacy",
    )


def get_multi_year_results_from_session(
    session_state: Mapping[str, Any],
    *,
    active_project: str | None = None,
) -> Optional[MultiYearResults]:
    raw = session_state.get("gp_multi_year_results")
    if isinstance(raw, MultiYearResults):
        raw_project = str(raw.metadata.get("project_name") or raw.project_name)
        if active_project is not None and raw_project not in {None, "", active_project}:
            return None
        return raw

    bundle = get_results_bundle_from_session(session_state, active_project=active_project)
    if bundle is None or not isinstance(bundle.data, xr.Dataset) or not isinstance(bundle.vars, dict):
        return None
    if str(((bundle.data.attrs or {}).get("settings", {}) or {}).get("formulation", "steady_state")) != "dynamic":
        return None
    summary = session_state.get("gp_solution_summary")
    objective_value = summary.get("objective_value") if isinstance(summary, dict) else bundle.objective_value
    status = summary.get("status") if isinstance(summary, dict) else bundle.status
    return build_multi_year_results(
        project_name=str(active_project or _dataset_project_name(bundle.data) or ""),
        sets=bundle.sets if isinstance(bundle.sets, xr.Dataset) else xr.Dataset(),
        data=bundle.data,
        vars=bundle.vars,
        solution=bundle.solution if isinstance(bundle.solution, xr.Dataset) else None,
        objective_value=objective_value,
        status=status,
        solver=bundle.metadata.get("solver") if isinstance(bundle.metadata, dict) else None,
        results_dir=None,
        source="session_legacy",
    )

def get_var_solution(*, bundle: ResultsBundle, name: str) -> Optional[xr.DataArray]:
    return _get_var_solution_common(
        vars_dict=bundle.vars if isinstance(bundle.vars, dict) else None,
        solution=bundle.solution if isinstance(bundle.solution, xr.Dataset) else None,
        name=name,
    )


def build_energy_balance_dataframe(bundle: ResultsBundle) -> pd.DataFrame:
    if bundle.data is None or not isinstance(bundle.vars, dict):
        raise RuntimeError("Missing data/vars in ResultsBundle.")
    formulation = get_bundle_formulation(bundle)
    if formulation == "dynamic":
        dispatch = build_dispatch_timeseries_table_multi_year(
            sets=bundle.sets,
            data=bundle.data,
            vars=bundle.vars,
            solution=bundle.solution if isinstance(bundle.solution, xr.Dataset) else None,
        )
        return build_energy_balance_table_multi_year(dispatch)
    dispatch = build_dispatch_timeseries_table(
        data=bundle.data,
        vars=bundle.vars,
        solution=bundle.solution if isinstance(bundle.solution, xr.Dataset) else None,
    )
    return build_energy_balance_table(data=bundle.data, dispatch_df=dispatch)


def export_results_from_bundle(
    project_name: str,
    bundle: ResultsBundle,
    model_obj: Any = None,
) -> Dict[str, str]:
    if bundle.data is None or not isinstance(bundle.vars, dict):
        raise RuntimeError("Missing data/vars in ResultsBundle.")

    sets_ds = bundle.sets if isinstance(bundle.sets, xr.Dataset) else xr.Dataset()
    formulation = get_bundle_formulation(bundle)
    if formulation == "dynamic":
        return export_multi_year_results(
            project_name=project_name,
            sets=sets_ds,
            data=bundle.data,
            model=getattr(model_obj, "model", None),
            vars=bundle.vars,
            solution=bundle.solution if isinstance(bundle.solution, xr.Dataset) else None,
            out_dir=None,
        )
    return export_typical_year_results(
        project_name=project_name,
        sets=sets_ds,
        data=bundle.data,
        model=getattr(model_obj, "model", None),
        vars=bundle.vars,
        solution=bundle.solution if isinstance(bundle.solution, xr.Dataset) else None,
        out_dir=None,
    )


def export_typical_year_results_from_object(results: TypicalYearResults) -> Dict[str, str]:
    return export_typical_year_results_package(results=results, out_dir=None)


def export_multi_year_results_from_object(results: MultiYearResults) -> Dict[str, str]:
    return export_multi_year_results_package(results=results, out_dir=None)
