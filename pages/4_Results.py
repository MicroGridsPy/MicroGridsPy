# generation_planning/pages/3_results.py
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import streamlit as st

from core.export.results_bundle import ResultsBundle
from core.export.results_page_helpers import (
    build_energy_balance_dataframe,
    export_results_from_bundle,
    get_results_bundle_from_session,
    load_multi_year_results_from_files,
    load_typical_year_results_from_files,
)
from core.export.typical_year_reporting import (
    build_reporting_tables,
    select_dispatch_view as select_reporting_dispatch_view,
    select_kpi_row as select_reporting_kpi_row,
)
from core.export.typical_year_results import build_design_summary_table, build_dispatch_timeseries_table
from core.visualization.page_helpers import get_dataset_settings, get_nested_flag, safe_float as _safe_float
from core.visualization.multi_year_results_page import render_multi_year_results, render_multi_year_results_from_files
from core.visualization.typical_year_file_results_page import render_typical_year_results_from_files


# Keep aligned with your Optimization page
KEYS = {
    "solution": "gp_solution",
    "data": "gp_data",
    "vars": "gp_vars",
    "active_project": "active_project",
}


# -----------------------------------------------------------------------------
# small utilities
# -----------------------------------------------------------------------------
def _get_var_solution(
    *,
    vars_dict: Dict[str, Any],
    sol_ds: Optional[xr.Dataset],
    name: str,
) -> Optional[xr.DataArray]:
    """
    Preferred source: solution dataset variable
    Fallback: linopy var.solution
    """
    # 1) from xr solution dataset
    if isinstance(sol_ds, xr.Dataset) and name in sol_ds:
        try:
            da = sol_ds[name]
            if isinstance(da, xr.DataArray):
                return da
        except Exception:
            pass

    # 2) fallback from linopy var
    try:
        v = vars_dict.get(name, None)
        if v is not None and hasattr(v, "solution") and v.solution is not None:
            return v.solution
    except Exception:
        pass

    return None


def _scenario_selector(settings: Dict[str, Any], data: xr.Dataset, *, key: str) -> Tuple[str, Optional[str]]:
    """
    Returns:
      mode: "expected" or "scenario"
      scenario_label: if mode == "scenario", the selected scenario label (string)
    """
    ms_enabled = bool(((settings.get("multi_scenario", {}) or {}).get("enabled", False)))

    if not ms_enabled:
        return "scenario", str(data.coords["scenario"].values[0])

    scen_labels = [str(s) for s in data.coords["scenario"].values.tolist()]
    options = ["Expected"] + [f"Scenario: {s}" for s in scen_labels]
    sel = st.selectbox("View metrics for:", options=options, index=0, key=key)


    if sel == "Expected":
        return "expected", None
    return "scenario", sel.split("Scenario: ", 1)[-1].strip()


def _weighted_over_scenario(da: xr.DataArray, w_s: xr.DataArray) -> xr.DataArray:
    """Collapse scenario using weights; returns da without scenario dim."""
    if "scenario" not in da.dims:
        return da
    # align weights
    w = w_s
    if not isinstance(w, xr.DataArray):
        w = xr.DataArray(w_s, dims=("scenario",), coords={"scenario": da.coords["scenario"]})
    return (da * w).sum("scenario")


def _pick_mode(da: xr.DataArray, *, mode: str, scenario_label: Optional[str], w_s: xr.DataArray) -> xr.DataArray:
    """Return (period, ...) DataArray with scenario collapsed or selected."""
    if "scenario" not in da.dims:
        return da
    if mode == "expected":
        return _weighted_over_scenario(da, w_s=w_s)
    # scenario-wise
    return da.sel(scenario=scenario_label)


def _safe_percent(numerator: float, denominator: float) -> float | None:
    if abs(float(denominator)) <= 1e-12:
        return None
    return 100.0 * float(numerator) / float(denominator)


def _build_typical_diagnostics_table(
    *,
    data: xr.Dataset,
    vars_dict: Dict[str, Any],
    sol_ds: Optional[xr.Dataset],
    mode: str,
    scenario_label: Optional[str],
    w_s: xr.DataArray,
) -> pd.DataFrame:
    settings = get_dataset_settings(data)
    battery_loss_model = str(((settings.get("battery_model", {}) or {}).get("loss_model", "constant_efficiency")) or "constant_efficiency").strip().lower()
    generator_partial_load = bool(((settings.get("generator", {}) or {}).get("partial_load_modelling_enabled", False)))
    if battery_loss_model != "convex_loss_epigraph" and not generator_partial_load:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []

    bat_ch = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="battery_charge")
    bat_dis = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="battery_discharge")
    bat_ch_dc = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="battery_charge_dc")
    bat_dis_dc = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="battery_discharge_dc")
    bat_ch_loss = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="battery_charge_loss")
    bat_dis_loss = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="battery_discharge_loss")
    fuel_cons = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="fuel_consumption")
    gen_gen = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="generator_generation")

    if all(isinstance(x, xr.DataArray) for x in (bat_ch, bat_dis, bat_ch_dc, bat_dis_dc)):
        ch_ac = _pick_mode(bat_ch, mode=mode, scenario_label=scenario_label, w_s=w_s)
        dis_ac = _pick_mode(bat_dis, mode=mode, scenario_label=scenario_label, w_s=w_s)
        ch_dc = _pick_mode(bat_ch_dc, mode=mode, scenario_label=scenario_label, w_s=w_s)
        dis_dc = _pick_mode(bat_dis_dc, mode=mode, scenario_label=scenario_label, w_s=w_s)
        ch_ac_sum = _safe_float(ch_ac.sum("period"))
        dis_ac_sum = _safe_float(dis_ac.sum("period"))
        ch_dc_sum = _safe_float(ch_dc.sum("period"))
        dis_dc_sum = _safe_float(dis_dc.sum("period"))
        rows.append({"Metric": "Battery DC throughput", "Value": 0.5 * (ch_dc_sum + dis_dc_sum) / 1e3, "Unit": "MWh"})
        charge_eff = _safe_percent(ch_dc_sum, ch_ac_sum)
        discharge_eff = _safe_percent(dis_ac_sum, dis_dc_sum)
        roundtrip_eff = None
        if charge_eff is not None and discharge_eff is not None:
            roundtrip_eff = (charge_eff / 100.0) * (discharge_eff / 100.0) * 100.0
        if charge_eff is not None:
            rows.append({"Metric": "Battery avg charging efficiency", "Value": charge_eff, "Unit": "%"})
        if discharge_eff is not None:
            rows.append({"Metric": "Battery avg discharging efficiency", "Value": discharge_eff, "Unit": "%"})
        if roundtrip_eff is not None:
            rows.append({"Metric": "Battery implied round-trip efficiency", "Value": roundtrip_eff, "Unit": "%"})
        if isinstance(bat_ch_loss, xr.DataArray) and isinstance(bat_dis_loss, xr.DataArray):
            ch_loss = _pick_mode(bat_ch_loss, mode=mode, scenario_label=scenario_label, w_s=w_s)
            dis_loss = _pick_mode(bat_dis_loss, mode=mode, scenario_label=scenario_label, w_s=w_s)
            rows.append(
                {
                    "Metric": "Battery conversion losses",
                    "Value": (_safe_float(ch_loss.sum("period")) + _safe_float(dis_loss.sum("period"))) / 1e3,
                    "Unit": "MWh",
                }
            )
    if isinstance(fuel_cons, xr.DataArray) and isinstance(gen_gen, xr.DataArray) and "fuel_lhv_kwh_per_unit_fuel" in data:
        fuel_sel = _pick_mode(fuel_cons, mode=mode, scenario_label=scenario_label, w_s=w_s)
        gen_sel = _pick_mode(gen_gen, mode=mode, scenario_label=scenario_label, w_s=w_s)
        lhv_sel = _pick_mode(data["fuel_lhv_kwh_per_unit_fuel"], mode=mode, scenario_label=scenario_label, w_s=w_s)
        fuel_sum = _safe_float(fuel_sel.sum("period"))
        gen_sum = _safe_float(gen_sel.sum("period"))
        lhv_val = _safe_float(lhv_sel)
        avg_eff = _safe_percent(gen_sum, fuel_sum * lhv_val)
        if avg_eff is not None:
            rows.append({"Metric": "Generator average conversion efficiency", "Value": avg_eff, "Unit": "%"})
        if "generator_nominal_efficiency_full_load" in data:
            gen_nom_eff = _pick_mode(
                data["generator_nominal_efficiency_full_load"],
                mode=mode,
                scenario_label=scenario_label,
                w_s=w_s,
            )
            rows.append(
                {
                    "Metric": "Generator nominal full-load efficiency",
                    "Value": 100.0 * _safe_float(gen_nom_eff),
                    "Unit": "%",
                }
            )
        rows.append({"Metric": "Generator fuel consumption", "Value": fuel_sum, "Unit": "fuel units"})

    return pd.DataFrame(rows)


def _days_to_slice(T: int, start_day: int, ndays: int) -> Tuple[slice, int, int]:
    """
    Convert day window to a 0-based slice for numpy arrays.
    Assumes hourly typical year: 24 hours/day.

    Returns:
      idx: slice for numpy
      start_hr_label: 1-based hour label for x-axis
      window: number of hours in window
    """
    ndays = int(np.clip(ndays, 1, 7))
    max_day = max(1, int(np.ceil(T / 24)))
    start_day = int(np.clip(start_day, 1, max_day))

    window = ndays * 24
    i0 = (start_day - 1) * 24
    i1 = min(T, i0 + window)

    # label is 1-based hour index
    start_hr_label = i0 + 1
    return slice(i0, i1), start_hr_label, (i1 - i0)

# ---------------------------------------------------------------------
# Plot palette (match reference)
# ---------------------------------------------------------------------
C_RES  = "#FFD700"  # Renewables
C_BAT  = "#00ACC1"  # Battery charge/discharge
C_GEN  = "#546E7A"  # Generators
C_IMP  = "#9C27B0"  # Grid import
C_EXP  = "#9C27B0"  # Grid export
C_LL   = "#E53935"  # Lost load
C_LOAD = "#111111"  # Load


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
    """
    Positive stack: RES → BDIS → GEN → G-Import → Lost Load.
    Negative stack: Battery charge → Grid export.
    """
    y_bnet = y_bdis - y_bch
    y_bnet_pos = np.clip(y_bnet, 0.0, None)
    y_bnet_neg = np.clip(-y_bnet, 0.0, None)

    # cumulative positive stack
    p1 = y_res
    p2 = p1 + y_bnet_pos
    p3 = p2 + y_gen
    p4 = p3 + (y_gimp if y_gimp is not None else 0.0)
    p5 = p4 + y_ll

    # negative stack
    n1 = -y_bnet_neg
    n2 = n1 - (y_gexp if y_gexp is not None else 0.0)

    # positive fills
    ax.fill_between(x, 0,  p1,  color=C_RES, alpha=0.85, label="Renewables")
    if np.any(y_bnet_pos > 0):
        ax.fill_between(x, p1, p2, color=C_BAT, alpha=0.35, label="Battery net discharge")
    ax.fill_between(x, p2, p3, color=C_GEN, alpha=0.85, label="Generator")
    if y_gimp is not None and np.any(y_gimp > 0):
        ax.fill_between(x, p3, p4, color=C_IMP, alpha=0.85, label="Grid import")
    if np.any(y_ll > 0):
        ax.fill_between(x, p4, p5, color=C_LL, alpha=0.45, label="Lost load")

    # negative fills
    if np.any(y_bnet_neg > 0):
        ax.fill_between(x, 0, n1, color=C_BAT, alpha=0.35, label="Battery net charge")
    if y_gexp is not None and np.any(y_gexp > 0):
        ax.fill_between(x, n1, n2, color=C_EXP, alpha=0.75, label="Grid export")

    # load line
    ax.plot(x, y_load, color=C_LOAD, linewidth=1.8, label="Load")

    ax.set_title(f"Dispatch plot – {title_suffix}")
    ax.set_xlabel("Hour of typical year")
    ax.set_ylabel("kWh per hour (≈ kW)")
    ax.grid(True, alpha=0.25, linestyle=":")
    ax.legend(ncols=4, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.25))


def _render_energy_balance_check(bundle: ResultsBundle, tolerance: float = 1e-6) -> None:
    with st.expander("Energy Balance Check", expanded=False):
        try:
            eb = build_energy_balance_dataframe(bundle)
        except Exception as e:
            st.info(f"Energy balance unavailable: {e}")
            return

        max_abs = float(np.max(np.abs(eb["balance_residual"].to_numpy(dtype=float))))
        mean_res = float(np.mean(eb["balance_residual"].to_numpy(dtype=float)))

        c1, c2 = st.columns(2)
        c1.metric("Max |residual|", f"{max_abs:.3e}")
        c2.metric("Mean residual", f"{mean_res:.3e}")

        if max_abs > tolerance:
            st.warning(f"Residual exceeds tolerance {tolerance:.1e}")
        else:
            st.success(f"Residual within tolerance {tolerance:.1e}")

        st.dataframe(eb, width="stretch")


def render_generation_planning_results_page() -> None:
    st.title("Results")
    st.caption("Explore the latest solved results from session state or, if available, saved results loaded from project files.")

    project_name = st.session_state.get(KEYS["active_project"])
    if project_name:
        st.success(f"Active project: {project_name}")

    # Canonical source for all sections: model.solution -> vars -> data via ResultsBundle helper.
    bundle = get_results_bundle_from_session(st.session_state, active_project=project_name)
    if bundle is None or not isinstance(bundle.data, xr.Dataset) or not isinstance(bundle.vars, dict):
        if project_name:
            try:
                file_results = load_typical_year_results_from_files(project_name)
            except Exception as exc:
                file_results = None
                st.warning(f"Saved results could not be loaded from files: {exc}")
            if file_results is not None:
                render_typical_year_results_from_files(file_results, project_name)
                return
            try:
                multi_year_file_results = load_multi_year_results_from_files(project_name)
            except Exception as exc:
                multi_year_file_results = None
                st.warning(f"Saved multi-year results could not be loaded from files: {exc}")
            if multi_year_file_results is not None:
                render_multi_year_results_from_files(multi_year_file_results, project_name)
                return
        st.error("No results found. Please run the optimization first (solve step).")
        return

    data: xr.Dataset = bundle.data
    vars_dict: Dict[str, Any] = bundle.vars
    sol_ds: Optional[xr.Dataset] = bundle.solution if isinstance(bundle.solution, xr.Dataset) else None

    settings = get_dataset_settings(data)
    formulation = str(settings.get("formulation", "steady_state"))
    if formulation == "dynamic":
        render_multi_year_results(bundle, project_name)
        return

    on_grid = get_nested_flag(settings, ("grid", "on_grid"), default=False)
    allow_export = get_nested_flag(settings, ("grid", "allow_export"), default=False)

    # weights (scenario,)
    w_s = data.get("scenario_weight", None)
    if w_s is None:
        # fall back to equal weights
        scen = data.coords["scenario"]
        w_s = xr.DataArray(np.ones(int(scen.size)) / float(scen.size), dims=("scenario",), coords={"scenario": scen})

    # -----------------------------------------------------------------------------
    # Read solved variables (design + ops)
    # -----------------------------------------------------------------------------
    res_units = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="res_units")
    battery_units = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="battery_units")
    generator_units = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="generator_units")

    if res_units is None or battery_units is None or generator_units is None:
        st.error("Design variables not found in results. Ensure the model solved and variables are stored in session.")
        return

    # -----------------------------------------------------------------------------
    # Sizing summary
    # -----------------------------------------------------------------------------
    st.subheader("Sizing summary")

    res_nom_kw = data["res_nominal_capacity_kw"]  # (resource,)
    bat_nom_kwh = data["battery_nominal_capacity_kwh"]  # scalar
    gen_nom_kw = data["generator_nominal_capacity_kw"]  # scalar

    cap_res_kw = (res_units * res_nom_kw)
    cap_bat_kwh = (battery_units * bat_nom_kwh)
    cap_gen_kw = (generator_units * gen_nom_kw)
    dispatch_df = build_dispatch_timeseries_table(data=data, vars=vars_dict, solution=sol_ds)
    design_df = build_design_summary_table(data=data, vars=vars_dict, solution=sol_ds)
    reporting = build_reporting_tables(
        data=data,
        dispatch_df=dispatch_df,
        design_df=design_df,
        solver_objective_value=bundle.objective_value,
    )

    df_size = pd.DataFrame(
        [
            {
                "Component": "Renewables (total)",
                "Installed units": _safe_float(res_units.sum("resource")),
                "Capacity": _safe_float(cap_res_kw.sum("resource")),
                "Unit": "kW",
            },
            {
                "Component": "Battery",
                "Installed units": _safe_float(battery_units),
                "Capacity": _safe_float(cap_bat_kwh),
                "Unit": "kWh",
            },
            {
                "Component": "Generator",
                "Installed units": _safe_float(generator_units),
                "Capacity": _safe_float(cap_gen_kw),
                "Unit": "kW",
            },
        ]
    )

    st.dataframe(
        df_size.style.format({"Installed units": "{:,.3g}", "Capacity": "{:,.3g}"}).hide(axis="index"),
        width="stretch",
    )

    with st.expander("Per-renewable breakdown", expanded=False):
        df_res = pd.DataFrame(
            {
                "Resource": [str(r) for r in cap_res_kw.coords["resource"].values.tolist()],
                "Installed units": [float(v) for v in res_units.values.tolist()],
                "Capacity [kW]": [float(v) for v in cap_res_kw.values.tolist()],
            }
        )
        st.dataframe(
            df_res.style.format({"Installed units": "{:,.3g}", "Capacity [kW]": "{:,.3g}"}).hide(axis="index"),
            width="stretch",
        )

    # -----------------------------------------------------------------------------
    # KPIs (Expected or Scenario)
    # -----------------------------------------------------------------------------
    st.subheader("Performance KPIs")

    mode, scen_label = _scenario_selector(settings, data, key="gp_kpi_view_sel")

    load = data.get("load_demand", None)  # expected dims: (period, scenario)
    if load is None:
        st.warning("load_demand not found in data. KPIs will be partial.")
    else:
        kpi_row = select_reporting_kpi_row(reporting.kpis, data, mode=mode, scenario_label=scen_label)
        kpi_df = pd.DataFrame(
            {
                "Metric": [
                    "Load",
                    "Delivered energy",
                    "Lost load",
                    "Renewable generation",
                    "Generator generation",
                    "Grid imports (delivered)" if on_grid else None,
                    "Grid renewable contribution" if on_grid else None,
                    "Grid exports" if (on_grid and allow_export) else None,
                    "Renewable share of primary supply",
                    "Curtailment share of renewables",
                    "Lost load fraction",
                ],
                "Value": [
                    float(_safe_float(kpi_row.get("total_demand_kwh", 0.0))) / 1e3,
                    float(_safe_float(kpi_row.get("served_energy_kwh", 0.0))) / 1e3,
                    float(_safe_float(kpi_row.get("lost_load_kwh", 0.0))) / 1e3,
                    float(_safe_float(kpi_row.get("total_res_kwh", 0.0))) / 1e3,
                    float(_safe_float(kpi_row.get("generator_generation_kwh", 0.0))) / 1e3,
                    float(_safe_float(kpi_row.get("grid_import_delivered_kwh", 0.0))) / 1e3 if on_grid else None,
                    float(_safe_float(kpi_row.get("grid_renewable_kwh", 0.0))) / 1e3 if on_grid else None,
                    float(_safe_float(kpi_row.get("grid_export_delivered_kwh", 0.0))) / 1e3 if (on_grid and allow_export) else None,
                    100.0 * float(_safe_float(kpi_row.get("renewable_penetration", 0.0))),
                    100.0 * float(_safe_float(kpi_row.get("renewable_curtailment_share", 0.0))),
                    100.0 * float(_safe_float(kpi_row.get("lost_load_fraction", 0.0))),
                ],
                "Unit": [
                    "MWh",
                    "MWh",
                    "MWh",
                    "MWh",
                    "MWh",
                    "MWh" if on_grid else None,
                    "MWh" if on_grid else None,
                    "MWh" if (on_grid and allow_export) else None,
                    "%",
                    "%",
                    "%",
                ],
            }
        ).dropna(subset=["Metric"])

        st.dataframe(
            kpi_df.style.format({"Value": "{:,.2f}"}).hide(axis="index"),
            width="stretch",
        )

        diagnostics_df = _build_typical_diagnostics_table(
            data=data,
            vars_dict=vars_dict,
            sol_ds=sol_ds,
            mode=mode,
            scenario_label=scen_label,
            w_s=w_s,
        )
        if not diagnostics_df.empty:
            st.markdown("**Efficiency diagnostics**")
            st.dataframe(
                diagnostics_df.style.format({"Value": "{:,.4f}"}).hide(axis="index"),
                width="stretch",
            )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Dispatch plot
    # -------------------------------------------------------------------------
    st.subheader("Least-Cost Energy Mix")
    st.caption(
        "Stacked dispatch over a selected time window. Positive areas are supply-side contributions; "
        "battery charging and grid exports are shown below zero."
    )

    required_dispatch_cols = {
        "load_demand",
        "lost_load",
        "res_generation_total",
        "generator_generation",
        "battery_charge",
        "battery_discharge",
    }
    if any(col not in reporting.dispatch.columns for col in required_dispatch_cols):
        st.info("Dispatch plot needs load_demand and the main operational variables. Some are missing.")
        return

    mode_d, scen_label_d = _scenario_selector(settings, data, key="gp_disp_view_sel")
    disp_view = select_reporting_dispatch_view(reporting.dispatch, data, mode=mode_d, scenario_label=scen_label_d)

    # ---------- Time window ----------
    T = int(len(disp_view))
    with st.expander("Time window", expanded=False):
        st.caption("Pick the start day and how many days to plot (1–7).")
        max_days = max(1, int(np.ceil(T / 24)))
        ndays = st.slider(
            "Number of days",
            min_value=1,
            max_value=min(7, max_days),
            value=1,
            step=1,
            key="gp_disp_ndays",
        )
        max_start_day = max(1, max_days - ndays + 1)
        start_day = st.slider(
            "Start day",
            min_value=1,
            max_value=max_start_day,
            value=1,
            step=1,
            key="gp_disp_start_day",
        )

    idx, start_hr, window = _days_to_slice(T, start_day=start_day, ndays=ndays)
    x = np.arange(start_hr, start_hr + window)

    # arrays
    y_load = disp_view["load_demand"].to_numpy(dtype=float)[idx]
    y_ll   = disp_view["lost_load"].to_numpy(dtype=float)[idx]
    y_res  = disp_view["res_generation_total"].to_numpy(dtype=float)[idx]
    y_gen  = disp_view["generator_generation"].to_numpy(dtype=float)[idx]
    y_bdis = disp_view["battery_discharge"].to_numpy(dtype=float)[idx]
    y_bch  = disp_view["battery_charge"].to_numpy(dtype=float)[idx]
    y_gimp = (disp_view["grid_import_delivered"].to_numpy(dtype=float)[idx] if "grid_import_delivered" in disp_view.columns else None)
    y_gexp = (disp_view["grid_export_delivered"].to_numpy(dtype=float)[idx] if "grid_export_delivered" in disp_view.columns else None)

    # ---------- Plot ----------
    fig, ax = plt.subplots(figsize=(11, 4))
    title_suffix = "Expected" if mode_d == "expected" else f"Scenario: {scen_label_d}"

    _plot_dispatch_stack(
        ax=ax,
        x=x,
        y_res=y_res,
        y_bdis=y_bdis,
        y_gen=y_gen,
        y_gimp=y_gimp,
        y_ll=y_ll,
        y_bch=y_bch,
        y_gexp=y_gexp,
        y_load=y_load,
        title_suffix=title_suffix,
    )

    st.pyplot(fig, width="stretch")
    _render_energy_balance_check(bundle, tolerance=1e-6)

    # -------------------------------------------------------------------------
    # Cost summary & Cash-flow (objective-consistent)
    # -------------------------------------------------------------------------
    st.subheader("Cost summary & Cash-flow")

    # -----------------------------
    # 11) Headline metrics
    # -----------------------------
    expected_row = select_reporting_kpi_row(reporting.kpis, data, mode="expected", scenario_label=None)
    total_annual_cost_exp = float(_safe_float(expected_row.get("reported_total_annual_cost", np.nan)))
    delivered_kwh = float(_safe_float(expected_row.get("served_energy_kwh", np.nan)))
    lcoe = total_annual_cost_exp / delivered_kwh if delivered_kwh > 1e-9 and np.isfinite(total_annual_cost_exp) else float("nan")
    total_upfront_gross_k = float(pd.to_numeric(reporting.upfront["Upfront gross [thousand]"], errors="coerce").fillna(0.0).sum()) if not reporting.upfront.empty else 0.0
    total_upfront_net_k = float(pd.to_numeric(reporting.upfront["Upfront net [thousand]"], errors="coerce").fillna(0.0).sum()) if not reporting.upfront.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Annualized Cost (Expected)", f"{total_annual_cost_exp:,.0f}/yr")
    c2.metric("LCOE (Expected, delivered)", f"{lcoe:,.4f}/kWh" if np.isfinite(lcoe) else "n/a")
    c3.metric("Upfront investment (gross / net) [thousand]", f"{total_upfront_gross_k:,.0f} / {total_upfront_net_k:,.0f}")

    st.markdown("---")
    st.markdown("**Upfront investment** *(per technology)*")
    st.dataframe(
        reporting.upfront.style.format({
            "Capacity": "{:,.3g}",
            "Grant share": "{:.0%}",
            "Upfront gross [thousand]": "{:,.0f}",
            "Upfront net [thousand]": "{:,.0f}",
        }).hide(axis="index"),
        width="stretch",
    )

    st.markdown("**Expected annual cost composition** *(objective-consistent)*")
    st.dataframe(
        reporting.expected_cost_components.style.format({"Value": "{:,.0f}"}).hide(axis="index"),
        width="stretch",
    )

    st.markdown("**Expected annual fixed O&M** *(per technology)*")
    st.dataframe(
        reporting.expected_fixed_om.style.format({"Annual FOM [/yr]": "{:,.0f}"}).hide(axis="index"),
        width="stretch",
    )

    st.markdown("**Cash-flow annuities** *(per technology, expected)*")
    st.dataframe(
        reporting.annuities.style.format({"Annuity [/yr]": "{:,.0f}"}).hide(axis="index"),
        width="stretch",
    )

    st.caption("Expected annual cost components and annuity breakdown per technology")
    cost_chart_df = reporting.expected_cost_components[
        reporting.expected_cost_components["Component"] != "TOTAL (Expected)"
    ].copy()
    annuity_total = float(_safe_float(expected_row.get("investment_annuity_cost", 0.0)))
    ann_vals = pd.to_numeric(reporting.annuities["Annuity [/yr]"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    ann_labels = reporting.annuities["Technology (lifetime)"].tolist()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={"width_ratios": [1.5, 1]})
    if not cost_chart_df.empty:
        ax1.barh(cost_chart_df["Component"], cost_chart_df["Value"])
        ax1.axvline(0.0, color="#444444", linewidth=1.0)
        ax1.set_xlabel("Value [/yr]")
        ax1.set_title("Expected Annual Cost Components")
    if annuity_total > 0 and ann_vals.size > 0:
        ann_pct = 100.0 * ann_vals / annuity_total
        ax2.barh(ann_labels, ann_pct)
        ax2.set_xlabel("Share of Total Annuity (%)")
        ax2.set_title("Annuity Breakdown by Technology")
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("**Embodied externalities** *(annualized)*")
    embodied_cost_exp = float(pd.to_numeric(reporting.embodied["Embodied Cost [/yr]"], errors="coerce").fillna(0.0).sum()) if not reporting.embodied.empty else 0.0
    scope3_kg_exp = float(_safe_float(expected_row.get("scope3_emissions_kgco2e", 0.0)))
    c1, c2 = st.columns(2)
    c1.metric("Embodied emissions (Expected)", f"{scope3_kg_exp:,.0f} kgCO2e/yr")
    c2.metric("Embodied externality cost (Expected)", f"{embodied_cost_exp:,.0f}/yr")
    st.dataframe(
        reporting.embodied.style.format({
            "Embodied Emissions [kg/yr]": "{:,.0f}",
            "Embodied Cost [/yr]": "{:,.0f}",
        }).hide(axis="index"),
        width="stretch",
    )

    st.subheader("Scenario-specific operational costs & emissions")
    st.caption("Variable operating cost and emissions can be inspected scenario-by-scenario.")

    ms_enabled = bool(((settings.get("multi_scenario", {}) or {}).get("enabled", False)))
    if ms_enabled:
        scen_vals = [str(s) for s in data.coords["scenario"].values.tolist()]
        view = st.selectbox("View:", ["Expected"] + [f"Scenario {s}" for s in scen_vals], key="fuel_view_sel")
    else:
        view = "Expected"

    if view == "Expected":
        variable_cost_view = float(_safe_float(expected_row.get("annual_variable_cost", 0.0)))
        total_emissions_view = float(_safe_float(expected_row.get("emissions_kgco2e", 0.0)))
    else:
        sc = view.split("Scenario ", 1)[-1].strip()
        scenario_row = select_reporting_kpi_row(reporting.kpis, data, mode="scenario", scenario_label=sc)
        variable_cost_view = float(_safe_float(scenario_row.get("annual_variable_cost", 0.0)))
        total_emissions_view = float(_safe_float(scenario_row.get("emissions_kgco2e", 0.0)))

    m1, m2 = st.columns(2)
    m1.metric("Annual variable cost", f"{variable_cost_view:,.0f}/yr")
    m2.metric("Total emissions", f"{total_emissions_view:,.0f} kgCO2e/yr")

    with st.expander("Scenario-wise variable cost breakdown", expanded=False):
        st.dataframe(
            reporting.scenario_variable_costs.style.format({
                "Fuel cost": "{:,.0f}",
                "Grid import cost": "{:,.0f}",
                "Grid export revenue": "{:,.0f}",
                "RES subsidy revenue": "{:,.0f}",
                "Annual variable cost": "{:,.0f}",
                "Weight": "{:.3f}",
            }).hide(axis="index"),
            width="stretch",
        )

    with st.expander("Scenario-wise emissions breakdown", expanded=False):
        st.dataframe(
            reporting.scenario_emissions.style.format({
                "Scope 1 emissions": "{:,.0f}",
                "Scope 2 emissions": "{:,.0f}",
                "Scope 3 emissions": "{:,.0f}",
                "Total emissions": "{:,.0f}",
                "Emissions cost": "{:,.0f}",
                "Weight": "{:.3f}",
            }).hide(axis="index"),
            width="stretch",
        )

    with st.expander("Scenario-wise total operating cost breakdown", expanded=False):
        st.dataframe(
            reporting.scenario_total_operating_costs.style.format({
                "Fixed O&M": "{:,.0f}",
                "Fuel cost": "{:,.0f}",
                "Grid import cost": "{:,.0f}",
                "Grid export revenue": "{:,.0f}",
                "RES subsidy revenue": "{:,.0f}",
                "Annual variable cost": "{:,.0f}",
                "Lost load penalty": "{:,.0f}",
                "Emissions cost": "{:,.0f}",
                "Total operating cost": "{:,.0f}",
                "Weight": "{:.3f}",
            }).hide(axis="index"),
            width="stretch",
        )

    # ======================================================
    # CSV export (Typical-Year)
    # ======================================================
    st.subheader("Export Results")
    if st.button("Export results to CSV", type="primary"):
        try:
            with st.spinner("Exporting results..."):
                model_obj = st.session_state.get("gp_model_obj")
                written = export_results_from_bundle(project_name, bundle, model_obj=model_obj)
            st.success("Export completed.")
            st.json(written)
            st.markdown("**Generated files**")
            for _, p in written.items():
                if isinstance(p, str) and p.endswith(".csv"):
                    st.write(p)
        except Exception as e:
            st.error(f"Export failed: {e}")




# Entrypoint
render_generation_planning_results_page()


