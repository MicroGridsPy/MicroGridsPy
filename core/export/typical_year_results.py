from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import xarray as xr
import linopy as lp

from core.export.common import (
    InputValidationError,
    ensure_results_dir,
    get_var_solution,
    require_data_array,
    safe_float,
    write_csv_outputs,
)
from core.export.typical_year_reporting import build_energy_balance_table as build_reporting_energy_balance_table
from core.export.typical_year_reporting import build_reporting_tables
from core.typical_year_model.params import get_params

def build_dispatch_timeseries_table(
    *,
    data: xr.Dataset,
    vars: Dict[str, Any],
    solution: Optional[xr.Dataset],
) -> pd.DataFrame:
    p = get_params(data)
    load = p.load_demand
    res = require_data_array("res_generation", get_var_solution(vars_dict=vars, solution=solution, name="res_generation", prefer_solution_dataset=False))
    gen = require_data_array("generator_generation", get_var_solution(vars_dict=vars, solution=solution, name="generator_generation", prefer_solution_dataset=False))
    bch = require_data_array("battery_charge", get_var_solution(vars_dict=vars, solution=solution, name="battery_charge", prefer_solution_dataset=False))
    bdis = require_data_array("battery_discharge", get_var_solution(vars_dict=vars, solution=solution, name="battery_discharge", prefer_solution_dataset=False))
    bsoc = require_data_array("battery_soc", get_var_solution(vars_dict=vars, solution=solution, name="battery_soc", prefer_solution_dataset=False))
    bch_dc = get_var_solution(vars_dict=vars, solution=solution, name="battery_charge_dc", prefer_solution_dataset=False)
    bdis_dc = get_var_solution(vars_dict=vars, solution=solution, name="battery_discharge_dc", prefer_solution_dataset=False)
    bch_loss = get_var_solution(vars_dict=vars, solution=solution, name="battery_charge_loss", prefer_solution_dataset=False)
    bdis_loss = get_var_solution(vars_dict=vars, solution=solution, name="battery_discharge_loss", prefer_solution_dataset=False)
    fuel_cons = get_var_solution(vars_dict=vars, solution=solution, name="fuel_consumption", prefer_solution_dataset=False)
    ll = require_data_array("lost_load", get_var_solution(vars_dict=vars, solution=solution, name="lost_load", prefer_solution_dataset=False))

    on_grid = p.is_grid_on()
    allow_export = p.is_grid_export_enabled()
    gimp = get_var_solution(vars_dict=vars, solution=solution, name="grid_import", prefer_solution_dataset=False) if on_grid else None
    gexp = get_var_solution(vars_dict=vars, solution=solution, name="grid_export", prefer_solution_dataset=False) if (on_grid and allow_export) else None

    records = []
    res_total = res.sum("resource")
    for s in load.coords["scenario"].values:
        s_label = str(s)
        d = pd.DataFrame(
            {
                "period": load.coords["period"].values.astype(int),
                "scenario": s_label,
                "load_demand": load.sel(scenario=s).values.astype(float),
                "res_generation_total": res_total.sel(scenario=s).values.astype(float),
                "generator_generation": gen.sel(scenario=s).values.astype(float),
                "battery_charge": bch.sel(scenario=s).values.astype(float),
                "battery_discharge": bdis.sel(scenario=s).values.astype(float),
                "battery_soc": bsoc.sel(scenario=s).values.astype(float),
                "lost_load": ll.sel(scenario=s).values.astype(float),
                "fuel_consumption": (
                    fuel_cons.sel(scenario=s).values.astype(float)
                    if isinstance(fuel_cons, xr.DataArray)
                    else 0.0
                ),
                "grid_import": gimp.sel(scenario=s).values.astype(float) if isinstance(gimp, xr.DataArray) else 0.0,
                "grid_export": gexp.sel(scenario=s).values.astype(float) if isinstance(gexp, xr.DataArray) else 0.0,
            }
        )
        grid_eta = float(p.grid_transmission_efficiency.sel(scenario=s)) if p.grid_transmission_efficiency is not None else 1.0
        d["grid_import_delivered"] = d["grid_import"] * grid_eta
        d["grid_export_delivered"] = d["grid_export"] * grid_eta
        for r in res.coords["resource"].values:
            d[f"res_generation__{str(r)}"] = res.sel(scenario=s, resource=r).values.astype(float)
        if isinstance(bch_dc, xr.DataArray):
            d["battery_charge_dc"] = bch_dc.sel(scenario=s).values.astype(float)
        if isinstance(bdis_dc, xr.DataArray):
            d["battery_discharge_dc"] = bdis_dc.sel(scenario=s).values.astype(float)
        if isinstance(bch_loss, xr.DataArray):
            d["battery_charge_loss"] = bch_loss.sel(scenario=s).values.astype(float)
        if isinstance(bdis_loss, xr.DataArray):
            d["battery_discharge_loss"] = bdis_loss.sel(scenario=s).values.astype(float)
        records.append(d)

    return pd.concat(records, ignore_index=True)


def build_energy_balance_table(*, data: xr.Dataset, dispatch_df: pd.DataFrame) -> pd.DataFrame:
    return build_reporting_energy_balance_table(data, dispatch_df)


def build_design_summary_table(
    *,
    data: xr.Dataset,
    vars: Dict[str, Any],
    solution: Optional[xr.Dataset],
) -> pd.DataFrame:
    p = get_params(data)
    res_units = require_data_array("res_units", get_var_solution(vars_dict=vars, solution=solution, name="res_units", prefer_solution_dataset=False))
    bat_units = require_data_array("battery_units", get_var_solution(vars_dict=vars, solution=solution, name="battery_units", prefer_solution_dataset=False))
    gen_units = require_data_array("generator_units", get_var_solution(vars_dict=vars, solution=solution, name="generator_units", prefer_solution_dataset=False))

    res_cap = res_units * p.res_nominal_capacity_kw
    bat_cap = bat_units * p.battery_nominal_capacity_kwh
    gen_cap = gen_units * p.generator_nominal_capacity_kw

    row: Dict[str, Any] = {
        "battery_units": safe_float(bat_units),
        "battery_installed_kwh": safe_float(bat_cap),
        "generator_units": safe_float(gen_units),
        "generator_installed_kw": safe_float(gen_cap),
        "res_units_total": safe_float(res_units.sum("resource")),
        "res_installed_kw_total": safe_float(res_cap.sum("resource")),
    }
    for r in res_units.coords["resource"].values:
        label = str(r)
        row[f"res_units__{label}"] = safe_float(res_units.sel(resource=r))
        row[f"res_installed_kw__{label}"] = safe_float(res_cap.sel(resource=r))
    return pd.DataFrame([row])


def _crf(r: float, n: float) -> float:
    if n <= 0:
        return float("nan")
    if abs(r) < 1e-12:
        return 1.0 / n
    a = (1.0 + r) ** n
    return (r * a) / (a - 1.0)


def build_kpis_table(
    *,
    data: xr.Dataset,
    vars: Dict[str, Any],
    solution: Optional[xr.Dataset],
    objective_value: Optional[float],
) -> pd.DataFrame:
    dispatch = build_dispatch_timeseries_table(data=data, vars=vars, solution=solution)
    design = build_design_summary_table(data=data, vars=vars, solution=solution)
    return build_reporting_tables(
        data=data,
        dispatch_df=dispatch,
        design_df=design,
        solver_objective_value=objective_value,
    ).kpis


def energy_balance_residual_summary(energy_balance_df: pd.DataFrame) -> pd.DataFrame:
    g = energy_balance_df.groupby("scenario", as_index=False)["balance_residual"].agg(
        max_abs_balance_residual=lambda x: float(np.max(np.abs(np.asarray(x, dtype=float))))
    )
    return g


def export_typical_year_results(
    project_name: str,
    sets: xr.Dataset,
    data: xr.Dataset,
    model: Optional[lp.Model],
    vars: Dict[str, Any],
    solution: Optional[xr.Dataset],
    out_dir: Path | None = None,
) -> dict:
    if out_dir is None:
        out_dir = ensure_results_dir(project_name, suffix="typical_year")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    model_obj = model
    objective_value = None
    if model_obj is not None and hasattr(model_obj, "objective"):
        objective_value = safe_float(getattr(model_obj.objective, "value", None))

    dispatch_df = build_dispatch_timeseries_table(data=data, vars=vars, solution=solution)
    energy_df = build_energy_balance_table(data=data, dispatch_df=dispatch_df)
    design_df = build_design_summary_table(data=data, vars=vars, solution=solution)
    kpi_df = build_kpis_table(data=data, vars=vars, solution=solution, objective_value=objective_value)

    return write_csv_outputs(
        out_dir,
        {
            "dispatch_timeseries.csv": dispatch_df,
            "energy_balance.csv": energy_df,
            "design_summary.csv": design_df,
            "kpis.csv": kpi_df,
        },
    )
