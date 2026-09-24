from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import xarray as xr

from microgridspy.data_pipeline.loader import load_project_dataset
from microgridspy.export.common import get_bundle_formulation
from microgridspy.export.common import get_var_solution as _get_var_solution_common
from microgridspy.export.multi_year_results import (
    MultiYearResults,
    build_dispatch_timeseries_table_multi_year,
    build_energy_balance_table_multi_year,
    build_multi_year_results_from_tables,
    export_multi_year_results,
    export_multi_year_results_package,
)
from microgridspy.export.results_bundle import ResultsBundle
from microgridspy.export.typical_year_results import (
    TypicalYearResults,
    build_dispatch_timeseries_table,
    build_energy_balance_table,
    build_typical_year_results_from_tables,
    export_typical_year_results,
    export_typical_year_results_package,
)
from microgridspy.io.formulation import MULTI_YEAR, TYPICAL_YEAR
from microgridspy.io.utils import project_paths
from microgridspy.multi_year_model.sets import initialize_sets as initialize_multi_year_sets
from microgridspy.typical_year_model.sets import initialize_sets as initialize_typical_year_sets


def _resolve_typical_year_results_dir(project_name: str) -> Path | None:
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


def load_typical_year_results_from_files(project_name: str) -> TypicalYearResults | None:
    paths = project_paths(project_name)
    if not paths.formulation_json.exists():
        return None

    try:
        formulation = json.loads(paths.formulation_json.read_text(encoding="utf-8"))
    except Exception:
        return None

    if str(formulation.get("core_formulation", TYPICAL_YEAR)) != TYPICAL_YEAR:
        return None

    results_dir = _resolve_typical_year_results_dir(project_name)
    if results_dir is None:
        return None

    sets = initialize_typical_year_sets(project_name)
    data = load_project_dataset(project_name, sets, mode="typical_year")

    optional_frames: dict[str, pd.DataFrame] = {}
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


def _resolve_multi_year_results_dir(project_name: str) -> Path | None:
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


def load_multi_year_results_from_files(project_name: str) -> MultiYearResults | None:
    paths = project_paths(project_name)
    if not paths.formulation_json.exists():
        return None

    try:
        formulation = json.loads(paths.formulation_json.read_text(encoding="utf-8"))
    except Exception:
        return None

    if str(formulation.get("core_formulation", TYPICAL_YEAR)) != MULTI_YEAR:
        return None

    results_dir = _resolve_multi_year_results_dir(project_name)
    if results_dir is None:
        return None

    sets = initialize_multi_year_sets(project_name)
    data = load_project_dataset(project_name, sets, mode="multi_year")

    optional_frames: dict[str, pd.DataFrame] = {}
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
        metadata={"project_name": project_name, "formulation": MULTI_YEAR},
        **optional_frames,
    )


def get_var_solution(*, bundle: ResultsBundle, name: str) -> xr.DataArray | None:
    return _get_var_solution_common(
        vars_dict=bundle.vars if isinstance(bundle.vars, dict) else None,
        solution=bundle.solution if isinstance(bundle.solution, xr.Dataset) else None,
        name=name,
    )


def build_energy_balance_dataframe(bundle: ResultsBundle) -> pd.DataFrame:
    if bundle.data is None or not isinstance(bundle.vars, dict):
        raise RuntimeError("Missing data/vars in ResultsBundle.")
    formulation = get_bundle_formulation(bundle)
    if formulation == MULTI_YEAR:
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
) -> dict[str, str]:
    if bundle.data is None or not isinstance(bundle.vars, dict):
        raise RuntimeError("Missing data/vars in ResultsBundle.")

    sets_ds = bundle.sets if isinstance(bundle.sets, xr.Dataset) else xr.Dataset()
    formulation = get_bundle_formulation(bundle)
    if formulation == MULTI_YEAR:
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


def export_typical_year_results_from_object(results: TypicalYearResults) -> dict[str, str]:
    return export_typical_year_results_package(results=results, out_dir=None)


def export_multi_year_results_from_object(results: MultiYearResults) -> dict[str, str]:
    return export_multi_year_results_package(results=results, out_dir=None)
