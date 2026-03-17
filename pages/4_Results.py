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

def _crf(r: float, n: float) -> float:
    """Capital recovery factor."""
    r = float(r)
    n = float(n)
    if n <= 0:
        return float("nan")
    if abs(r) < 1e-12:
        return 1.0 / n
    a = (1.0 + r) ** n
    return (r * a) / (a - 1.0)


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
    # cumulative positive stack
    p1 = y_res
    p2 = p1 + y_bdis
    p3 = p2 + y_gen
    p4 = p3 + (y_gimp if y_gimp is not None else 0.0)
    p5 = p4 + y_ll

    # negative stack
    n1 = -y_bch
    n2 = n1 - (y_gexp if y_gexp is not None else 0.0)

    # positive fills
    ax.fill_between(x, 0,  p1,  color=C_RES, alpha=0.85, label="Renewables")
    ax.fill_between(x, p1, p2, color=C_BAT, alpha=0.35, label="Battery discharge")
    ax.fill_between(x, p2, p3, color=C_GEN, alpha=0.85, label="Generator")
    if y_gimp is not None and np.any(y_gimp > 0):
        ax.fill_between(x, p3, p4, color=C_IMP, alpha=0.85, label="Grid import")
    if np.any(y_ll > 0):
        ax.fill_between(x, p4, p5, color=C_LL, alpha=0.45, label="Lost load")

    # negative fills
    if np.any(y_bch > 0):
        ax.fill_between(x, 0, n1, color=C_BAT, alpha=0.35, label="Battery charge")
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

    res_gen = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="res_generation")
    gen_gen = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="generator_generation")
    ll = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="lost_load")
    bat_ch = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="battery_charge")
    bat_dis = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="battery_discharge")

    grid_imp = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="grid_import") if on_grid else None
    grid_exp = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="grid_export") if (on_grid and allow_export) else None

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
        # Collapse/Select per mode, then aggregate totals
        load_p = _pick_mode(load, mode=mode, scenario_label=scen_label, w_s=w_s)
        ll_p = _pick_mode(ll, mode=mode, scenario_label=scen_label, w_s=w_s) if ll is not None else 0.0

        # generation totals
        res_p = _pick_mode(res_gen.sum("resource"), mode=mode, scenario_label=scen_label, w_s=w_s) if res_gen is not None else 0.0
        gen_p = _pick_mode(gen_gen, mode=mode, scenario_label=scen_label, w_s=w_s) if gen_gen is not None else 0.0

        # on-grid
        gimp_p = _pick_mode(grid_imp, mode=mode, scenario_label=scen_label, w_s=w_s) if grid_imp is not None else 0.0
        gexp_p = _pick_mode(grid_exp, mode=mode, scenario_label=scen_label, w_s=w_s) if grid_exp is not None else 0.0

        grid_eta = data.get("grid_transmission_efficiency", None) if on_grid else None
        grid_ren_share = data.get("grid_renewable_share", None) if on_grid else None
        if on_grid and grid_eta is None:
            grid_eta = xr.DataArray(
                np.ones(int(data.coords["scenario"].size)),
                dims=("scenario",),
                coords={"scenario": data.coords["scenario"]},
            )
        if on_grid and grid_ren_share is None:
            grid_ren_share = xr.DataArray(
                np.zeros(int(data.coords["scenario"].size)),
                dims=("scenario",),
                coords={"scenario": data.coords["scenario"]},
            )

        grid_delivered_p = (gimp_p * _pick_mode(grid_eta, mode=mode, scenario_label=scen_label, w_s=w_s)) if on_grid else 0.0
        grid_renewable_p = (
            grid_delivered_p * _pick_mode(grid_ren_share, mode=mode, scenario_label=scen_label, w_s=w_s)
            if on_grid
            else 0.0
        )

        # totals (kWh -> MWh)
        total_load_mwh = _safe_float(load_p.sum("period")) / 1e3
        total_ll_mwh = _safe_float(ll_p.sum("period")) / 1e3
        total_res_mwh = _safe_float(res_p.sum("period")) / 1e3
        total_gen_mwh = _safe_float(gen_p.sum("period")) / 1e3
        total_imp_mwh = _safe_float(grid_delivered_p.sum("period")) / 1e3 if on_grid else 0.0
        total_grid_ren_mwh = _safe_float(grid_renewable_p.sum("period")) / 1e3 if on_grid else 0.0
        total_exp_mwh = _safe_float(gexp_p.sum("period")) / 1e3 if (on_grid and allow_export) else 0.0

        delivered_mwh = max(total_load_mwh - total_ll_mwh, 0.0)
        total_supply_mwh = total_res_mwh + total_gen_mwh + total_imp_mwh

        def _pct(a: float, b: float) -> float:
            return (a / b * 100.0) if b > 1e-12 else 0.0

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
                    "Renewable share of supply",
                    "Lost load fraction",
                ],
                "Value": [
                    total_load_mwh,
                    delivered_mwh,
                    total_ll_mwh,
                    total_res_mwh,
                    total_gen_mwh,
                    total_imp_mwh if on_grid else None,
                    total_grid_ren_mwh if on_grid else None,
                    total_exp_mwh if (on_grid and allow_export) else None,
                    _pct(total_res_mwh + total_grid_ren_mwh, total_supply_mwh),
                    _pct(total_ll_mwh, total_load_mwh),
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
                ],
            }
        ).dropna(subset=["Metric"])

        st.dataframe(
            kpi_df.style.format({"Value": "{:,.2f}"}).hide(axis="index"),
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

    if load is None or ll is None or res_gen is None or gen_gen is None or bat_ch is None or bat_dis is None:
        st.info("Dispatch plot needs load_demand and the main operational variables. Some are missing.")
        return

    mode_d, scen_label_d = _scenario_selector(settings, data, key="gp_disp_view_sel")

    # time series (period) after scenario selection / expectation
    load_p = _pick_mode(load, mode=mode_d, scenario_label=scen_label_d, w_s=w_s)
    ll_p   = _pick_mode(ll,   mode=mode_d, scenario_label=scen_label_d, w_s=w_s)

    res_p  = _pick_mode(res_gen.sum("resource"), mode=mode_d, scenario_label=scen_label_d, w_s=w_s)
    gen_p  = _pick_mode(gen_gen,                mode=mode_d, scenario_label=scen_label_d, w_s=w_s)

    bch_p  = _pick_mode(bat_ch,  mode=mode_d, scenario_label=scen_label_d, w_s=w_s)
    bdis_p = _pick_mode(bat_dis, mode=mode_d, scenario_label=scen_label_d, w_s=w_s)

    gimp_p = _pick_mode(grid_imp, mode=mode_d, scenario_label=scen_label_d, w_s=w_s) if grid_imp is not None else None
    gexp_p = _pick_mode(grid_exp, mode=mode_d, scenario_label=scen_label_d, w_s=w_s) if grid_exp is not None else None

    # ---------- Time window ----------
    T = int(load_p.sizes["period"])
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
    y_load = np.asarray(load_p.values)[idx]
    y_ll   = np.asarray(ll_p.values)[idx]
    y_res  = np.asarray(res_p.values)[idx]
    y_gen  = np.asarray(gen_p.values)[idx]
    y_bdis = np.asarray(bdis_p.values)[idx]
    y_bch  = np.asarray(bch_p.values)[idx]
    y_gimp = (np.asarray(gimp_p.values)[idx] if gimp_p is not None else None)
    y_gexp = (np.asarray(gexp_p.values)[idx] if gexp_p is not None else None)

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
    # Helpers (local)
    # -----------------------------
    def _as_scenario_da(x: Any, *, scenario_like: xr.DataArray) -> xr.DataArray:
        """
        Ensure x is (scenario,) DataArray aligned to scenario_like.
        Accepts scalar, numpy, list, or DataArray (scenario or scalar).
        """
        if isinstance(x, xr.DataArray):
            if "scenario" in x.dims:
                return x.sel(scenario=scenario_like.coords["scenario"])
            # scalar DA -> broadcast
            return xr.DataArray(
                float(_safe_float(x)),
                dims=("scenario",),
                coords={"scenario": scenario_like.coords["scenario"]},
            )
        # python scalar
        return xr.DataArray(
            float(_safe_float(x)),
            dims=("scenario",),
            coords={"scenario": scenario_like.coords["scenario"]},
        )

    def _zeros_scenario(*, scenario_like: xr.DataArray) -> xr.DataArray:
        return xr.DataArray(
            np.zeros((int(scenario_like.size),), dtype=float),
            dims=("scenario",),
            coords={"scenario": scenario_like.coords["scenario"]},
        )

    def _sum_if_dim(da: xr.DataArray, dim: str) -> xr.DataArray:
        return da.sum(dim) if (isinstance(da, xr.DataArray) and dim in da.dims) else da

    # -----------------------------
    # 1) Design capacities
    # -----------------------------
    cap_res_kw = (res_units * data["res_nominal_capacity_kw"]).fillna(0.0)  # (resource,)
    cap_bat_kwh = (battery_units * data["battery_nominal_capacity_kwh"])    # scalar
    cap_gen_kw = (generator_units * data["generator_nominal_capacity_kw"])  # scalar

    # -----------------------------
    # 2) Parameters (as in objective.py)
    # -----------------------------
    # Renewables
    res_capex_kw = data["res_specific_investment_cost_per_kw"]               # (resource,)
    res_grant = data["res_grant_share_of_capex"]                             # (resource,)
    res_life_y = data["res_lifetime_years"]                                  # (resource,)
    res_wacc = data["res_wacc"]                                              # (resource,)
    res_fom_share = data["res_fixed_om_share_per_year"]                      # (scenario, resource)
    res_subsidy_kwh = data["res_production_subsidy_per_kwh"]                 # (scenario, resource)
    res_emb_kg_per_kw = data["res_embedded_emissions_kgco2e_per_kw"]         # (scenario, resource)

    # Battery
    bat_capex_kwh = data["battery_specific_investment_cost_per_kwh"]         # scalar
    bat_life_y = data["battery_calendar_lifetime_years"]                     # scalar
    bat_wacc = data["battery_wacc"]                                          # scalar
    bat_fom_share = data["battery_fixed_om_share_per_year"]                  # (scenario,)
    bat_emb_kg_per_kwh = data["battery_embedded_emissions_kgco2e_per_kwh"]   # (scenario,)

    # Generator
    gen_capex_kw = data["generator_specific_investment_cost_per_kw"]         # scalar
    gen_life_y = data["generator_lifetime_years"]                            # scalar
    gen_wacc = data["generator_wacc"]                                        # scalar
    gen_fom_share = data["generator_fixed_om_share_per_year"]                # (scenario,)
    gen_emb_kg_per_kw = data["generator_embedded_emissions_kgco2e_per_kw"]   # (scenario,)

    # Fuel
    fuel_cost = data["fuel_fuel_cost_per_unit_fuel"]                         # (scenario,)
    fuel_dir_kg_per_unit = data["fuel_direct_emissions_kgco2e_per_unit_fuel"]# (scenario,)

    # Policy / externalities
    lost_load_cost = data["lost_load_cost_per_kwh"]                          # scalar or (scenario,)
    emission_cost = data["emission_cost_per_kgco2e"]                         # scalar or (scenario,)

    # Scenario weights
    scenario_like = data.coords["scenario"]
    w_s = data.get("scenario_weight", None)
    if w_s is None:
        w_s = xr.DataArray(
            np.ones(int(scenario_like.size)) / float(scenario_like.size),
            dims=("scenario",),
            coords={"scenario": scenario_like},
        )

    # Flags
    settings = get_dataset_settings(data)
    on_grid = get_nested_flag(settings, ("grid", "on_grid"), default=False)
    allow_export = get_nested_flag(settings, ("grid", "allow_export"), default=False)

    # Grid prices (only if on-grid)
    grid_import_price = data["grid_import_price"] if on_grid else None       # (period, scenario)
    grid_export_price = data["grid_export_price"] if (on_grid and allow_export) else None
    grid_eta = data.get("grid_transmission_efficiency", None) if on_grid else None
    grid_em_factor = data.get("grid_emissions_factor_kgco2e_per_kwh", None) if on_grid else None

    # -----------------------------
    # 3) Variables (solution)
    # -----------------------------
    # These are already fetched earlier in your page; re-use if available
    # res_gen, ll, grid_imp, grid_exp are already above in your file
    fuel_cons = _get_var_solution(vars_dict=vars_dict, sol_ds=sol_ds, name="fuel_consumption")  # (period, scenario) expected

    if fuel_cons is None:
        st.warning("fuel_consumption not found; fuel costs & direct emissions will be omitted (set to 0).")

    # -----------------------------
    # 4) CRFs (match objective formula)
    # -----------------------------
    crf_res = xr.DataArray(
        [_crf(float(r), float(n)) for r, n in zip(res_wacc.values.tolist(), res_life_y.values.tolist())],
        dims=("resource",),
        coords={"resource": res_wacc.coords["resource"]},
    )
    crf_bat = _crf(_safe_float(bat_wacc), _safe_float(bat_life_y))
    crf_gen = _crf(_safe_float(gen_wacc), _safe_float(gen_life_y))

    # -----------------------------
    # 5) Upfront investment (gross + net after RES grants)
    # -----------------------------
    upfront_res_gross = (cap_res_kw * res_capex_kw).fillna(0.0)                       # (resource,)
    upfront_res_net   = (cap_res_kw * res_capex_kw * (1.0 - res_grant)).fillna(0.0)   # (resource,)
    upfront_bat = (cap_bat_kwh * bat_capex_kwh)
    upfront_gen = (cap_gen_kw * gen_capex_kw)

    total_upfront_gross = _safe_float(upfront_res_gross.sum("resource")) + _safe_float(upfront_bat) + _safe_float(upfront_gen)
    total_upfront_net   = _safe_float(upfront_res_net.sum("resource"))   + _safe_float(upfront_bat) + _safe_float(upfront_gen)

    # convert in kcurrency
    total_upfront_gross_k = total_upfront_gross / 1e3
    total_upfront_net_k   = total_upfront_net / 1e3

    # -----------------------------
    # 6) Annualized CAPEX (annuity) — objective-consistent
    # -----------------------------
    res_capex_eff_kw = (1.0 - res_grant) * res_capex_kw
    ann_res = (crf_res * res_capex_eff_kw * cap_res_kw).fillna(0.0)  # (resource,)
    ann_bat = crf_bat * bat_capex_kwh * cap_bat_kwh                  # scalar
    ann_gen = crf_gen * gen_capex_kw * cap_gen_kw                    # scalar

    total_annuity = _safe_float(ann_res.sum("resource")) + _safe_float(ann_bat) + _safe_float(ann_gen)

    # -----------------------------
    # 7) Fixed O&M (scenario-dependent) + Expected
    #   annual_res_fom_s = Σ_r res_capex_kw[r] * res_fom_share[s,r] * cap_res_kw[r]
    # -----------------------------
    annual_res_fom_s = (res_capex_kw * res_fom_share * cap_res_kw).sum("resource").fillna(0.0)  # (scenario,)
    annual_bat_fom_s = (bat_capex_kwh * bat_fom_share * cap_bat_kwh).fillna(0.0)                # (scenario,)
    annual_gen_fom_s = (gen_capex_kw * gen_fom_share * cap_gen_kw).fillna(0.0)                  # (scenario,)
    annual_fom_s = annual_res_fom_s + annual_bat_fom_s + annual_gen_fom_s                        # (scenario,)

    total_fom_exp = _safe_float((w_s * annual_fom_s).sum("scenario"))

    # Also keep a clean expected per-tech breakdown (Expected of each block)
    res_fom_exp = _weighted_over_scenario(annual_res_fom_s, w_s=w_s)
    bat_fom_exp = _safe_float(_weighted_over_scenario(annual_bat_fom_s, w_s=w_s))
    gen_fom_exp = _safe_float(_weighted_over_scenario(annual_gen_fom_s, w_s=w_s))

    # -----------------------------
    # 8) Variable operating costs per scenario (match objective.py)
    # -----------------------------
    # 8.1 Fuel
    fuel_cost_s = _zeros_scenario(scenario_like=scenario_like)
    if fuel_cons is not None:
        fc = fuel_cons
        # if extra dims sneak in, collapse them safely
        fc = _sum_if_dim(fc, "generator")
        fuel_cost_s = (fc.sum("period") * fuel_cost).fillna(0.0)  # (scenario,)

    fuel_cost_exp = _safe_float((w_s * fuel_cost_s).sum("scenario"))

    # 8.2 Grid import/export
    grid_import_cost_s = _zeros_scenario(scenario_like=scenario_like)
    grid_export_rev_s  = _zeros_scenario(scenario_like=scenario_like)

    if on_grid and grid_imp is not None and grid_import_price is not None:
        grid_import_cost_s = (grid_imp * grid_import_price).sum("period").fillna(0.0)  # (scenario,)
        if allow_export and grid_exp is not None and grid_export_price is not None:
            grid_export_rev_s = (grid_exp * grid_export_price).sum("period").fillna(0.0)  # (scenario,)

    grid_import_cost_exp = _safe_float((w_s * grid_import_cost_s).sum("scenario"))
    grid_export_rev_exp  = _safe_float((w_s * grid_export_rev_s).sum("scenario"))

    # 8.3 RES production subsidy (revenue)
    res_subsidy_rev_s = _zeros_scenario(scenario_like=scenario_like)
    if res_gen is not None:
        res_subsidy_rev_s = (res_gen.sum("period") * res_subsidy_kwh).sum("resource").fillna(0.0)  # (scenario,)
    res_subsidy_rev_exp = _safe_float((w_s * res_subsidy_rev_s).sum("scenario"))

    # 8.4 Lost load penalty
    ll_cost_param_s = _as_scenario_da(lost_load_cost, scenario_like=scenario_like)  # (scenario,)
    ll_cost_s = _zeros_scenario(scenario_like=scenario_like)
    if ll is not None:
        ll_cost_s = (ll.sum("period") * ll_cost_param_s).fillna(0.0)  # (scenario,)
    ll_cost_exp = _safe_float((w_s * ll_cost_s).sum("scenario"))

    # 8.5 Emissions (scope 1 + scope 2 + scope 3), priced
    emission_cost_s = _as_scenario_da(emission_cost, scenario_like=scenario_like)  # (scenario,)

    scope1_kg_s = _zeros_scenario(scenario_like=scenario_like)
    if fuel_cons is not None:
        fc = fuel_cons
        fc = _sum_if_dim(fc, "generator")
        scope1_kg_s = (fc.sum("period") * fuel_dir_kg_per_unit).fillna(0.0)  # (scenario,)

    scope2_kg_s = _zeros_scenario(scenario_like=scenario_like)
    if on_grid and grid_imp is not None:
        grid_eta_s = _as_scenario_da(grid_eta if grid_eta is not None else 1.0, scenario_like=scenario_like)
        grid_em_factor_s = _as_scenario_da(grid_em_factor if grid_em_factor is not None else 0.0, scenario_like=scenario_like)
        scope2_kg_s = ((grid_imp * grid_eta_s).sum("period") * grid_em_factor_s).fillna(0.0)

    # Embodied annualized by lifetime (scenario-dependent factors)
    emb_res_kg_s = ((cap_res_kw * res_emb_kg_per_kw) / res_life_y).sum("resource").fillna(0.0)  # (scenario,)
    emb_gen_kg_s = ((cap_gen_kw * gen_emb_kg_per_kw) / gen_life_y).fillna(0.0)                  # (scenario,)
    emb_bat_kg_s = ((cap_bat_kwh * bat_emb_kg_per_kwh) / bat_life_y).fillna(0.0)                # (scenario,)
    scope3_kg_s = _as_scenario_da(
        (emb_res_kg_s + emb_gen_kg_s + emb_bat_kg_s).fillna(0.0),
        scenario_like=scenario_like,
    )

    total_emissions_kg_s = _as_scenario_da(
        (scope1_kg_s + scope2_kg_s + scope3_kg_s).fillna(0.0),
        scenario_like=scenario_like,
    )
    emissions_cost_s = (emission_cost_s * total_emissions_kg_s).fillna(0.0)         # (scenario,)
    emissions_cost_exp = _safe_float((w_s * emissions_cost_s).sum("scenario"))

    scope1_kg_exp = _safe_float((w_s * scope1_kg_s).sum("scenario"))
    scope2_kg_exp = _safe_float((w_s * scope2_kg_s).sum("scenario"))
    scope3_kg_exp = _safe_float((w_s * scope3_kg_s).sum("scenario"))
    total_emissions_kg_exp = _safe_float((w_s * total_emissions_kg_s).sum("scenario"))

    # -----------------------------
    # 9) Total annual costs (objective-consistent)
    # -----------------------------
    annual_operating_cost_s = (
        annual_fom_s
        + fuel_cost_s
        + grid_import_cost_s
        - grid_export_rev_s
        - res_subsidy_rev_s
        + ll_cost_s
        + emissions_cost_s
    )  # (scenario,)

    expected_annual_operating_cost = _safe_float((w_s * annual_operating_cost_s).sum("scenario"))

    total_annual_cost_exp = total_annuity + expected_annual_operating_cost

    # -----------------------------
    # 10) LCOE (Expected, delivered)
    # -----------------------------
    lcoe = float("nan")
    delivered_kwh = float("nan")
    load = data.get("load_demand", None)
    if (load is not None) and (ll is not None):
        load_exp = _weighted_over_scenario(load, w_s=w_s)  # (period)
        ll_exp   = _weighted_over_scenario(ll, w_s=w_s)    # (period)
        delivered_kwh = max(_safe_float((load_exp - ll_exp).sum("period")), 0.0)
        if delivered_kwh > 1e-9:
            lcoe = total_annual_cost_exp / delivered_kwh

    # -----------------------------
    # 11) Headline metrics
    # -----------------------------
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Annualized Cost (Expected)", f"{total_annual_cost_exp:,.0f}/yr")
    c2.metric("LCOE (Expected, delivered)", f"{lcoe:,.4f}/kWh" if np.isfinite(lcoe) else "n/a")
    c3.metric("Upfront investment (gross / net) [thousand]", f"{total_upfront_gross_k:,.0f} / {total_upfront_net_k:,.0f}")

    st.markdown("---")

    # ======================================================
    # Upfront investment breakdown
    # ======================================================
    st.markdown("**Upfront investment** *(per technology)*")
    df_up = pd.concat(
        [
            pd.DataFrame({
                "Technology": [str(r) for r in cap_res_kw.coords["resource"].values],
                "Capacity": [float(v) for v in cap_res_kw.values],
                "Unit": ["kW"] * int(cap_res_kw.sizes["resource"]),
                "Grant share": [float(v) for v in res_grant.values],
                "Upfront gross [thousand]": [float(_safe_float(upfront_res_gross.sel(resource=r))) / 1e3 for r in cap_res_kw.coords["resource"].values], # convert to kcurrency
                "Upfront net [thousand]":   [float(_safe_float(upfront_res_net.sel(resource=r))) / 1e3   for r in cap_res_kw.coords["resource"].values], # convert to kcurrency
            }),
            pd.DataFrame({
                "Technology": ["Battery", "Generator"],
                "Capacity": [float(_safe_float(cap_bat_kwh)), float(_safe_float(cap_gen_kw))],
                "Unit": ["kWh", "kW"],
                "Grant share": [np.nan, np.nan],
                "Upfront gross [thousand]": [float(_safe_float(upfront_bat)) / 1e3, float(_safe_float(upfront_gen)) / 1e3], # convert to kcurrency
                "Upfront net [thousand]":   [float(_safe_float(upfront_bat)) / 1e3, float(_safe_float(upfront_gen)) / 1e3], # convert to kcurrency
            }),
        ],
        ignore_index=True,
    )

    st.dataframe(
        df_up.style.format({
            "Capacity": "{:,.3g}",
            "Grant share": "{:.0%}",
            "Upfront gross [thousand]": "{:,.0f}",
            "Upfront net [thousand]": "{:,.0f}",
        }).hide(axis="index"),
        width="stretch",
    )

    # ======================================================
    # Annual cost composition (Expected) table (objective-consistent)
    # ======================================================
    st.markdown("**Expected annual cost composition** *(objective-consistent)*")
    df_cost = pd.DataFrame(
        [
            {"Component": "Annualized CAPEX (annuity)", "Value": total_annuity, "Unit": "/yr"},
            {"Component": "Fixed O&M (expected)", "Value": total_fom_exp, "Unit": "/yr"},
            {"Component": "Fuel cost (expected)", "Value": fuel_cost_exp, "Unit": "/yr"},
            {"Component": "Grid import cost (expected)", "Value": grid_import_cost_exp, "Unit": "/yr"},
            {"Component": "Grid export revenue (expected)", "Value": -grid_export_rev_exp, "Unit": "/yr"},
            {"Component": "RES production subsidy (expected)", "Value": -res_subsidy_rev_exp, "Unit": "/yr"},
            {"Component": "Lost load penalty (expected)", "Value": ll_cost_exp, "Unit": "/yr"},
            {"Component": "Emissions cost (scope 1 + 2 + 3, expected)", "Value": emissions_cost_exp, "Unit": "/yr"},
            {"Component": "TOTAL (Expected)", "Value": total_annual_cost_exp, "Unit": "/yr"},
        ]
    )

    st.dataframe(
        df_cost.style.format({"Value": "{:,.0f}"}).hide(axis="index"),
        width="stretch",
    )

    # ======================================================
    # Annual Fixed O&M breakdown (Expected)
    # ======================================================
    st.markdown("**Expected annual fixed O&M** *(per technology)*")
    df_fom = pd.DataFrame(
        [
            {"Technology": "Renewables", "Annual FOM [/yr]": float(_safe_float(res_fom_exp))},
            {"Technology": "Battery",    "Annual FOM [/yr]": float(_safe_float(bat_fom_exp))},
            {"Technology": "Generator",  "Annual FOM [/yr]": float(_safe_float(gen_fom_exp))},
        ]
    )
    st.dataframe(
        df_fom.style.format({"Annual FOM [/yr]": "{:,.0f}"}).hide(axis="index"),
        width="stretch",
    )

    # ======================================================
    # Cash-flow annuities (per technology, with lifetimes)
    # ======================================================
    st.markdown("**Cash-flow annuities** *(per technology, expected)*")
    rows = []
    for r in cap_res_kw.coords["resource"].values:
        rows.append({
            "Technology (lifetime)": f"{str(r)} ({int(_safe_float(res_life_y.sel(resource=r)))}y)",
            "Annuity [/yr]": float(_safe_float(ann_res.sel(resource=r))),
        })
    rows.append({"Technology (lifetime)": f"Battery ({int(_safe_float(bat_life_y))}y)",   "Annuity [/yr]": float(_safe_float(ann_bat))})
    rows.append({"Technology (lifetime)": f"Generator ({int(_safe_float(gen_life_y))}y)", "Annuity [/yr]": float(_safe_float(ann_gen))})

    df_ann = pd.DataFrame(rows)
    st.dataframe(
        df_ann.style.format({"Annuity [/yr]": "{:,.0f}"}).hide(axis="index"),
        width="stretch",
    )

    # --------------------------------------------------
    # Cost Share Visualization
    # --------------------------------------------------
    st.caption("Annual cost composition (Expected) and Annuity breakdown per technology")

    comp_vals = np.array([total_annuity, total_fom_exp, fuel_cost_exp])
    comp_labels = ["Annualized CAPEX", "Annual Fixed O&M", "Annual Fuel Cost"]

    ann_vals = np.array([
        _safe_float(ann_res.sum()),
        _safe_float(ann_gen),
        _safe_float(ann_bat)
    ])
    ann_labels = ["Renewables", "Generator", "Battery"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={'width_ratios': [1.5, 1]})

    # Donut
    if comp_vals.sum() > 0:
        ax1.pie(comp_vals, labels=comp_labels, autopct='%1.1f%%',
                startangle=90, wedgeprops=dict(width=0.45))
        ax1.axis("equal")
        ax1.set_title("Annual Cost Shares")

    # Bar
    if total_annuity > 0:
        ann_pct = 100 * ann_vals / total_annuity
        ax2.barh(ann_labels, ann_pct)
        ax2.set_xlabel("Share of Total Annuity (%)")
        ax2.set_title("Annuity Breakdown by Technology")

    plt.tight_layout()
    st.pyplot(fig)


    # ======================================================
    # Embodied externalities (annualized) — Expected + breakdown
    # ======================================================
    st.markdown("**Embodied externalities** *(annualized)*")
    embodied_cost_exp = _safe_float((w_s * (emission_cost_s * scope3_kg_s)).sum("scenario"))

    c1, c2 = st.columns(2)
    c1.metric("Embodied emissions (Expected)", f"{scope3_kg_exp:,.0f} kgCO₂e/yr")
    c2.metric("Embodied externality cost (Expected)", f"{embodied_cost_exp:,.0f}/yr")

    rows = []
    for r in cap_res_kw.coords["resource"].values:
        kg_s = ((cap_res_kw.sel(resource=r) * res_emb_kg_per_kw.sel(resource=r)) / res_life_y.sel(resource=r)).fillna(0.0)  # (scenario,)
        kg_exp = _safe_float((w_s * kg_s).sum("scenario"))
        rows.append({
            "Technology": str(r),
            "Lifetime [y]": int(_safe_float(res_life_y.sel(resource=r))),
            "Embodied Emissions [kg/yr]": kg_exp,
            "Embodied Cost [/yr]": kg_exp * _safe_float((w_s * emission_cost_s).sum("scenario")),
        })

    kg_gen_exp = _safe_float((w_s * emb_gen_kg_s).sum("scenario"))
    rows.append({
        "Technology": "Generator",
        "Lifetime [y]": int(_safe_float(gen_life_y)),
        "Embodied Emissions [kg/yr]": kg_gen_exp,
        "Embodied Cost [/yr]": kg_gen_exp * _safe_float((w_s * emission_cost_s).sum("scenario")),
    })

    kg_bat_exp = _safe_float((w_s * emb_bat_kg_s).sum("scenario"))
    rows.append({
        "Technology": "Battery",
        "Lifetime [y]": int(_safe_float(bat_life_y)),
        "Embodied Emissions [kg/yr]": kg_bat_exp,
        "Embodied Cost [/yr]": kg_bat_exp * _safe_float((w_s * emission_cost_s).sum("scenario")),
    })

    df_emb = pd.DataFrame(rows)
    st.dataframe(
        df_emb.style.format({
            "Embodied Emissions [kg/yr]": "{:,.0f}",
            "Embodied Cost [/yr]": "{:,.0f}",
        }).hide(axis="index"),
        width="stretch",
    )

    # ======================================================
    # Scenario-specific operational fuel costs (Expected vs Scenario)
    # ======================================================
    st.subheader("Scenario-specific operational costs & emissions")
    st.caption("Variable operating cost and emissions can be inspected scenario-by-scenario.")

    ms_enabled = bool(((settings.get("multi_scenario", {}) or {}).get("enabled", False)))
    if ms_enabled:
        scen_vals = [str(s) for s in data.coords["scenario"].values.tolist()]
        view = st.selectbox("View:", ["Expected"] + [f"Scenario {s}" for s in scen_vals], key="fuel_view_sel")
    else:
        view = "Expected"

    annual_variable_cost_s = (fuel_cost_s + grid_import_cost_s - grid_export_rev_s - res_subsidy_rev_s).fillna(0.0)
    annual_variable_cost_exp = _safe_float((w_s * annual_variable_cost_s).sum("scenario"))

    if fuel_cons is not None or on_grid:
        if view == "Expected":
            variable_cost_view = annual_variable_cost_exp
            total_emissions_view = total_emissions_kg_exp
        else:
            sc = view.split("Scenario ", 1)[-1].strip()
            variable_cost_view = _safe_float(annual_variable_cost_s.sel(scenario=sc))
            total_emissions_view = _safe_float(total_emissions_kg_s.sel(scenario=sc))

        m1, m2 = st.columns(2)
        m1.metric("Annual variable cost", f"{variable_cost_view:,.0f}/yr")
        m2.metric("Total emissions", f"{total_emissions_view:,.0f} kgCO₂e/yr")
    else:
        st.info("No fuel or grid-import variables found; skipping emissions breakdown.")

    df_cost_breakdown = pd.DataFrame({
        "Scenario": [str(s) for s in scenario_like.values.tolist()],
        "Fuel cost": [float(_safe_float(fuel_cost_s.sel(scenario=s))) for s in scenario_like.values],
        "Grid import cost": [float(_safe_float(grid_import_cost_s.sel(scenario=s))) for s in scenario_like.values],
        "Grid export revenue": [float(_safe_float(grid_export_rev_s.sel(scenario=s))) for s in scenario_like.values],
        "RES subsidy revenue": [float(_safe_float(res_subsidy_rev_s.sel(scenario=s))) for s in scenario_like.values],
        "Annual variable cost": [float(_safe_float(annual_variable_cost_s.sel(scenario=s))) for s in scenario_like.values],
        "Weight": [float(_safe_float(w_s.sel(scenario=s))) for s in scenario_like.values],
    })
    with st.expander("Scenario-wise variable cost breakdown", expanded=False):
        st.dataframe(
            df_cost_breakdown.style.format({
                "Fuel cost": "{:,.0f}",
                "Grid import cost": "{:,.0f}",
                "Grid export revenue": "{:,.0f}",
                "RES subsidy revenue": "{:,.0f}",
                "Annual variable cost": "{:,.0f}",
                "Weight": "{:.3f}",
            }).hide(axis="index"),
            width="stretch",
        )

    df_emissions_breakdown = pd.DataFrame({
        "Scenario": [str(s) for s in scenario_like.values.tolist()],
        "Scope 1 emissions": [float(_safe_float(scope1_kg_s.sel(scenario=s))) for s in scenario_like.values],
        "Scope 2 emissions": [float(_safe_float(scope2_kg_s.sel(scenario=s))) for s in scenario_like.values],
        "Scope 3 emissions": [float(_safe_float(scope3_kg_s.sel(scenario=s))) for s in scenario_like.values],
        "Total emissions": [float(_safe_float(total_emissions_kg_s.sel(scenario=s))) for s in scenario_like.values],
        "Emissions cost": [float(_safe_float(emissions_cost_s.sel(scenario=s))) for s in scenario_like.values],
        "Weight": [float(_safe_float(w_s.sel(scenario=s))) for s in scenario_like.values],
    })
    with st.expander("Scenario-wise emissions breakdown", expanded=False):
        st.dataframe(
            df_emissions_breakdown.style.format({
                "Scope 1 emissions": "{:,.0f}",
                "Scope 2 emissions": "{:,.0f}",
                "Scope 3 emissions": "{:,.0f}",
                "Total emissions": "{:,.0f}",
                "Emissions cost": "{:,.0f}",
                "Weight": "{:.3f}",
            }).hide(axis="index"),
            width="stretch",
        )

    # ======================================================
    # (Optional) Scenario-wise total operating cost table
    # ======================================================
    with st.expander("Scenario-wise total operating cost breakdown", expanded=False):
        df_sc = pd.DataFrame({
            "Scenario": [str(s) for s in scenario_like.values.tolist()],
            "Fixed O&M": [float(_safe_float(annual_fom_s.sel(scenario=s))) for s in scenario_like.values],
            "Fuel cost": [float(_safe_float(fuel_cost_s.sel(scenario=s))) for s in scenario_like.values],
            "Grid import cost": [float(_safe_float(grid_import_cost_s.sel(scenario=s))) for s in scenario_like.values],
            "Grid export revenue": [float(_safe_float(grid_export_rev_s.sel(scenario=s))) for s in scenario_like.values],
            "RES subsidy revenue": [float(_safe_float(res_subsidy_rev_s.sel(scenario=s))) for s in scenario_like.values],
            "Annual variable cost": [float(_safe_float(annual_variable_cost_s.sel(scenario=s))) for s in scenario_like.values],
            "Lost load penalty": [float(_safe_float(ll_cost_s.sel(scenario=s))) for s in scenario_like.values],
            "Scope 1 emissions": [float(_safe_float(scope1_kg_s.sel(scenario=s))) for s in scenario_like.values],
            "Scope 2 emissions": [float(_safe_float(scope2_kg_s.sel(scenario=s))) for s in scenario_like.values],
            "Scope 3 emissions": [float(_safe_float(scope3_kg_s.sel(scenario=s))) for s in scenario_like.values],
            "Total emissions": [float(_safe_float(total_emissions_kg_s.sel(scenario=s))) for s in scenario_like.values],
            "Emissions cost": [float(_safe_float(emissions_cost_s.sel(scenario=s))) for s in scenario_like.values],
            "Total operating cost": [float(_safe_float(annual_operating_cost_s.sel(scenario=s))) for s in scenario_like.values],
            "Weight": [float(_safe_float(w_s.sel(scenario=s))) for s in scenario_like.values],
        })
        st.dataframe(
            df_sc.style.format({
                "Fixed O&M": "{:,.0f}",
                "Fuel cost": "{:,.0f}",
                "Grid import cost": "{:,.0f}",
                "Grid export revenue": "{:,.0f}",
                "RES subsidy revenue": "{:,.0f}",
                "Annual variable cost": "{:,.0f}",
                "Lost load penalty": "{:,.0f}",
                "Scope 1 emissions": "{:,.0f}",
                "Scope 2 emissions": "{:,.0f}",
                "Scope 3 emissions": "{:,.0f}",
                "Total emissions": "{:,.0f}",
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
