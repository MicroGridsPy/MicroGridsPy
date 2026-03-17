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
from core.typical_year_model.params import get_params

def _sel_scenario_or_self(x: Any, scenario: str) -> Any:
    if isinstance(x, xr.DataArray) and "scenario" in x.dims:
        return x.sel(scenario=scenario)
    return x


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
                "grid_import": gimp.sel(scenario=s).values.astype(float) if isinstance(gimp, xr.DataArray) else 0.0,
                "grid_export": gexp.sel(scenario=s).values.astype(float) if isinstance(gexp, xr.DataArray) else 0.0,
            }
        )
        for r in res.coords["resource"].values:
            d[f"res_generation__{str(r)}"] = res.sel(scenario=s, resource=r).values.astype(float)
        records.append(d)

    return pd.concat(records, ignore_index=True)


def build_energy_balance_table(dispatch_df: pd.DataFrame) -> pd.DataFrame:
    """
    Sign convention:
    - Positive terms: renewable, generator, grid_import, battery_discharge, lost_load.
    - Negative sinks: battery_charge, grid_export.
    - balance_lhs = positives - sinks.
    - balance_residual = balance_lhs - demand.
    """
    df = dispatch_df.copy()
    df["supply_renewable"] = df["res_generation_total"]
    df["supply_generator"] = df["generator_generation"]
    df["supply_grid_import"] = df["grid_import"]
    df["supply_battery_discharge"] = df["battery_discharge"]
    df["supply_lost_load"] = df["lost_load"]
    df["sink_battery_charge"] = df["battery_charge"]
    df["sink_grid_export"] = df["grid_export"]
    df["demand"] = df["load_demand"]
    df["balance_lhs"] = (
        df["supply_renewable"]
        + df["supply_generator"]
        + df["supply_grid_import"]
        + df["supply_battery_discharge"]
        + df["supply_lost_load"]
        - df["sink_battery_charge"]
        - df["sink_grid_export"]
    )
    df["balance_residual"] = df["balance_lhs"] - df["demand"]
    cols = [
        "period",
        "scenario",
        "demand",
        "supply_renewable",
        "supply_generator",
        "supply_grid_import",
        "supply_battery_discharge",
        "supply_lost_load",
        "sink_battery_charge",
        "sink_grid_export",
        "balance_lhs",
        "balance_residual",
    ]
    return df[cols]


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
    p = get_params(data)
    w_s = p.scenario_weight

    dispatch = build_dispatch_timeseries_table(data=data, vars=vars, solution=solution)
    scen_labels = [str(s) for s in p.load_demand.coords["scenario"].values]

    res_units = require_data_array("res_units", get_var_solution(vars_dict=vars, solution=solution, name="res_units", prefer_solution_dataset=False))
    bat_units = require_data_array("battery_units", get_var_solution(vars_dict=vars, solution=solution, name="battery_units", prefer_solution_dataset=False))
    gen_units = require_data_array("generator_units", get_var_solution(vars_dict=vars, solution=solution, name="generator_units", prefer_solution_dataset=False))
    fuel_cons = get_var_solution(vars_dict=vars, solution=solution, name="fuel_consumption", prefer_solution_dataset=False)

    cap_res_kw = res_units * p.res_nominal_capacity_kw
    cap_bat_kwh = bat_units * p.battery_nominal_capacity_kwh
    cap_gen_kw = gen_units * p.generator_nominal_capacity_kw

    crf_res = xr.DataArray(
        [_crf(float(r), float(n)) for r, n in zip(p.res_wacc.values.tolist(), p.res_lifetime_years.values.tolist())],
        dims=("resource",),
        coords={"resource": p.res_wacc.coords["resource"]},
    )
    ann_res = (crf_res * (1.0 - p.res_grant_share_of_capex) * p.res_specific_investment_cost_per_kw * cap_res_kw).sum("resource")
    ann_bat = _crf(safe_float(p.battery_wacc), safe_float(p.battery_calendar_lifetime_years)) * safe_float(p.battery_specific_investment_cost_per_kwh * cap_bat_kwh)
    ann_gen = _crf(safe_float(p.generator_wacc), safe_float(p.generator_lifetime_years)) * safe_float(p.generator_specific_investment_cost_per_kw * cap_gen_kw)
    annuity = safe_float(ann_res) + ann_bat + ann_gen

    rows = []
    for s in scen_labels:
        df_s = dispatch[dispatch["scenario"] == s]
        total_demand = float(df_s["load_demand"].sum())
        lost_load = float(df_s["lost_load"].sum())
        served = total_demand - lost_load
        total_res = float(df_s["res_generation_total"].sum())
        grid_eta = float(p.grid_transmission_efficiency.sel(scenario=s)) if p.grid_transmission_efficiency is not None else 1.0
        grid_ren_share = float(p.grid_renewable_share.sel(scenario=s)) if p.grid_renewable_share is not None else 0.0
        grid_delivered = float(df_s["grid_import"].sum()) * grid_eta
        grid_renewable = grid_delivered * grid_ren_share
        ren_denom = total_res + float(df_s["generator_generation"].sum()) + grid_delivered
        ren_num = total_res + grid_renewable
        ren_pen = (ren_num / ren_denom) if ren_denom > 0 else 0.0
        ll_frac = (lost_load / total_demand) if total_demand > 0 else 0.0

        fuel = float(fuel_cons.sel(scenario=s).sum("period")) if isinstance(fuel_cons, xr.DataArray) else 0.0
        scope1_emissions = fuel * float(_sel_scenario_or_self(p.fuel_direct_emissions_kgco2e_per_unit_fuel, s))
        grid_em_factor = (
            float(_sel_scenario_or_self(p.grid_emissions_factor_kgco2e_per_kwh, s))
            if p.grid_emissions_factor_kgco2e_per_kwh is not None
            else 0.0
        )
        scope2_emissions = grid_delivered * grid_em_factor
        res_emb = _sel_scenario_or_self(p.res_embedded_emissions_kgco2e_per_kw, s)
        gen_emb = _sel_scenario_or_self(p.generator_embedded_emissions_kgco2e_per_kw, s)
        bat_emb = _sel_scenario_or_self(p.battery_embedded_emissions_kgco2e_per_kwh, s)
        scope3_emissions = (
            float(((cap_res_kw * res_emb) / p.res_lifetime_years).sum("resource"))
            + float((cap_gen_kw * gen_emb) / p.generator_lifetime_years)
            + float((cap_bat_kwh * bat_emb) / p.battery_calendar_lifetime_years)
        )
        total_emissions = scope1_emissions + scope2_emissions + scope3_emissions

        fuel_cost = fuel * float(_sel_scenario_or_self(p.fuel_fuel_cost_per_unit_fuel, s))
        grid_cost = 0.0
        if p.grid_import_price is not None and "scenario" in p.grid_import_price.dims:
            imp_price = p.grid_import_price.sel(scenario=s).values.astype(float)
            grid_cost += float((df_s["grid_import"].to_numpy(dtype=float) * imp_price).sum())
        if p.grid_export_price is not None and "scenario" in p.grid_export_price.dims:
            exp_price = p.grid_export_price.sel(scenario=s).values.astype(float)
            grid_cost -= float((df_s["grid_export"].to_numpy(dtype=float) * exp_price).sum())
        ll_cost = lost_load * float(_sel_scenario_or_self(p.lost_load_cost_per_kwh, s))
        em_cost = total_emissions * float(_sel_scenario_or_self(p.emission_cost_per_kgco2e, s))

        rows.append(
            {
                "scenario": s,
                "total_demand_kwh": total_demand,
                "served_energy_kwh": served,
                "lost_load_kwh": lost_load,
                "lost_load_fraction": ll_frac,
                "total_res_kwh": total_res,
                "grid_renewable_kwh": grid_renewable,
                "renewable_penetration": ren_pen,
                "fuel_consumption": fuel,
                "scope1_emissions_kgco2e": scope1_emissions,
                "scope2_emissions_kgco2e": scope2_emissions,
                "scope3_emissions_kgco2e": scope3_emissions,
                "emissions_kgco2e": total_emissions,
                "investment_annuity_cost": annuity,
                "fuel_cost": fuel_cost,
                "grid_net_cost": grid_cost,
                "lost_load_cost": ll_cost,
                "emissions_cost": em_cost,
                "objective_value": safe_float(objective_value),
            }
        )

    kpis = pd.DataFrame(rows)
    w_map = {str(s): float(w_s.sel(scenario=s)) for s in w_s.coords["scenario"].values}
    kpis["weight"] = kpis["scenario"].map(w_map).fillna(0.0)

    num_cols = [c for c in kpis.columns if c not in ("scenario",)]
    expected = {"scenario": "expected"}
    for c in num_cols:
        expected[c] = float((kpis[c] * kpis["weight"]).sum()) if c != "objective_value" else safe_float(objective_value)
    return pd.concat([kpis.drop(columns=["weight"]), pd.DataFrame([expected])], ignore_index=True)


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
    energy_df = build_energy_balance_table(dispatch_df)
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
