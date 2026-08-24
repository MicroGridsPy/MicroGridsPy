from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import linopy as lp
import numpy as np
import pandas as pd
import xarray as xr

from microgridspy.export.common import (
    ensure_results_dir,
    get_var_solution,
    require_data_array,
    safe_float,
    write_csv_outputs,
)
from microgridspy.export.typical_year_reporting import (
    build_energy_balance_table as build_reporting_energy_balance_table,
)
from microgridspy.export.typical_year_reporting import build_reporting_tables
from microgridspy.typical_year_model.params import get_params


@dataclass
class TypicalYearResults:
    project_name: str
    data: xr.Dataset
    metadata: dict[str, Any]
    dispatch: pd.DataFrame
    energy_balance: pd.DataFrame
    design_summary: pd.DataFrame
    kpis: pd.DataFrame
    upfront: pd.DataFrame
    expected_cost_components: pd.DataFrame
    expected_fixed_om: pd.DataFrame
    annuities: pd.DataFrame
    embodied: pd.DataFrame
    scenario_variable_costs: pd.DataFrame
    scenario_emissions: pd.DataFrame
    scenario_total_operating_costs: pd.DataFrame
    renewable_design: pd.DataFrame
    battery_design: pd.DataFrame
    generator_design: pd.DataFrame
    renewable_inverter_design: pd.DataFrame
    battery_inverter_design: pd.DataFrame
    inverter_metrics: pd.DataFrame
    results_dir: Path | None = None
    source: str = "session"

    def to_excel(self, out_dir: Path | None = None) -> dict:
        """Write these results to CSV/Excel files.

        Args:
            out_dir: destination directory; defaults to the project's ``results/``.

        Returns:
            dict: mapping of output name to the written file path.
        """
        return export_typical_year_results_package(results=self, out_dir=out_dir)


def build_dispatch_timeseries_table(
    *,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
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
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> pd.DataFrame:
    p = get_params(data)
    res_units = require_data_array("res_units", get_var_solution(vars_dict=vars, solution=solution, name="res_units", prefer_solution_dataset=False))
    bat_units = require_data_array("battery_units", get_var_solution(vars_dict=vars, solution=solution, name="battery_units", prefer_solution_dataset=False))
    bat_inv_units_raw = get_var_solution(vars_dict=vars, solution=solution, name="battery_inverter_units", prefer_solution_dataset=False)
    if isinstance(bat_inv_units_raw, xr.DataArray):
        bat_inv_units = require_data_array("battery_inverter_units", bat_inv_units_raw)
    else:
        legacy_bat_inv_power = get_var_solution(vars_dict=vars, solution=solution, name="battery_inverter_power", prefer_solution_dataset=False)
        if isinstance(legacy_bat_inv_power, xr.DataArray):
            bat_inv_units = require_data_array("battery_inverter_power", legacy_bat_inv_power)
        else:
            bat_inv_units = xr.DataArray(0.0, name="battery_inverter_units")
    gen_units = require_data_array("generator_units", get_var_solution(vars_dict=vars, solution=solution, name="generator_units", prefer_solution_dataset=False))

    res_cap = res_units * p.res_nominal_capacity_kw
    res_inv_cap = res_cap / p.res_dc_ac_ratio
    bat_cap = bat_units * p.battery_nominal_capacity_kwh
    bat_inv_power = bat_inv_units * p.battery_inverter_nominal_power_kw
    gen_cap = gen_units * p.generator_nominal_capacity_kw

    row: dict[str, Any] = {
        "battery_units": safe_float(bat_units),
        "battery_inverter_units": safe_float(bat_inv_units),
        "battery_installed_kwh": safe_float(bat_cap),
        "battery_inverter_power_kw": safe_float(bat_inv_power),
        "generator_units": safe_float(gen_units),
        "generator_installed_kw": safe_float(gen_cap),
        "res_units_total": safe_float(res_units.sum("resource")),
        "res_installed_kw_total": safe_float(res_cap.sum("resource")),
        "res_inverter_installed_kw_ac_total": safe_float(res_inv_cap.sum("resource")),
    }
    for r in res_units.coords["resource"].values:
        label = str(r)
        row[f"res_units__{label}"] = safe_float(res_units.sel(resource=r))
        row[f"res_installed_kw__{label}"] = safe_float(res_cap.sel(resource=r))
        row[f"res_inverter_installed_kw_ac__{label}"] = safe_float(res_inv_cap.sel(resource=r))
    return pd.DataFrame([row])


def build_structured_design_tables(
    *,
    data: xr.Dataset,
    design_summary_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    row = design_summary_df.iloc[0] if not design_summary_df.empty else pd.Series(dtype=float)
    resources = [str(r) for r in data.coords["resource"].values.tolist()] if "resource" in data.coords else []

    renewable_rows = []
    renewable_inverter_rows = []
    for resource in resources:
        renewable_dc_kw = float(pd.to_numeric(pd.Series([row.get(f"res_installed_kw__{resource}", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
        renewable_units = float(pd.to_numeric(pd.Series([row.get(f"res_units__{resource}", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
        inverter_ac_kw = float(pd.to_numeric(pd.Series([row.get(f"res_inverter_installed_kw_ac__{resource}", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
        dc_ac_ratio = float(safe_float(data["res_dc_ac_ratio"].sel(resource=resource))) if "res_dc_ac_ratio" in data else float("nan")
        inverter_efficiency = float(safe_float(data["res_inverter_efficiency"].sel(resource=resource))) if "res_inverter_efficiency" in data else float("nan")
        renewable_rows.append(
            {
                "Resource": resource,
                "Installed units": renewable_units,
                "Installed DC capacity [kW]": renewable_dc_kw,
                "DC/AC ratio": dc_ac_ratio,
                "Inverter efficiency": inverter_efficiency,
            }
        )
        renewable_inverter_rows.append(
            {
                "Resource": resource,
                "Installed DC capacity [kW]": renewable_dc_kw,
                "Installed inverter AC capacity [kW_ac]": inverter_ac_kw,
                "Effective AC exportable renewable capacity [kW_ac]": inverter_ac_kw,
                "DC/AC ratio": dc_ac_ratio,
                "Inverter efficiency": inverter_efficiency,
            }
        )

    battery_units = float(pd.to_numeric(pd.Series([row.get("battery_units", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    battery_inverter_units = float(pd.to_numeric(pd.Series([row.get("battery_inverter_units", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    battery_kwh = float(pd.to_numeric(pd.Series([row.get("battery_installed_kwh", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    battery_inv_kw = float(pd.to_numeric(pd.Series([row.get("battery_inverter_power_kw", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    battery_inv_nom_kw = float(safe_float(data["battery_inverter_nominal_power_kw"])) if "battery_inverter_nominal_power_kw" in data else float("nan")
    generator_units = float(pd.to_numeric(pd.Series([row.get("generator_units", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    generator_kw = float(pd.to_numeric(pd.Series([row.get("generator_installed_kw", 0.0)]), errors="coerce").fillna(0.0).iloc[0])

    return {
        "renewable_design": pd.DataFrame(renewable_rows),
        "battery_design": pd.DataFrame(
            [
                {
                    "Component": "Battery",
                    "Installed units": battery_units,
                    "Installed energy capacity [kWh]": battery_kwh,
                }
            ]
        ),
        "generator_design": pd.DataFrame(
            [
                {
                    "Component": "Generator",
                    "Installed units": generator_units,
                    "Installed capacity [kW]": generator_kw,
                }
            ]
        ),
        "renewable_inverter_design": pd.DataFrame(renewable_inverter_rows),
        "battery_inverter_design": pd.DataFrame(
            [
                {
                    "Component": "Battery inverter",
                    "Installed inverter units": battery_inverter_units,
                    "Nominal inverter power per unit [kW]": battery_inv_nom_kw,
                    "Installed inverter power [kW]": battery_inv_kw,
                }
            ]
        ),
    }


def build_inverter_metrics_table(
    *,
    data: xr.Dataset,
    dispatch_df: pd.DataFrame,
    renewable_inverter_design_df: pd.DataFrame,
    battery_inverter_design_df: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    dispatch = dispatch_df.copy()
    if "scenario" in dispatch.columns:
        dispatch["scenario"] = dispatch["scenario"].astype(str)

    if not renewable_inverter_design_df.empty:
        scenarios = [str(s) for s in data.coords["scenario"].values.tolist()] if "scenario" in data.coords else []
        for _, resource_row in renewable_inverter_design_df.iterrows():
            resource = str(resource_row["Resource"])
            inverter_ac_kw = float(pd.to_numeric(pd.Series([resource_row.get("Installed inverter AC capacity [kW_ac]", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
            col = f"res_generation__{resource}"
            max_dispatch = float(pd.to_numeric(dispatch[col], errors="coerce").fillna(0.0).max()) if col in dispatch.columns else 0.0
            pre_inverter_potential = 0.0
            effective_potential = 0.0
            if {"resource_availability", "res_inverter_efficiency"}.issubset(set(data.data_vars)):
                installed_dc_kw = float(pd.to_numeric(pd.Series([resource_row.get("Installed DC capacity [kW]", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
                inverter_efficiency = float(safe_float(data["res_inverter_efficiency"].sel(resource=resource)))
                for scenario in scenarios:
                    availability = np.asarray(data["resource_availability"].sel(scenario=scenario, resource=resource).values, dtype=float)
                    scenario_pre = availability * installed_dc_kw * inverter_efficiency
                    pre_inverter_potential += float(np.sum(scenario_pre))
                    effective_potential += float(np.sum(np.minimum(scenario_pre, inverter_ac_kw)))
            rows.append(
                {
                    "Component": f"{resource} inverter",
                    "Installed inverter AC capacity [kW_ac]": inverter_ac_kw,
                    "Peak dispatched renewable output [kW_ac]": max_dispatch,
                    "Peak utilization [%]": 100.0 * safe_float(max_dispatch / inverter_ac_kw) if inverter_ac_kw > 1e-12 else 0.0,
                    "Pre-inverter renewable AC-equivalent potential [kWh]": pre_inverter_potential,
                    "Effective inverter-limited renewable potential [kWh]": effective_potential,
                    "Inverter clipping potential [kWh]": max(pre_inverter_potential - effective_potential, 0.0),
                }
            )

    if not battery_inverter_design_df.empty:
        battery_inv_kw = float(pd.to_numeric(pd.Series([battery_inverter_design_df.iloc[0].get("Installed inverter power [kW]", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
        max_charge = float(pd.to_numeric(dispatch.get("battery_charge", pd.Series(dtype=float)), errors="coerce").fillna(0.0).max()) if "battery_charge" in dispatch.columns else 0.0
        max_discharge = float(pd.to_numeric(dispatch.get("battery_discharge", pd.Series(dtype=float)), errors="coerce").fillna(0.0).max()) if "battery_discharge" in dispatch.columns else 0.0
        rows.append(
            {
                "Component": "Battery inverter",
                "Installed inverter AC capacity [kW_ac]": battery_inv_kw,
                "Peak dispatched renewable output [kW_ac]": np.nan,
                "Peak utilization [%]": 100.0 * safe_float(max(max_charge, max_discharge) / battery_inv_kw) if battery_inv_kw > 1e-12 else 0.0,
                "Pre-inverter renewable AC-equivalent potential [kWh]": np.nan,
                "Effective inverter-limited renewable potential [kWh]": np.nan,
                "Inverter clipping potential [kWh]": np.nan,
            }
        )

    return pd.DataFrame(rows)


def build_typical_year_results(
    *,
    project_name: str,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
    objective_value: float | None,
    status: str | None = None,
    solver: str | None = None,
    results_dir: Path | None = None,
    source: str = "session",
) -> TypicalYearResults:
    dispatch_df = build_dispatch_timeseries_table(data=data, vars=vars, solution=solution)
    energy_df = build_energy_balance_table(data=data, dispatch_df=dispatch_df)
    design_df = build_design_summary_table(data=data, vars=vars, solution=solution)
    reporting = build_reporting_tables(
        data=data,
        dispatch_df=dispatch_df,
        design_df=design_df,
        solver_objective_value=objective_value,
    )
    structured_design = build_structured_design_tables(data=data, design_summary_df=design_df)
    inverter_metrics = build_inverter_metrics_table(
        data=data,
        dispatch_df=dispatch_df,
        renewable_inverter_design_df=structured_design["renewable_inverter_design"],
        battery_inverter_design_df=structured_design["battery_inverter_design"],
    )
    metadata = {
        "project_name": project_name,
        "formulation": "steady_state",
        "solver": solver,
        "status": status,
        "objective_value": objective_value,
    }
    return TypicalYearResults(
        project_name=project_name,
        data=data,
        metadata=metadata,
        dispatch=dispatch_df,
        energy_balance=energy_df,
        design_summary=design_df,
        kpis=reporting.kpis,
        upfront=reporting.upfront,
        expected_cost_components=reporting.expected_cost_components,
        expected_fixed_om=reporting.expected_fixed_om,
        annuities=reporting.annuities,
        embodied=reporting.embodied,
        scenario_variable_costs=reporting.scenario_variable_costs,
        scenario_emissions=reporting.scenario_emissions,
        scenario_total_operating_costs=reporting.scenario_total_operating_costs,
        renewable_design=structured_design["renewable_design"],
        battery_design=structured_design["battery_design"],
        generator_design=structured_design["generator_design"],
        renewable_inverter_design=structured_design["renewable_inverter_design"],
        battery_inverter_design=structured_design["battery_inverter_design"],
        inverter_metrics=inverter_metrics,
        results_dir=results_dir,
        source=source,
    )


def build_typical_year_results_from_tables(
    *,
    project_name: str,
    data: xr.Dataset,
    dispatch_df: pd.DataFrame,
    energy_balance_df: pd.DataFrame,
    design_summary_df: pd.DataFrame,
    kpis_df: pd.DataFrame,
    upfront_df: pd.DataFrame | None = None,
    expected_cost_components_df: pd.DataFrame | None = None,
    expected_fixed_om_df: pd.DataFrame | None = None,
    annuities_df: pd.DataFrame | None = None,
    embodied_df: pd.DataFrame | None = None,
    scenario_variable_costs_df: pd.DataFrame | None = None,
    scenario_emissions_df: pd.DataFrame | None = None,
    scenario_total_operating_costs_df: pd.DataFrame | None = None,
    results_dir: Path | None = None,
    source: str = "files",
) -> TypicalYearResults:
    raw_expected = kpis_df[kpis_df["scenario"].astype(str).str.lower() == "expected"] if "scenario" in kpis_df.columns else pd.DataFrame()
    objective_value = float(safe_float(raw_expected.iloc[0].get("objective_value", np.nan))) if not raw_expected.empty else float("nan")
    reporting = build_reporting_tables(
        data=data,
        dispatch_df=dispatch_df,
        design_df=design_summary_df,
        solver_objective_value=objective_value,
    )
    structured_design = build_structured_design_tables(data=data, design_summary_df=design_summary_df)
    inverter_metrics = build_inverter_metrics_table(
        data=data,
        dispatch_df=dispatch_df,
        renewable_inverter_design_df=structured_design["renewable_inverter_design"],
        battery_inverter_design_df=structured_design["battery_inverter_design"],
    )
    return TypicalYearResults(
        project_name=project_name,
        data=data,
        metadata={
            "project_name": project_name,
            "formulation": "steady_state",
            "solver": None,
            "status": None,
            "objective_value": objective_value,
        },
        dispatch=dispatch_df,
        energy_balance=energy_balance_df,
        design_summary=design_summary_df,
        kpis=kpis_df,
        upfront=upfront_df if upfront_df is not None else reporting.upfront,
        expected_cost_components=expected_cost_components_df if expected_cost_components_df is not None else reporting.expected_cost_components,
        expected_fixed_om=expected_fixed_om_df if expected_fixed_om_df is not None else reporting.expected_fixed_om,
        annuities=annuities_df if annuities_df is not None else reporting.annuities,
        embodied=embodied_df if embodied_df is not None else reporting.embodied,
        scenario_variable_costs=scenario_variable_costs_df if scenario_variable_costs_df is not None else reporting.scenario_variable_costs,
        scenario_emissions=scenario_emissions_df if scenario_emissions_df is not None else reporting.scenario_emissions,
        scenario_total_operating_costs=scenario_total_operating_costs_df if scenario_total_operating_costs_df is not None else reporting.scenario_total_operating_costs,
        renewable_design=structured_design["renewable_design"],
        battery_design=structured_design["battery_design"],
        generator_design=structured_design["generator_design"],
        renewable_inverter_design=structured_design["renewable_inverter_design"],
        battery_inverter_design=structured_design["battery_inverter_design"],
        inverter_metrics=inverter_metrics,
        results_dir=results_dir,
        source=source,
    )


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
    vars: dict[str, Any],
    solution: xr.Dataset | None,
    objective_value: float | None,
) -> pd.DataFrame:
    dispatch = build_dispatch_timeseries_table(data=data, vars=vars, solution=solution)
    design = build_design_summary_table(data=data, vars=vars, solution=solution)
    return build_reporting_tables(
        data=data,
        dispatch_df=dispatch,
        design_df=design,
        solver_objective_value=objective_value,
    ).kpis


def build_summary_metrics_table(reporting) -> pd.DataFrame:
    kpis = reporting.kpis.copy()
    kpis["scenario"] = kpis["scenario"].astype(str)
    expected = kpis[kpis["scenario"].str.lower() == "expected"]
    expected_row = expected.iloc[0] if not expected.empty else pd.Series(dtype=float)

    total_annual_cost_exp = float(safe_float(expected_row.get("reported_total_annual_cost", np.nan)))
    delivered_kwh = float(safe_float(expected_row.get("served_energy_kwh", np.nan)))
    lcoe = total_annual_cost_exp / delivered_kwh if delivered_kwh > 1e-9 and np.isfinite(total_annual_cost_exp) else float("nan")
    total_upfront_gross_k = (
        float(pd.to_numeric(reporting.upfront["Upfront gross [thousand]"], errors="coerce").fillna(0.0).sum())
        if not reporting.upfront.empty
        else 0.0
    )
    total_upfront_net_k = (
        float(pd.to_numeric(reporting.upfront["Upfront net [thousand]"], errors="coerce").fillna(0.0).sum())
        if not reporting.upfront.empty
        else 0.0
    )
    embodied_cost_exp = (
        float(pd.to_numeric(reporting.embodied["Embodied Cost [/yr]"], errors="coerce").fillna(0.0).sum())
        if not reporting.embodied.empty
        else 0.0
    )
    scope3_kg_exp = float(safe_float(expected_row.get("scope3_emissions_kgco2e", 0.0)))

    return pd.DataFrame(
        [
            {"Metric": "Total Annualized Cost (Expected)", "Value": total_annual_cost_exp, "Unit": "/yr"},
            {"Metric": "LCOE (Expected, delivered)", "Value": lcoe, "Unit": "/kWh"},
            {"Metric": "Upfront investment gross", "Value": total_upfront_gross_k, "Unit": "thousand"},
            {"Metric": "Upfront investment net", "Value": total_upfront_net_k, "Unit": "thousand"},
            {"Metric": "Embodied emissions (Expected)", "Value": scope3_kg_exp, "Unit": "kgCO2e/yr"},
            {"Metric": "Embodied externality cost (Expected)", "Value": embodied_cost_exp, "Unit": "/yr"},
        ]
    )


def energy_balance_residual_summary(energy_balance_df: pd.DataFrame) -> pd.DataFrame:
    g = energy_balance_df.groupby("scenario", as_index=False)["balance_residual"].agg(
        max_abs_balance_residual=lambda x: float(np.max(np.abs(np.asarray(x, dtype=float))))
    )
    return g


def export_typical_year_results(
    project_name: str,
    sets: xr.Dataset,
    data: xr.Dataset,
    model: lp.Model | None,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
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
    reporting = build_reporting_tables(
        data=data,
        dispatch_df=dispatch_df,
        design_df=design_df,
        solver_objective_value=objective_value,
    )
    kpi_df = reporting.kpis
    summary_metrics_df = build_summary_metrics_table(reporting)
    structured_design = build_structured_design_tables(data=data, design_summary_df=design_df)
    inverter_metrics_df = build_inverter_metrics_table(
        data=data,
        dispatch_df=dispatch_df,
        renewable_inverter_design_df=structured_design["renewable_inverter_design"],
        battery_inverter_design_df=structured_design["battery_inverter_design"],
    )

    return write_csv_outputs(
        out_dir,
        {
            "dispatch_timeseries.csv": dispatch_df,
            "energy_balance.csv": energy_df,
            "design_summary.csv": design_df,
            "kpis.csv": kpi_df,
            "summary_metrics.csv": summary_metrics_df,
            "renewable_design.csv": structured_design["renewable_design"],
            "battery_design.csv": structured_design["battery_design"],
            "generator_design.csv": structured_design["generator_design"],
            "renewable_inverter_design.csv": structured_design["renewable_inverter_design"],
            "battery_inverter_design.csv": structured_design["battery_inverter_design"],
            "inverter_metrics.csv": inverter_metrics_df,
            "upfront_investment.csv": reporting.upfront,
            "expected_cost_components.csv": reporting.expected_cost_components,
            "expected_fixed_om.csv": reporting.expected_fixed_om,
            "annuities.csv": reporting.annuities,
            "embodied_externalities.csv": reporting.embodied,
            "scenario_variable_costs.csv": reporting.scenario_variable_costs,
            "scenario_emissions.csv": reporting.scenario_emissions,
            "scenario_total_operating_costs.csv": reporting.scenario_total_operating_costs,
        },
    )


def export_typical_year_results_package(
    *,
    results: TypicalYearResults,
    out_dir: Path | None = None,
) -> dict:
    if out_dir is None:
        out_dir = ensure_results_dir(results.project_name, suffix="typical_year")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    reporting_proxy = type(
        "TypicalYearReportingProxy",
        (),
        {
            "kpis": results.kpis,
            "upfront": results.upfront,
            "embodied": results.embodied,
        },
    )()
    summary_metrics_df = build_summary_metrics_table(reporting_proxy)

    return write_csv_outputs(
        out_dir,
        {
            "dispatch_timeseries.csv": results.dispatch,
            "energy_balance.csv": results.energy_balance,
            "design_summary.csv": results.design_summary,
            "kpis.csv": results.kpis,
            "summary_metrics.csv": summary_metrics_df,
            "renewable_design.csv": results.renewable_design,
            "battery_design.csv": results.battery_design,
            "generator_design.csv": results.generator_design,
            "renewable_inverter_design.csv": results.renewable_inverter_design,
            "battery_inverter_design.csv": results.battery_inverter_design,
            "inverter_metrics.csv": results.inverter_metrics,
            "upfront_investment.csv": results.upfront,
            "expected_cost_components.csv": results.expected_cost_components,
            "expected_fixed_om.csv": results.expected_fixed_om,
            "annuities.csv": results.annuities,
            "embodied_externalities.csv": results.embodied,
            "scenario_variable_costs.csv": results.scenario_variable_costs,
            "scenario_emissions.csv": results.scenario_emissions,
            "scenario_total_operating_costs.csv": results.scenario_total_operating_costs,
        },
    )
