from __future__ import annotations

from dataclasses import dataclass
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
    build_dispatch_timeseries_table,
    build_energy_balance_table,
    export_typical_year_results,
)
from core.export.multi_year_results import (
    build_dispatch_timeseries_table_multi_year,
    build_energy_balance_table_multi_year,
    export_multi_year_results,
)


@dataclass
class TypicalYearFileResults:
    project_name: str
    results_dir: Path
    data: xr.Dataset
    dispatch: pd.DataFrame
    energy_balance: pd.DataFrame
    design: pd.DataFrame
    kpis: pd.DataFrame


@dataclass
class MultiYearFileResults:
    project_name: str
    results_dir: Path
    sets: xr.Dataset
    data: xr.Dataset
    dispatch: pd.DataFrame
    energy_balance: pd.DataFrame
    design: pd.DataFrame
    kpis: pd.DataFrame
    cash: pd.DataFrame
    scenario_costs: pd.DataFrame


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


def load_typical_year_results_from_files(project_name: str) -> Optional[TypicalYearFileResults]:
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

    return TypicalYearFileResults(
        project_name=project_name,
        results_dir=results_dir,
        data=data,
        dispatch=pd.read_csv(results_dir / "dispatch_timeseries.csv"),
        energy_balance=pd.read_csv(results_dir / "energy_balance.csv"),
        design=pd.read_csv(results_dir / "design_summary.csv"),
        kpis=pd.read_csv(results_dir / "kpis.csv"),
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


def load_multi_year_results_from_files(project_name: str) -> Optional[MultiYearFileResults]:
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

    return MultiYearFileResults(
        project_name=project_name,
        results_dir=results_dir,
        sets=sets,
        data=data,
        dispatch=pd.read_csv(results_dir / "dispatch_timeseries.csv"),
        energy_balance=pd.read_csv(results_dir / "energy_balance.csv"),
        design=pd.read_csv(results_dir / "design_by_step.csv"),
        kpis=pd.read_csv(results_dir / "kpis_yearly.csv"),
        cash=pd.read_csv(results_dir / "cashflows_discounted.csv"),
        scenario_costs=pd.read_csv(results_dir / "scenario_costs_yearly.csv"),
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
