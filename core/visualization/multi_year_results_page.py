from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import xarray as xr

from core.export.common import get_var_solution, require_data_array, safe_float
from core.export.results_page_helpers import MultiYearFileResults, export_results_from_bundle
from core.export.multi_year_results import (
    build_design_by_step_table_multi_year,
    build_discounted_cashflows_table_multi_year,
    build_dispatch_timeseries_table_multi_year,
    build_yearly_kpis_table_multi_year,
)
from core.export.results_bundle import ResultsBundle
from core.multi_year_model.lifecycle import inv_step_start_ordinal, replacement_active_mask, replacement_commission_mask
from core.multi_year_model.params import get_params


C_RES = "#FFD700"
C_BAT = "#00ACC1"
C_GEN = "#546E7A"
C_IMP = "#9C27B0"
C_EXP = "#9C27B0"
C_LL = "#E53935"
C_LOAD = "#111111"


@dataclass(frozen=True)
class MultiYearResultsContext:
    bundle: ResultsBundle
    data: xr.Dataset
    sets: xr.Dataset
    settings: Dict[str, Any]
    vars_dict: Dict[str, Any]
    solution: Optional[xr.Dataset]
    dispatch: pd.DataFrame
    design: pd.DataFrame
    kpis: pd.DataFrame
    cash: pd.DataFrame
    capacity_by_year: pd.DataFrame
    yearly_expected: pd.DataFrame
    scenario_costs: pd.DataFrame
    investment_summary: pd.DataFrame
    on_grid: bool
    allow_export: bool
    years: list[str]
    scenarios: list[str]
    file_backed: bool = False
    results_dir: Optional[str] = None


def _get_settings(data: xr.Dataset) -> Dict[str, Any]:
    settings = (data.attrs or {}).get("settings", {})
    return settings if isinstance(settings, dict) else {}


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if abs(float(denominator)) > 1e-12 else 0.0


def _days_to_slice(T: int, start_day: int, ndays: int) -> Tuple[slice, int]:
    ndays = int(np.clip(ndays, 1, 7))
    max_day = max(1, int(np.ceil(T / 24)))
    start_day = int(np.clip(start_day, 1, max_day))
    window = ndays * 24
    i0 = (start_day - 1) * 24
    i1 = min(T, i0 + window)
    return slice(i0, i1), i1 - i0


def _scenario_options(settings: Dict[str, Any], data: xr.Dataset) -> list[str]:
    ms_enabled = bool(((settings.get("multi_scenario", {}) or {}).get("enabled", False)))
    scen_labels = [str(s) for s in data.coords["scenario"].values.tolist()]
    return scen_labels if not ms_enabled else ["Expected"] + scen_labels


def _build_expected_dispatch(view: pd.DataFrame, weights: Optional[xr.DataArray]) -> pd.DataFrame:
    if not isinstance(weights, xr.DataArray):
        return view.groupby("period", as_index=False).mean(numeric_only=True)
    w_map = {str(s): float(weights.sel(scenario=s)) for s in weights.coords["scenario"].values}
    weighted = view.copy()
    weighted["weight"] = weighted["scenario"].astype(str).map(w_map).fillna(0.0)
    agg_cols = [
        "load_demand",
        "res_generation_total",
        "generator_generation",
        "battery_charge",
        "battery_discharge",
        "lost_load",
        "grid_import",
        "grid_export",
    ]
    for col in agg_cols:
        weighted[f"weighted__{col}"] = weighted[col] * weighted["weight"]
    grouped = weighted.groupby("period", as_index=False)[[f"weighted__{col}" for col in agg_cols]].sum()
    grouped.columns = ["period"] + agg_cols
    return grouped


def _window_dispatch_profile(view: pd.DataFrame, *, start_day: int, ndays: int) -> pd.DataFrame:
    ordered = view.sort_values("period").reset_index(drop=True)
    idx, window = _days_to_slice(len(ordered), start_day=start_day, ndays=ndays)
    window_df = ordered.iloc[idx].copy().reset_index(drop=True)
    if window <= 0:
        return pd.DataFrame()
    start_hour = (start_day - 1) * 24 + 1
    window_df["window_hour"] = np.arange(start_hour, start_hour + len(window_df))
    return window_df


def _plot_dispatch_stack(*, ax: Any, profile: pd.DataFrame, title_suffix: str) -> None:
    x = profile["window_hour"].to_numpy(dtype=float)
    y_res = profile["res_generation_total"].to_numpy(dtype=float)
    y_bdis = profile["battery_discharge"].to_numpy(dtype=float)
    y_gen = profile["generator_generation"].to_numpy(dtype=float)
    y_gimp = profile["grid_import"].to_numpy(dtype=float)
    y_ll = profile["lost_load"].to_numpy(dtype=float)
    y_bch = profile["battery_charge"].to_numpy(dtype=float)
    y_gexp = profile["grid_export"].to_numpy(dtype=float)
    y_load = profile["load_demand"].to_numpy(dtype=float)

    p1 = y_res
    p2 = p1 + y_bdis
    p3 = p2 + y_gen
    p4 = p3 + y_gimp
    p5 = p4 + y_ll
    n1 = -y_bch
    n2 = n1 - y_gexp

    ax.fill_between(x, 0, p1, color=C_RES, alpha=0.85, label="Renewables")
    ax.fill_between(x, p1, p2, color=C_BAT, alpha=0.35, label="Battery discharge")
    ax.fill_between(x, p2, p3, color=C_GEN, alpha=0.85, label="Generator")
    if np.any(y_gimp > 0):
        ax.fill_between(x, p3, p4, color=C_IMP, alpha=0.85, label="Grid import")
    if np.any(y_ll > 0):
        ax.fill_between(x, p4, p5, color=C_LL, alpha=0.45, label="Lost load")
    if np.any(y_bch > 0):
        ax.fill_between(x, 0, n1, color=C_BAT, alpha=0.35, label="Battery charge")
    if np.any(y_gexp > 0):
        ax.fill_between(x, n1, n2, color=C_EXP, alpha=0.75, label="Grid export")

    ax.plot(x, y_load, color=C_LOAD, linewidth=1.8, label="Load")
    ax.set_title(f"Dispatch profile - {title_suffix}")
    ax.set_xlabel("Hour of selected window")
    ax.set_ylabel("kWh per hour (approx. kW)")
    ax.grid(True, alpha=0.25, linestyle=":")
    ax.legend(ncols=4, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.22))


def _as_year_scenario_da(x: Any, sets: xr.Dataset) -> xr.DataArray:
    year = sets.coords["year"]
    scenario = sets.coords["scenario"]
    if isinstance(x, xr.DataArray):
        da = x
    else:
        da = xr.DataArray(float(safe_float(x)))
    if "year" not in da.dims:
        da = da.expand_dims(year=year)
    else:
        da = da.sel(year=year)
    if "scenario" not in da.dims:
        da = da.expand_dims(scenario=scenario)
    else:
        da = da.sel(scenario=scenario)
    ordered_dims = ["year", "scenario"] + [dim for dim in da.dims if dim not in {"year", "scenario"}]
    return da.transpose(*ordered_dims)


def _weights_da(data: xr.Dataset) -> xr.DataArray:
    scenario = data.coords["scenario"]
    if "scenario_weight" in data:
        return data["scenario_weight"].sel(scenario=scenario)
    n = int(scenario.size)
    return xr.DataArray(
        np.full((n,), 1.0 / max(n, 1), dtype=float),
        dims=("scenario",),
        coords={"scenario": scenario},
    )


def _capacity_by_year(sets_ds: xr.Dataset, design_df: pd.DataFrame) -> pd.DataFrame:
    years = [str(y) for y in sets_ds.coords["year"].values.tolist()]
    rows = []
    for year in years:
        active = design_df[design_df["inv_step_start_year"].astype(str) <= year].copy()
        rows.append(
            {
                "year": year,
                "renewables_kw": float(active.loc[active["technology"] == "renewable", "installed_capacity"].sum()),
                "battery_kwh": float(active.loc[active["technology"] == "battery", "installed_capacity"].sum()),
                "generator_kw": float(active.loc[active["technology"] == "generator", "installed_capacity"].sum()),
            }
        )
    return pd.DataFrame(rows)


def _append_expected_rows(df: pd.DataFrame, *, numeric_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    expected_rows = []
    for year, group in df.groupby("year", sort=False):
        row = {"year": year, "scenario": "Expected", "weight": 1.0}
        weights = group["weight"].to_numpy(dtype=float)
        for col in numeric_cols:
            row[col] = float(np.sum(group[col].to_numpy(dtype=float) * weights))
        expected_rows.append(row)
    return pd.concat([df, pd.DataFrame(expected_rows)], ignore_index=True)


def _scalar_float(x: Any) -> float:
    if isinstance(x, xr.DataArray):
        values = np.asarray(x.values, dtype=float).reshape(-1)
        return float(values[0]) if values.size else float("nan")
    return float(safe_float(x))


def _normalize_dim_selector(da: xr.DataArray, dim: str, value: Any) -> Any:
    if dim not in da.dims:
        return value

    coord_values = da.coords[dim].values.tolist()
    if not coord_values:
        return value

    if value in coord_values:
        return value

    value_str = str(value)
    for candidate in coord_values:
        if str(candidate) == value_str:
            return candidate

    if value_str.lower() == "base" and len(coord_values) == 1:
        return coord_values[0]

    try:
        value_int = int(value)
    except Exception:
        return value

    for candidate in coord_values:
        try:
            if int(candidate) == value_int:
                return candidate
        except Exception:
            continue
    return value


def _scalar_param(x: Any, **indexers: Any) -> float:
    if not isinstance(x, xr.DataArray):
        return float(safe_float(x))
    da = x
    valid_indexers = {
        k: _normalize_dim_selector(da, k, v)
        for k, v in indexers.items()
        if k in da.dims
    }
    if valid_indexers:
        da = da.sel(**valid_indexers)
    extra_dims = [d for d in da.dims if da.sizes.get(d, 1) > 1]
    if extra_dims:
        da = da.isel({d: 0 for d in extra_dims})
    return _scalar_float(da)


def _build_investment_summary_from_design(*, sets: xr.Dataset, data: xr.Dataset, design_df: pd.DataFrame) -> pd.DataFrame:
    p = get_params(data)
    rs = float((p.settings.get("social_discount_rate", 0.0) or 0.0))
    years = [str(y) for y in sets.coords["year"].values.tolist()]
    start_year_map = {str(step): str(sets["inv_step_start_year"].sel(inv_step=step).item()) for step in sets.coords["inv_step"].values} if "inv_step_start_year" in sets else {}
    year_to_ordinal = {year: idx for idx, year in enumerate(years)}

    rows = []
    for _, row in design_df.iterrows():
        technology = str(row.get("technology", "")).strip().lower()
        inv_step = str(row.get("inv_step", ""))
        resource = str(row.get("resource", "")).strip()
        installed_capacity = float(pd.to_numeric(pd.Series([row.get("installed_capacity", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
        if installed_capacity == 0.0:
            continue
        start_year = str(row.get("inv_step_start_year", start_year_map.get(inv_step, years[0] if years else "")))
        discount_factor = 1.0 / ((1.0 + rs) ** year_to_ordinal.get(start_year, 0))

        if technology == "renewable":
            capex = _scalar_param(p.res_specific_investment_cost_per_kw, inv_step=inv_step, resource=resource)
            grant = _scalar_param(p.res_grant_share_of_capex, inv_step=inv_step, resource=resource)
            nominal = installed_capacity * capex * (1.0 - grant)
            label = resource
            unit = "kW"
        elif technology == "battery":
            capex = _scalar_param(p.battery_specific_investment_cost_per_kwh, inv_step=inv_step)
            nominal = installed_capacity * capex
            label = "Battery"
            unit = "kWh"
        elif technology == "generator":
            capex = _scalar_param(p.generator_specific_investment_cost_per_kw, inv_step=inv_step)
            nominal = installed_capacity * capex
            label = "Generator"
            unit = "kW"
        else:
            continue

        rows.append(
            {
                "Technology": label,
                "Capacity unit": unit,
                "Nominal investment cost": nominal,
                "Present-value investment cost": nominal * discount_factor,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["Technology", "Capacity unit", "Nominal investment cost", "Present-value investment cost"])

    out = pd.DataFrame(rows)
    return out.groupby(["Technology", "Capacity unit"], as_index=False)[["Nominal investment cost", "Present-value investment cost"]].sum()


def _build_investment_summary(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars_dict: Dict[str, Any],
    solution: Optional[xr.Dataset],
) -> pd.DataFrame:
    p = get_params(data)
    rs = float((p.settings.get("social_discount_rate", 0.0) or 0.0))
    step_disc = 1.0 / ((1.0 + rs) ** inv_step_start_ordinal(sets))

    res_units = require_data_array("res_units", get_var_solution(vars_dict=vars_dict, solution=solution, name="res_units"))
    bat_units = require_data_array("battery_units", get_var_solution(vars_dict=vars_dict, solution=solution, name="battery_units"))
    gen_units = require_data_array("generator_units", get_var_solution(vars_dict=vars_dict, solution=solution, name="generator_units"))

    res_nom = require_data_array("res_nominal_capacity_kw", p.res_nominal_capacity_kw)
    res_capex = require_data_array("res_specific_investment_cost_per_kw", p.res_specific_investment_cost_per_kw)
    res_grant = require_data_array("res_grant_share_of_capex", p.res_grant_share_of_capex)
    bat_nom = require_data_array("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    bat_capex = require_data_array("battery_specific_investment_cost_per_kwh", p.battery_specific_investment_cost_per_kwh)
    gen_nom = require_data_array("generator_nominal_capacity_kw", p.generator_nominal_capacity_kw)
    gen_capex = require_data_array("generator_specific_investment_cost_per_kw", p.generator_specific_investment_cost_per_kw)

    res_inv = res_units * res_nom * res_capex * (1.0 - res_grant)
    bat_inv = bat_units * bat_nom * bat_capex
    gen_inv = gen_units * gen_nom * gen_capex

    rows = []
    for resource in res_inv.coords["resource"].values:
        resource_inv = res_inv.sel(resource=resource)
        rows.append(
            {
                "Technology": str(resource),
                "Capacity unit": "kW",
                "Nominal investment cost": float(resource_inv.sum()),
                "Present-value investment cost": float((resource_inv * step_disc).sum()),
            }
        )
    rows.append(
        {
            "Technology": "Battery",
            "Capacity unit": "kWh",
            "Nominal investment cost": float(bat_inv.sum()),
            "Present-value investment cost": float((bat_inv * step_disc).sum()),
        }
    )
    rows.append(
        {
            "Technology": "Generator",
            "Capacity unit": "kW",
            "Nominal investment cost": float(gen_inv.sum()),
            "Present-value investment cost": float((gen_inv * step_disc).sum()),
        }
    )
    return pd.DataFrame(rows)


def _build_scenario_costs(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars_dict: Dict[str, Any],
    solution: Optional[xr.Dataset],
) -> pd.DataFrame:
    p = get_params(data)
    weights = _weights_da(data)

    res_units = require_data_array("res_units", get_var_solution(vars_dict=vars_dict, solution=solution, name="res_units"))
    bat_units = require_data_array("battery_units", get_var_solution(vars_dict=vars_dict, solution=solution, name="battery_units"))
    gen_units = require_data_array("generator_units", get_var_solution(vars_dict=vars_dict, solution=solution, name="generator_units"))
    res_gen = require_data_array("res_generation", get_var_solution(vars_dict=vars_dict, solution=solution, name="res_generation"))
    fuel_cons = require_data_array("fuel_consumption", get_var_solution(vars_dict=vars_dict, solution=solution, name="fuel_consumption"))
    lost_load = require_data_array("lost_load", get_var_solution(vars_dict=vars_dict, solution=solution, name="lost_load"))

    grid_imp = get_var_solution(vars_dict=vars_dict, solution=solution, name="grid_import")
    grid_exp = get_var_solution(vars_dict=vars_dict, solution=solution, name="grid_export")

    res_nom = require_data_array("res_nominal_capacity_kw", p.res_nominal_capacity_kw)
    res_capex = require_data_array("res_specific_investment_cost_per_kw", p.res_specific_investment_cost_per_kw)
    res_grant = require_data_array("res_grant_share_of_capex", p.res_grant_share_of_capex)
    bat_nom = require_data_array("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    bat_capex = require_data_array("battery_specific_investment_cost_per_kwh", p.battery_specific_investment_cost_per_kwh)
    gen_nom = require_data_array("generator_nominal_capacity_kw", p.generator_nominal_capacity_kw)
    gen_capex = require_data_array("generator_specific_investment_cost_per_kw", p.generator_specific_investment_cost_per_kw)

    fuel_price = p.fuel_cost_per_unit_fuel if p.fuel_cost_per_unit_fuel is not None else p.fuel_fuel_cost_per_unit_fuel
    fuel_cost_y_s = _as_year_scenario_da((fuel_cons * fuel_price).sum("period"), sets) if fuel_price is not None else _as_year_scenario_da(0.0, sets)
    grid_import_cost_y_s = _as_year_scenario_da((grid_imp * p.grid_import_price).sum("period"), sets) if (p.is_grid_on() and isinstance(grid_imp, xr.DataArray) and p.grid_import_price is not None) else _as_year_scenario_da(0.0, sets)
    grid_export_rev_y_s = _as_year_scenario_da((grid_exp * p.grid_export_price).sum("period"), sets) if (p.is_grid_export_enabled() and isinstance(grid_exp, xr.DataArray) and p.grid_export_price is not None) else _as_year_scenario_da(0.0, sets)

    res_subsidy_y_s = _as_year_scenario_da(0.0, sets)
    if p.res_production_subsidy_per_kwh is not None:
        subsidy = p.res_production_subsidy_per_kwh
        if "inv_step" in subsidy.dims:
            subsidy = subsidy.isel(inv_step=0, drop=True)
        res_subsidy_y_s = _as_year_scenario_da((res_gen * subsidy).sum("period").sum("resource"), sets)

    res_inv = res_units * res_nom * res_capex * (1.0 - res_grant)
    bat_inv = bat_units * bat_nom * bat_capex
    gen_inv = gen_units * gen_nom * gen_capex
    active = replacement_active_mask(sets)

    res_fom_share = p.res_fixed_om_share_per_year if p.res_fixed_om_share_per_year is not None else 0.0
    bat_fom_share = p.battery_fixed_om_share_per_year if p.battery_fixed_om_share_per_year is not None else 0.0
    gen_fom_share = p.generator_fixed_om_share_per_year if p.generator_fixed_om_share_per_year is not None else 0.0

    fixed_om_res_y_s = _as_year_scenario_da((res_inv * res_fom_share * active).sum("inv_step").sum("resource"), sets)
    fixed_om_battery_y_s = _as_year_scenario_da((bat_inv * bat_fom_share * active).sum("inv_step"), sets)
    fixed_om_generator_y_s = _as_year_scenario_da((gen_inv * gen_fom_share * active).sum("inv_step"), sets)

    lost_load_cost_y_s = _as_year_scenario_da(lost_load.sum("period") * p.lost_load_cost_per_kwh, sets) if p.lost_load_cost_per_kwh is not None else _as_year_scenario_da(0.0, sets)

    scope1_y_s = _as_year_scenario_da(fuel_cons.sum("period") * p.fuel_direct_emissions_kgco2e_per_unit_fuel, sets) if p.fuel_direct_emissions_kgco2e_per_unit_fuel is not None else _as_year_scenario_da(0.0, sets)
    scope2_y_s = _as_year_scenario_da(0.0, sets)

    commission_res = replacement_commission_mask(sets, require_data_array("res_lifetime_years", p.res_lifetime_years))
    commission_bat = replacement_commission_mask(sets, require_data_array("battery_calendar_lifetime_years", p.battery_calendar_lifetime_years))
    commission_gen = replacement_commission_mask(sets, require_data_array("generator_lifetime_years", p.generator_lifetime_years))

    scope3_res_y = _as_year_scenario_da(
        (res_units * res_nom * p.res_embedded_emissions_kgco2e_per_kw * commission_res).sum("inv_step").sum("resource"),
        sets,
    ) if p.res_embedded_emissions_kgco2e_per_kw is not None else _as_year_scenario_da(0.0, sets)
    scope3_battery_y = _as_year_scenario_da(
        (bat_units * bat_nom * p.battery_embedded_emissions_kgco2e_per_kwh * commission_bat).sum("inv_step"),
        sets,
    ) if p.battery_embedded_emissions_kgco2e_per_kwh is not None else _as_year_scenario_da(0.0, sets)
    scope3_generator_y = _as_year_scenario_da(
        (gen_units * gen_nom * p.generator_embedded_emissions_kgco2e_per_kw * commission_gen).sum("inv_step"),
        sets,
    ) if p.generator_embedded_emissions_kgco2e_per_kw is not None else _as_year_scenario_da(0.0, sets)
    scope3_y_s = scope3_res_y + scope3_battery_y + scope3_generator_y

    emission_cost_y_s = _as_year_scenario_da(p.emission_cost_per_kgco2e, sets) if p.emission_cost_per_kgco2e is not None else _as_year_scenario_da(0.0, sets)
    scope1_cost_y_s = scope1_y_s * emission_cost_y_s
    scope2_cost_y_s = scope2_y_s * emission_cost_y_s
    scope3_res_cost_y_s = scope3_res_y * emission_cost_y_s
    scope3_battery_cost_y_s = scope3_battery_y * emission_cost_y_s
    scope3_generator_cost_y_s = scope3_generator_y * emission_cost_y_s
    emissions_cost_y_s = scope1_cost_y_s + scope2_cost_y_s + scope3_res_cost_y_s + scope3_battery_cost_y_s + scope3_generator_cost_y_s

    variable_cost_y_s = fuel_cost_y_s + grid_import_cost_y_s - grid_export_rev_y_s - res_subsidy_y_s
    total_operating_cost_y_s = (
        variable_cost_y_s
        + fixed_om_res_y_s
        + fixed_om_battery_y_s
        + fixed_om_generator_y_s
        + lost_load_cost_y_s
        + emissions_cost_y_s
    )

    rows = []
    for year in sets.coords["year"].values:
        for scenario in sets.coords["scenario"].values:
            rows.append(
                {
                    "year": str(year),
                    "scenario": str(scenario),
                    "weight": float(weights.sel(scenario=scenario)),
                    "fuel_cost": _scalar_float(fuel_cost_y_s.sel(year=year, scenario=scenario)),
                    "grid_import_cost": _scalar_float(grid_import_cost_y_s.sel(year=year, scenario=scenario)),
                    "grid_export_revenue": _scalar_float(grid_export_rev_y_s.sel(year=year, scenario=scenario)),
                    "res_subsidy_revenue": _scalar_float(res_subsidy_y_s.sel(year=year, scenario=scenario)),
                    "annual_variable_cost": _scalar_float(variable_cost_y_s.sel(year=year, scenario=scenario)),
                    "fixed_om_res": _scalar_float(fixed_om_res_y_s.sel(year=year, scenario=scenario)),
                    "fixed_om_battery": _scalar_float(fixed_om_battery_y_s.sel(year=year, scenario=scenario)),
                    "fixed_om_generator": _scalar_float(fixed_om_generator_y_s.sel(year=year, scenario=scenario)),
                    "fixed_om_total": _scalar_float((fixed_om_res_y_s + fixed_om_battery_y_s + fixed_om_generator_y_s).sel(year=year, scenario=scenario)),
                    "lost_load_penalty": _scalar_float(lost_load_cost_y_s.sel(year=year, scenario=scenario)),
                    "scope1_emissions": _scalar_float(scope1_y_s.sel(year=year, scenario=scenario)),
                    "scope2_emissions": _scalar_float(scope2_y_s.sel(year=year, scenario=scenario)),
                    "scope3_res_emissions": _scalar_float(scope3_res_y.sel(year=year, scenario=scenario)),
                    "scope3_battery_emissions": _scalar_float(scope3_battery_y.sel(year=year, scenario=scenario)),
                    "scope3_generator_emissions": _scalar_float(scope3_generator_y.sel(year=year, scenario=scenario)),
                    "scope3_emissions": _scalar_float(scope3_y_s.sel(year=year, scenario=scenario)),
                    "total_emissions": _scalar_float((scope1_y_s + scope2_y_s + scope3_y_s).sel(year=year, scenario=scenario)),
                    "scope1_emissions_cost": _scalar_float(scope1_cost_y_s.sel(year=year, scenario=scenario)),
                    "scope2_emissions_cost": _scalar_float(scope2_cost_y_s.sel(year=year, scenario=scenario)),
                    "scope3_res_emissions_cost": _scalar_float(scope3_res_cost_y_s.sel(year=year, scenario=scenario)),
                    "scope3_battery_emissions_cost": _scalar_float(scope3_battery_cost_y_s.sel(year=year, scenario=scenario)),
                    "scope3_generator_emissions_cost": _scalar_float(scope3_generator_cost_y_s.sel(year=year, scenario=scenario)),
                    "emissions_cost": _scalar_float(emissions_cost_y_s.sel(year=year, scenario=scenario)),
                    "total_operating_cost": _scalar_float(total_operating_cost_y_s.sel(year=year, scenario=scenario)),
                }
            )

    scenario_df = pd.DataFrame(rows)
    numeric_cols = [col for col in scenario_df.columns if col not in {"year", "scenario", "weight"}]
    return _append_expected_rows(scenario_df, numeric_cols=numeric_cols)


def _build_yearly_expected(cash: pd.DataFrame, scenario_costs: pd.DataFrame) -> pd.DataFrame:
    cash = cash.copy()
    cash["year"] = cash["year"].astype(str)
    expected = scenario_costs[scenario_costs["scenario"] == "Expected"].copy()
    expected["year"] = expected["year"].astype(str)
    expected = expected.drop(columns=["scenario", "weight"], errors="ignore")
    yearly = cash.copy().merge(expected, on="year", how="left")
    yearly["annuity_total"] = yearly[["annuity_res", "annuity_battery", "annuity_generator"]].sum(axis=1)
    yearly["renewables_cost"] = (
        yearly["annuity_res"]
        + yearly["fixed_om_res"]
        - yearly["res_subsidy_revenue"]
        + yearly["scope3_res_emissions_cost"]
    )
    yearly["battery_cost"] = (
        yearly["annuity_battery"]
        + yearly["fixed_om_battery"]
        + yearly["scope3_battery_emissions_cost"]
    )
    yearly["generator_cost"] = (
        yearly["annuity_generator"]
        + yearly["fixed_om_generator"]
        + yearly["fuel_cost"]
        + yearly["scope1_emissions_cost"]
        + yearly["scope3_generator_emissions_cost"]
    )
    yearly["grid_cost"] = yearly["grid_import_cost"] - yearly["grid_export_revenue"]
    yearly["reliability_cost"] = yearly["lost_load_penalty"] + yearly["scope2_emissions_cost"]
    return yearly


def _build_context(bundle: ResultsBundle) -> MultiYearResultsContext:
    data = bundle.data
    if not isinstance(data, xr.Dataset):
        raise RuntimeError("Missing data dataset.")
    vars_dict = bundle.vars if isinstance(bundle.vars, dict) else {}
    solution = bundle.solution if isinstance(bundle.solution, xr.Dataset) else None
    sets = bundle.sets if isinstance(bundle.sets, xr.Dataset) else xr.Dataset()
    settings = _get_settings(data)
    dispatch = build_dispatch_timeseries_table_multi_year(data=data, vars=vars_dict, solution=solution)
    design = build_design_by_step_table_multi_year(sets=sets, data=data, vars=vars_dict, solution=solution)
    kpis = build_yearly_kpis_table_multi_year(data=data, vars=vars_dict, solution=solution, objective_value=bundle.objective_value)
    cash = build_discounted_cashflows_table_multi_year(sets=sets, data=data, vars=vars_dict, solution=solution)
    capacity = _capacity_by_year(sets, design)
    scenario_costs = _build_scenario_costs(sets=sets, data=data, vars_dict=vars_dict, solution=solution)
    yearly_expected = _build_yearly_expected(cash, scenario_costs)
    investment_summary = _build_investment_summary(sets=sets, data=data, vars_dict=vars_dict, solution=solution)
    return MultiYearResultsContext(
        bundle=bundle,
        data=data,
        sets=sets,
        settings=settings,
        vars_dict=vars_dict,
        solution=solution,
        dispatch=dispatch,
        design=design,
        kpis=kpis,
        cash=cash,
        capacity_by_year=capacity,
        yearly_expected=yearly_expected,
        scenario_costs=scenario_costs,
        investment_summary=investment_summary,
        on_grid=bool(((settings.get("grid", {}) or {}).get("on_grid", False))),
        allow_export=bool(((settings.get("grid", {}) or {}).get("allow_export", False))),
        years=[str(y) for y in sets.coords["year"].values.tolist()],
        scenarios=[str(s) for s in sets.coords["scenario"].values.tolist()],
    )


def _build_context_from_files(file_results: MultiYearFileResults) -> MultiYearResultsContext:
    data = file_results.data
    sets = file_results.sets
    settings = _get_settings(data)
    dispatch = file_results.dispatch.copy()
    design = file_results.design.copy()
    kpis = file_results.kpis.copy()
    cash = file_results.cash.copy()
    scenario_costs = file_results.scenario_costs.copy()

    for frame in (dispatch, design, kpis, cash, scenario_costs):
        if "year" in frame.columns:
            frame["year"] = frame["year"].astype(str)
        if "scenario" in frame.columns:
            frame["scenario"] = frame["scenario"].astype(str)
        if "inv_step" in frame.columns:
            frame["inv_step"] = frame["inv_step"].astype(str)
        if "inv_step_start_year" in frame.columns:
            frame["inv_step_start_year"] = frame["inv_step_start_year"].astype(str)

    capacity = _capacity_by_year(sets, design)
    yearly_expected = _build_yearly_expected(cash, scenario_costs)
    investment_summary = _build_investment_summary_from_design(sets=sets, data=data, design_df=design)
    objective_value = float(safe_float(cash["discounted_objective_contribution"].sum())) if "discounted_objective_contribution" in cash.columns else None
    bundle = ResultsBundle(
        formulation_mode="dynamic",
        sets=sets,
        data=data,
        vars=None,
        solution=None,
        objective_value=objective_value,
        status=None,
        metadata={"source": "files"},
    )
    return MultiYearResultsContext(
        bundle=bundle,
        data=data,
        sets=sets,
        settings=settings,
        vars_dict={},
        solution=None,
        dispatch=dispatch,
        design=design,
        kpis=kpis,
        cash=cash,
        capacity_by_year=capacity,
        yearly_expected=yearly_expected,
        scenario_costs=scenario_costs,
        investment_summary=investment_summary,
        on_grid=bool(((settings.get("grid", {}) or {}).get("on_grid", False))),
        allow_export=bool(((settings.get("grid", {}) or {}).get("allow_export", False))),
        years=[str(y) for y in sets.coords["year"].values.tolist()],
        scenarios=[str(s) for s in sets.coords["scenario"].values.tolist()],
        file_backed=True,
        results_dir=str(file_results.results_dir),
    )


def _dispatch_kpi_summary(ctx: MultiYearResultsContext, selection: str) -> Dict[str, float]:
    dispatch = ctx.dispatch.copy()
    weights = _weights_da(ctx.data)
    weight_map = {str(s): float(weights.sel(scenario=s)) for s in weights.coords["scenario"].values}
    grid_eta = ctx.data.get("grid_transmission_efficiency")
    grid_ren = ctx.data.get("grid_renewable_share")

    def _expected_for_year(year_value: str) -> Dict[str, float]:
        year_df = dispatch[dispatch["year"].astype(str) == str(year_value)].copy()
        rows = []
        for scenario, group in year_df.groupby("scenario", sort=False):
            scenario_label = str(scenario)
            raw_import = float(group["grid_import"].sum())
            eta = float(grid_eta.sel(scenario=scenario)) if isinstance(grid_eta, xr.DataArray) else 1.0
            ren_share = float(grid_ren.sel(scenario=scenario)) if isinstance(grid_ren, xr.DataArray) else 0.0
            delivered_import = raw_import * eta
            rows.append(
                {
                    "load": float(group["load_demand"].sum()),
                    "lost_load": float(group["lost_load"].sum()),
                    "renewables": float(group["res_generation_total"].sum()),
                    "generator": float(group["generator_generation"].sum()),
                    "grid_import_delivered": delivered_import,
                    "grid_renewable": delivered_import * ren_share,
                    "grid_export": float(group["grid_export"].sum()),
                    "weight": weight_map.get(scenario_label, 0.0),
                }
            )
        metrics = {key: float(np.sum([row[key] * row["weight"] for row in rows])) for key in rows[0] if key != "weight"} if rows else {}
        load = metrics.get("load", 0.0)
        lost_load = metrics.get("lost_load", 0.0)
        supply = metrics.get("renewables", 0.0) + metrics.get("generator", 0.0) + metrics.get("grid_import_delivered", 0.0)
        metrics["served"] = max(load - lost_load, 0.0)
        metrics["renewable_share"] = _safe_div(metrics.get("renewables", 0.0) + metrics.get("grid_renewable", 0.0), supply)
        metrics["lost_load_fraction"] = _safe_div(lost_load, load)
        return metrics

    if selection == "Average yearly":
        yearly = [_expected_for_year(year) for year in ctx.years]
        return {key: float(np.mean([row.get(key, 0.0) for row in yearly])) for key in yearly[0]} if yearly else {}
    return _expected_for_year(selection)


def _render_sizing_summary(ctx: MultiYearResultsContext) -> None:
    st.subheader("Sizing summary")
    st.dataframe(
        ctx.capacity_by_year.style.format(
            {
                "renewables_kw": "{:,.1f}",
                "battery_kwh": "{:,.1f}",
                "generator_kw": "{:,.1f}",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    if len(ctx.design["inv_step"].astype(str).unique()) > 1:
        st.caption("Capacity evolution across the planning horizon.")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, height_ratios=[2, 1.4])
        years = ctx.capacity_by_year["year"].tolist()
        x = np.arange(len(years))
        ax1.bar(x, ctx.capacity_by_year["renewables_kw"], color=C_RES, alpha=0.85, label="Renewables [kW]")
        ax1.bar(x, ctx.capacity_by_year["generator_kw"], bottom=ctx.capacity_by_year["renewables_kw"], color=C_GEN, alpha=0.85, label="Generator [kW]")
        ax1.set_ylabel("kW")
        ax1.set_title("Installed power capacity by year")
        ax1.grid(True, axis="y", alpha=0.25, linestyle=":")
        ax1.legend()
        ax2.bar(x, ctx.capacity_by_year["battery_kwh"], color=C_BAT, alpha=0.85, label="Battery [kWh]")
        ax2.set_ylabel("kWh")
        ax2.set_title("Installed battery energy capacity by year")
        ax2.set_xticks(x, years)
        ax2.grid(True, axis="y", alpha=0.25, linestyle=":")
        ax2.legend()
        plt.tight_layout()
        st.pyplot(fig)

    with st.expander("Investment-step breakdown", expanded=False):
        st.dataframe(
            ctx.design.style.format({"units": "{:,.3f}", "installed_capacity": "{:,.1f}"}),
            hide_index=True,
            width="stretch",
        )


def _render_performance_kpis(ctx: MultiYearResultsContext) -> None:
    st.subheader("Performance KPIs")
    expected = ctx.kpis[ctx.kpis["scenario"].astype(str).str.lower() == "expected"].copy()
    options = ["Average yearly"] + ctx.years
    choice = st.selectbox("View performance for", options, key="my_results_kpi_period")
    if choice == "Average yearly":
        row = expected.select_dtypes(include=[np.number]).mean(numeric_only=True)
    else:
        row = expected[expected["year"].astype(str) == str(choice)].select_dtypes(include=[np.number]).iloc[0]
    dispatch_summary = _dispatch_kpi_summary(ctx, choice)

    kpi_rows = [
        {"Metric": "Load", "Value": dispatch_summary.get("load", float(row.get("total_demand_kwh", 0.0))) / 1e3, "Unit": "MWh"},
        {"Metric": "Delivered energy", "Value": dispatch_summary.get("served", float(row.get("served_energy_kwh", 0.0))) / 1e3, "Unit": "MWh"},
        {"Metric": "Lost load", "Value": dispatch_summary.get("lost_load", float(row.get("lost_load_kwh", 0.0))) / 1e3, "Unit": "MWh"},
        {"Metric": "Renewable generation", "Value": dispatch_summary.get("renewables", float(row.get("total_res_kwh", 0.0))) / 1e3, "Unit": "MWh"},
        {"Metric": "Generator generation", "Value": dispatch_summary.get("generator", 0.0) / 1e3, "Unit": "MWh"},
        {"Metric": "Renewable share of supply", "Value": 100.0 * dispatch_summary.get("renewable_share", float(row.get("renewable_penetration", 0.0))), "Unit": "%"},
        {"Metric": "Lost load fraction", "Value": 100.0 * dispatch_summary.get("lost_load_fraction", float(row.get("lost_load_fraction", 0.0))), "Unit": "%"},
        {"Metric": "Fuel consumption", "Value": float(row.get("fuel_consumption", 0.0)), "Unit": "fuel units"},
        {"Metric": "Emissions", "Value": float(row.get("emissions_kgco2e", 0.0)), "Unit": "kgCO2e"},
    ]
    if ctx.on_grid:
        kpi_rows.insert(
            5,
            {
                "Metric": "Grid renewable contribution",
                "Value": dispatch_summary.get("grid_renewable", float(row.get("grid_renewable_kwh", 0.0))) / 1e3,
                "Unit": "MWh",
            },
        )
        kpi_rows.insert(
            5,
            {
                "Metric": "Grid imports (delivered)",
                "Value": dispatch_summary.get("grid_import_delivered", 0.0) / 1e3,
                "Unit": "MWh",
            },
        )
    if ctx.allow_export:
        kpi_rows.insert(
            7 if ctx.on_grid else 5,
            {
                "Metric": "Grid exports",
                "Value": dispatch_summary.get("grid_export", 0.0) / 1e3,
                "Unit": "MWh",
            },
        )
    st.dataframe(
        pd.DataFrame(kpi_rows).style.format({"Value": "{:,.2f}"}),
        hide_index=True,
        width="stretch",
    )


def _render_energy_mix(ctx: MultiYearResultsContext) -> None:
    st.subheader("Least-Cost Energy Mix")
    st.caption("Hourly dispatch over a selected contiguous day window, using the same color convention as the typical-year results.")

    c1, c2 = st.columns(2)
    with c1:
        year_sel = st.selectbox("Year", ctx.years, key="my_results_year")
    with c2:
        scenario_sel = st.selectbox("Scenario", _scenario_options(ctx.settings, ctx.data), key="my_results_scenario")

    year_view = ctx.dispatch[ctx.dispatch["year"].astype(str) == str(year_sel)].copy()
    if scenario_sel == "Expected":
        series_view = _build_expected_dispatch(year_view, ctx.data.get("scenario_weight"))
        scenario_label = "Expected"
    else:
        series_view = year_view[year_view["scenario"].astype(str) == str(scenario_sel)].copy()
        scenario_label = str(scenario_sel)

    T = int(len(series_view))
    with st.expander("Time window", expanded=False):
        st.caption("Pick the start day and how many consecutive days to plot (1-7).")
        max_days = max(1, int(np.ceil(T / 24)))
        ndays = st.slider(
            "Number of days",
            min_value=1,
            max_value=min(7, max_days),
            value=1,
            step=1,
            key="my_results_ndays",
        )
        max_start_day = max(1, max_days - ndays + 1)
        start_day = st.slider(
            "Start day",
            min_value=1,
            max_value=max_start_day,
            value=1,
            step=1,
            key="my_results_start_day",
        )

    profile = _window_dispatch_profile(series_view, start_day=start_day, ndays=ndays)
    if profile.empty:
        st.warning("No dispatch data available for the selected year/scenario window.")
        return

    fig, ax = plt.subplots(figsize=(11, 4))
    _plot_dispatch_stack(ax=ax, profile=profile, title_suffix=f"Year {year_sel} - {scenario_label}")
    st.pyplot(fig)

    with st.expander("Windowed dispatch table", expanded=False):
        numeric_cols = profile.select_dtypes(include=[np.number]).columns.tolist()
        fmt = {col: "{:,.2f}" for col in numeric_cols}
        st.dataframe(profile.style.format(fmt), hide_index=True, width="stretch")


def _render_costs_and_cashflow(ctx: MultiYearResultsContext) -> None:
    st.subheader("Cost summary & Cash-flow")

    npc = float(safe_float(ctx.bundle.objective_value))
    if not np.isfinite(npc):
        npc = float(ctx.yearly_expected["discounted_objective_contribution"].sum())

    expected_kpis = ctx.kpis[ctx.kpis["scenario"].astype(str).str.lower() == "expected"].copy()
    lcoe_df = ctx.cash.merge(expected_kpis[["year", "served_energy_kwh"]], on="year", how="left")
    discounted_energy = float((lcoe_df["discount_factor"] * lcoe_df["served_energy_kwh"]).sum())
    lcoe = npc / discounted_energy if discounted_energy > 1e-12 else float("nan")

    nominal_investment = float(ctx.investment_summary["Nominal investment cost"].sum())
    pv_investment = float(ctx.investment_summary["Present-value investment cost"].sum())

    m1, m2, m3 = st.columns(3)
    m1.metric("Net Present Cost (Expected)", f"{npc:,.0f}")
    m2.metric("LCOE", f"{lcoe:,.4f}/kWh" if np.isfinite(lcoe) else "n/a")
    m3.metric("Investment cost (nominal / present)", f"{nominal_investment:,.0f} / {pv_investment:,.0f}")

    st.caption("Investment costs are shown net of grants and discounted to present using the social discount rate.")
    st.dataframe(
        ctx.investment_summary.style.format(
            {
                "Nominal investment cost": "{:,.0f}",
                "Present-value investment cost": "{:,.0f}",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    options = ["Average yearly"] + ctx.years
    period_choice = st.selectbox("View yearly cost tables for", options, key="my_results_cost_period")
    if period_choice == "Average yearly":
        selected = ctx.yearly_expected.select_dtypes(include=[np.number]).mean(numeric_only=True)
    else:
        selected = ctx.yearly_expected[ctx.yearly_expected["year"].astype(str) == str(period_choice)].select_dtypes(include=[np.number]).iloc[0]

    st.markdown("**Expected annual cost composition**")
    composition = pd.DataFrame(
        [
            {"Component": "Annualized CAPEX", "Value": float(selected["annuity_total"]), "Unit": "/yr"},
            {"Component": "Fixed O&M", "Value": float(selected["fixed_om_total"]), "Unit": "/yr"},
            {"Component": "Fuel cost", "Value": float(selected["fuel_cost"]), "Unit": "/yr"},
            {"Component": "Grid import cost", "Value": float(selected["grid_import_cost"]), "Unit": "/yr"},
            {"Component": "Grid export revenue", "Value": -float(selected["grid_export_revenue"]), "Unit": "/yr"},
            {"Component": "RES subsidy revenue", "Value": -float(selected["res_subsidy_revenue"]), "Unit": "/yr"},
            {"Component": "Lost load penalty", "Value": float(selected["lost_load_penalty"]), "Unit": "/yr"},
            {"Component": "Emissions cost", "Value": float(selected["emissions_cost"]), "Unit": "/yr"},
            {"Component": "Embedded emissions cost", "Value": float(selected["embedded_expected"]), "Unit": "/yr"},
            {"Component": "TOTAL", "Value": float(selected["total_before_discount"]), "Unit": "/yr"},
        ]
    )
    st.dataframe(
        composition.style.format({"Value": "{:,.0f}"}),
        hide_index=True,
        width="stretch",
    )

    st.markdown("**Expected annual fixed O&M**")
    fixed_om = pd.DataFrame(
        [
            {"Technology": "Renewables", "Annual fixed O&M": float(selected["fixed_om_res"])},
            {"Technology": "Battery", "Annual fixed O&M": float(selected["fixed_om_battery"])},
            {"Technology": "Generator", "Annual fixed O&M": float(selected["fixed_om_generator"])},
        ]
    )
    st.dataframe(
        fixed_om.style.format({"Annual fixed O&M": "{:,.0f}"}),
        hide_index=True,
        width="stretch",
    )

    st.caption("Expected yearly cash flow across the planning horizon.")
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    years = ctx.yearly_expected["year"].astype(str).tolist()
    x = np.arange(len(years))

    annuity = ctx.yearly_expected["annuity_total"].to_numpy(dtype=float)
    fixed_om_total = ctx.yearly_expected["fixed_om_total"].to_numpy(dtype=float)
    fuel_cost = ctx.yearly_expected["fuel_cost"].to_numpy(dtype=float)
    axes[0].bar(x, annuity, color="#1B4965", label="CAPEX annuity")
    axes[0].bar(x, fixed_om_total, bottom=annuity, color="#5FA8D3", label="Fixed O&M")
    axes[0].bar(x, fuel_cost, bottom=annuity + fixed_om_total, color=C_GEN, label="Fuel cost")
    axes[0].set_title("Expected yearly cash flow by cost class")
    axes[0].set_ylabel("Currency / year")
    axes[0].grid(True, axis="y", alpha=0.25, linestyle=":")
    axes[0].legend()

    renewables = ctx.yearly_expected["renewables_cost"].to_numpy(dtype=float)
    battery = ctx.yearly_expected["battery_cost"].to_numpy(dtype=float)
    generator = ctx.yearly_expected["generator_cost"].to_numpy(dtype=float)
    grid = ctx.yearly_expected["grid_cost"].to_numpy(dtype=float)
    reliability = ctx.yearly_expected["reliability_cost"].to_numpy(dtype=float)
    axes[1].bar(x, renewables, color=C_RES, label="Renewables")
    axes[1].bar(x, battery, bottom=renewables, color=C_BAT, label="Battery")
    axes[1].bar(x, generator, bottom=renewables + battery, color=C_GEN, label="Generator")
    axes[1].bar(x, grid, bottom=renewables + battery + generator, color=C_IMP, label="Grid")
    axes[1].bar(x, reliability, bottom=renewables + battery + generator + grid, color=C_LL, label="Reliability & policy")
    axes[1].set_title("Expected yearly cash flow by technology bucket")
    axes[1].set_ylabel("Currency / year")
    axes[1].set_xticks(x, years)
    axes[1].grid(True, axis="y", alpha=0.25, linestyle=":")
    axes[1].legend()
    plt.tight_layout()
    st.pyplot(fig)


def _render_scenario_costs_and_emissions(ctx: MultiYearResultsContext) -> None:
    st.subheader("Scenario-specific operational costs & emissions")
    st.caption("Inspect yearly operational costs and emissions by scenario, alongside an expected-value view.")

    year_options = ["All years"] + ctx.years
    selected_year = st.selectbox("Filter scenario tables by year", year_options, key="my_results_scenario_year")
    metric = st.selectbox("Scenario comparison plot", ["Annual variable cost", "Total emissions"], key="my_results_scenario_metric")

    scenario_df = ctx.scenario_costs.copy()
    if selected_year != "All years":
        scenario_df = scenario_df[scenario_df["year"].astype(str) == str(selected_year)].copy()

    expected_df = scenario_df[scenario_df["scenario"] == "Expected"].copy()
    top_cost = float(expected_df["annual_variable_cost"].mean()) if not expected_df.empty else float("nan")
    top_em = float(expected_df["total_emissions"].mean()) if not expected_df.empty else float("nan")
    c1, c2 = st.columns(2)
    c1.metric("Annual variable cost (Expected)", f"{top_cost:,.0f}/yr" if np.isfinite(top_cost) else "n/a")
    c2.metric("Total emissions (Expected)", f"{top_em:,.0f} kgCO2e" if np.isfinite(top_em) else "n/a")

    with st.expander("Scenario-wise variable cost breakdown", expanded=False):
        cols = [
            "year",
            "scenario",
            "fuel_cost",
            "grid_import_cost",
            "grid_export_revenue",
            "res_subsidy_revenue",
            "annual_variable_cost",
            "weight",
        ]
        st.dataframe(
            scenario_df[cols].style.format(
                {
                    "fuel_cost": "{:,.0f}",
                    "grid_import_cost": "{:,.0f}",
                    "grid_export_revenue": "{:,.0f}",
                    "res_subsidy_revenue": "{:,.0f}",
                    "annual_variable_cost": "{:,.0f}",
                    "weight": "{:.3f}",
                }
            ),
            hide_index=True,
            width="stretch",
        )

    with st.expander("Scenario-wise emissions breakdown", expanded=False):
        cols = [
            "year",
            "scenario",
            "scope1_emissions",
            "scope2_emissions",
            "scope3_emissions",
            "total_emissions",
            "emissions_cost",
            "weight",
        ]
        st.dataframe(
            scenario_df[cols].style.format(
                {
                    "scope1_emissions": "{:,.0f}",
                    "scope2_emissions": "{:,.0f}",
                    "scope3_emissions": "{:,.0f}",
                    "total_emissions": "{:,.0f}",
                    "emissions_cost": "{:,.0f}",
                    "weight": "{:.3f}",
                }
            ),
            hide_index=True,
            width="stretch",
        )

    fig, ax = plt.subplots(figsize=(11, 4))
    plot_df = ctx.scenario_costs.copy()
    expected = plot_df[plot_df["scenario"] == "Expected"].copy()
    plot_df = plot_df[plot_df["scenario"] != "Expected"].copy()
    value_col = "annual_variable_cost" if metric == "Annual variable cost" else "total_emissions"
    y_label = "Currency / year" if metric == "Annual variable cost" else "kgCO2e / year"

    for scenario in ctx.scenarios:
        series = plot_df[plot_df["scenario"] == scenario].copy()
        if series.empty:
            continue
        ax.plot(
            series["year"].astype(str),
            series[value_col].to_numpy(dtype=float),
            marker="o",
            linewidth=1.6,
            label=f"Scenario {scenario}",
        )
    if not expected.empty:
        ax.plot(
            expected["year"].astype(str),
            expected[value_col].to_numpy(dtype=float),
            marker="o",
            linewidth=2.4,
            linestyle="--",
            color="#111111",
            label="Expected",
        )
    ax.set_title(f"{metric} by year")
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.25, linestyle=":")
    ax.legend(ncols=3, fontsize=9)
    st.pyplot(fig)


def _render_export_section(ctx: MultiYearResultsContext, project_name: Optional[str]) -> None:
    st.subheader("Export Results")
    if ctx.file_backed:
        st.caption("Displaying saved results loaded from project files.")
        if ctx.results_dir:
            st.write(ctx.results_dir)
        return
    st.caption("Export multi-year results to CSV and an Excel workbook with one sheet per model year.")

    if st.button("Export results to CSV / Excel", type="primary", key="my_results_export"):
        if not project_name:
            st.error("Active project name is missing; cannot export results.")
            return
        try:
            with st.spinner("Exporting multi-year results..."):
                model_obj = st.session_state.get("gp_model_obj")
                written = export_results_from_bundle(project_name, ctx.bundle, model_obj=model_obj)
            st.success("Export completed.")
            st.json(written)
            st.markdown("**Generated files**")
            for _, path in written.items():
                if isinstance(path, str) and (path.endswith(".csv") or path.endswith(".xlsx")):
                    st.write(path)
        except Exception as exc:
            st.error(f"Export failed: {exc}")


def render_multi_year_results(bundle: ResultsBundle, project_name: Optional[str]) -> None:
    _ = project_name
    try:
        ctx = _build_context(bundle)
    except Exception as exc:
        st.error(f"Unable to render multi-year results: {exc}")
        return

    _render_sizing_summary(ctx)
    _render_performance_kpis(ctx)
    _render_energy_mix(ctx)
    _render_costs_and_cashflow(ctx)
    _render_scenario_costs_and_emissions(ctx)
    _render_export_section(ctx, project_name)


def render_multi_year_results_from_files(file_results: MultiYearFileResults, project_name: Optional[str]) -> None:
    _ = project_name
    try:
        ctx = _build_context_from_files(file_results)
    except Exception as exc:
        st.error(f"Unable to render saved multi-year results: {exc}")
        return

    st.info(f"Displaying saved results loaded from project files in `{file_results.results_dir}`.")
    _render_sizing_summary(ctx)
    _render_performance_kpis(ctx)
    _render_energy_mix(ctx)
    _render_costs_and_cashflow(ctx)
    _render_scenario_costs_and_emissions(ctx)
    _render_export_section(ctx, project_name)
