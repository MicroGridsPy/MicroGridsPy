from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import xarray as xr

from core.export.common import safe_float
from core.export.results_page_helpers import export_multi_year_results_from_object
from core.export.multi_year_results import (
    MultiYearResults,
)
from core.multi_year_model.params import get_params


C_RES = "#FFD700"
C_BAT = "#00ACC1"
C_GEN = "#546E7A"
C_IMP = "#9C27B0"
C_EXP = "#9C27B0"
C_LL = "#E53935"
C_LOAD = "#111111"
C_SCOPE1 = "#B71C1C"
C_SCOPE2 = "#1565C0"
C_SCOPE3 = "#2E7D32"


@dataclass(frozen=True)
class MultiYearResultsContext:
    results: MultiYearResults
    data: xr.Dataset
    sets: xr.Dataset
    settings: Dict[str, Any]
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
        "grid_import_delivered",
        "grid_export_delivered",
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
    y_gimp = profile["grid_import_delivered"].to_numpy(dtype=float) if "grid_import_delivered" in profile.columns else profile["grid_import"].to_numpy(dtype=float)
    y_ll = profile["lost_load"].to_numpy(dtype=float)
    y_bch = profile["battery_charge"].to_numpy(dtype=float)
    y_gexp = profile["grid_export_delivered"].to_numpy(dtype=float) if "grid_export_delivered" in profile.columns else profile["grid_export"].to_numpy(dtype=float)
    y_load = profile["load_demand"].to_numpy(dtype=float)
    y_bnet = y_bdis - y_bch
    y_bnet_pos = np.clip(y_bnet, 0.0, None)
    y_bnet_neg = np.clip(-y_bnet, 0.0, None)

    p1 = y_res
    p2 = p1 + y_bnet_pos
    p3 = p2 + y_gen
    p4 = p3 + y_gimp
    p5 = p4 + y_ll
    n1 = -y_bnet_neg
    n2 = n1 - y_gexp

    ax.fill_between(x, 0, p1, color=C_RES, alpha=0.85, label="Renewables")
    if np.any(y_bnet_pos > 0):
        ax.fill_between(x, p1, p2, color=C_BAT, alpha=0.35, label="Battery net discharge")
    ax.fill_between(x, p2, p3, color=C_GEN, alpha=0.85, label="Generator")
    if np.any(y_gimp > 0):
        ax.fill_between(x, p3, p4, color=C_IMP, alpha=0.85, label="Grid import (delivered)")
    if np.any(y_ll > 0):
        ax.fill_between(x, p4, p5, color=C_LL, alpha=0.45, label="Lost load")
    if np.any(y_bnet_neg > 0):
        ax.fill_between(x, 0, n1, color=C_BAT, alpha=0.35, label="Battery net charge")
    if np.any(y_gexp > 0):
        ax.fill_between(x, n1, n2, color=C_EXP, alpha=0.75, label="Grid export (delivered)")

    ax.plot(x, y_load, color=C_LOAD, linewidth=1.8, label="Load")
    ax.set_title(f"Dispatch profile - {title_suffix}")
    ax.set_xlabel("Hour of selected window")
    ax.set_ylabel("kWh per hour (approx. kW)")
    ax.grid(True, alpha=0.25, linestyle=":")
    ax.legend(ncols=4, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.22))


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


def _emissions_priced_in_objective(data: xr.Dataset) -> bool:
    emission_cost = data.get("emission_cost_per_kgco2e")
    if not isinstance(emission_cost, xr.DataArray):
        return False
    vals = np.asarray(emission_cost.values, dtype=float)
    vals = vals[np.isfinite(vals)]
    return bool(vals.size > 0 and float(np.max(vals)) > 0.0)


def _ensure_delivered_grid_columns(dispatch: pd.DataFrame, data: xr.Dataset) -> pd.DataFrame:
    df = dispatch.copy()
    if "grid_import_delivered" not in df.columns:
        df["grid_import_delivered"] = np.nan
    if "grid_export_delivered" not in df.columns:
        df["grid_export_delivered"] = np.nan
    if "scenario" not in df.columns:
        df["grid_import_delivered"] = df["grid_import_delivered"].fillna(df.get("grid_import", 0.0))
        df["grid_export_delivered"] = df["grid_export_delivered"].fillna(df.get("grid_export", 0.0))
        return df

    grid_eta = data.get("grid_transmission_efficiency")
    for scenario in df["scenario"].astype(str).unique():
        mask = df["scenario"].astype(str) == str(scenario)
        eta = float(grid_eta.sel(scenario=scenario)) if isinstance(grid_eta, xr.DataArray) else 1.0
        if "grid_import" in df.columns:
            df.loc[mask & df["grid_import_delivered"].isna(), "grid_import_delivered"] = df.loc[mask, "grid_import"] * eta
        if "grid_export" in df.columns:
            df.loc[mask & df["grid_export_delivered"].isna(), "grid_export_delivered"] = df.loc[mask, "grid_export"] * eta
    df["grid_import_delivered"] = pd.to_numeric(df["grid_import_delivered"], errors="coerce").fillna(0.0)
    df["grid_export_delivered"] = pd.to_numeric(df["grid_export_delivered"], errors="coerce").fillna(0.0)
    return df


def _build_context(results: MultiYearResults) -> MultiYearResultsContext:
    data = results.data
    sets = results.sets
    settings = _get_settings(data)
    dispatch = _ensure_delivered_grid_columns(results.dispatch.copy(), data)
    design = results.design_by_step.copy()
    kpis = results.kpis_yearly.copy()
    cash = results.cashflows_discounted.copy()
    capacity = results.capacity_by_year.copy()
    scenario_costs = results.scenario_costs_yearly.copy()
    yearly_expected = results.yearly_expected.copy()
    investment_summary = results.investment_summary.copy()
    return MultiYearResultsContext(
        results=results,
        data=data,
        sets=sets,
        settings=settings,
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


def _build_context_from_files(results: MultiYearResults) -> MultiYearResultsContext:
    ctx = _build_context(results)
    return MultiYearResultsContext(
        results=ctx.results,
        data=ctx.data,
        sets=ctx.sets,
        settings=ctx.settings,
        dispatch=ctx.dispatch,
        design=ctx.design,
        kpis=ctx.kpis,
        cash=ctx.cash,
        capacity_by_year=ctx.capacity_by_year,
        yearly_expected=ctx.yearly_expected,
        scenario_costs=ctx.scenario_costs,
        investment_summary=ctx.investment_summary,
        on_grid=ctx.on_grid,
        allow_export=ctx.allow_export,
        years=ctx.years,
        scenarios=ctx.scenarios,
        file_backed=True,
        results_dir=str(results.results_dir) if results.results_dir is not None else None,
    )


def _dispatch_kpi_summary(ctx: MultiYearResultsContext, selection: str) -> Dict[str, float]:
    dispatch = ctx.dispatch.copy()
    weights = _weights_da(ctx.data)
    weight_map = {str(s): float(weights.sel(scenario=s)) for s in weights.coords["scenario"].values}
    grid_ren = ctx.data.get("grid_renewable_share")

    def _expected_for_year(year_value: str) -> Dict[str, float]:
        year_df = dispatch[dispatch["year"].astype(str) == str(year_value)].copy()
        rows = []
        for scenario, group in year_df.groupby("scenario", sort=False):
            scenario_label = str(scenario)
            raw_import = float(group["grid_import"].sum())
            delivered_import = float(group["grid_import_delivered"].sum()) if "grid_import_delivered" in group.columns else raw_import
            ren_share = float(grid_ren.sel(scenario=scenario)) if isinstance(grid_ren, xr.DataArray) else 0.0
            rows.append(
                {
                    "load": float(group["load_demand"].sum()),
                    "lost_load": float(group["lost_load"].sum()),
                    "renewables": float(group["res_generation_total"].sum()),
                    "generator": float(group["generator_generation"].sum()),
                    "grid_import_delivered": delivered_import,
                    "grid_renewable": delivered_import * ren_share,
                    "grid_export_delivered": float(group["grid_export_delivered"].sum()) if "grid_export_delivered" in group.columns else float(group["grid_export"].sum()),
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


def _build_multi_year_diagnostics_table(ctx: MultiYearResultsContext, selection: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    weights = _weights_da(ctx.data)

    def _expected_year_view(year_label: str) -> pd.DataFrame:
        year_view = ctx.dispatch[ctx.dispatch["year"].astype(str) == str(year_label)].copy()
        return _build_expected_dispatch(year_view, weights)

    if selection == "Average yearly":
        views = [_expected_year_view(year_label) for year_label in ctx.years]
        if not views:
            return pd.DataFrame()
        frame = pd.concat(views, ignore_index=True)
        divisor = max(len(ctx.years), 1)
        soh_views = [view for view in views if "battery_soh" in view.columns and not view.empty]
        initial_soh = float(np.mean([view["battery_soh"].iloc[0] for view in soh_views])) if soh_views else None
        final_soh = float(np.mean([view["battery_soh"].iloc[-1] for view in soh_views])) if soh_views else None
    else:
        frame = _expected_year_view(str(selection))
        divisor = 1
        initial_soh = float(frame["battery_soh"].iloc[0]) if "battery_soh" in frame.columns and not frame.empty else None
        final_soh = float(frame["battery_soh"].iloc[-1]) if "battery_soh" in frame.columns and not frame.empty else None

    if {"battery_charge", "battery_discharge", "battery_charge_dc", "battery_discharge_dc"}.issubset(frame.columns):
        ch_ac_sum = float(frame["battery_charge"].sum()) / divisor
        dis_ac_sum = float(frame["battery_discharge"].sum()) / divisor
        ch_dc_sum = float(frame["battery_charge_dc"].sum()) / divisor
        dis_dc_sum = float(frame["battery_discharge_dc"].sum()) / divisor
        rows.append({"Metric": "Battery DC throughput", "Value": 0.5 * (ch_dc_sum + dis_dc_sum) / 1e3, "Unit": "MWh/yr"})
        if ch_ac_sum > 1e-12:
            rows.append({"Metric": "Battery avg charging efficiency", "Value": 100.0 * ch_dc_sum / ch_ac_sum, "Unit": "%"})
        if dis_dc_sum > 1e-12:
            rows.append({"Metric": "Battery avg discharging efficiency", "Value": 100.0 * dis_ac_sum / dis_dc_sum, "Unit": "%"})
        if ch_ac_sum > 1e-12 and dis_dc_sum > 1e-12:
            rows.append({"Metric": "Battery implied round-trip efficiency", "Value": 100.0 * (ch_dc_sum / ch_ac_sum) * (dis_ac_sum / dis_dc_sum), "Unit": "%"})
    if {"battery_charge_loss", "battery_discharge_loss"}.issubset(frame.columns):
        rows.append({"Metric": "Battery conversion losses", "Value": (float(frame["battery_charge_loss"].sum()) + float(frame["battery_discharge_loss"].sum())) / divisor / 1e3, "Unit": "MWh/yr"})
    if "battery_cycle_fade" in frame.columns:
        rows.append({"Metric": "Battery cycle fade", "Value": float(frame["battery_cycle_fade"].sum()) / divisor / 1e3, "Unit": "MWh cap./yr"})
    if "battery_calendar_fade" in frame.columns:
        rows.append({"Metric": "Battery calendar fade", "Value": float(frame["battery_calendar_fade"].sum()) / divisor / 1e3, "Unit": "MWh cap./yr"})
    if initial_soh is not None and final_soh is not None:
        rows.append({"Metric": "Battery initial SoH", "Value": initial_soh, "Unit": "-"})
        rows.append({"Metric": "Battery final SoH", "Value": final_soh, "Unit": "-"})
        rows.append({"Metric": "Battery SoH drop", "Value": 100.0 * max(initial_soh - final_soh, 0.0), "Unit": "p.p."})
    if "battery_effective_energy_capacity" in frame.columns:
        rows.append(
            {
                "Metric": "Battery avg effective energy capacity",
                "Value": float(frame["battery_effective_energy_capacity"].mean()) / 1e3,
                "Unit": "MWh",
            }
        )
        rows.append(
            {
                "Metric": "Battery min effective energy capacity",
                "Value": float(frame["battery_effective_energy_capacity"].min()) / 1e3,
                "Unit": "MWh",
            }
        )

    p = get_params(ctx.data)
    if selection == "Average yearly":
        kpi_expected = ctx.kpis[ctx.kpis["scenario"].astype(str).str.lower() == "expected"].copy()
        fuel_sum = float(kpi_expected["fuel_consumption"].mean()) if "fuel_consumption" in kpi_expected.columns and not kpi_expected.empty else 0.0
    else:
        kpi_expected = ctx.kpis[
            (ctx.kpis["scenario"].astype(str).str.lower() == "expected")
            & (ctx.kpis["year"].astype(str) == str(selection))
        ].copy()
        fuel_sum = float(kpi_expected.iloc[0]["fuel_consumption"]) if "fuel_consumption" in kpi_expected.columns and not kpi_expected.empty else 0.0
    gen_sum = float(frame["generator_generation"].sum()) / divisor if "generator_generation" in frame.columns else 0.0
    if p.fuel_lhv_kwh_per_unit_fuel is not None and fuel_sum > 1e-12:
        lhv_expected = float((p.fuel_lhv_kwh_per_unit_fuel * weights).sum("scenario")) if "scenario" in p.fuel_lhv_kwh_per_unit_fuel.dims else float(safe_float(p.fuel_lhv_kwh_per_unit_fuel))
        if fuel_sum * lhv_expected > 1e-12:
            rows.append({"Metric": "Generator average conversion efficiency", "Value": 100.0 * gen_sum / (fuel_sum * lhv_expected), "Unit": "%"})
    if p.generator_nominal_efficiency_full_load is not None:
        gen_nom_eff = float((p.generator_nominal_efficiency_full_load * weights).sum("scenario")) if "scenario" in p.generator_nominal_efficiency_full_load.dims else float(safe_float(p.generator_nominal_efficiency_full_load))
        rows.append({"Metric": "Generator nominal full-load efficiency", "Value": 100.0 * gen_nom_eff, "Unit": "%"})
    if fuel_sum > 0.0:
        rows.append({"Metric": "Generator fuel consumption", "Value": fuel_sum, "Unit": "fuel units/yr" if selection == "Average yearly" else "fuel units"})

    return pd.DataFrame(rows)


def _battery_lifetime_soh_warning(ctx: MultiYearResultsContext) -> str | None:
    degradation_settings = (((ctx.settings.get("battery_model", {}) or {}).get("degradation_model", {}) or {}))
    end_of_life_soh_raw = degradation_settings.get("end_of_life_soh", None)
    if end_of_life_soh_raw in (None, ""):
        return None
    try:
        end_of_life_soh = float(end_of_life_soh_raw)
    except Exception:
        return None

    p = get_params(ctx.data)
    if p.battery_calendar_lifetime_years is None:
        return None
    vals = np.asarray(p.battery_calendar_lifetime_years.values, dtype=float).reshape(-1)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return None
    calendar_lifetime_years = float(vals[0])
    if not np.allclose(vals, calendar_lifetime_years, atol=1e-9, rtol=0.0):
        return None
    target_service_year = int(np.floor(calendar_lifetime_years))
    if target_service_year < 1:
        return None
    if target_service_year > len(ctx.years):
        return None
    target_year_label = str(ctx.years[target_service_year - 1])

    expected_dispatch = _build_expected_dispatch(ctx.dispatch.copy(), _weights_da(ctx.data))
    if expected_dispatch.empty or "battery_soh" not in expected_dispatch.columns:
        return None
    year_view = expected_dispatch[expected_dispatch["year"].astype(str) == target_year_label].copy()
    if year_view.empty:
        return None

    simulated_soh = float(year_view["battery_soh"].iloc[-1])
    diff = simulated_soh - end_of_life_soh
    if abs(diff) < 0.05:
        return None

    relation = "above" if diff > 0.0 else "below"
    return (
        f"Battery expected SoH at the end of service year {target_service_year} ({target_year_label}) is {simulated_soh:.2f}, "
        f"which is {abs(diff):.2f} {relation} the configured end-of-life SoH {end_of_life_soh:.2f}. "
        f"This means the degradation settings and `calendar_lifetime_years` are not closely aligned."
    )


def _render_sizing_summary(ctx: MultiYearResultsContext) -> None:
    st.subheader("Sizing summary")
    st.dataframe(
        ctx.capacity_by_year.style.format(
            {
                "renewables_kw": "{:,.1f}",
                "renewable_inverter_kw_ac": "{:,.1f}",
                "battery_kwh": "{:,.1f}",
                "battery_inverter_kw": "{:,.1f}",
                "generator_kw": "{:,.1f}",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    if len(ctx.design["inv_step"].astype(str).unique()) > 1:
        st.caption("Capacity evolution across the planning horizon.")
        fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True, height_ratios=[2, 1.2, 1.2])
        years = ctx.capacity_by_year["year"].tolist()
        x = np.arange(len(years))
        ax1, ax2, ax3 = axes
        ax1.bar(x, ctx.capacity_by_year["renewables_kw"], color=C_RES, alpha=0.85, label="Renewables DC [kW]")
        ax1.bar(x, ctx.capacity_by_year["generator_kw"], bottom=ctx.capacity_by_year["renewables_kw"], color=C_GEN, alpha=0.85, label="Generator [kW]")
        ax1.set_ylabel("kW")
        ax1.set_title("Installed generation capacity by year")
        ax1.grid(True, axis="y", alpha=0.25, linestyle=":")
        ax1.legend()
        ax2.bar(x, ctx.capacity_by_year["renewable_inverter_kw_ac"], color="#F4A261", alpha=0.85, label="Renewable inverter AC [kW_ac]")
        ax2.bar(x, ctx.capacity_by_year["battery_inverter_kw"], bottom=ctx.capacity_by_year["renewable_inverter_kw_ac"], color="#2A9D8F", alpha=0.85, label="Battery inverter [kW]")
        ax2.set_ylabel("kW")
        ax2.set_title("Installed inverter/converter capacity by year")
        ax2.grid(True, axis="y", alpha=0.25, linestyle=":")
        ax2.legend()
        ax3.bar(x, ctx.capacity_by_year["battery_kwh"], color=C_BAT, alpha=0.85, label="Battery energy [kWh]")
        ax3.set_ylabel("kWh")
        ax3.set_title("Installed battery energy capacity by year")
        ax3.set_xticks(x, years)
        ax3.grid(True, axis="y", alpha=0.25, linestyle=":")
        ax3.legend()
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
    lifetime_warning = _battery_lifetime_soh_warning(ctx)
    if lifetime_warning:
        st.warning(lifetime_warning)
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
        {"Metric": "Renewable share of primary supply", "Value": 100.0 * dispatch_summary.get("renewable_share", float(row.get("renewable_penetration", 0.0))), "Unit": "%"},
        {"Metric": "Curtailment share of renewables", "Value": 100.0 * float(row.get("renewable_curtailment_share", 0.0)), "Unit": "%"},
        {"Metric": "Lost load fraction", "Value": 100.0 * dispatch_summary.get("lost_load_fraction", float(row.get("lost_load_fraction", 0.0))), "Unit": "%"},
        {"Metric": "Fuel consumption", "Value": float(row.get("fuel_consumption", 0.0)), "Unit": "fuel units"},
        {"Metric": "Total emissions", "Value": float(row.get("emissions_kgco2e", 0.0)), "Unit": "kgCO2e"},
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
                "Value": dispatch_summary.get("grid_export_delivered", dispatch_summary.get("grid_export", 0.0)) / 1e3,
                "Unit": "MWh",
            },
        )
    st.dataframe(
        pd.DataFrame(kpi_rows).style.format({"Value": "{:,.2f}"}),
        hide_index=True,
        width="stretch",
    )
    diagnostics_df = _build_multi_year_diagnostics_table(ctx, choice)
    if not diagnostics_df.empty:
        st.markdown("**Efficiency & degradation diagnostics**")
        st.dataframe(
            diagnostics_df.style.format({"Value": "{:,.4f}"}),
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

    npc = float(safe_float(ctx.results.metadata.get("objective_value")))
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
            {"Technology": "Renewables inverter", "Annual fixed O&M": float(selected.get("fixed_om_res_inverter", 0.0))},
            {"Technology": "Battery", "Annual fixed O&M": float(selected["fixed_om_battery"])},
            {"Technology": "Battery inverter", "Annual fixed O&M": float(selected.get("fixed_om_battery_inverter", 0.0))},
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

    if not _emissions_priced_in_objective(ctx.data):
        return

    st.markdown("**Emissions by scope**")
    scope_view_options = ["Expected"] + ctx.scenarios if len(ctx.scenarios) > 1 else [ctx.scenarios[0]]
    default_scope_view = "Expected" if "Expected" in scope_view_options else scope_view_options[0]
    scope_view = st.selectbox(
        "Emissions scope view",
        scope_view_options,
        index=scope_view_options.index(default_scope_view),
        key="my_results_scope_emissions_view",
    )

    scope_df = ctx.scenario_costs.copy()
    if scope_view == "Expected":
        scope_df = scope_df[scope_df["scenario"] == "Expected"].copy()
    else:
        scope_df = scope_df[scope_df["scenario"] == str(scope_view)].copy()
    if selected_year != "All years":
        scope_df = scope_df[scope_df["year"].astype(str) == str(selected_year)].copy()

    if scope_df.empty:
        st.info("No emissions data available for the selected scope view.")
        return

    fig_scope, ax_scope = plt.subplots(figsize=(11, 4))
    x_labels = scope_df["year"].astype(str).tolist()
    x = np.arange(len(x_labels))
    scope1 = scope_df["scope1_emissions"].to_numpy(dtype=float)
    scope2 = scope_df["scope2_emissions"].to_numpy(dtype=float)
    scope3 = scope_df["scope3_emissions"].to_numpy(dtype=float)

    ax_scope.bar(x, scope1, color=C_SCOPE1, alpha=0.9, label="Scope 1")
    ax_scope.bar(x, scope2, bottom=scope1, color=C_SCOPE2, alpha=0.9, label="Scope 2")
    ax_scope.bar(x, scope3, bottom=scope1 + scope2, color=C_SCOPE3, alpha=0.9, label="Scope 3")
    ax_scope.set_title(f"Emissions by scope - {scope_view}")
    ax_scope.set_ylabel("kgCO2e / year")
    ax_scope.set_xticks(x, x_labels)
    ax_scope.grid(True, axis="y", alpha=0.25, linestyle=":")
    ax_scope.legend(ncols=3, fontsize=9)
    st.pyplot(fig_scope)


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
                written = export_multi_year_results_from_object(ctx.results)
            st.success("Export completed.")
            st.json(written)
            st.markdown("**Generated files**")
            for _, path in written.items():
                if isinstance(path, str) and (path.endswith(".csv") or path.endswith(".xlsx")):
                    st.write(path)
        except Exception as exc:
            st.error(f"Export failed: {exc}")


def render_multi_year_results(results: MultiYearResults, project_name: Optional[str]) -> None:
    _ = project_name
    try:
        ctx = _build_context(results)
    except Exception as exc:
        st.error(f"Unable to render multi-year results: {exc}")
        return

    _render_sizing_summary(ctx)
    _render_performance_kpis(ctx)
    _render_energy_mix(ctx)
    _render_costs_and_cashflow(ctx)
    _render_scenario_costs_and_emissions(ctx)
    _render_export_section(ctx, project_name)


def render_multi_year_results_from_files(file_results: MultiYearResults, project_name: Optional[str]) -> None:
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
