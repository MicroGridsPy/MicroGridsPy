from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import linopy as lp
import numpy as np
import pandas as pd
import xarray as xr

from microgridspy.export.common import (
    InputValidationError,
    ensure_results_dir,
    get_var_solution,
    require_data_array,
    safe_float,
    safe_share,
    scalarize,
    select_or_self,
    write_csv_outputs,
)
from microgridspy.io.vintage_labels import (
    load_multi_year_vintage_labels,
    vintage_display_for_step,
    vintage_label_for_step,
)
from microgridspy.multi_year_model.lifecycle import (
    discounted_annuity_tail_memo,
    map_inv_step_to_year,
    repeating_degradation_factor,
    replacement_active_mask,
    replacement_commission_mask,
    year_ordinal,
)
from microgridspy.multi_year_model.params import get_params


@dataclass
class MultiYearResults:
    """Structured, analysis-ready results of a solved multi-year model.

    Returned by `MultiYearModel.results()` (and `microgridspy.load_results()`).
    Analogous to `TypicalYearResults`, but with quantities resolved over the planning
    horizon: `pandas` DataFrames for headline KPIs, per-year installed capacity,
    staged design by investment step, dispatch and energy balances, discounted cash
    flows and cost components, and emissions — plus the underlying solved
    `data`/`sets` (`xarray.Dataset`). Write them to disk with
    `microgridspy.export_results()`.

    Stability: provisional until the 1.0 release (the set of tables may grow).
    """

    project_name: str
    data: xr.Dataset
    sets: xr.Dataset
    metadata: dict[str, Any]
    dispatch: pd.DataFrame
    energy_balance: pd.DataFrame
    design_by_step: pd.DataFrame
    renewable_inverter_design_by_step: pd.DataFrame
    battery_inverter_design_by_step: pd.DataFrame
    inverter_capacity_by_year: pd.DataFrame
    inverter_metrics_yearly: pd.DataFrame
    capacity_by_year: pd.DataFrame
    kpis_yearly: pd.DataFrame
    cashflows_discounted: pd.DataFrame
    scenario_costs_yearly: pd.DataFrame
    yearly_expected: pd.DataFrame
    investment_summary: pd.DataFrame
    reporting_summary: pd.DataFrame
    results_dir: Path | None = None
    source: str = "session"

    def to_excel(self, out_dir: Path | None = None) -> dict:
        """Write these results to CSV/Excel files.

        Args:
            out_dir: destination directory; defaults to the project's ``results/``.

        Returns:
            dict: mapping of output name to the written file path.
        """
        return export_multi_year_results_package(results=self, out_dir=out_dir)


def _sanitize_sheet_name(name: Any) -> str:
    text = str(name)
    invalid = "[]:*?/\\"
    for ch in invalid:
        text = text.replace(ch, "_")
    return text[:31] or "Sheet"


def _write_multi_year_excel_workbook(
    out_path: Path,
    *,
    design: pd.DataFrame,
    dispatch: pd.DataFrame,
    balance: pd.DataFrame,
    kpis: pd.DataFrame,
    cash: pd.DataFrame,
) -> str:
    with pd.ExcelWriter(out_path) as writer:
        design.to_excel(writer, sheet_name="design_by_step", index=False)
        dispatch.to_excel(writer, sheet_name="dispatch_timeseries", index=False)
        cash.to_excel(writer, sheet_name="cashflows_discounted", index=False)

        for year in cash["year"].tolist():
            year_label = str(year)
            sheet_name = _sanitize_sheet_name(year_label)
            row = 0

            pd.DataFrame({"section": [f"Performance KPIs - {year_label}"]}).to_excel(
                writer, sheet_name=sheet_name, index=False, header=False, startrow=row
            )
            row += 2
            kpis_year = kpis[kpis["year"].astype(str) == year_label].copy()
            kpis_year.to_excel(writer, sheet_name=sheet_name, index=False, startrow=row)
            row += len(kpis_year) + 3

            pd.DataFrame({"section": [f"Discounted cash flow - {year_label}"]}).to_excel(
                writer, sheet_name=sheet_name, index=False, header=False, startrow=row
            )
            row += 2
            cash_year = cash[cash["year"].astype(str) == year_label].copy()
            cash_year.to_excel(writer, sheet_name=sheet_name, index=False, startrow=row)
            row += len(cash_year) + 3

            pd.DataFrame({"section": [f"Energy balance - {year_label}"]}).to_excel(
                writer, sheet_name=sheet_name, index=False, header=False, startrow=row
            )
            row += 2
            balance_year = balance[balance["year"].astype(str) == year_label].copy()
            balance_year.to_excel(writer, sheet_name=sheet_name, index=False, startrow=row)

    return str(out_path)


def _scenario_weights(p: Any, scenario_coord: xr.DataArray) -> xr.DataArray:
    if isinstance(p.scenario_weight, xr.DataArray):
        return p.scenario_weight.sel(scenario=scenario_coord)
    n = int(scenario_coord.size)
    return xr.DataArray(
        np.ones((n,), dtype=float) / float(n),
        dims=("scenario",),
        coords={"scenario": scenario_coord},
    )


def _crf(r: xr.DataArray | float, n: xr.DataArray | float) -> xr.DataArray:
    rr = xr.DataArray(r)
    nn = xr.DataArray(n)
    a = (1.0 + rr) ** nn
    out = (rr * a) / (a - 1.0)
    out = xr.where(np.abs(rr) < 1e-12, 1.0 / nn, out)
    return xr.where(nn > 0, out, 0.0)


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
    ordered_dims = ["year", "scenario"] + [
        dim for dim in da.dims if dim not in {"year", "scenario"}
    ]
    return da.transpose(*ordered_dims)


def _renewable_subsidy_by_year(
    sets: xr.Dataset,
    subsidy: xr.DataArray,
) -> xr.DataArray:
    mapped = map_inv_step_to_year(
        sets,
        require_data_array("res_production_subsidy_per_kwh", subsidy),
        name="res_production_subsidy_per_kwh",
    )
    return xr.where(np.isfinite(mapped), mapped, 0.0)


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
        key: _normalize_dim_selector(da, key, value)
        for key, value in indexers.items()
        if key in da.dims
    }
    if valid_indexers:
        da = da.sel(**valid_indexers)
    extra_dims = [dim for dim in da.dims if da.sizes.get(dim, 1) > 1]
    if extra_dims:
        da = da.isel({dim: 0 for dim in extra_dims})
    values = np.asarray(da.values, dtype=float).reshape(-1)
    return float(values[0]) if values.size else float("nan")


def _sum_if_has_inv_step(x: Any) -> Any:
    if isinstance(x, xr.DataArray) and "inv_step" in x.dims:
        return x.sum("inv_step")
    return x


def _broadcast_year_state_to_period(x: Any, sets: xr.Dataset) -> Any:
    if not isinstance(x, xr.DataArray):
        return x
    if "period" in x.dims:
        return x
    if {"year", "scenario"}.issubset(x.dims):
        return x.expand_dims(period=sets.coords["period"]).transpose(
            "period",
            *[dim for dim in x.dims],
        )
    if {"year", "inv_step"}.issubset(x.dims):
        return x.expand_dims(
            period=sets.coords["period"], scenario=sets.coords["scenario"]
        ).transpose("period", "year", "scenario", "inv_step")
    if "year" in x.dims:
        return x.expand_dims(
            period=sets.coords["period"], scenario=sets.coords["scenario"]
        ).transpose("period", "year", "scenario")
    return x


def _renewable_display_name(data: xr.Dataset, resource: Any) -> str:
    mapping = (data.attrs or {}).get("conversion_technology_by_resource", {})
    if isinstance(mapping, dict):
        label = str(mapping.get(str(resource), "") or "").strip()
        if label:
            return label
    return str(resource)


def _renewable_capacity_tables(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    p = get_params(data)
    res_units = require_data_array(
        "res_units", get_var_solution(vars_dict=vars, solution=solution, name="res_units")
    )
    res_nom = require_data_array("res_nominal_capacity_kw", p.res_nominal_capacity_kw)
    res_life = require_data_array("res_lifetime_years", p.res_lifetime_years)
    res_dc_ac_ratio = require_data_array("res_dc_ac_ratio", p.res_dc_ac_ratio)
    res_eta = require_data_array("res_inverter_efficiency", p.res_inverter_efficiency)
    active_mask = replacement_active_mask(sets)
    degradation = repeating_degradation_factor(
        sets=sets,
        lifetime_years=res_life,
        degradation_rate=p.res_capacity_degradation_rate_per_year,
    )
    dc_by_step = res_units * res_nom
    active_dc_by_step = dc_by_step * active_mask * degradation
    active_inv_ac_by_step = active_dc_by_step / res_dc_ac_ratio
    effective_ac_by_step = xr.apply_ufunc(
        np.minimum, active_dc_by_step * res_eta, active_inv_ac_by_step
    )
    return active_dc_by_step, active_inv_ac_by_step, effective_ac_by_step


def _battery_capacity_tables(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> tuple[xr.DataArray, xr.DataArray]:
    p = get_params(data)
    bat_units = require_data_array(
        "battery_units", get_var_solution(vars_dict=vars, solution=solution, name="battery_units")
    )
    bat_inv_power = require_data_array(
        "battery_inverter_power",
        get_var_solution(vars_dict=vars, solution=solution, name="battery_inverter_power"),
    )
    bat_nom = require_data_array("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    bat_life = require_data_array(
        "battery_calendar_lifetime_years", p.battery_calendar_lifetime_years
    )
    active_mask = replacement_active_mask(sets)
    degradation = repeating_degradation_factor(
        sets=sets,
        lifetime_years=bat_life,
        degradation_rate=p.battery_capacity_degradation_rate_per_year,
    )
    active_energy_by_step = (bat_units * bat_nom) * active_mask * degradation
    active_inv_power_by_step = bat_inv_power * active_mask
    return active_energy_by_step, active_inv_power_by_step


def build_dispatch_timeseries_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> pd.DataFrame:
    p = get_params(data)
    load = require_data_array("load_demand", p.load_demand)
    res = require_data_array(
        "res_generation", get_var_solution(vars_dict=vars, solution=solution, name="res_generation")
    )
    gen = _sum_if_has_inv_step(
        require_data_array(
            "generator_generation",
            get_var_solution(vars_dict=vars, solution=solution, name="generator_generation"),
        )
    )
    bch = _sum_if_has_inv_step(
        require_data_array(
            "battery_charge",
            get_var_solution(vars_dict=vars, solution=solution, name="battery_charge"),
        )
    )
    bdis = _sum_if_has_inv_step(
        require_data_array(
            "battery_discharge",
            get_var_solution(vars_dict=vars, solution=solution, name="battery_discharge"),
        )
    )
    bsoc = _sum_if_has_inv_step(
        require_data_array(
            "battery_soc", get_var_solution(vars_dict=vars, solution=solution, name="battery_soc")
        )
    )
    bch_dc = _sum_if_has_inv_step(
        get_var_solution(vars_dict=vars, solution=solution, name="battery_charge_dc")
    )
    bdis_dc = _sum_if_has_inv_step(
        get_var_solution(vars_dict=vars, solution=solution, name="battery_discharge_dc")
    )
    bch_loss = _sum_if_has_inv_step(
        get_var_solution(vars_dict=vars, solution=solution, name="battery_charge_loss")
    )
    bdis_loss = _sum_if_has_inv_step(
        get_var_solution(vars_dict=vars, solution=solution, name="battery_discharge_loss")
    )
    raw_bcycle = get_var_solution(vars_dict=vars, solution=solution, name="battery_cycle_fade")
    raw_bcal = get_var_solution(vars_dict=vars, solution=solution, name="battery_calendar_fade")
    raw_beff = get_var_solution(
        vars_dict=vars, solution=solution, name="battery_effective_energy_capacity"
    )
    bcycle = _sum_if_has_inv_step(raw_bcycle)
    bcal = _broadcast_year_state_to_period(_sum_if_has_inv_step(raw_bcal), sets)
    beff = _broadcast_year_state_to_period(_sum_if_has_inv_step(raw_beff), sets)
    _, bat_inv_active = _battery_capacity_tables(sets=sets, data=data, vars=vars, solution=solution)
    bat_inv_active_total = _broadcast_year_state_to_period(bat_inv_active.sum("inv_step"), sets)
    bsoh = get_var_solution(vars_dict=vars, solution=solution, name="battery_soh")
    if isinstance(bsoh, xr.DataArray) and "inv_step" in bsoh.dims:
        # A simple arithmetic mean across cohorts is misleading once different
        # vintages can coexist. Use a capacity-weighted mean based on each
        # cohort's effective usable energy whenever available, and return NaN
        # when no cohort has active usable capacity.
        if isinstance(raw_beff, xr.DataArray):
            denom = raw_beff.sum("inv_step")
            weighted_num = (bsoh * raw_beff).sum("inv_step")
            bsoh = xr.where(denom > 1e-12, weighted_num / denom, np.nan)
        else:
            bsoh = None
    elif bsoh is None and isinstance(raw_beff, xr.DataArray):
        bat_units = get_var_solution(vars_dict=vars, solution=solution, name="battery_units")
        if (
            isinstance(bat_units, xr.DataArray)
            and p.battery_nominal_capacity_kwh is not None
            and p.battery_calendar_lifetime_years is not None
        ):
            nominal_available = (
                bat_units
                * p.battery_nominal_capacity_kwh
                * replacement_active_mask(sets)
                * repeating_degradation_factor(
                    sets,
                    p.battery_calendar_lifetime_years,
                    p.battery_capacity_degradation_rate_per_year,
                )
            )
            nominal_available = nominal_available.expand_dims(
                scenario=sets.coords["scenario"]
            ).transpose("year", "scenario", "inv_step")
            denom = nominal_available.sum("inv_step")
            bsoh_year = xr.where(denom > 1e-12, raw_beff.sum("inv_step") / denom, np.nan)
            bsoh = _broadcast_year_state_to_period(bsoh_year, sets)
    ll = require_data_array(
        "lost_load", get_var_solution(vars_dict=vars, solution=solution, name="lost_load")
    )

    gimp = (
        get_var_solution(vars_dict=vars, solution=solution, name="grid_import")
        if p.is_grid_on()
        else None
    )
    gexp = (
        get_var_solution(vars_dict=vars, solution=solution, name="grid_export")
        if p.is_grid_export_enabled()
        else None
    )

    idx = load.to_series().index
    df = pd.DataFrame(index=idx).reset_index()
    df["load_demand"] = load.to_series().values.astype(float)
    df["res_generation_total"] = res.sum("resource").to_series().values.astype(float)
    for resource in res.coords["resource"].values.tolist():
        df[f"res_generation__{resource}"] = (
            res.sel(resource=resource).to_series().values.astype(float)
        )
    df["generator_generation"] = gen.to_series().values.astype(float)
    df["battery_charge"] = bch.to_series().values.astype(float)
    df["battery_discharge"] = bdis.to_series().values.astype(float)
    df["battery_soc"] = bsoc.to_series().values.astype(float)
    if isinstance(bch_dc, xr.DataArray):
        df["battery_charge_dc"] = bch_dc.to_series().values.astype(float)
    if isinstance(bdis_dc, xr.DataArray):
        df["battery_discharge_dc"] = bdis_dc.to_series().values.astype(float)
    if isinstance(bch_loss, xr.DataArray):
        df["battery_charge_loss"] = bch_loss.to_series().values.astype(float)
    if isinstance(bdis_loss, xr.DataArray):
        df["battery_discharge_loss"] = bdis_loss.to_series().values.astype(float)
    if isinstance(bcycle, xr.DataArray):
        df["battery_cycle_fade"] = bcycle.to_series().values.astype(float)
    if isinstance(bcal, xr.DataArray):
        df["battery_calendar_fade"] = bcal.to_series().values.astype(float)
    if isinstance(bsoh, xr.DataArray):
        df["battery_soh"] = bsoh.to_series().values.astype(float)
    if isinstance(beff, xr.DataArray):
        df["battery_effective_energy_capacity"] = beff.to_series().values.astype(float)
    if isinstance(bat_inv_active_total, xr.DataArray):
        df["battery_inverter_active_power"] = bat_inv_active_total.to_series().values.astype(float)
    df["lost_load"] = ll.to_series().values.astype(float)
    df["grid_import"] = (
        gimp.to_series().values.astype(float) if isinstance(gimp, xr.DataArray) else 0.0
    )
    df["grid_export"] = (
        gexp.to_series().values.astype(float) if isinstance(gexp, xr.DataArray) else 0.0
    )
    grid_eta = (
        df["scenario"]
        .astype(str)
        .map(
            lambda scenario: (
                float(p.grid_transmission_efficiency.sel(scenario=scenario))
                if p.grid_transmission_efficiency is not None
                else 1.0
            )
        )
    )
    df["grid_import_delivered"] = df["grid_import"] * grid_eta
    df["grid_export_delivered"] = df["grid_export"] * grid_eta
    return df


def build_energy_balance_table_multi_year(dispatch_df: pd.DataFrame) -> pd.DataFrame:
    df = dispatch_df.copy()
    grid_import_delivered = (
        df["grid_import_delivered"] if "grid_import_delivered" in df.columns else df["grid_import"]
    )
    grid_export_delivered = (
        df["grid_export_delivered"] if "grid_export_delivered" in df.columns else df["grid_export"]
    )
    df["supply_renewable"] = df["res_generation_total"]
    df["supply_generator"] = df["generator_generation"]
    df["supply_grid_import"] = grid_import_delivered
    df["supply_battery_discharge"] = df["battery_discharge"]
    df["supply_lost_load"] = df["lost_load"]
    df["sink_battery_charge"] = df["battery_charge"]
    df["sink_grid_export"] = grid_export_delivered
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
        "year",
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


def build_design_by_step_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> pd.DataFrame:
    p = get_params(data)
    settings = (data.attrs or {}).get("settings", {}) or {}
    project_name = str(settings.get("project_name", "") or "").strip()
    vintage_labels = load_multi_year_vintage_labels(project_name) if project_name else {}
    res_units = require_data_array(
        "res_units", get_var_solution(vars_dict=vars, solution=solution, name="res_units")
    )
    bat_units = require_data_array(
        "battery_units", get_var_solution(vars_dict=vars, solution=solution, name="battery_units")
    )
    bat_inv_power = require_data_array(
        "battery_inverter_power",
        get_var_solution(vars_dict=vars, solution=solution, name="battery_inverter_power"),
    )
    gen_units = require_data_array(
        "generator_units",
        get_var_solution(vars_dict=vars, solution=solution, name="generator_units"),
    )
    res_nom = require_data_array("res_nominal_capacity_kw", p.res_nominal_capacity_kw)
    res_dc_ac_ratio = require_data_array("res_dc_ac_ratio", p.res_dc_ac_ratio)
    bat_nom = require_data_array("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    gen_nom = require_data_array("generator_nominal_capacity_kw", p.generator_nominal_capacity_kw)

    rows = []
    for s in sets.coords["inv_step"].values:
        start_y = (
            str(sets["inv_step_start_year"].sel(inv_step=s).item())
            if "inv_step_start_year" in sets
            else ""
        )
        for r in res_units.coords["resource"].values:
            u = float(res_units.sel(inv_step=s, resource=r))
            installed_dc = u * scalarize(res_nom, inv_step=s, resource=r)
            installed_inv_ac = installed_dc / scalarize(res_dc_ac_ratio, resource=r)
            renewable_label = vintage_label_for_step(
                labels=vintage_labels, family="renewable", step=s
            )
            rows.append(
                {
                    "inv_step": s,
                    "inv_step_start_year": start_y,
                    "technology": "renewable",
                    "technology_label": _renewable_display_name(data, r),
                    "vintage_label": renewable_label,
                    "display_label": vintage_display_for_step(
                        labels=vintage_labels, family="renewable", step=s
                    ),
                    "fuel_vintage_label": "",
                    "resource": str(r),
                    "units": u,
                    "installed_capacity": installed_dc,
                    "capacity_unit": "kW",
                    "installed_inverter_capacity_ac": installed_inv_ac,
                    "inverter_capacity_unit": "kW_ac",
                }
            )
        bu = float(bat_units.sel(inv_step=s))
        battery_inv_kw = float(bat_inv_power.sel(inv_step=s))
        battery_label = vintage_label_for_step(labels=vintage_labels, family="battery", step=s)
        rows.append(
            {
                "inv_step": s,
                "inv_step_start_year": start_y,
                "technology": "battery",
                "technology_label": "Battery",
                "vintage_label": battery_label,
                "display_label": vintage_display_for_step(
                    labels=vintage_labels, family="battery", step=s
                ),
                "fuel_vintage_label": "",
                "resource": "",
                "units": bu,
                "installed_capacity": bu * scalarize(bat_nom, inv_step=s),
                "capacity_unit": "kWh",
                "installed_inverter_capacity_ac": battery_inv_kw,
                "inverter_capacity_unit": "kW",
            }
        )
        gu = float(gen_units.sel(inv_step=s))
        generator_label = vintage_label_for_step(labels=vintage_labels, family="generator", step=s)
        fuel_label = vintage_label_for_step(labels=vintage_labels, family="fuel", step=s)
        rows.append(
            {
                "inv_step": s,
                "inv_step_start_year": start_y,
                "technology": "generator",
                "technology_label": "Generator",
                "vintage_label": generator_label,
                "display_label": vintage_display_for_step(
                    labels=vintage_labels, family="generator", step=s
                ),
                "fuel_vintage_label": fuel_label,
                "resource": "",
                "units": gu,
                "installed_capacity": gu * scalarize(gen_nom, inv_step=s),
                "capacity_unit": "kW",
                "installed_inverter_capacity_ac": np.nan,
                "inverter_capacity_unit": "",
            }
        )
    return pd.DataFrame(rows)


def build_renewable_inverter_design_by_step_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> pd.DataFrame:
    p = get_params(data)
    design = build_design_by_step_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    res_capex = require_data_array(
        "res_inverter_specific_investment_cost_per_kw_ac",
        p.res_inverter_specific_investment_cost_per_kw_ac,
    )
    res_life = require_data_array("res_inverter_lifetime_years", p.res_inverter_lifetime_years)
    res_fom = p.res_inverter_fixed_om_share_per_year
    rows = []
    renewable_rows = design[design["technology"] == "renewable"].copy()
    for _, row in renewable_rows.iterrows():
        inv_step = str(row["inv_step"])
        resource = str(row["resource"])
        rows.append(
            {
                "inv_step": inv_step,
                "inv_step_start_year": str(row["inv_step_start_year"]),
                "resource": resource,
                "technology_label": str(row.get("technology_label", resource)),
                "installed_inverter_capacity_ac_kw": float(
                    row.get("installed_inverter_capacity_ac", 0.0)
                ),
                "specific_investment_cost_per_kw_ac": _scalar_param(
                    res_capex, inv_step=inv_step, resource=resource
                ),
                "lifetime_years": _scalar_param(res_life, inv_step=inv_step, resource=resource),
                "fixed_om_share_per_year": _scalar_param(
                    res_fom, inv_step=inv_step, resource=resource
                )
                if isinstance(res_fom, xr.DataArray)
                else 0.0,
            }
        )
    return pd.DataFrame(rows)


def build_battery_inverter_design_by_step_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> pd.DataFrame:
    p = get_params(data)
    design = build_design_by_step_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    bat_capex = require_data_array(
        "battery_inverter_specific_investment_cost_per_kw",
        p.battery_inverter_specific_investment_cost_per_kw,
    )
    bat_life = require_data_array(
        "battery_inverter_lifetime_years", p.battery_inverter_lifetime_years
    )
    bat_fom = p.battery_inverter_fixed_om_share_per_year
    battery_rows = design[design["technology"] == "battery"].copy()
    rows = []
    for _, row in battery_rows.iterrows():
        inv_step = str(row["inv_step"])
        rows.append(
            {
                "inv_step": inv_step,
                "inv_step_start_year": str(row["inv_step_start_year"]),
                "technology_label": "Battery inverter",
                "installed_inverter_power_kw": float(
                    row.get("installed_inverter_capacity_ac", 0.0)
                ),
                "specific_investment_cost_per_kw": _scalar_param(bat_capex, inv_step=inv_step),
                "lifetime_years": _scalar_param(bat_life, inv_step=inv_step),
                "fixed_om_share_per_year": _scalar_param(bat_fom, inv_step=inv_step)
                if isinstance(bat_fom, xr.DataArray)
                else 0.0,
            }
        )
    return pd.DataFrame(rows)


def build_inverter_capacity_by_year_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> pd.DataFrame:
    active_res_dc, active_res_inv_ac, effective_res_ac = _renewable_capacity_tables(
        sets=sets,
        data=data,
        vars=vars,
        solution=solution,
    )
    _, active_bat_inv = _battery_capacity_tables(sets=sets, data=data, vars=vars, solution=solution)
    rows = []
    for year in sets.coords["year"].values.tolist():
        year_label = str(year)
        for resource in active_res_inv_ac.coords["resource"].values.tolist():
            rows.append(
                {
                    "year": year_label,
                    "component": "renewable_inverter",
                    "resource": str(resource),
                    "technology_label": _renewable_display_name(data, resource),
                    "active_dc_capacity_kw": float(
                        active_res_dc.sel(year=year, resource=resource).sum("inv_step")
                    ),
                    "active_inverter_capacity_ac_kw": float(
                        active_res_inv_ac.sel(year=year, resource=resource).sum("inv_step")
                    ),
                    "effective_ac_capacity_kw": float(
                        effective_res_ac.sel(year=year, resource=resource).sum("inv_step")
                    ),
                }
            )
        rows.append(
            {
                "year": year_label,
                "component": "battery_inverter",
                "resource": "",
                "technology_label": "Battery inverter",
                "active_dc_capacity_kw": np.nan,
                "active_inverter_capacity_ac_kw": float(
                    active_bat_inv.sel(year=year).sum("inv_step")
                ),
                "effective_ac_capacity_kw": float(active_bat_inv.sel(year=year).sum("inv_step")),
            }
        )
    return pd.DataFrame(rows)


def build_capacity_by_year_table_multi_year(
    *,
    sets: xr.Dataset,
    design_df: pd.DataFrame,
) -> pd.DataFrame:
    years = [str(y) for y in sets.coords["year"].values.tolist()]
    rows = []
    for year in years:
        active = design_df[design_df["inv_step_start_year"].astype(str) <= year].copy()
        rows.append(
            {
                "year": year,
                "renewables_kw": float(
                    active.loc[active["technology"] == "renewable", "installed_capacity"].sum()
                ),
                "renewable_inverter_kw_ac": float(
                    pd.to_numeric(
                        active.loc[
                            active["technology"] == "renewable", "installed_inverter_capacity_ac"
                        ],
                        errors="coerce",
                    )
                    .fillna(0.0)
                    .sum()
                )
                if "installed_inverter_capacity_ac" in active.columns
                else 0.0,
                "battery_kwh": float(
                    active.loc[active["technology"] == "battery", "installed_capacity"].sum()
                ),
                "battery_inverter_kw": float(
                    pd.to_numeric(
                        active.loc[
                            active["technology"] == "battery", "installed_inverter_capacity_ac"
                        ],
                        errors="coerce",
                    )
                    .fillna(0.0)
                    .sum()
                )
                if "installed_inverter_capacity_ac" in active.columns
                else 0.0,
                "generator_kw": float(
                    active.loc[active["technology"] == "generator", "installed_capacity"].sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def build_yearly_kpis_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
    objective_value: float | None = None,
) -> pd.DataFrame:
    p = get_params(data)
    dispatch = build_dispatch_timeseries_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    fuel_by_step = get_var_solution(vars_dict=vars, solution=solution, name="fuel_consumption")
    fuel = _sum_if_has_inv_step(fuel_by_step)
    bat_units = require_data_array(
        "battery_units", get_var_solution(vars_dict=vars, solution=solution, name="battery_units")
    )
    gen_units = require_data_array(
        "generator_units",
        get_var_solution(vars_dict=vars, solution=solution, name="generator_units"),
    )
    bat_nom = require_data_array("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    gen_nom = require_data_array("generator_nominal_capacity_kw", p.generator_nominal_capacity_kw)
    w = _scenario_weights(p, p.load_demand.coords["scenario"])
    commission_res = replacement_commission_mask(
        sets, require_data_array("res_lifetime_years", p.res_lifetime_years)
    )
    commission_bat = replacement_commission_mask(
        sets,
        require_data_array("battery_calendar_lifetime_years", p.battery_calendar_lifetime_years),
    )
    commission_gen = replacement_commission_mask(
        sets, require_data_array("generator_lifetime_years", p.generator_lifetime_years)
    )
    active_res_dc, active_res_inv_ac, effective_res_ac = _renewable_capacity_tables(
        sets=sets,
        data=data,
        vars=vars,
        solution=solution,
    )
    res_units = require_data_array(
        "res_units", get_var_solution(vars_dict=vars, solution=solution, name="res_units")
    )
    res_nom = require_data_array("res_nominal_capacity_kw", p.res_nominal_capacity_kw)

    rows = []
    for (year, scenario), g in dispatch.groupby(["year", "scenario"], as_index=False):
        demand = float(g["load_demand"].sum())
        ll = float(g["lost_load"].sum())
        served = demand - ll
        res = float(g["res_generation_total"].sum())
        res_potential = float(
            (
                require_data_array("resource_availability", p.resource_availability).sel(
                    year=year, scenario=scenario
                )
                * effective_res_ac.sel(year=year).sum("inv_step")
            ).sum(("period", "resource"))
        )
        res_curtailment = max(res_potential - res, 0.0)
        res_curtailment_share = safe_share(res_curtailment, res_potential)
        inverter_clipping_potential = float(
            (
                require_data_array("resource_availability", p.resource_availability).sel(
                    year=year, scenario=scenario
                )
                * xr.apply_ufunc(
                    np.maximum,
                    (
                        active_res_dc.sel(year=year).sum("inv_step")
                        * require_data_array("res_inverter_efficiency", p.res_inverter_efficiency)
                    )
                    - active_res_inv_ac.sel(year=year).sum("inv_step"),
                    0.0,
                )
            ).sum(("period", "resource"))
        )
        active_inverter_capacity = float(
            active_res_inv_ac.sel(year=year).sum("inv_step").sum("resource")
        )
        gen = float(g["generator_generation"].sum())
        imp = float(g["grid_import"].sum())
        imp_delivered = (
            float(g["grid_import_delivered"].sum()) if "grid_import_delivered" in g.columns else imp
        )
        exp_delivered = (
            float(g["grid_export_delivered"].sum())
            if "grid_export_delivered" in g.columns
            else float(g["grid_export"].sum())
        )
        grid_ren_share = 0.0
        if p.grid_renewable_share is not None:
            grid_ren_share = float(p.grid_renewable_share.sel(scenario=scenario))
        imp_renewable = imp_delivered * grid_ren_share
        denom = res + gen + imp_delivered
        ren_pen = ((res + imp_renewable) / denom) if denom > 0 else 0.0
        ll_frac = (ll / demand) if demand > 0 else 0.0
        fuel_y = 0.0
        if isinstance(fuel, xr.DataArray):
            fuel_y = float(fuel.sel(year=year, scenario=scenario).sum("period"))
        scope1 = 0.0
        if p.fuel_direct_emissions_kgco2e_per_unit_fuel is not None:
            fuel_emission_factor = p.fuel_direct_emissions_kgco2e_per_unit_fuel
            if "inv_step" in fuel_emission_factor.dims and isinstance(fuel_by_step, xr.DataArray):
                extra_dims = set(fuel_emission_factor.dims) - {"inv_step", "year", "scenario"}
                if extra_dims:
                    raise InputValidationError(
                        "fuel_direct_emissions_kgco2e_per_unit_fuel carries unsupported dimensions "
                        f"{sorted(extra_dims)} in multi-year KPI export."
                    )
                fuel_period_by_step = fuel_by_step.sel(year=year, scenario=scenario).sum("period")
                factor = fuel_emission_factor
                if "year" in factor.dims:
                    factor = factor.sel(year=year)
                if "scenario" in factor.dims:
                    factor = factor.sel(scenario=scenario)
                scope1 = float((fuel_period_by_step * factor).sum("inv_step"))
            else:
                scope1 = fuel_y * float(
                    select_or_self(
                        fuel_emission_factor,
                        year=year,
                        scenario=scenario,
                    )
                )
        scope2 = 0.0
        if p.grid_emissions_factor_kgco2e_per_kwh is not None:
            scope2 = imp_delivered * float(
                select_or_self(p.grid_emissions_factor_kgco2e_per_kwh, year=year, scenario=scenario)
            )

        scope3 = 0.0
        if p.res_embedded_emissions_kgco2e_per_kw is not None:
            scope3 += float(
                (
                    res_units
                    * res_nom
                    * p.res_embedded_emissions_kgco2e_per_kw
                    * commission_res.sel(year=year)
                )
                .sum("inv_step")
                .sum("resource")
            )
        if p.battery_embedded_emissions_kgco2e_per_kwh is not None:
            scope3 += float(
                (
                    bat_units
                    * bat_nom
                    * p.battery_embedded_emissions_kgco2e_per_kwh
                    * commission_bat.sel(year=year)
                ).sum("inv_step")
            )
        if p.generator_embedded_emissions_kgco2e_per_kw is not None:
            scope3 += float(
                (
                    gen_units
                    * gen_nom
                    * p.generator_embedded_emissions_kgco2e_per_kw
                    * commission_gen.sel(year=year)
                ).sum("inv_step")
            )
        em = scope1 + scope2 + scope3
        rows.append(
            {
                "year": year,
                "scenario": scenario,
                "total_demand_kwh": demand,
                "served_energy_kwh": served,
                "lost_load_kwh": ll,
                "lost_load_fraction": ll_frac,
                "total_res_kwh": res,
                "renewable_potential_kwh": res_potential,
                "renewable_curtailment_kwh": res_curtailment,
                "renewable_curtailment_share": res_curtailment_share,
                "renewable_inverter_clipping_potential_kwh": inverter_clipping_potential,
                "renewable_active_inverter_capacity_ac_kw": active_inverter_capacity,
                "generator_generation_kwh": gen,
                "grid_import_raw_kwh": imp,
                "grid_import_delivered_kwh": imp_delivered,
                "grid_export_delivered_kwh": exp_delivered,
                "grid_renewable_kwh": imp_renewable,
                "renewable_penetration": ren_pen,
                "fuel_consumption": fuel_y,
                "scope1_emissions_kgco2e": scope1,
                "scope2_emissions_kgco2e": scope2,
                "scope3_emissions_kgco2e": scope3,
                "emissions_kgco2e": em,
                "objective_value": safe_float(objective_value),
            }
        )

    out = pd.DataFrame(rows)
    w_map = {str(s): float(w.sel(scenario=s)) for s in w.coords["scenario"].values}
    out["weight"] = out["scenario"].astype(str).map(w_map).fillna(0.0)
    num_cols = [c for c in out.columns if c not in ("year", "scenario", "weight")]
    expected_rows = []
    for year, gy in out.groupby("year", as_index=False):
        row = {"year": year, "scenario": "expected"}
        for c in num_cols:
            if c == "objective_value":
                row[c] = safe_float(objective_value)
            else:
                row[c] = float((gy[c] * gy["weight"]).sum())
        expected_rows.append(row)
    return pd.concat([out.drop(columns=["weight"]), pd.DataFrame(expected_rows)], ignore_index=True)


def build_inverter_metrics_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> pd.DataFrame:
    dispatch = build_dispatch_timeseries_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    inverter_capacity = build_inverter_capacity_by_year_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    kpis = build_yearly_kpis_table_multi_year(sets=sets, data=data, vars=vars, solution=solution)
    weights = _scenario_weights(get_params(data), sets.coords["scenario"])
    weight_map = {str(s): float(weights.sel(scenario=s)) for s in weights.coords["scenario"].values}

    rows = []
    for year in sets.coords["year"].values.tolist():
        year_label = str(year)
        year_dispatch = dispatch[dispatch["year"].astype(str) == year_label].copy()
        year_dispatch["weight"] = year_dispatch["scenario"].astype(str).map(weight_map).fillna(0.0)
        weighted_battery_inv = (
            year_dispatch.assign(
                weighted_dispatch=pd.to_numeric(
                    year_dispatch.get("battery_inverter_active_power", pd.Series([0.0])),
                    errors="coerce",
                ).fillna(0.0)
                * year_dispatch["weight"]
            )
            .groupby("period", as_index=False)["weighted_dispatch"]
            .sum()
        )
        peak_battery_inv = float(
            pd.to_numeric(
                weighted_battery_inv.get("weighted_dispatch", pd.Series([0.0])), errors="coerce"
            )
            .fillna(0.0)
            .max()
        )
        battery_capacity_row = inverter_capacity[
            (inverter_capacity["year"].astype(str) == year_label)
            & (inverter_capacity["component"] == "battery_inverter")
        ]
        battery_capacity = (
            float(battery_capacity_row["active_inverter_capacity_ac_kw"].sum())
            if not battery_capacity_row.empty
            else 0.0
        )
        rows.append(
            {
                "year": year_label,
                "component": "battery_inverter",
                "resource": "",
                "technology_label": "Battery inverter",
                "active_inverter_capacity_ac_kw": battery_capacity,
                "peak_dispatch_or_power_kw": peak_battery_inv,
                "peak_utilization_pct": safe_share(peak_battery_inv, battery_capacity) * 100.0,
                "renewable_inverter_clipping_potential_kwh": np.nan,
            }
        )
        year_kpis = kpis[
            (kpis["year"].astype(str) == year_label)
            & (kpis["scenario"].astype(str).str.lower() == "expected")
        ]
        clipping = (
            float(year_kpis["renewable_inverter_clipping_potential_kwh"].iloc[0])
            if not year_kpis.empty
            and "renewable_inverter_clipping_potential_kwh" in year_kpis.columns
            else 0.0
        )
        for resource in data.coords["resource"].values.tolist():
            resource_col = f"res_generation__{resource}"
            weighted_resource = (
                year_dispatch.assign(
                    weighted_dispatch=pd.to_numeric(
                        year_dispatch.get(resource_col, pd.Series([0.0])), errors="coerce"
                    ).fillna(0.0)
                    * year_dispatch["weight"]
                )
                .groupby("period", as_index=False)["weighted_dispatch"]
                .sum()
            )
            resource_capacity = inverter_capacity[
                (inverter_capacity["year"].astype(str) == year_label)
                & (inverter_capacity["component"] == "renewable_inverter")
                & (inverter_capacity["resource"].astype(str) == str(resource))
            ]
            active_capacity = (
                float(resource_capacity["active_inverter_capacity_ac_kw"].sum())
                if not resource_capacity.empty
                else 0.0
            )
            peak_dispatch = float(
                pd.to_numeric(
                    weighted_resource.get("weighted_dispatch", pd.Series([0.0])), errors="coerce"
                )
                .fillna(0.0)
                .max()
            )
            rows.append(
                {
                    "year": year_label,
                    "component": "renewable_inverter",
                    "resource": str(resource),
                    "technology_label": _renewable_display_name(data, resource),
                    "active_inverter_capacity_ac_kw": active_capacity,
                    "peak_dispatch_or_power_kw": peak_dispatch,
                    "peak_utilization_pct": safe_share(peak_dispatch, active_capacity) * 100.0,
                    "renewable_inverter_clipping_potential_kwh": clipping,
                }
            )
    return pd.DataFrame(rows)


def build_discounted_cashflows_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> pd.DataFrame:
    p = get_params(data)
    w = _scenario_weights(p, sets.coords["scenario"])
    rs = float(p.settings.get("social_discount_rate", 0.0) or 0.0)
    disc = 1.0 / ((1.0 + rs) ** year_ordinal(sets))

    res_units = require_data_array(
        "res_units", get_var_solution(vars_dict=vars, solution=solution, name="res_units")
    )
    bat_units = require_data_array(
        "battery_units", get_var_solution(vars_dict=vars, solution=solution, name="battery_units")
    )
    bat_inv_power = require_data_array(
        "battery_inverter_power",
        get_var_solution(vars_dict=vars, solution=solution, name="battery_inverter_power"),
    )
    gen_units = require_data_array(
        "generator_units",
        get_var_solution(vars_dict=vars, solution=solution, name="generator_units"),
    )
    res_gen = require_data_array(
        "res_generation", get_var_solution(vars_dict=vars, solution=solution, name="res_generation")
    )
    fuel_cons = require_data_array(
        "fuel_consumption",
        get_var_solution(vars_dict=vars, solution=solution, name="fuel_consumption"),
    )
    lost_load = require_data_array(
        "lost_load", get_var_solution(vars_dict=vars, solution=solution, name="lost_load")
    )
    gimp = get_var_solution(vars_dict=vars, solution=solution, name="grid_import")
    gexp = get_var_solution(vars_dict=vars, solution=solution, name="grid_export")

    res_nom = require_data_array("res_nominal_capacity_kw", p.res_nominal_capacity_kw)
    res_capex = require_data_array(
        "res_specific_investment_cost_per_kw", p.res_specific_investment_cost_per_kw
    )
    res_inv_capex = require_data_array(
        "res_inverter_specific_investment_cost_per_kw_ac",
        p.res_inverter_specific_investment_cost_per_kw_ac,
    )
    res_life = require_data_array("res_lifetime_years", p.res_lifetime_years)
    res_inv_life = require_data_array("res_inverter_lifetime_years", p.res_inverter_lifetime_years)
    res_wacc = require_data_array("res_wacc", p.res_wacc)
    res_grant = require_data_array("res_grant_share_of_capex", p.res_grant_share_of_capex)
    res_dc_ac_ratio = require_data_array("res_dc_ac_ratio", p.res_dc_ac_ratio)
    bat_nom = require_data_array("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    bat_capex = require_data_array(
        "battery_specific_investment_cost_per_kwh", p.battery_specific_investment_cost_per_kwh
    )
    bat_inv_capex = require_data_array(
        "battery_inverter_specific_investment_cost_per_kw",
        p.battery_inverter_specific_investment_cost_per_kw,
    )
    bat_life = require_data_array(
        "battery_calendar_lifetime_years", p.battery_calendar_lifetime_years
    )
    bat_inv_life = require_data_array(
        "battery_inverter_lifetime_years", p.battery_inverter_lifetime_years
    )
    bat_wacc = require_data_array("battery_wacc", p.battery_wacc)
    gen_nom = require_data_array("generator_nominal_capacity_kw", p.generator_nominal_capacity_kw)
    gen_capex = require_data_array(
        "generator_specific_investment_cost_per_kw", p.generator_specific_investment_cost_per_kw
    )
    gen_life = require_data_array("generator_lifetime_years", p.generator_lifetime_years)
    gen_wacc = require_data_array("generator_wacc", p.generator_wacc)

    res_inv = res_units * res_nom * res_capex * (1.0 - res_grant)
    res_inv_inverter = (res_units * res_nom / res_dc_ac_ratio) * res_inv_capex * (1.0 - res_grant)
    bat_inv = bat_units * bat_nom * bat_capex
    bat_inv_converter = bat_inv_power * bat_inv_capex
    gen_inv = gen_units * gen_nom * gen_capex
    ann_res = res_inv * _crf(res_wacc, res_life)
    ann_res_inverter = res_inv_inverter * _crf(res_wacc, res_inv_life)
    ann_bat = bat_inv * _crf(bat_wacc, bat_life)
    ann_bat_inverter = bat_inv_converter * _crf(bat_wacc, bat_inv_life)
    ann_gen = gen_inv * _crf(gen_wacc, gen_life)
    act_res = replacement_active_mask(sets)
    act_bat = replacement_active_mask(sets)
    act_gen = replacement_active_mask(sets)
    ann_res_y = (ann_res * act_res).sum("inv_step").sum("resource")
    ann_res_inv_y = (ann_res_inverter * act_res).sum("inv_step").sum("resource")
    ann_bat_y = (ann_bat * act_bat).sum("inv_step")
    ann_bat_inv_y = (ann_bat_inverter * act_bat).sum("inv_step")
    ann_gen_y = (ann_gen * act_gen).sum("inv_step")

    fuel_price = (
        p.fuel_cost_per_unit_fuel
        if p.fuel_cost_per_unit_fuel is not None
        else p.fuel_fuel_cost_per_unit_fuel
    )
    fuel_price = require_data_array("fuel_cost_per_unit_fuel", fuel_price)
    opex_y_s = (fuel_cons * fuel_price).sum("period").sum("inv_step")
    if p.is_grid_on() and isinstance(gimp, xr.DataArray) and p.grid_import_price is not None:
        opex_y_s = opex_y_s + (gimp * p.grid_import_price).sum("period")
    if (
        p.is_grid_export_enabled()
        and isinstance(gexp, xr.DataArray)
        and p.grid_export_price is not None
    ):
        opex_y_s = opex_y_s - (gexp * p.grid_export_price).sum("period")
    if p.res_production_subsidy_per_kwh is not None:
        subsidy = _renewable_subsidy_by_year(sets, p.res_production_subsidy_per_kwh)
        opex_y_s = opex_y_s - (res_gen * subsidy).sum("period").sum("resource")

    ext_y_s = xr.DataArray(0.0).broadcast_like(opex_y_s)
    fixed_om_res_inv_y_s = _as_year_scenario_da(0.0, sets)
    fixed_om_bat_inv_y_s = _as_year_scenario_da(0.0, sets)
    if p.res_inverter_fixed_om_share_per_year is not None:
        fixed_om_res_inv_y_s = _as_year_scenario_da(
            (res_inv_inverter * p.res_inverter_fixed_om_share_per_year * act_res)
            .sum("inv_step")
            .sum("resource"),
            sets,
        )
        opex_y_s = opex_y_s + fixed_om_res_inv_y_s
    if p.battery_inverter_fixed_om_share_per_year is not None:
        fixed_om_bat_inv_y_s = _as_year_scenario_da(
            (bat_inv_converter * p.battery_inverter_fixed_om_share_per_year * act_bat).sum(
                "inv_step"
            ),
            sets,
        )
        opex_y_s = opex_y_s + fixed_om_bat_inv_y_s
    if p.lost_load_cost_per_kwh is not None:
        ext_y_s = ext_y_s + lost_load.sum("period") * p.lost_load_cost_per_kwh
    if (
        p.fuel_direct_emissions_kgco2e_per_unit_fuel is not None
        and p.emission_cost_per_kgco2e is not None
    ):
        ext_y_s = (
            ext_y_s
            + (fuel_cons.sum("period") * p.fuel_direct_emissions_kgco2e_per_unit_fuel).sum(
                "inv_step"
            )
            * p.emission_cost_per_kgco2e
        )

    commission_res = replacement_commission_mask(sets, res_life)
    commission_bat = replacement_commission_mask(sets, bat_life)
    commission_gen = replacement_commission_mask(sets, gen_life)
    emb_y = xr.DataArray(0.0).broadcast_like(ann_res_y)
    em_cost_exp = 0.0
    if p.emission_cost_per_kgco2e is not None:
        em_cost_exp = (
            (p.emission_cost_per_kgco2e * w).sum("scenario")
            if "scenario" in p.emission_cost_per_kgco2e.dims
            else p.emission_cost_per_kgco2e
        )
    if p.res_embedded_emissions_kgco2e_per_kw is not None:
        emb_y = (
            emb_y
            + (res_units * res_nom * p.res_embedded_emissions_kgco2e_per_kw * commission_res)
            .sum("inv_step")
            .sum("resource")
            * em_cost_exp
        )
    if p.battery_embedded_emissions_kgco2e_per_kwh is not None:
        emb_y = (
            emb_y
            + (
                bat_units * bat_nom * p.battery_embedded_emissions_kgco2e_per_kwh * commission_bat
            ).sum("inv_step")
            * em_cost_exp
        )
    if p.generator_embedded_emissions_kgco2e_per_kw is not None:
        emb_y = (
            emb_y
            + (
                gen_units * gen_nom * p.generator_embedded_emissions_kgco2e_per_kw * commission_gen
            ).sum("inv_step")
            * em_cost_exp
        )

    opex_exp_y = (opex_y_s * w).sum("scenario")
    ext_exp_y = (ext_y_s * w).sum("scenario")
    gross_y = (
        ann_res_y
        + ann_res_inv_y
        + ann_bat_y
        + ann_bat_inv_y
        + ann_gen_y
        + opex_exp_y
        + ext_exp_y
        + emb_y
    )
    discounted_y = gross_y * disc

    # Reporting-only indicator of the discounted annuity stream that would
    # continue beyond the modeled horizon. It is not part of the optimized
    # objective and should not be interpreted as an in-objective salvage credit.
    post_horizon_annuity_tail = (
        discounted_annuity_tail_memo(sets, ann_res, res_life, rs).sum("inv_step").sum("resource")
        + discounted_annuity_tail_memo(sets, ann_res_inverter, res_inv_life, rs)
        .sum("inv_step")
        .sum("resource")
        + discounted_annuity_tail_memo(sets, ann_bat, bat_life, rs).sum("inv_step")
        + discounted_annuity_tail_memo(sets, ann_bat_inverter, bat_inv_life, rs).sum("inv_step")
        + discounted_annuity_tail_memo(sets, ann_gen, gen_life, rs).sum("inv_step")
    )

    rows = []
    years = sets.coords["year"].values.tolist()
    last_year = years[-1]
    for y in years:
        post_horizon_tail = safe_float(post_horizon_annuity_tail) if y == last_year else 0.0
        row = {
            "year": y,
            "discount_factor": float(disc.sel(year=y)),
            "annuity_res": float(ann_res_y.sel(year=y)),
            "annuity_res_inverter": float(ann_res_inv_y.sel(year=y)),
            "annuity_battery": float(ann_bat_y.sel(year=y)),
            "annuity_battery_inverter": float(ann_bat_inv_y.sel(year=y)),
            "annuity_generator": float(ann_gen_y.sel(year=y)),
            "opex_expected": float(opex_exp_y.sel(year=y)),
            "externalities_expected": float(ext_exp_y.sel(year=y)),
            "embedded_expected": float(emb_y.sel(year=y)),
            "total_before_discount": float(gross_y.sel(year=y)),
            "discounted_total": float(discounted_y.sel(year=y)),
            "post_horizon_annuity_tail_discounted": post_horizon_tail,
            "discounted_objective_contribution": float(discounted_y.sel(year=y)),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def build_scenario_costs_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
) -> pd.DataFrame:
    p = get_params(data)
    weights = _scenario_weights(p, sets.coords["scenario"])

    res_units = require_data_array(
        "res_units", get_var_solution(vars_dict=vars, solution=solution, name="res_units")
    )
    bat_units = require_data_array(
        "battery_units", get_var_solution(vars_dict=vars, solution=solution, name="battery_units")
    )
    bat_inv_power = require_data_array(
        "battery_inverter_power",
        get_var_solution(vars_dict=vars, solution=solution, name="battery_inverter_power"),
    )
    gen_units = require_data_array(
        "generator_units",
        get_var_solution(vars_dict=vars, solution=solution, name="generator_units"),
    )
    res_gen = require_data_array(
        "res_generation", get_var_solution(vars_dict=vars, solution=solution, name="res_generation")
    )
    fuel_cons = require_data_array(
        "fuel_consumption",
        get_var_solution(vars_dict=vars, solution=solution, name="fuel_consumption"),
    )
    lost_load = require_data_array(
        "lost_load", get_var_solution(vars_dict=vars, solution=solution, name="lost_load")
    )

    grid_imp = get_var_solution(vars_dict=vars, solution=solution, name="grid_import")
    grid_exp = get_var_solution(vars_dict=vars, solution=solution, name="grid_export")

    res_nom = require_data_array("res_nominal_capacity_kw", p.res_nominal_capacity_kw)
    res_capex = require_data_array(
        "res_specific_investment_cost_per_kw", p.res_specific_investment_cost_per_kw
    )
    res_inv_capex = require_data_array(
        "res_inverter_specific_investment_cost_per_kw_ac",
        p.res_inverter_specific_investment_cost_per_kw_ac,
    )
    res_dc_ac_ratio = require_data_array("res_dc_ac_ratio", p.res_dc_ac_ratio)
    res_grant = require_data_array("res_grant_share_of_capex", p.res_grant_share_of_capex)
    bat_nom = require_data_array("battery_nominal_capacity_kwh", p.battery_nominal_capacity_kwh)
    bat_capex = require_data_array(
        "battery_specific_investment_cost_per_kwh", p.battery_specific_investment_cost_per_kwh
    )
    bat_inv_capex = require_data_array(
        "battery_inverter_specific_investment_cost_per_kw",
        p.battery_inverter_specific_investment_cost_per_kw,
    )
    gen_nom = require_data_array("generator_nominal_capacity_kw", p.generator_nominal_capacity_kw)
    gen_capex = require_data_array(
        "generator_specific_investment_cost_per_kw", p.generator_specific_investment_cost_per_kw
    )

    fuel_price = (
        p.fuel_cost_per_unit_fuel
        if p.fuel_cost_per_unit_fuel is not None
        else p.fuel_fuel_cost_per_unit_fuel
    )
    fuel_cost_y_s = (
        _as_year_scenario_da((fuel_cons * fuel_price).sum("period").sum("inv_step"), sets)
        if fuel_price is not None
        else _as_year_scenario_da(0.0, sets)
    )
    grid_import_cost_y_s = (
        _as_year_scenario_da((grid_imp * p.grid_import_price).sum("period"), sets)
        if (
            p.is_grid_on()
            and isinstance(grid_imp, xr.DataArray)
            and p.grid_import_price is not None
        )
        else _as_year_scenario_da(0.0, sets)
    )
    grid_export_rev_y_s = (
        _as_year_scenario_da((grid_exp * p.grid_export_price).sum("period"), sets)
        if (
            p.is_grid_export_enabled()
            and isinstance(grid_exp, xr.DataArray)
            and p.grid_export_price is not None
        )
        else _as_year_scenario_da(0.0, sets)
    )

    res_subsidy_y_s = _as_year_scenario_da(0.0, sets)
    if p.res_production_subsidy_per_kwh is not None:
        subsidy = _renewable_subsidy_by_year(sets, p.res_production_subsidy_per_kwh)
        res_subsidy_y_s = _as_year_scenario_da(
            (res_gen * subsidy).sum("period").sum("resource"), sets
        )

    res_inv = res_units * res_nom * res_capex * (1.0 - res_grant)
    res_inv_inverter = (res_units * res_nom / res_dc_ac_ratio) * res_inv_capex * (1.0 - res_grant)
    bat_inv = bat_units * bat_nom * bat_capex
    bat_inv_converter = bat_inv_power * bat_inv_capex
    gen_inv = gen_units * gen_nom * gen_capex
    active = replacement_active_mask(sets)

    res_fom_share = (
        p.res_fixed_om_share_per_year if p.res_fixed_om_share_per_year is not None else 0.0
    )
    res_inv_fom_share = (
        p.res_inverter_fixed_om_share_per_year
        if p.res_inverter_fixed_om_share_per_year is not None
        else 0.0
    )
    bat_fom_share = (
        p.battery_fixed_om_share_per_year if p.battery_fixed_om_share_per_year is not None else 0.0
    )
    bat_inv_fom_share = (
        p.battery_inverter_fixed_om_share_per_year
        if p.battery_inverter_fixed_om_share_per_year is not None
        else 0.0
    )
    gen_fom_share = (
        p.generator_fixed_om_share_per_year
        if p.generator_fixed_om_share_per_year is not None
        else 0.0
    )

    fixed_om_res_y_s = _as_year_scenario_da(
        (res_inv * res_fom_share * active).sum("inv_step").sum("resource"), sets
    )
    fixed_om_res_inverter_y_s = _as_year_scenario_da(
        (res_inv_inverter * res_inv_fom_share * active).sum("inv_step").sum("resource"), sets
    )
    fixed_om_battery_y_s = _as_year_scenario_da(
        (bat_inv * bat_fom_share * active).sum("inv_step"), sets
    )
    fixed_om_battery_inverter_y_s = _as_year_scenario_da(
        (bat_inv_converter * bat_inv_fom_share * active).sum("inv_step"), sets
    )
    fixed_om_generator_y_s = _as_year_scenario_da(
        (gen_inv * gen_fom_share * active).sum("inv_step"), sets
    )

    lost_load_cost_y_s = (
        _as_year_scenario_da(lost_load.sum("period") * p.lost_load_cost_per_kwh, sets)
        if p.lost_load_cost_per_kwh is not None
        else _as_year_scenario_da(0.0, sets)
    )

    scope1_y_s = (
        _as_year_scenario_da(
            (fuel_cons.sum("period") * p.fuel_direct_emissions_kgco2e_per_unit_fuel).sum(
                "inv_step"
            ),
            sets,
        )
        if p.fuel_direct_emissions_kgco2e_per_unit_fuel is not None
        else _as_year_scenario_da(0.0, sets)
    )
    scope2_y_s = _as_year_scenario_da(0.0, sets)
    if (
        p.is_grid_on()
        and isinstance(grid_imp, xr.DataArray)
        and p.grid_transmission_efficiency is not None
        and p.grid_emissions_factor_kgco2e_per_kwh is not None
    ):
        scope2_y_s = _as_year_scenario_da(
            (grid_imp * p.grid_transmission_efficiency).sum("period")
            * p.grid_emissions_factor_kgco2e_per_kwh,
            sets,
        )

    commission_res = replacement_commission_mask(
        sets, require_data_array("res_lifetime_years", p.res_lifetime_years)
    )
    commission_bat = replacement_commission_mask(
        sets,
        require_data_array("battery_calendar_lifetime_years", p.battery_calendar_lifetime_years),
    )
    commission_gen = replacement_commission_mask(
        sets, require_data_array("generator_lifetime_years", p.generator_lifetime_years)
    )

    scope3_res_y = (
        _as_year_scenario_da(
            (res_units * res_nom * p.res_embedded_emissions_kgco2e_per_kw * commission_res)
            .sum("inv_step")
            .sum("resource"),
            sets,
        )
        if p.res_embedded_emissions_kgco2e_per_kw is not None
        else _as_year_scenario_da(0.0, sets)
    )
    scope3_battery_y = (
        _as_year_scenario_da(
            (
                bat_units * bat_nom * p.battery_embedded_emissions_kgco2e_per_kwh * commission_bat
            ).sum("inv_step"),
            sets,
        )
        if p.battery_embedded_emissions_kgco2e_per_kwh is not None
        else _as_year_scenario_da(0.0, sets)
    )
    scope3_generator_y = (
        _as_year_scenario_da(
            (
                gen_units * gen_nom * p.generator_embedded_emissions_kgco2e_per_kw * commission_gen
            ).sum("inv_step"),
            sets,
        )
        if p.generator_embedded_emissions_kgco2e_per_kw is not None
        else _as_year_scenario_da(0.0, sets)
    )
    scope3_y_s = scope3_res_y + scope3_battery_y + scope3_generator_y

    emission_cost_y_s = (
        _as_year_scenario_da(p.emission_cost_per_kgco2e, sets)
        if p.emission_cost_per_kgco2e is not None
        else _as_year_scenario_da(0.0, sets)
    )
    scope1_cost_y_s = scope1_y_s * emission_cost_y_s
    scope2_cost_y_s = scope2_y_s * emission_cost_y_s
    scope3_res_cost_y_s = scope3_res_y * emission_cost_y_s
    scope3_battery_cost_y_s = scope3_battery_y * emission_cost_y_s
    scope3_generator_cost_y_s = scope3_generator_y * emission_cost_y_s
    emissions_cost_y_s = (
        scope1_cost_y_s
        + scope2_cost_y_s
        + scope3_res_cost_y_s
        + scope3_battery_cost_y_s
        + scope3_generator_cost_y_s
    )

    variable_cost_y_s = fuel_cost_y_s + grid_import_cost_y_s - grid_export_rev_y_s - res_subsidy_y_s
    total_operating_cost_y_s = (
        variable_cost_y_s
        + fixed_om_res_y_s
        + fixed_om_res_inverter_y_s
        + fixed_om_battery_y_s
        + fixed_om_battery_inverter_y_s
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
                    "fuel_cost": scalarize(fuel_cost_y_s, year=year, scenario=scenario),
                    "grid_import_cost": scalarize(
                        grid_import_cost_y_s, year=year, scenario=scenario
                    ),
                    "grid_export_revenue": scalarize(
                        grid_export_rev_y_s, year=year, scenario=scenario
                    ),
                    "res_subsidy_revenue": scalarize(res_subsidy_y_s, year=year, scenario=scenario),
                    "annual_variable_cost": scalarize(
                        variable_cost_y_s, year=year, scenario=scenario
                    ),
                    "fixed_om_res": scalarize(fixed_om_res_y_s, year=year, scenario=scenario),
                    "fixed_om_res_inverter": scalarize(
                        fixed_om_res_inverter_y_s, year=year, scenario=scenario
                    ),
                    "fixed_om_battery": scalarize(
                        fixed_om_battery_y_s, year=year, scenario=scenario
                    ),
                    "fixed_om_battery_inverter": scalarize(
                        fixed_om_battery_inverter_y_s, year=year, scenario=scenario
                    ),
                    "fixed_om_generator": scalarize(
                        fixed_om_generator_y_s, year=year, scenario=scenario
                    ),
                    "fixed_om_total": scalarize(
                        fixed_om_res_y_s
                        + fixed_om_res_inverter_y_s
                        + fixed_om_battery_y_s
                        + fixed_om_battery_inverter_y_s
                        + fixed_om_generator_y_s,
                        year=year,
                        scenario=scenario,
                    ),
                    "lost_load_penalty": scalarize(
                        lost_load_cost_y_s, year=year, scenario=scenario
                    ),
                    "scope1_emissions": scalarize(scope1_y_s, year=year, scenario=scenario),
                    "scope2_emissions": scalarize(scope2_y_s, year=year, scenario=scenario),
                    "scope3_res_emissions": scalarize(scope3_res_y, year=year, scenario=scenario),
                    "scope3_battery_emissions": scalarize(
                        scope3_battery_y, year=year, scenario=scenario
                    ),
                    "scope3_generator_emissions": scalarize(
                        scope3_generator_y, year=year, scenario=scenario
                    ),
                    "scope3_emissions": scalarize(scope3_y_s, year=year, scenario=scenario),
                    "total_emissions": scalarize(
                        scope1_y_s + scope2_y_s + scope3_y_s, year=year, scenario=scenario
                    ),
                    "scope1_emissions_cost": scalarize(
                        scope1_cost_y_s, year=year, scenario=scenario
                    ),
                    "scope2_emissions_cost": scalarize(
                        scope2_cost_y_s, year=year, scenario=scenario
                    ),
                    "scope3_res_emissions_cost": scalarize(
                        scope3_res_cost_y_s, year=year, scenario=scenario
                    ),
                    "scope3_battery_emissions_cost": scalarize(
                        scope3_battery_cost_y_s, year=year, scenario=scenario
                    ),
                    "scope3_generator_emissions_cost": scalarize(
                        scope3_generator_cost_y_s, year=year, scenario=scenario
                    ),
                    "emissions_cost": scalarize(emissions_cost_y_s, year=year, scenario=scenario),
                    "total_operating_cost": scalarize(
                        total_operating_cost_y_s, year=year, scenario=scenario
                    ),
                }
            )

    scenario_df = pd.DataFrame(rows)
    numeric_cols = [col for col in scenario_df.columns if col not in {"year", "scenario", "weight"}]
    return _append_expected_rows(scenario_df, numeric_cols=numeric_cols)


def build_investment_summary_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    design_df: pd.DataFrame,
) -> pd.DataFrame:
    p = get_params(data)
    rs = float(p.settings.get("social_discount_rate", 0.0) or 0.0)
    years = [str(y) for y in sets.coords["year"].values.tolist()]
    start_year_map = (
        {
            str(step): str(sets["inv_step_start_year"].sel(inv_step=step).item())
            for step in sets.coords["inv_step"].values
        }
        if "inv_step_start_year" in sets
        else {}
    )
    year_to_ordinal = {year: idx for idx, year in enumerate(years)}

    rows = []
    for _, row in design_df.iterrows():
        technology = str(row.get("technology", "")).strip().lower()
        inv_step = str(row.get("inv_step", ""))
        resource = str(row.get("resource", "")).strip()
        installed_capacity = float(
            pd.to_numeric(pd.Series([row.get("installed_capacity", 0.0)]), errors="coerce")
            .fillna(0.0)
            .iloc[0]
        )
        if installed_capacity == 0.0:
            continue
        start_year = str(
            row.get("inv_step_start_year", start_year_map.get(inv_step, years[0] if years else ""))
        )
        discount_factor = 1.0 / ((1.0 + rs) ** year_to_ordinal.get(start_year, 0))

        if technology == "renewable":
            capex = _scalar_param(
                p.res_specific_investment_cost_per_kw, inv_step=inv_step, resource=resource
            )
            inv_capex = _scalar_param(
                p.res_inverter_specific_investment_cost_per_kw_ac,
                inv_step=inv_step,
                resource=resource,
            )
            grant = _scalar_param(p.res_grant_share_of_capex, inv_step=inv_step, resource=resource)
            nominal = installed_capacity * capex * (1.0 - grant)
            label = str(row.get("technology_label", resource))
            unit = "kW"
            inverter_capacity = float(
                pd.to_numeric(
                    pd.Series([row.get("installed_inverter_capacity_ac", 0.0)]), errors="coerce"
                )
                .fillna(0.0)
                .iloc[0]
            )
            if inverter_capacity > 0.0:
                rows.append(
                    {
                        "Technology": f"{label} inverter",
                        "Capacity unit": "kW_ac",
                        "Nominal investment cost": inverter_capacity * inv_capex * (1.0 - grant),
                        "Present-value investment cost": inverter_capacity
                        * inv_capex
                        * (1.0 - grant)
                        * discount_factor,
                    }
                )
        elif technology == "battery":
            capex = _scalar_param(p.battery_specific_investment_cost_per_kwh, inv_step=inv_step)
            nominal = installed_capacity * capex
            label = "Battery"
            unit = "kWh"
            inverter_capacity = float(
                pd.to_numeric(
                    pd.Series([row.get("installed_inverter_capacity_ac", 0.0)]), errors="coerce"
                )
                .fillna(0.0)
                .iloc[0]
            )
            inv_capex = _scalar_param(
                p.battery_inverter_specific_investment_cost_per_kw, inv_step=inv_step
            )
            if inverter_capacity > 0.0:
                rows.append(
                    {
                        "Technology": "Battery inverter",
                        "Capacity unit": "kW",
                        "Nominal investment cost": inverter_capacity * inv_capex,
                        "Present-value investment cost": inverter_capacity
                        * inv_capex
                        * discount_factor,
                    }
                )
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
        return pd.DataFrame(
            columns=[
                "Technology",
                "Capacity unit",
                "Nominal investment cost",
                "Present-value investment cost",
            ]
        )

    out = pd.DataFrame(rows)
    return out.groupby(["Technology", "Capacity unit"], as_index=False)[
        ["Nominal investment cost", "Present-value investment cost"]
    ].sum()


def build_yearly_expected_table_multi_year(
    cash_df: pd.DataFrame, scenario_costs_df: pd.DataFrame
) -> pd.DataFrame:
    cash = cash_df.copy()
    cash["year"] = cash["year"].astype(str)
    expected = scenario_costs_df[
        scenario_costs_df["scenario"].astype(str).str.lower() == "expected"
    ].copy()
    expected["year"] = expected["year"].astype(str)
    expected = expected.drop(columns=["scenario", "weight"], errors="ignore")
    yearly = cash.merge(expected, on="year", how="left")
    for column in [
        "annuity_res",
        "annuity_res_inverter",
        "annuity_battery",
        "annuity_battery_inverter",
        "annuity_generator",
        "fixed_om_res",
        "fixed_om_res_inverter",
        "fixed_om_battery",
        "fixed_om_battery_inverter",
        "fixed_om_generator",
        "res_subsidy_revenue",
        "scope3_res_emissions_cost",
        "scope3_battery_emissions_cost",
        "fuel_cost",
        "scope1_emissions_cost",
        "scope3_generator_emissions_cost",
        "grid_import_cost",
        "grid_export_revenue",
        "lost_load_penalty",
        "scope2_emissions_cost",
    ]:
        if column not in yearly.columns:
            yearly[column] = 0.0
    yearly["annuity_total"] = yearly[
        [
            "annuity_res",
            "annuity_res_inverter",
            "annuity_battery",
            "annuity_battery_inverter",
            "annuity_generator",
        ]
    ].sum(axis=1)
    yearly["renewables_cost"] = (
        yearly["annuity_res"]
        + yearly["annuity_res_inverter"]
        + yearly["fixed_om_res"]
        + yearly["fixed_om_res_inverter"]
        - yearly["res_subsidy_revenue"]
        + yearly["scope3_res_emissions_cost"]
    )
    yearly["battery_cost"] = (
        yearly["annuity_battery"]
        + yearly["annuity_battery_inverter"]
        + yearly["fixed_om_battery"]
        + yearly["fixed_om_battery_inverter"]
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


def build_additional_reporting_table_multi_year(
    *,
    sets: xr.Dataset,
    data: xr.Dataset,
    design_df: pd.DataFrame,
    kpis_df: pd.DataFrame,
    cash_df: pd.DataFrame,
    scenario_costs_df: pd.DataFrame,
    objective_value: float | None = None,
) -> pd.DataFrame:
    investment = build_investment_summary_table_multi_year(
        sets=sets, data=data, design_df=design_df
    )
    yearly = build_yearly_expected_table_multi_year(cash_df, scenario_costs_df)

    expected_kpis = kpis_df[kpis_df["scenario"].astype(str).str.lower() == "expected"].copy()
    expected_kpis["year"] = expected_kpis["year"].astype(str)
    lcoe_df = cash_df.copy()
    lcoe_df["year"] = lcoe_df["year"].astype(str)
    lcoe_df = lcoe_df.merge(expected_kpis[["year", "served_energy_kwh"]], on="year", how="left")

    npc = float(safe_float(objective_value))
    if not np.isfinite(npc):
        npc = float(
            pd.to_numeric(cash_df.get("discounted_objective_contribution"), errors="coerce")
            .fillna(0.0)
            .sum()
        )

    discounted_energy = float(
        (
            pd.to_numeric(lcoe_df.get("discount_factor"), errors="coerce").fillna(0.0)
            * pd.to_numeric(lcoe_df.get("served_energy_kwh"), errors="coerce").fillna(0.0)
        ).sum()
    )
    lcoe = npc / discounted_energy if discounted_energy > 1e-12 else float("nan")

    rows: list[dict[str, Any]] = [
        {
            "section": "summary_metrics",
            "row_label": "Net Present Cost (Expected)",
            "year": "",
            "unit": "",
            "value": npc,
        },
        {
            "section": "summary_metrics",
            "row_label": "LCOE",
            "year": "",
            "unit": "/kWh",
            "value": lcoe,
        },
        {
            "section": "summary_metrics",
            "row_label": "Investment cost (nominal)",
            "year": "",
            "unit": "",
            "value": float(
                pd.to_numeric(investment.get("Nominal investment cost"), errors="coerce")
                .fillna(0.0)
                .sum()
            ),
        },
        {
            "section": "summary_metrics",
            "row_label": "Investment cost (present)",
            "year": "",
            "unit": "",
            "value": float(
                pd.to_numeric(investment.get("Present-value investment cost"), errors="coerce")
                .fillna(0.0)
                .sum()
            ),
        },
    ]

    for _, row in investment.iterrows():
        rows.append(
            {
                "section": "investment_summary",
                "row_label": str(row.get("Technology", "")),
                "year": "",
                "unit": str(row.get("Capacity unit", "")),
                "value": float(safe_float(row.get("Nominal investment cost", 0.0))),
                "value_secondary": float(safe_float(row.get("Present-value investment cost", 0.0))),
                "secondary_label": "present_value_investment_cost",
            }
        )

    cost_components = [
        ("Annualized CAPEX", "annuity_total"),
        ("Fixed O&M", "fixed_om_total"),
        ("Fuel cost", "fuel_cost"),
        ("Grid import cost", "grid_import_cost"),
        ("Grid export revenue", "grid_export_revenue"),
        ("RES subsidy revenue", "res_subsidy_revenue"),
        ("Lost load penalty", "lost_load_penalty"),
        ("Emissions cost", "emissions_cost"),
        ("Embedded emissions cost", "embedded_expected"),
        ("TOTAL", "total_before_discount"),
    ]
    fixed_om_components = [
        ("Renewables", "fixed_om_res"),
        ("Renewables inverter", "fixed_om_res_inverter"),
        ("Battery", "fixed_om_battery"),
        ("Battery inverter", "fixed_om_battery_inverter"),
        ("Generator", "fixed_om_generator"),
    ]

    yearly_numeric = yearly.select_dtypes(include=[np.number])
    average_year = (
        yearly_numeric.mean(numeric_only=True)
        if not yearly_numeric.empty
        else pd.Series(dtype=float)
    )
    year_views: list[tuple[str, pd.Series]] = [("Average yearly", average_year)]
    for _, row in yearly.iterrows():
        year_views.append((str(row.get("year", "")), row))

    for year_label, year_row in year_views:
        if year_row.empty:
            continue
        for label, key in cost_components:
            rows.append(
                {
                    "section": "expected_cost_components",
                    "row_label": label,
                    "year": year_label,
                    "unit": "/yr",
                    "value": float(safe_float(year_row.get(key, 0.0))),
                }
            )
        for label, key in fixed_om_components:
            rows.append(
                {
                    "section": "expected_fixed_om",
                    "row_label": label,
                    "year": year_label,
                    "unit": "/yr",
                    "value": float(safe_float(year_row.get(key, 0.0))),
                }
            )

    out = pd.DataFrame(rows)
    for column in ["value_secondary", "secondary_label"]:
        if column not in out.columns:
            out[column] = np.nan if column == "value_secondary" else ""
    return out[
        ["section", "row_label", "year", "unit", "value", "secondary_label", "value_secondary"]
    ]


def build_multi_year_results_from_tables(
    *,
    project_name: str,
    data: xr.Dataset,
    sets: xr.Dataset,
    dispatch_df: pd.DataFrame,
    energy_balance_df: pd.DataFrame,
    design_by_step_df: pd.DataFrame,
    kpis_yearly_df: pd.DataFrame,
    cashflows_discounted_df: pd.DataFrame,
    scenario_costs_yearly_df: pd.DataFrame,
    renewable_inverter_design_by_step_df: pd.DataFrame | None = None,
    battery_inverter_design_by_step_df: pd.DataFrame | None = None,
    inverter_capacity_by_year_df: pd.DataFrame | None = None,
    inverter_metrics_yearly_df: pd.DataFrame | None = None,
    capacity_by_year_df: pd.DataFrame | None = None,
    investment_summary_df: pd.DataFrame | None = None,
    yearly_expected_df: pd.DataFrame | None = None,
    reporting_summary_df: pd.DataFrame | None = None,
    results_dir: Path | None = None,
    source: str = "files",
    metadata: dict[str, Any] | None = None,
) -> MultiYearResults:
    design = design_by_step_df.copy()
    dispatch = dispatch_df.copy()
    energy_balance = energy_balance_df.copy()
    kpis = kpis_yearly_df.copy()
    cash = cashflows_discounted_df.copy()
    scenario_costs = scenario_costs_yearly_df.copy()
    renewable_inverter_design = (
        renewable_inverter_design_by_step_df.copy()
        if isinstance(renewable_inverter_design_by_step_df, pd.DataFrame)
        else pd.DataFrame()
    )
    battery_inverter_design = (
        battery_inverter_design_by_step_df.copy()
        if isinstance(battery_inverter_design_by_step_df, pd.DataFrame)
        else pd.DataFrame()
    )
    inverter_capacity_by_year = (
        inverter_capacity_by_year_df.copy()
        if isinstance(inverter_capacity_by_year_df, pd.DataFrame)
        else pd.DataFrame()
    )
    inverter_metrics_yearly = (
        inverter_metrics_yearly_df.copy()
        if isinstance(inverter_metrics_yearly_df, pd.DataFrame)
        else pd.DataFrame()
    )

    for frame in (
        dispatch,
        energy_balance,
        design,
        kpis,
        cash,
        scenario_costs,
        renewable_inverter_design,
        battery_inverter_design,
        inverter_capacity_by_year,
        inverter_metrics_yearly,
    ):
        if "year" in frame.columns:
            frame["year"] = frame["year"].astype(str)
        if "scenario" in frame.columns:
            frame["scenario"] = frame["scenario"].astype(str)
        if "inv_step" in frame.columns:
            frame["inv_step"] = frame["inv_step"].astype(str)
        if "inv_step_start_year" in frame.columns:
            frame["inv_step_start_year"] = frame["inv_step_start_year"].astype(str)

    capacity_by_year = (
        capacity_by_year_df.copy()
        if isinstance(capacity_by_year_df, pd.DataFrame)
        else build_capacity_by_year_table_multi_year(sets=sets, design_df=design)
    )
    yearly_expected = (
        yearly_expected_df.copy()
        if isinstance(yearly_expected_df, pd.DataFrame)
        else build_yearly_expected_table_multi_year(cash, scenario_costs)
    )
    investment_summary = (
        investment_summary_df.copy()
        if isinstance(investment_summary_df, pd.DataFrame)
        else build_investment_summary_table_multi_year(sets=sets, data=data, design_df=design)
    )
    reporting_summary = (
        reporting_summary_df.copy()
        if isinstance(reporting_summary_df, pd.DataFrame)
        else build_additional_reporting_table_multi_year(
            sets=sets,
            data=data,
            design_df=design,
            kpis_df=kpis,
            cash_df=cash,
            scenario_costs_df=scenario_costs,
            objective_value=float(
                pd.to_numeric(cash.get("discounted_objective_contribution"), errors="coerce")
                .fillna(0.0)
                .sum()
            )
            if "discounted_objective_contribution" in cash.columns
            else None,
        )
    )
    meta = dict(metadata or {})
    meta.setdefault("project_name", project_name)
    meta.setdefault("formulation", "dynamic")
    meta.setdefault("results_dir", str(results_dir) if results_dir is not None else None)
    return MultiYearResults(
        project_name=project_name,
        data=data,
        sets=sets,
        metadata=meta,
        dispatch=dispatch,
        energy_balance=energy_balance,
        design_by_step=design,
        renewable_inverter_design_by_step=renewable_inverter_design,
        battery_inverter_design_by_step=battery_inverter_design,
        inverter_capacity_by_year=inverter_capacity_by_year,
        inverter_metrics_yearly=inverter_metrics_yearly,
        capacity_by_year=capacity_by_year,
        kpis_yearly=kpis,
        cashflows_discounted=cash,
        scenario_costs_yearly=scenario_costs,
        yearly_expected=yearly_expected,
        investment_summary=investment_summary,
        reporting_summary=reporting_summary,
        results_dir=results_dir,
        source=source,
    )


def build_multi_year_results(
    *,
    project_name: str,
    sets: xr.Dataset,
    data: xr.Dataset,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
    objective_value: float | None = None,
    status: str | None = None,
    solver: str | None = None,
    results_dir: Path | None = None,
    source: str = "session",
) -> MultiYearResults:
    dispatch = build_dispatch_timeseries_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    energy_balance = build_energy_balance_table_multi_year(dispatch)
    design = build_design_by_step_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    renewable_inverter_design = build_renewable_inverter_design_by_step_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    battery_inverter_design = build_battery_inverter_design_by_step_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    inverter_capacity_by_year = build_inverter_capacity_by_year_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    inverter_metrics = build_inverter_metrics_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    kpis = build_yearly_kpis_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution, objective_value=objective_value
    )
    cash = build_discounted_cashflows_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    scenario_costs = build_scenario_costs_table_multi_year(
        sets=sets, data=data, vars=vars, solution=solution
    )
    return build_multi_year_results_from_tables(
        project_name=project_name,
        data=data,
        sets=sets,
        dispatch_df=dispatch,
        energy_balance_df=energy_balance,
        design_by_step_df=design,
        renewable_inverter_design_by_step_df=renewable_inverter_design,
        battery_inverter_design_by_step_df=battery_inverter_design,
        inverter_capacity_by_year_df=inverter_capacity_by_year,
        inverter_metrics_yearly_df=inverter_metrics,
        kpis_yearly_df=kpis,
        cashflows_discounted_df=cash,
        scenario_costs_yearly_df=scenario_costs,
        results_dir=results_dir,
        source=source,
        metadata={
            "project_name": project_name,
            "formulation": "dynamic",
            "objective_value": safe_float(objective_value),
            "status": status,
            "solver": solver,
        },
    )


def export_multi_year_results(
    project_name: str,
    sets: xr.Dataset,
    data: xr.Dataset,
    model: lp.Model | None,
    vars: dict[str, Any],
    solution: xr.Dataset | None,
    out_dir: Path | None = None,
) -> dict:
    if out_dir is None:
        out_dir = ensure_results_dir(project_name)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    obj = None
    if model is not None and hasattr(model, "objective"):
        obj = safe_float(getattr(model.objective, "value", None))
    results = build_multi_year_results(
        project_name=project_name,
        sets=sets,
        data=data,
        vars=vars,
        solution=solution,
        objective_value=obj,
        status=None,
        solver=None,
        results_dir=out_dir,
        source="export",
    )
    return export_multi_year_results_package(results=results, out_dir=out_dir)


def export_multi_year_results_package(
    *,
    results: MultiYearResults,
    out_dir: Path | None = None,
) -> dict:
    if out_dir is None:
        out_dir = ensure_results_dir(results.project_name)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
    written = write_csv_outputs(
        out_dir,
        {
            "dispatch_timeseries.csv": results.dispatch,
            "energy_balance.csv": results.energy_balance,
            "design_by_step.csv": results.design_by_step,
            "renewable_inverter_design_by_step.csv": results.renewable_inverter_design_by_step,
            "battery_inverter_design_by_step.csv": results.battery_inverter_design_by_step,
            "inverter_capacity_by_year.csv": results.inverter_capacity_by_year,
            "inverter_metrics_yearly.csv": results.inverter_metrics_yearly,
            "capacity_by_year.csv": results.capacity_by_year,
            "kpis_yearly.csv": results.kpis_yearly,
            "cashflows_discounted.csv": results.cashflows_discounted,
            "scenario_costs_yearly.csv": results.scenario_costs_yearly,
            "yearly_expected.csv": results.yearly_expected,
            "investment_summary.csv": results.investment_summary,
            "reporting_summary.csv": results.reporting_summary,
        },
    )

    excel_path = out_dir / "results_multi_year.xlsx"
    written["results_excel"] = _write_multi_year_excel_workbook(
        excel_path,
        design=results.design_by_step,
        dispatch=results.dispatch,
        balance=results.energy_balance,
        kpis=results.kpis_yearly,
        cash=results.cashflows_discounted,
    )
    return written
