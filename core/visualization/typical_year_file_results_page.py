from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import xarray as xr

from core.export.results_page_helpers import TypicalYearFileResults
from core.export.typical_year_reporting import (
    build_reporting_tables,
    select_dispatch_view as select_reporting_dispatch_view,
    select_kpi_row as select_reporting_kpi_row,
)
from core.visualization.page_helpers import get_dataset_settings, get_nested_flag, safe_float as _safe_float


C_RES = "#FFD700"
C_BAT = "#00ACC1"
C_GEN = "#546E7A"
C_IMP = "#9C27B0"
C_EXP = "#9C27B0"
C_LL = "#E53935"
C_LOAD = "#111111"


def _crf(r: float, n: float) -> float:
    r = float(r)
    n = float(n)
    if n <= 0:
        return float("nan")
    if abs(r) < 1e-12:
        return 1.0 / n
    a = (1.0 + r) ** n
    return (r * a) / (a - 1.0)


def _days_to_slice(T: int, start_day: int, ndays: int) -> Tuple[slice, int, int]:
    ndays = int(np.clip(ndays, 1, 7))
    max_day = max(1, int(np.ceil(T / 24)))
    start_day = int(np.clip(start_day, 1, max_day))
    window = ndays * 24
    i0 = (start_day - 1) * 24
    i1 = min(T, i0 + window)
    return slice(i0, i1), i0 + 1, i1 - i0


def _plot_dispatch_stack(
    *,
    ax,
    x,
    y_res,
    y_bdis,
    y_gen,
    y_gimp,
    y_ll,
    y_bch,
    y_gexp,
    y_load,
    title_suffix: str,
) -> None:
    y_bnet = y_bdis - y_bch
    y_bnet_pos = np.clip(y_bnet, 0.0, None)
    y_bnet_neg = np.clip(-y_bnet, 0.0, None)

    p1 = y_res
    p2 = p1 + y_bnet_pos
    p3 = p2 + y_gen
    p4 = p3 + (y_gimp if y_gimp is not None else 0.0)
    p5 = p4 + y_ll
    n1 = -y_bnet_neg
    n2 = n1 - (y_gexp if y_gexp is not None else 0.0)

    ax.fill_between(x, 0, p1, color=C_RES, alpha=0.85, label="Renewables")
    if np.any(y_bnet_pos > 0):
        ax.fill_between(x, p1, p2, color=C_BAT, alpha=0.35, label="Battery net discharge")
    ax.fill_between(x, p2, p3, color=C_GEN, alpha=0.85, label="Generator")
    if y_gimp is not None and np.any(y_gimp > 0):
        ax.fill_between(x, p3, p4, color=C_IMP, alpha=0.85, label="Grid import")
    if np.any(y_ll > 0):
        ax.fill_between(x, p4, p5, color=C_LL, alpha=0.45, label="Lost load")
    if np.any(y_bnet_neg > 0):
        ax.fill_between(x, 0, n1, color=C_BAT, alpha=0.35, label="Battery net charge")
    if y_gexp is not None and np.any(y_gexp > 0):
        ax.fill_between(x, n1, n2, color=C_EXP, alpha=0.75, label="Grid export")

    ax.plot(x, y_load, color=C_LOAD, linewidth=1.8, label="Load")
    ax.set_title(f"Dispatch plot - {title_suffix}")
    ax.set_xlabel("Hour of typical year")
    ax.set_ylabel("kWh per hour")
    ax.grid(True, alpha=0.25, linestyle=":")
    ax.legend(ncols=4, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.25))


def _scenario_selector(settings: Dict[str, Any], data: xr.Dataset, *, key: str) -> Tuple[str, Optional[str]]:
    ms_enabled = bool(((settings.get("multi_scenario", {}) or {}).get("enabled", False)))
    if not ms_enabled:
        return "scenario", str(data.coords["scenario"].values[0])

    scen_labels = [str(s) for s in data.coords["scenario"].values.tolist()]
    options = ["Expected"] + [f"Scenario: {s}" for s in scen_labels]
    selected = st.selectbox("View metrics for:", options=options, index=0, key=key)
    if selected == "Expected":
        return "expected", None
    return "scenario", selected.split("Scenario: ", 1)[-1].strip()


def _weights_map(data: xr.Dataset) -> Dict[str, float]:
    w_s = data.get("scenario_weight", None)
    scenarios = [str(s) for s in data.coords["scenario"].values.tolist()]
    if isinstance(w_s, xr.DataArray) and "scenario" in w_s.dims:
        return {str(s): float(_safe_float(w_s.sel(scenario=s))) for s in scenarios}
    if not scenarios:
        return {}
    eq = 1.0 / float(len(scenarios))
    return {s: eq for s in scenarios}


def _select_exported_kpi_row(kpis: pd.DataFrame, data: xr.Dataset, *, mode: str, scenario_label: Optional[str]) -> pd.Series:
    frame = kpis.copy()
    frame["scenario"] = frame["scenario"].astype(str)
    if mode == "scenario" and scenario_label is not None:
        row = frame[frame["scenario"] == str(scenario_label)]
        if not row.empty:
            return row.iloc[0]

    expected = frame[frame["scenario"].str.lower() == "expected"]
    if not expected.empty:
        return expected.iloc[0]

    scenario_rows = frame[~frame["scenario"].str.lower().eq("expected")].copy()
    scenario_rows["weight_fallback"] = scenario_rows["scenario"].map(_weights_map(data)).fillna(0.0)
    numeric_cols = scenario_rows.select_dtypes(include=[np.number]).columns.tolist()
    values = {"scenario": "expected"}
    for col in numeric_cols:
        values[col] = float((pd.to_numeric(scenario_rows[col], errors="coerce").fillna(0.0) * scenario_rows["weight_fallback"]).sum())
    return pd.Series(values)


def _select_dispatch_export(dispatch: pd.DataFrame, data: xr.Dataset, *, mode: str, scenario_label: Optional[str]) -> pd.DataFrame:
    frame = dispatch.copy()
    frame["scenario"] = frame["scenario"].astype(str)
    numeric_cols = [c for c in frame.columns if c not in {"period", "scenario"}]
    for col in numeric_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)

    if mode == "scenario" and scenario_label is not None:
        return frame[frame["scenario"] == str(scenario_label)].sort_values("period").reset_index(drop=True)

    frame["weight"] = frame["scenario"].map(_weights_map(data)).fillna(0.0)
    weighted = frame[numeric_cols].mul(frame["weight"], axis=0)
    expected = pd.concat([frame[["period"]], weighted], axis=1).groupby("period", as_index=False).sum()
    expected["scenario"] = "expected"
    return expected.sort_values("period").reset_index(drop=True)


def _weighted_scalar_from_scenarios(data: xr.Dataset, da: xr.DataArray, *, mode: str, scenario_label: Optional[str]) -> float:
    if "scenario" not in da.dims:
        return float(_safe_float(da))
    if mode == "scenario" and scenario_label is not None:
        return float(_safe_float(da.sel(scenario=str(scenario_label))))
    weights = _weights_map(data)
    total = 0.0
    for scenario in da.coords["scenario"].values.tolist():
        total += float(_safe_float(da.sel(scenario=scenario))) * float(weights.get(str(scenario), 0.0))
    return total


def _build_typical_file_diagnostics_table(
    *,
    dispatch_view: pd.DataFrame,
    data: xr.Dataset,
    mode: str,
    scenario_label: Optional[str],
    kpi_row: pd.Series,
) -> pd.DataFrame:
    settings = get_dataset_settings(data)
    battery_loss_model = str(((settings.get("battery_model", {}) or {}).get("loss_model", "constant_efficiency")) or "constant_efficiency").strip().lower()
    generator_partial_load = bool(((settings.get("generator", {}) or {}).get("partial_load_modelling_enabled", False)))
    if battery_loss_model != "convex_loss_epigraph" and not generator_partial_load:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []

    if {"battery_charge", "battery_discharge", "battery_charge_dc", "battery_discharge_dc"}.issubset(dispatch_view.columns):
        ch_ac_sum = float(dispatch_view["battery_charge"].sum())
        dis_ac_sum = float(dispatch_view["battery_discharge"].sum())
        ch_dc_sum = float(dispatch_view["battery_charge_dc"].sum())
        dis_dc_sum = float(dispatch_view["battery_discharge_dc"].sum())
        rows.append({"Metric": "Battery DC throughput", "Value": 0.5 * (ch_dc_sum + dis_dc_sum) / 1e3, "Unit": "MWh"})
        if ch_ac_sum > 1e-12:
            rows.append({"Metric": "Battery avg charging efficiency", "Value": 100.0 * ch_dc_sum / ch_ac_sum, "Unit": "%"})
        if dis_dc_sum > 1e-12:
            rows.append({"Metric": "Battery avg discharging efficiency", "Value": 100.0 * dis_ac_sum / dis_dc_sum, "Unit": "%"})
        if ch_ac_sum > 1e-12 and dis_dc_sum > 1e-12:
            rows.append(
                {
                    "Metric": "Battery implied round-trip efficiency",
                    "Value": 100.0 * (ch_dc_sum / ch_ac_sum) * (dis_ac_sum / dis_dc_sum),
                    "Unit": "%",
                }
            )
    if {"battery_charge_loss", "battery_discharge_loss"}.issubset(dispatch_view.columns):
        rows.append(
            {
                "Metric": "Battery conversion losses",
                "Value": (float(dispatch_view["battery_charge_loss"].sum()) + float(dispatch_view["battery_discharge_loss"].sum())) / 1e3,
                "Unit": "MWh",
            }
        )
    if "fuel_consumption" in kpi_row.index and "fuel_lhv_kwh_per_unit_fuel" in data:
        fuel_sum = float(_safe_float(kpi_row.get("fuel_consumption", 0.0)))
        gen_sum = float(dispatch_view["generator_generation"].sum()) if "generator_generation" in dispatch_view.columns else 0.0
        lhv_val = _weighted_scalar_from_scenarios(data, data["fuel_lhv_kwh_per_unit_fuel"], mode=mode, scenario_label=scenario_label)
        if fuel_sum * lhv_val > 1e-12:
            rows.append({"Metric": "Generator average conversion efficiency", "Value": 100.0 * gen_sum / (fuel_sum * lhv_val), "Unit": "%"})
        if "generator_nominal_efficiency_full_load" in data:
            rows.append(
                {
                    "Metric": "Generator nominal full-load efficiency",
                    "Value": 100.0
                    * _weighted_scalar_from_scenarios(
                        data,
                        data["generator_nominal_efficiency_full_load"],
                        mode=mode,
                        scenario_label=scenario_label,
                    ),
                    "Unit": "%",
                }
            )
        rows.append({"Metric": "Generator fuel consumption", "Value": fuel_sum, "Unit": "fuel units"})

    return pd.DataFrame(rows)


def _render_energy_balance_check_df(energy_balance_df: pd.DataFrame, tolerance: float = 1e-6) -> None:
    with st.expander("Energy Balance Check", expanded=False):
        if energy_balance_df.empty or "balance_residual" not in energy_balance_df.columns:
            st.info("Energy balance unavailable from exported files.")
            return

        residual = pd.to_numeric(energy_balance_df["balance_residual"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        max_abs = float(np.max(np.abs(residual))) if residual.size else 0.0
        mean_res = float(np.mean(residual)) if residual.size else 0.0

        c1, c2 = st.columns(2)
        c1.metric("Max |residual|", f"{max_abs:.3e}")
        c2.metric("Mean residual", f"{mean_res:.3e}")
        if max_abs > tolerance:
            st.warning(f"Residual exceeds tolerance {tolerance:.1e}")
        else:
            st.success(f"Residual within tolerance {tolerance:.1e}")
        st.dataframe(energy_balance_df, width="stretch")


def _select_scalar(da: xr.DataArray, **indexers: Any) -> float:
    view = da
    for dim, value in indexers.items():
        if dim in view.dims:
            view = view.sel({dim: value})
    return float(_safe_float(view))


def render_typical_year_results_from_files(file_results: TypicalYearFileResults, project_name: Optional[str]) -> None:
    _ = project_name
    data = file_results.data
    settings = get_dataset_settings(data)
    on_grid = get_nested_flag(settings, ("grid", "on_grid"), default=False)
    allow_export = get_nested_flag(settings, ("grid", "allow_export"), default=False)

    dispatch = file_results.dispatch.copy()
    design = file_results.design.copy()
    raw_kpis = file_results.kpis.copy()
    dispatch["scenario"] = dispatch["scenario"].astype(str)
    raw_kpis["scenario"] = raw_kpis["scenario"].astype(str)
    raw_expected = raw_kpis[raw_kpis["scenario"].str.lower() == "expected"]
    solver_objective_value = (
        float(_safe_float(raw_expected.iloc[0].get("objective_value", np.nan)))
        if not raw_expected.empty
        else float("nan")
    )
    reporting = build_reporting_tables(
        data=data,
        dispatch_df=dispatch,
        design_df=design,
        solver_objective_value=solver_objective_value,
    )
    dispatch = reporting.dispatch
    energy_balance = reporting.energy_balance
    kpis = reporting.kpis.copy()

    st.info(f"Displaying saved results loaded from project files in `{file_results.results_dir}`.")

    row = design.iloc[0] if not design.empty else pd.Series(dtype=float)
    resources = [str(r) for r in data.coords["resource"].values.tolist()] if "resource" in data.coords else []
    res_units = {r: float(pd.to_numeric(pd.Series([row.get(f'res_units__{r}', 0.0)]), errors='coerce').fillna(0.0).iloc[0]) for r in resources}
    res_caps = {r: float(pd.to_numeric(pd.Series([row.get(f'res_installed_kw__{r}', 0.0)]), errors='coerce').fillna(0.0).iloc[0]) for r in resources}
    battery_units = float(pd.to_numeric(pd.Series([row.get("battery_units", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    generator_units = float(pd.to_numeric(pd.Series([row.get("generator_units", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    cap_bat_kwh = float(pd.to_numeric(pd.Series([row.get("battery_installed_kwh", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    cap_gen_kw = float(pd.to_numeric(pd.Series([row.get("generator_installed_kw", 0.0)]), errors="coerce").fillna(0.0).iloc[0])

    st.subheader("Sizing summary")
    df_size = pd.DataFrame(
        [
            {"Component": "Renewables (total)", "Installed units": float(sum(res_units.values())), "Capacity": float(sum(res_caps.values())), "Unit": "kW"},
            {"Component": "Battery", "Installed units": battery_units, "Capacity": cap_bat_kwh, "Unit": "kWh"},
            {"Component": "Generator", "Installed units": generator_units, "Capacity": cap_gen_kw, "Unit": "kW"},
        ]
    )
    st.dataframe(df_size.style.format({"Installed units": "{:,.3g}", "Capacity": "{:,.3g}"}).hide(axis="index"), width="stretch")

    with st.expander("Per-renewable breakdown", expanded=False):
        df_res = pd.DataFrame(
            {
                "Resource": resources,
                "Installed units": [res_units[r] for r in resources],
                "Capacity [kW]": [res_caps[r] for r in resources],
            }
        )
        st.dataframe(df_res.style.format({"Installed units": "{:,.3g}", "Capacity [kW]": "{:,.3g}"}).hide(axis="index"), width="stretch")

    st.subheader("Performance KPIs")
    mode, scen_label = _scenario_selector(settings, data, key="gp_kpi_view_sel_file")
    kpi_row = select_reporting_kpi_row(kpis, data, mode=mode, scenario_label=scen_label)
    dispatch_kpi = select_reporting_dispatch_view(dispatch, data, mode=mode, scenario_label=scen_label)
    generator_generation_mwh = float(dispatch_kpi["generator_generation"].sum()) / 1e3 if "generator_generation" in dispatch_kpi.columns else 0.0
    grid_imports_mwh = 0.0
    grid_exports_mwh = 0.0
    if on_grid and "grid_import_delivered" in dispatch_kpi.columns:
        grid_imports_mwh = float(dispatch_kpi["grid_import_delivered"].sum()) / 1e3
    if on_grid and allow_export and "grid_export_delivered" in dispatch_kpi.columns:
        grid_exports_mwh = float(dispatch_kpi["grid_export_delivered"].sum()) / 1e3
    kpi_rows = [
        {"Metric": "Load", "Value": float(_safe_float(kpi_row.get("total_demand_kwh", 0.0))) / 1e3, "Unit": "MWh"},
        {"Metric": "Delivered energy", "Value": float(_safe_float(kpi_row.get("served_energy_kwh", 0.0))) / 1e3, "Unit": "MWh"},
        {"Metric": "Lost load", "Value": float(_safe_float(kpi_row.get("lost_load_kwh", 0.0))) / 1e3, "Unit": "MWh"},
        {"Metric": "Renewable generation", "Value": float(_safe_float(kpi_row.get("total_res_kwh", 0.0))) / 1e3, "Unit": "MWh"},
        {"Metric": "Generator generation", "Value": generator_generation_mwh, "Unit": "MWh"},
    ]
    if on_grid:
        kpi_rows.append({"Metric": "Grid imports (delivered)", "Value": grid_imports_mwh, "Unit": "MWh"})
        kpi_rows.append({"Metric": "Grid renewable contribution", "Value": float(_safe_float(kpi_row.get("grid_renewable_kwh", 0.0))) / 1e3, "Unit": "MWh"})
    if on_grid and allow_export:
        kpi_rows.append({"Metric": "Grid exports", "Value": grid_exports_mwh, "Unit": "MWh"})
    kpi_rows.extend(
        [
            {"Metric": "Renewable share of primary supply", "Value": 100.0 * float(_safe_float(kpi_row.get("renewable_penetration", 0.0))), "Unit": "%"},
            {"Metric": "Curtailment share of renewables", "Value": 100.0 * float(_safe_float(kpi_row.get("renewable_curtailment_share", 0.0))), "Unit": "%"},
            {"Metric": "Lost load fraction", "Value": 100.0 * float(_safe_float(kpi_row.get("lost_load_fraction", 0.0))), "Unit": "%"},
        ]
    )
    st.dataframe(pd.DataFrame(kpi_rows).style.format({"Value": "{:,.2f}"}).hide(axis="index"), width="stretch")
    diagnostics_df = _build_typical_file_diagnostics_table(
        dispatch_view=dispatch_kpi,
        data=data,
        mode=mode,
        scenario_label=scen_label,
        kpi_row=kpi_row,
    )
    if not diagnostics_df.empty:
        st.markdown("**Efficiency diagnostics**")
        st.dataframe(
            diagnostics_df.style.format({"Value": "{:,.4f}"}).hide(axis="index"),
            width="stretch",
        )

    st.markdown("---")
    st.subheader("Least-Cost Energy Mix")
    st.caption("Stacked dispatch over a selected time window. Positive areas are supply-side contributions; battery charging and grid exports are shown below zero.")
    mode_d, scen_label_d = _scenario_selector(settings, data, key="gp_disp_view_sel_file")
    disp_view = select_reporting_dispatch_view(dispatch, data, mode=mode_d, scenario_label=scen_label_d)
    T = int(len(disp_view))
    with st.expander("Time window", expanded=False):
        st.caption("Pick the start day and how many days to plot (1-7).")
        max_days = max(1, int(np.ceil(T / 24)))
        ndays = st.slider("Number of days", min_value=1, max_value=min(7, max_days), value=1, step=1, key="gp_disp_ndays_file")
        max_start_day = max(1, max_days - ndays + 1)
        start_day = st.slider("Start day", min_value=1, max_value=max_start_day, value=1, step=1, key="gp_disp_start_day_file")
    idx, start_hr, window = _days_to_slice(T, start_day=start_day, ndays=ndays)
    x = np.arange(start_hr, start_hr + window)
    fig, ax = plt.subplots(figsize=(11, 4))
    _plot_dispatch_stack(
        ax=ax,
        x=x,
        y_res=disp_view["res_generation_total"].to_numpy(dtype=float)[idx],
        y_bdis=disp_view["battery_discharge"].to_numpy(dtype=float)[idx],
        y_gen=disp_view["generator_generation"].to_numpy(dtype=float)[idx],
        y_gimp=disp_view["grid_import_delivered"].to_numpy(dtype=float)[idx] if (on_grid and "grid_import_delivered" in disp_view.columns) else None,
        y_ll=disp_view["lost_load"].to_numpy(dtype=float)[idx],
        y_bch=disp_view["battery_charge"].to_numpy(dtype=float)[idx],
        y_gexp=disp_view["grid_export_delivered"].to_numpy(dtype=float)[idx] if (on_grid and allow_export and "grid_export_delivered" in disp_view.columns) else None,
        y_load=disp_view["load_demand"].to_numpy(dtype=float)[idx],
        title_suffix="Expected" if mode_d == "expected" else f"Scenario: {scen_label_d}",
    )
    st.pyplot(fig, width="stretch")
    _render_energy_balance_check_df(energy_balance)

    st.subheader("Cost summary & Cash-flow")
    expected_row = select_reporting_kpi_row(kpis, data, mode="expected", scenario_label=None)
    total_annual_cost_exp = float(_safe_float(expected_row.get("reported_total_annual_cost", np.nan)))
    delivered_kwh = float(_safe_float(expected_row.get("served_energy_kwh", np.nan)))
    lcoe = total_annual_cost_exp / delivered_kwh if delivered_kwh > 1e-9 and np.isfinite(total_annual_cost_exp) else float("nan")
    gross_k = float(pd.to_numeric(reporting.upfront["Upfront gross [thousand]"], errors="coerce").fillna(0.0).sum()) if not reporting.upfront.empty else 0.0
    net_k = float(pd.to_numeric(reporting.upfront["Upfront net [thousand]"], errors="coerce").fillna(0.0).sum()) if not reporting.upfront.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Annualized Cost (Expected)", f"{total_annual_cost_exp:,.0f}/yr" if np.isfinite(total_annual_cost_exp) else "n/a")
    c2.metric("LCOE (Expected, delivered)", f"{lcoe:,.4f}/kWh" if np.isfinite(lcoe) else "n/a")
    c3.metric("Upfront investment (gross / net) [thousand]", f"{gross_k:,.0f} / {net_k:,.0f}")

    st.markdown("---")
    st.markdown("**Upfront investment** *(per technology)*")
    st.dataframe(reporting.upfront.style.format({"Capacity": "{:,.3g}", "Grant share": "{:.0%}", "Upfront gross [thousand]": "{:,.0f}", "Upfront net [thousand]": "{:,.0f}"}).hide(axis="index"), width="stretch")

    st.markdown("**Expected annual cost composition** *(objective-consistent)*")
    st.dataframe(reporting.expected_cost_components.style.format({"Value": "{:,.0f}"}).hide(axis="index"), width="stretch")

    st.markdown("**Annual fixed O&M** *(per technology)*")
    st.dataframe(reporting.expected_fixed_om.style.format({"Annual FOM [/yr]": "{:,.0f}"}).hide(axis="index"), width="stretch")

    st.markdown("**Cash-flow annuities** *(per technology, expected)*")
    st.dataframe(reporting.annuities.style.format({"Annuity [/yr]": "{:,.0f}"}).hide(axis="index"), width="stretch")

    st.caption("Expected annual cost components and annuity breakdown per technology")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={"width_ratios": [1.5, 1]})
    cost_chart_df = reporting.expected_cost_components[reporting.expected_cost_components["Component"] != "TOTAL (Expected)"].copy()
    if not cost_chart_df.empty:
        ax1.barh(cost_chart_df["Component"], cost_chart_df["Value"])
        ax1.axvline(0.0, color="#444444", linewidth=1.0)
        ax1.set_xlabel("Value [/yr]")
        ax1.set_title("Expected Annual Cost Components")

    total_annuity = float(_safe_float(expected_row.get("investment_annuity_cost", 0.0)))
    ann_vals = pd.to_numeric(reporting.annuities["Annuity [/yr]"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    ann_labels = reporting.annuities["Technology (lifetime)"].tolist()
    if total_annuity > 0 and ann_vals.size > 0:
        ann_pct = 100.0 * ann_vals / total_annuity
        ax2.barh(ann_labels, ann_pct)
        ax2.set_xlabel("Share of Total Annuity (%)")
        ax2.set_title("Annuity Breakdown by Technology")

    plt.tight_layout()
    st.pyplot(fig, width="stretch")

    st.markdown("**Embodied externalities** *(annualized)*")
    scope3_kg_exp = float(_safe_float(expected_row.get("scope3_emissions_kgco2e", 0.0)))
    embodied_cost_exp = float(pd.to_numeric(reporting.embodied["Embodied Cost [/yr]"], errors="coerce").fillna(0.0).sum()) if not reporting.embodied.empty else 0.0
    c1, c2 = st.columns(2)
    c1.metric("Embodied emissions (Expected)", f"{scope3_kg_exp:,.0f} kgCO2e/yr")
    c2.metric("Embodied externality cost (Expected)", f"{embodied_cost_exp:,.0f}/yr")
    st.dataframe(reporting.embodied.style.format({"Embodied Emissions [kg/yr]": "{:,.0f}", "Embodied Cost [/yr]": "{:,.0f}"}).hide(axis="index"), width="stretch")

    st.markdown("**Scenario-specific operational costs & emissions**")
    st.caption("Variable operating cost and emissions can be inspected scenario-by-scenario.")
    scenario_values = [str(s) for s in data.coords["scenario"].values.tolist()]
    ms_enabled = bool(((settings.get("multi_scenario", {}) or {}).get("enabled", False)))
    view = st.selectbox("View:", ["Expected"] + [f"Scenario {s}" for s in scenario_values], key="fuel_view_sel_file") if ms_enabled else "Expected"

    annual_variable_cost_exp = float(_safe_float(expected_row.get("annual_variable_cost", 0.0)))
    if view == "Expected":
        variable_cost_view = annual_variable_cost_exp
        total_emissions_view = float(_safe_float(expected_row.get("emissions_kgco2e", 0.0)))
    else:
        sc = view.split("Scenario ", 1)[-1].strip()
        scenario_row = select_reporting_kpi_row(kpis, data, mode="scenario", scenario_label=sc)
        variable_cost_view = float(_safe_float(scenario_row.get("annual_variable_cost", 0.0)))
        total_emissions_view = float(_safe_float(scenario_row.get("emissions_kgco2e", 0.0)))
    m1, m2 = st.columns(2)
    m1.metric("Annual variable cost", f"{variable_cost_view:,.0f}/yr")
    m2.metric("Total emissions", f"{total_emissions_view:,.0f} kgCO2e/yr")

    with st.expander("Scenario-wise variable cost breakdown", expanded=False):
        st.dataframe(reporting.scenario_variable_costs.style.format({"Fuel cost": "{:,.0f}", "Grid import cost": "{:,.0f}", "Grid export revenue": "{:,.0f}", "RES subsidy revenue": "{:,.0f}", "Annual variable cost": "{:,.0f}", "Weight": "{:.3f}"}).hide(axis="index"), width="stretch")

    with st.expander("Scenario-wise emissions breakdown", expanded=False):
        st.dataframe(reporting.scenario_emissions.style.format({"Scope 1 emissions": "{:,.0f}", "Scope 2 emissions": "{:,.0f}", "Scope 3 emissions": "{:,.0f}", "Total emissions": "{:,.0f}", "Emissions cost": "{:,.0f}", "Weight": "{:.3f}"}).hide(axis="index"), width="stretch")

    with st.expander("Scenario-wise total operating cost breakdown", expanded=False):
        st.dataframe(reporting.scenario_total_operating_costs.style.format({"Fixed O&M": "{:,.0f}", "Fuel cost": "{:,.0f}", "Grid import cost": "{:,.0f}", "Grid export revenue": "{:,.0f}", "RES subsidy revenue": "{:,.0f}", "Annual variable cost": "{:,.0f}", "Lost load penalty": "{:,.0f}", "Emissions cost": "{:,.0f}", "Total operating cost": "{:,.0f}", "Weight": "{:.3f}"}).hide(axis="index"), width="stretch")

    st.subheader("Saved Result Files")
    st.caption("These result views were reconstructed from files already exported in the project folder.")
    for name in ("dispatch_timeseries.csv", "energy_balance.csv", "design_summary.csv", "kpis.csv"):
        st.write(str(file_results.results_dir / name))
