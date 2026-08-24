from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import xarray as xr

from microgridspy.app.page_helpers import get_dataset_settings, get_nested_flag
from microgridspy.app.page_helpers import safe_float as _safe_float
from microgridspy.export.results_page_helpers import export_typical_year_results_from_object
from microgridspy.export.typical_year_reporting import select_dispatch_view, select_kpi_row
from microgridspy.export.typical_year_results import TypicalYearResults

C_RES = "#FFD700"
C_BAT = "#00ACC1"
C_GEN = "#546E7A"
C_IMP = "#9C27B0"
C_EXP = "#9C27B0"
C_LL = "#E53935"
C_LOAD = "#111111"
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_HOURS = [31 * 24, 28 * 24, 31 * 24, 30 * 24, 31 * 24, 30 * 24, 31 * 24, 31 * 24, 30 * 24, 31 * 24, 30 * 24, 31 * 24]


def _days_to_slice(T: int, start_day: int, ndays: int) -> tuple[slice, int, int]:
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


def _scenario_selector(settings: dict[str, Any], data: xr.Dataset, *, key: str) -> tuple[str, str | None]:
    ms_enabled = bool((settings.get("multi_scenario", {}) or {}).get("enabled", False))
    if not ms_enabled:
        return "scenario", str(data.coords["scenario"].values[0])

    scen_labels = [str(s) for s in data.coords["scenario"].values.tolist()]
    options = ["Expected"] + [f"Scenario: {s}" for s in scen_labels]
    selected = st.selectbox("View metrics for:", options=options, index=0, key=key)
    if selected == "Expected":
        return "expected", None
    return "scenario", selected.split("Scenario: ", 1)[-1].strip()


def _weights_map(data: xr.Dataset) -> dict[str, float]:
    w_s = data.get("scenario_weight", None)
    scenarios = [str(s) for s in data.coords["scenario"].values.tolist()]
    if isinstance(w_s, xr.DataArray) and "scenario" in w_s.dims:
        return {str(s): float(_safe_float(w_s.sel(scenario=s))) for s in scenarios}
    if not scenarios:
        return {}
    eq = 1.0 / float(len(scenarios))
    return {s: eq for s in scenarios}


def _weighted_scalar_from_scenarios(data: xr.Dataset, da: xr.DataArray, *, mode: str, scenario_label: str | None) -> float:
    if "scenario" not in da.dims:
        return float(_safe_float(da))
    if mode == "scenario" and scenario_label is not None:
        return float(_safe_float(da.sel(scenario=str(scenario_label))))
    weights = _weights_map(data)
    total = 0.0
    for scenario in da.coords["scenario"].values.tolist():
        total += float(_safe_float(da.sel(scenario=scenario))) * float(weights.get(str(scenario), 0.0))
    return total


def _weighted_timeseries_from_scenarios(data: xr.Dataset, da: xr.DataArray | None, *, mode: str, scenario_label: str | None) -> np.ndarray | None:
    if da is None:
        return None
    if "period" not in da.dims:
        return np.asarray([float(_safe_float(da))], dtype=float)
    if "scenario" not in da.dims:
        return np.asarray(da.values, dtype=float).reshape(-1)
    if mode == "scenario" and scenario_label is not None:
        return np.asarray(da.sel(scenario=str(scenario_label)).values, dtype=float).reshape(-1)

    weights = _weights_map(data)
    acc = np.zeros((int(da.sizes["period"]),), dtype=float)
    for scenario in da.coords["scenario"].values.tolist():
        acc += np.asarray(da.sel(scenario=scenario).values, dtype=float).reshape(-1) * float(weights.get(str(scenario), 0.0))
    return acc


def _month_index_for_periods(T: int) -> np.ndarray:
    labels: list[str] = []
    for month, hours in zip(MONTH_LABELS, MONTH_HOURS):
        labels.extend([month] * hours)
        if len(labels) >= T:
            break
    if len(labels) < T:
        labels.extend([MONTH_LABELS[-1]] * (T - len(labels)))
    return np.asarray(labels[:T], dtype=object)


def _build_monthly_operational_profile(
    *,
    dispatch_view: pd.DataFrame,
    data: xr.Dataset,
    mode: str,
    scenario_label: str | None,
) -> pd.DataFrame:
    if dispatch_view.empty:
        return pd.DataFrame()

    T = len(dispatch_view)
    month_index = _month_index_for_periods(T)
    monthly = pd.DataFrame({"Month": month_index})

    def _series(name: str, fallback: float = 0.0) -> np.ndarray:
        if name in dispatch_view.columns:
            return pd.to_numeric(dispatch_view[name], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        return np.full((T,), float(fallback), dtype=float)

    fuel_cost_rate = _weighted_scalar_from_scenarios(data, data["fuel_fuel_cost_per_unit_fuel"], mode=mode, scenario_label=scenario_label) if "fuel_fuel_cost_per_unit_fuel" in data else 0.0
    fuel_emissions_rate = _weighted_scalar_from_scenarios(data, data["fuel_direct_emissions_kgco2e_per_unit_fuel"], mode=mode, scenario_label=scenario_label) if "fuel_direct_emissions_kgco2e_per_unit_fuel" in data else 0.0
    grid_emissions_rate = _weighted_scalar_from_scenarios(data, data["grid_emissions_factor_kgco2e_per_kwh"], mode=mode, scenario_label=scenario_label) if "grid_emissions_factor_kgco2e_per_kwh" in data else 0.0

    import_price = _weighted_timeseries_from_scenarios(data, data["grid_import_price"] if "grid_import_price" in data else None, mode=mode, scenario_label=scenario_label)
    export_price = _weighted_timeseries_from_scenarios(data, data["grid_export_price"] if "grid_export_price" in data else None, mode=mode, scenario_label=scenario_label)

    fuel_consumption = _series("fuel_consumption")
    grid_import = _series("grid_import") if "grid_import" in dispatch_view.columns else _series("grid_import_delivered")
    grid_import_delivered = _series("grid_import_delivered") if "grid_import_delivered" in dispatch_view.columns else _series("grid_import")
    grid_export = _series("grid_export") if "grid_export" in dispatch_view.columns else _series("grid_export_delivered")

    monthly["Fuel cost"] = fuel_consumption * fuel_cost_rate
    monthly["Grid import cost"] = grid_import * (import_price if import_price is not None and import_price.size == T else 0.0)
    monthly["Grid export revenue"] = grid_export * (export_price if export_price is not None and export_price.size == T else 0.0)

    total_res_subsidy = np.zeros((T,), dtype=float)
    if "res_production_subsidy_per_kwh" in data:
        for resource in data.coords["resource"].values.tolist():
            col = f"res_generation__{resource}"
            if col not in dispatch_view.columns:
                continue
            subsidy_rate = float(_safe_float(
                data["res_production_subsidy_per_kwh"].sel(
                    scenario=str(scenario_label) if mode == "scenario" and scenario_label is not None else data.coords["scenario"].values[0],
                    resource=resource,
                )
            )) if mode == "scenario" and scenario_label is not None else _weighted_scalar_from_scenarios(
                data,
                data["res_production_subsidy_per_kwh"].sel(resource=resource),
                mode=mode,
                scenario_label=scenario_label,
            )
            total_res_subsidy += _series(col) * subsidy_rate
    monthly["RES subsidy revenue"] = total_res_subsidy
    monthly["Scope 1 emissions"] = fuel_consumption * fuel_emissions_rate
    monthly["Scope 2 emissions"] = grid_import_delivered * grid_emissions_rate

    grouped = monthly.groupby("Month", sort=False).sum(numeric_only=True).reset_index()
    return grouped


def _build_typical_file_diagnostics_table(
    *,
    dispatch_view: pd.DataFrame,
    data: xr.Dataset,
    mode: str,
    scenario_label: str | None,
    kpi_row: pd.Series,
) -> pd.DataFrame:
    settings = get_dataset_settings(data)
    battery_loss_model = str(((settings.get("battery_model", {}) or {}).get("loss_model", "constant_efficiency")) or "constant_efficiency").strip().lower()
    generator_partial_load = bool((settings.get("generator", {}) or {}).get("partial_load_modelling_enabled", False))
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
        rows.append({"Metric": "Generator fuel consumption", "Value": fuel_sum, "Unit": "fuel units"})

    return pd.DataFrame(rows)


def _render_energy_balance_check_df(energy_balance_df: pd.DataFrame, tolerance: float = 1e-6) -> None:
    with st.expander("Energy Balance Check", expanded=False):
        if energy_balance_df.empty or "balance_residual" not in energy_balance_df.columns:
            st.info("Energy balance unavailable from solved results.")
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


def _emissions_priced_in_objective(data: xr.Dataset) -> bool:
    if "emission_cost_per_kgco2e" not in data:
        return False
    try:
        vals = np.asarray(data["emission_cost_per_kgco2e"].values, dtype=float)
    except Exception:
        return False
    return bool(np.any(np.abs(vals) > 1e-12))


def render_typical_year_results(results: TypicalYearResults, project_name: str | None = None) -> None:
    _ = project_name
    data = results.data
    settings = get_dataset_settings(data)
    on_grid = get_nested_flag(settings, ("grid", "on_grid"), default=False)
    allow_export = get_nested_flag(settings, ("grid", "allow_export"), default=False)

    if results.source == "files" and results.results_dir is not None:
        st.info(f"Displaying saved results loaded from project files in `{results.results_dir}`.")

    st.subheader("Sizing summary")
    total_res_units = float(pd.to_numeric(results.renewable_design["Installed units"], errors="coerce").fillna(0.0).sum()) if not results.renewable_design.empty else 0.0
    total_res_dc_kw = float(pd.to_numeric(results.renewable_design["Installed DC capacity [kW]"], errors="coerce").fillna(0.0).sum()) if not results.renewable_design.empty else 0.0
    total_res_inv_kw = float(pd.to_numeric(results.renewable_inverter_design["Installed inverter AC capacity [kW_ac]"], errors="coerce").fillna(0.0).sum()) if not results.renewable_inverter_design.empty else 0.0
    battery_row = results.battery_design.iloc[0] if not results.battery_design.empty else pd.Series(dtype=float)
    generator_row = results.generator_design.iloc[0] if not results.generator_design.empty else pd.Series(dtype=float)
    battery_inv_row = results.battery_inverter_design.iloc[0] if not results.battery_inverter_design.empty else pd.Series(dtype=float)

    df_size = pd.DataFrame(
        [
            {"Component": "Renewables (total)", "Installed units": total_res_units, "Capacity": total_res_dc_kw, "Unit": "kW_dc"},
            {"Component": "Renewable inverter/converter (total)", "Installed units": np.nan, "Capacity": total_res_inv_kw, "Unit": "kW_ac"},
            {"Component": "Battery", "Installed units": float(_safe_float(battery_row.get("Installed units", 0.0))), "Capacity": float(_safe_float(battery_row.get("Installed energy capacity [kWh]", 0.0))), "Unit": "kWh"},
            {"Component": "Battery converter/inverter power", "Installed units": float(_safe_float(battery_inv_row.get("Installed inverter units", 0.0))), "Capacity": float(_safe_float(battery_inv_row.get("Installed inverter power [kW]", 0.0))), "Unit": "kW"},
            {"Component": "Generator", "Installed units": float(_safe_float(generator_row.get("Installed units", 0.0))), "Capacity": float(_safe_float(generator_row.get("Installed capacity [kW]", 0.0))), "Unit": "kW"},
        ]
    )
    st.dataframe(df_size.style.format({"Installed units": "{:,.3g}", "Capacity": "{:,.3g}"}).hide(axis="index"), width="stretch")

    st.markdown("**Inverter sizing**")
    inverter_summary = pd.DataFrame(
        [
            {"Component": "Renewable inverter/converter (total)", "Capacity": total_res_inv_kw, "Unit": "kW_ac"},
            {"Component": "Battery inverter units", "Capacity": float(_safe_float(battery_inv_row.get("Installed inverter units", 0.0))), "Unit": "units"},
            {"Component": "Battery converter/inverter power", "Capacity": float(_safe_float(battery_inv_row.get("Installed inverter power [kW]", 0.0))), "Unit": "kW"},
        ]
    )
    st.dataframe(inverter_summary.style.format({"Capacity": "{:,.3g}"}).hide(axis="index"), width="stretch")

    with st.expander("Per-renewable breakdown", expanded=False):
        st.dataframe(results.renewable_inverter_design.style.format({
            "Installed DC capacity [kW]": "{:,.3g}",
            "Installed inverter AC capacity [kW_ac]": "{:,.3g}",
            "Effective AC exportable renewable capacity [kW_ac]": "{:,.3g}",
            "DC/AC ratio": "{:,.3g}",
            "Inverter efficiency": "{:,.3g}",
        }).hide(axis="index"), width="stretch")

    if not results.inverter_metrics.empty:
        with st.expander("Inverter metrics", expanded=False):
            st.dataframe(results.inverter_metrics.style.format({
                "Installed inverter AC capacity [kW_ac]": "{:,.3g}",
                "Peak dispatched renewable output [kW_ac]": "{:,.3g}",
                "Peak utilization [%]": "{:,.2f}",
                "Pre-inverter renewable AC-equivalent potential [kWh]": "{:,.2f}",
                "Effective inverter-limited renewable potential [kWh]": "{:,.2f}",
                "Inverter clipping potential [kWh]": "{:,.2f}",
            }).hide(axis="index"), width="stretch")

    with st.expander("Battery inverter breakdown", expanded=False):
        st.dataframe(results.battery_inverter_design.style.format({
            "Installed inverter units": "{:,.3g}",
            "Nominal inverter power per unit [kW]": "{:,.3g}",
            "Installed inverter power [kW]": "{:,.3g}",
        }).hide(axis="index"), width="stretch")

    st.subheader("Performance KPIs")
    mode, scen_label = _scenario_selector(settings, data, key="gp_kpi_view_sel_canonical")
    kpi_row = select_kpi_row(results.kpis, data, mode=mode, scenario_label=scen_label)
    dispatch_kpi = select_dispatch_view(results.dispatch, data, mode=mode, scenario_label=scen_label)
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
                "Renewable inverter clipping potential",
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
                float(_safe_float(kpi_row.get("renewable_inverter_clipping_kwh", 0.0))) / 1e3,
                100.0 * float(_safe_float(kpi_row.get("lost_load_fraction", 0.0))),
            ],
            "Unit": ["MWh", "MWh", "MWh", "MWh", "MWh", "MWh" if on_grid else None, "MWh" if on_grid else None, "MWh" if (on_grid and allow_export) else None, "%", "%", "MWh", "%"],
        }
    ).dropna(subset=["Metric"])
    st.dataframe(kpi_df.style.format({"Value": "{:,.2f}"}).hide(axis="index"), width="stretch")

    diagnostics_df = _build_typical_file_diagnostics_table(
        dispatch_view=dispatch_kpi,
        data=data,
        mode=mode,
        scenario_label=scen_label,
        kpi_row=kpi_row,
    )
    if not diagnostics_df.empty:
        st.markdown("**Efficiency diagnostics**")
        st.dataframe(diagnostics_df.style.format({"Value": "{:,.4f}"}).hide(axis="index"), width="stretch")

    st.markdown("---")
    st.subheader("Least-Cost Energy Mix")
    st.caption("Stacked dispatch over a selected time window. Positive areas are supply-side contributions; battery charging and grid exports are shown below zero.")

    disp_view = select_dispatch_view(results.dispatch, data, mode=mode, scenario_label=scen_label)
    T = int(len(disp_view))
    with st.expander("Time window", expanded=False):
        max_days = max(1, int(np.ceil(T / 24)))
        ndays = st.slider("Number of days", min_value=1, max_value=min(7, max_days), value=1, step=1, key="gp_disp_ndays_canonical")
        max_start_day = max(1, max_days - ndays + 1)
        start_day = st.slider("Start day", min_value=1, max_value=max_start_day, value=1, step=1, key="gp_disp_start_day_canonical")

    idx, start_hr, window = _days_to_slice(T, start_day=start_day, ndays=ndays)
    fig, ax = plt.subplots(figsize=(11, 4))
    _plot_dispatch_stack(
        ax=ax,
        x=np.arange(start_hr, start_hr + window),
        y_res=disp_view["res_generation_total"].to_numpy(dtype=float)[idx],
        y_bdis=disp_view["battery_discharge"].to_numpy(dtype=float)[idx],
        y_gen=disp_view["generator_generation"].to_numpy(dtype=float)[idx],
        y_gimp=disp_view["grid_import_delivered"].to_numpy(dtype=float)[idx] if "grid_import_delivered" in disp_view.columns else None,
        y_ll=disp_view["lost_load"].to_numpy(dtype=float)[idx],
        y_bch=disp_view["battery_charge"].to_numpy(dtype=float)[idx],
        y_gexp=disp_view["grid_export_delivered"].to_numpy(dtype=float)[idx] if "grid_export_delivered" in disp_view.columns else None,
        y_load=disp_view["load_demand"].to_numpy(dtype=float)[idx],
        title_suffix="Expected" if mode == "expected" else f"Scenario: {scen_label}",
    )
    st.pyplot(fig, width="stretch")
    _render_energy_balance_check_df(results.energy_balance, tolerance=1e-6)

    st.subheader("Cost summary & Cash-flow")
    expected_row = select_kpi_row(results.kpis, data, mode="expected", scenario_label=None)
    total_annual_cost_exp = float(_safe_float(expected_row.get("reported_total_annual_cost", np.nan)))
    delivered_kwh = float(_safe_float(expected_row.get("served_energy_kwh", np.nan)))
    lcoe = total_annual_cost_exp / delivered_kwh if delivered_kwh > 1e-9 and np.isfinite(total_annual_cost_exp) else float("nan")
    total_upfront_gross_k = float(pd.to_numeric(results.upfront["Upfront gross [thousand]"], errors="coerce").fillna(0.0).sum()) if not results.upfront.empty else 0.0
    total_upfront_net_k = float(pd.to_numeric(results.upfront["Upfront net [thousand]"], errors="coerce").fillna(0.0).sum()) if not results.upfront.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Annualized Cost (Expected)", f"{total_annual_cost_exp:,.0f}/yr")
    c2.metric("LCOE (Expected, delivered)", f"{lcoe:,.4f}/kWh" if np.isfinite(lcoe) else "n/a")
    c3.metric("Upfront investment (gross / net) [thousand]", f"{total_upfront_gross_k:,.0f} / {total_upfront_net_k:,.0f}")

    st.markdown("---")
    st.markdown("**Upfront investment** *(per technology)*")
    st.dataframe(results.upfront.style.format({
        "Capacity": "{:,.3g}",
        "Grant share": "{:.0%}",
        "Upfront gross [thousand]": "{:,.0f}",
        "Upfront net [thousand]": "{:,.0f}",
    }).hide(axis="index"), width="stretch")

    st.markdown("**Expected annual cost composition** *(objective-consistent)*")
    st.dataframe(results.expected_cost_components.style.format({"Value": "{:,.0f}"}).hide(axis="index"), width="stretch")
    st.markdown("**Expected annual fixed O&M** *(per technology)*")
    st.dataframe(results.expected_fixed_om.style.format({"Annual FOM [/yr]": "{:,.0f}"}).hide(axis="index"), width="stretch")
    st.markdown("**Cash-flow annuities** *(per technology, expected)*")
    st.dataframe(results.annuities.style.format({"Annuity [/yr]": "{:,.0f}"}).hide(axis="index"), width="stretch")
    st.markdown("**Embodied externalities** *(annualized)*")
    st.dataframe(results.embodied.style.format({
        "Embodied Emissions [kg/yr]": "{:,.0f}",
        "Embodied Cost [/yr]": "{:,.0f}",
    }).hide(axis="index"), width="stretch")

    st.subheader("Scenario-specific operational costs & emissions")
    st.caption("Inspect operational costs and emissions by scenario, alongside an expected-value view.")

    expected_variable_cost = float(_safe_float(expected_row.get("annual_variable_cost", np.nan)))
    expected_total_emissions = float(_safe_float(expected_row.get("emissions_kgco2e", np.nan)))

    c1, c2 = st.columns(2)
    c1.metric("Annual variable cost (Expected)", f"{expected_variable_cost:,.0f}/yr" if np.isfinite(expected_variable_cost) else "n/a")
    c2.metric("Total emissions (Expected)", f"{expected_total_emissions:,.0f} kgCO2e/yr" if np.isfinite(expected_total_emissions) else "n/a")

    variable_df = results.scenario_variable_costs.copy()
    emissions_df = results.scenario_emissions.copy()
    operating_df = results.scenario_total_operating_costs.copy()
    for frame in (variable_df, emissions_df, operating_df):
        if "Scenario" in frame.columns:
            frame["Scenario"] = frame["Scenario"].astype(str)

    monthly_view_options = ["Expected"] + [s for s in emissions_df["Scenario"].astype(str).tolist() if str(s).lower() != "expected"] if not emissions_df.empty else ["Expected"]
    monthly_view = st.selectbox(
        "Monthly profile view",
        monthly_view_options,
        index=0,
        key="ty_results_monthly_view",
    )
    monthly_mode = "expected" if str(monthly_view).lower() == "expected" else "scenario"
    monthly_scenario_label = None if monthly_mode == "expected" else str(monthly_view)
    monthly_dispatch = select_dispatch_view(results.dispatch, data, mode=monthly_mode, scenario_label=monthly_scenario_label)
    monthly_profile = _build_monthly_operational_profile(
        dispatch_view=monthly_dispatch,
        data=data,
        mode=monthly_mode,
        scenario_label=monthly_scenario_label,
    )
    monthly_metric = st.selectbox(
        "Monthly plot",
        ["Variable cost breakdown", "Operational emissions breakdown"],
        key="ty_results_monthly_metric",
    )

    fig_cmp, ax_cmp = plt.subplots(figsize=(11, 4.5))
    if not monthly_profile.empty:
        x = np.arange(len(monthly_profile))
        x_labels = monthly_profile["Month"].astype(str).tolist()
        if monthly_metric == "Variable cost breakdown":
            fuel_vals = pd.to_numeric(monthly_profile["Fuel cost"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            import_vals = pd.to_numeric(monthly_profile["Grid import cost"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            subsidy_vals = pd.to_numeric(monthly_profile["RES subsidy revenue"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            export_vals = pd.to_numeric(monthly_profile["Grid export revenue"], errors="coerce").fillna(0.0).to_numpy(dtype=float)

            ax_cmp.bar(x, fuel_vals, color=C_GEN, label="Fuel cost")
            ax_cmp.bar(x, import_vals, bottom=fuel_vals, color=C_IMP, label="Grid import cost")
            if np.any(subsidy_vals > 0.0):
                ax_cmp.bar(x, -subsidy_vals, color=C_RES, alpha=0.75, label="RES subsidy revenue")
            if np.any(export_vals > 0.0):
                ax_cmp.bar(x, -export_vals, bottom=-subsidy_vals, color=C_EXP, alpha=0.75, label="Grid export revenue")
            ax_cmp.set_title(f"Monthly variable cost breakdown - {monthly_view}")
            ax_cmp.set_ylabel("Currency / month")
        else:
            scope1_vals = pd.to_numeric(monthly_profile["Scope 1 emissions"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            scope2_vals = pd.to_numeric(monthly_profile["Scope 2 emissions"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            ax_cmp.bar(x, scope1_vals, color="#D1495B", label="Scope 1")
            ax_cmp.bar(x, scope2_vals, bottom=scope1_vals, color="#00798C", label="Scope 2")
            ax_cmp.set_title(f"Monthly operational emissions - {monthly_view}")
            ax_cmp.set_ylabel("kgCO2e / month")

        ax_cmp.set_xticks(x, x_labels)
        ax_cmp.grid(True, axis="y", alpha=0.25, linestyle=":")
        ax_cmp.legend(ncols=4, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, 1.2))
    st.pyplot(fig_cmp)

    scope_view_options = ["Expected"] + [s for s in emissions_df["Scenario"].astype(str).tolist() if str(s).lower() != "expected"] if not emissions_df.empty else ["Expected"]
    scope_view = st.selectbox(
        "Emissions scope view",
        scope_view_options,
        index=0,
        key="ty_results_scope_emissions_view",
    )
    scope_df = emissions_df[emissions_df["Scenario"].astype(str) == str(scope_view)].copy() if "Scenario" in emissions_df.columns else pd.DataFrame()
    if not scope_df.empty:
        scope_row = scope_df.iloc[0]
        fig_scope, ax_scope = plt.subplots(figsize=(8, 4))
        scope_labels = ["Scope 1", "Scope 2", "Scope 3"]
        scope_values = [
            float(_safe_float(scope_row.get("Scope 1 emissions", 0.0))),
            float(_safe_float(scope_row.get("Scope 2 emissions", 0.0))),
            float(_safe_float(scope_row.get("Scope 3 emissions", 0.0))),
        ]
        ax_scope.bar(scope_labels, scope_values, color=["#D1495B", "#00798C", "#EDAe49"])
        ax_scope.set_title(f"Emissions by scope - {scope_view}")
        ax_scope.set_ylabel("kgCO2e / year")
        ax_scope.grid(True, axis="y", alpha=0.25, linestyle=":")
        st.pyplot(fig_scope)

    with st.expander("Scenario-wise variable cost breakdown", expanded=False):
        st.dataframe(variable_df.style.format({
            "Fuel cost": "{:,.0f}",
            "Grid import cost": "{:,.0f}",
            "Grid export revenue": "{:,.0f}",
            "RES subsidy revenue": "{:,.0f}",
            "Annual variable cost": "{:,.0f}",
            "Weight": "{:.3f}",
        }).hide(axis="index"), width="stretch")
    with st.expander("Scenario-wise emissions breakdown", expanded=False):
        st.dataframe(emissions_df.style.format({
            "Scope 1 emissions": "{:,.0f}",
            "Scope 2 emissions": "{:,.0f}",
            "Scope 3 emissions": "{:,.0f}",
            "Total emissions": "{:,.0f}",
            "Emissions cost": "{:,.0f}",
            "Weight": "{:.3f}",
        }).hide(axis="index"), width="stretch")
    with st.expander("Scenario-wise total operating cost breakdown", expanded=False):
        st.dataframe(operating_df.style.format({
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
        }).hide(axis="index"), width="stretch")

    st.subheader("Export Results")
    if st.button("Export results to CSV", type="primary", key="typical_year_export_canonical"):
        try:
            with st.spinner("Exporting results..."):
                written = export_typical_year_results_from_object(results)
            st.success("Export completed.")
            st.json(written)
        except Exception as exc:
            st.error(f"Export failed: {exc}")
