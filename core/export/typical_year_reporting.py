from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import xarray as xr

from core.export.common import safe_float, safe_share, scalarize


@dataclass
class TypicalYearReportingTables:
    dispatch: pd.DataFrame
    energy_balance: pd.DataFrame
    kpis: pd.DataFrame
    upfront: pd.DataFrame
    expected_cost_components: pd.DataFrame
    expected_fixed_om: pd.DataFrame
    annuities: pd.DataFrame
    embodied: pd.DataFrame
    scenario_variable_costs: pd.DataFrame
    scenario_emissions: pd.DataFrame
    scenario_total_operating_costs: pd.DataFrame


def _crf(r: float, n: float) -> float:
    r = float(r)
    n = float(n)
    if n <= 0.0:
        return float("nan")
    if abs(r) < 1e-12:
        return 1.0 / n
    a = (1.0 + r) ** n
    return (r * a) / (a - 1.0)


def weights_map(data: xr.Dataset) -> Dict[str, float]:
    scenario_values = [str(s) for s in data.coords["scenario"].values.tolist()]
    w_s = data.get("scenario_weight", None)
    if isinstance(w_s, xr.DataArray) and "scenario" in w_s.dims:
        return {str(s): float(safe_float(w_s.sel(scenario=s))) for s in scenario_values}
    if not scenario_values:
        return {}
    equal = 1.0 / float(len(scenario_values))
    return {str(s): equal for s in scenario_values}


def select_dispatch_view(dispatch: pd.DataFrame, data: xr.Dataset, *, mode: str, scenario_label: Optional[str]) -> pd.DataFrame:
    frame = dispatch.copy()
    frame["scenario"] = frame["scenario"].astype(str)
    numeric_cols = [c for c in frame.columns if c not in {"period", "scenario"}]
    for col in numeric_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)

    if mode == "scenario" and scenario_label is not None:
        return frame[frame["scenario"] == str(scenario_label)].sort_values("period").reset_index(drop=True)

    frame["weight"] = frame["scenario"].map(weights_map(data)).fillna(0.0)
    weighted = frame[numeric_cols].mul(frame["weight"], axis=0)
    expected = pd.concat([frame[["period"]], weighted], axis=1).groupby("period", as_index=False).sum()
    expected["scenario"] = "expected"
    return expected.sort_values("period").reset_index(drop=True)


def select_kpi_row(kpis: pd.DataFrame, data: xr.Dataset, *, mode: str, scenario_label: Optional[str]) -> pd.Series:
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
    scenario_rows["weight_fallback"] = scenario_rows["scenario"].map(weights_map(data)).fillna(0.0)
    numeric_cols = scenario_rows.select_dtypes(include=[np.number]).columns.tolist()
    values = {"scenario": "expected"}
    for col in numeric_cols:
        if col in {"objective_value", "solver_objective_value"}:
            values[col] = float(pd.to_numeric(scenario_rows[col], errors="coerce").fillna(0.0).iloc[0]) if len(scenario_rows) else float("nan")
        else:
            values[col] = float((pd.to_numeric(scenario_rows[col], errors="coerce").fillna(0.0) * scenario_rows["weight_fallback"]).sum())
    return pd.Series(values)


def build_energy_balance_table(data: xr.Dataset, dispatch_df: pd.DataFrame) -> pd.DataFrame:
    """
    Formulation-consistent energy balance using delivered grid energy.
    """
    df = dispatch_df.copy()
    for col in (
        "res_generation_total",
        "generator_generation",
        "battery_discharge",
        "lost_load",
        "battery_charge",
        "grid_import_delivered",
        "grid_export_delivered",
        "load_demand",
    ):
        if col not in df.columns:
            df[col] = 0.0

    df["supply_renewable"] = df["res_generation_total"]
    df["supply_generator"] = df["generator_generation"]
    df["supply_grid_import"] = df["grid_import_delivered"]
    df["supply_battery_discharge"] = df["battery_discharge"]
    df["supply_lost_load"] = df["lost_load"]
    df["sink_battery_charge"] = df["battery_charge"]
    df["sink_grid_export"] = df["grid_export_delivered"]
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


def build_reporting_tables(
    *,
    data: xr.Dataset,
    dispatch_df: pd.DataFrame,
    design_df: pd.DataFrame,
    solver_objective_value: Optional[float],
) -> TypicalYearReportingTables:
    dispatch = dispatch_df.copy()
    dispatch["scenario"] = dispatch["scenario"].astype(str)
    if "period" in dispatch.columns:
        dispatch["period"] = pd.to_numeric(dispatch["period"], errors="coerce").fillna(0).astype(int)

    row = design_df.iloc[0] if not design_df.empty else pd.Series(dtype=float)
    resources = [str(r) for r in data.coords["resource"].values.tolist()] if "resource" in data.coords else []
    scenarios = [str(s) for s in data.coords["scenario"].values.tolist()] if "scenario" in data.coords else []
    weights = weights_map(data)

    res_caps = {
        r: float(pd.to_numeric(pd.Series([row.get(f"res_installed_kw__{r}", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
        for r in resources
    }
    res_units = {
        r: float(pd.to_numeric(pd.Series([row.get(f"res_units__{r}", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
        for r in resources
    }
    cap_bat_kwh = float(pd.to_numeric(pd.Series([row.get("battery_installed_kwh", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    cap_gen_kw = float(pd.to_numeric(pd.Series([row.get("generator_installed_kw", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    battery_units = float(pd.to_numeric(pd.Series([row.get("battery_units", 0.0)]), errors="coerce").fillna(0.0).iloc[0])
    generator_units = float(pd.to_numeric(pd.Series([row.get("generator_units", 0.0)]), errors="coerce").fillna(0.0).iloc[0])

    for col in (
        "grid_import",
        "grid_export",
        "fuel_consumption",
        "res_generation_total",
        "generator_generation",
        "battery_charge",
        "battery_discharge",
        "load_demand",
        "lost_load",
    ):
        if col not in dispatch.columns:
            dispatch[col] = 0.0
        dispatch[col] = pd.to_numeric(dispatch[col], errors="coerce").fillna(0.0)

    if "grid_import_delivered" not in dispatch.columns:
        dispatch["grid_import_delivered"] = 0.0
    if "grid_export_delivered" not in dispatch.columns:
        dispatch["grid_export_delivered"] = 0.0
    dispatch["grid_import_delivered"] = pd.to_numeric(dispatch["grid_import_delivered"], errors="coerce").fillna(np.nan)
    dispatch["grid_export_delivered"] = pd.to_numeric(dispatch["grid_export_delivered"], errors="coerce").fillna(np.nan)
    for s in scenarios:
        mask = dispatch["scenario"] == s
        grid_eta = scalarize(data["grid_transmission_efficiency"], scenario=s) if "grid_transmission_efficiency" in data else 1.0
        dispatch.loc[mask & dispatch["grid_import_delivered"].isna(), "grid_import_delivered"] = dispatch.loc[mask, "grid_import"] * grid_eta
        dispatch.loc[mask & dispatch["grid_export_delivered"].isna(), "grid_export_delivered"] = dispatch.loc[mask, "grid_export"] * grid_eta
    dispatch["grid_import_delivered"] = dispatch["grid_import_delivered"].fillna(0.0)
    dispatch["grid_export_delivered"] = dispatch["grid_export_delivered"].fillna(0.0)

    energy_balance = build_energy_balance_table(data, dispatch)

    annualized_capex = 0.0
    annuity_rows: list[dict[str, Any]] = []
    upfront_rows: list[dict[str, Any]] = []
    embodied_rows: list[dict[str, Any]] = []
    expected_fom_rows: list[dict[str, Any]] = []

    res_annuity_total = 0.0
    for r in resources:
        res_capex = scalarize(data["res_specific_investment_cost_per_kw"], resource=r)
        res_grant = scalarize(data["res_grant_share_of_capex"], resource=r)
        res_life = scalarize(data["res_lifetime_years"], resource=r)
        res_wacc = scalarize(data["res_wacc"], resource=r)
        res_ann = res_caps[r] * res_capex * (1.0 - res_grant) * _crf(res_wacc, res_life)
        res_annuity_total += res_ann
        annualized_capex += res_ann
        annuity_rows.append({"Technology (lifetime)": f"{r} ({int(res_life)}y)", "Annuity [/yr]": res_ann})
        upfront_rows.append(
            {
                "Technology": r,
                "Capacity": res_caps[r],
                "Unit": "kW",
                "Grant share": res_grant,
                "Upfront gross [thousand]": res_caps[r] * res_capex / 1e3,
                "Upfront net [thousand]": res_caps[r] * res_capex * (1.0 - res_grant) / 1e3,
            }
        )

        kg_exp = 0.0
        cost_exp = 0.0
        for s in scenarios:
            kg_s = (
                res_caps[r]
                * scalarize(data["res_embedded_emissions_kgco2e_per_kw"], scenario=s, resource=r)
                / max(res_life, 1e-12)
            )
            emission_cost_s = scalarize(data["emission_cost_per_kgco2e"], scenario=s)
            kg_exp += weights.get(s, 0.0) * kg_s
            cost_exp += weights.get(s, 0.0) * kg_s * emission_cost_s
        embodied_rows.append(
            {
                "Technology": r,
                "Lifetime [y]": int(res_life),
                "Embodied Emissions [kg/yr]": kg_exp,
                "Embodied Cost [/yr]": cost_exp,
            }
        )

    bat_capex = float(safe_float(data["battery_specific_investment_cost_per_kwh"]))
    bat_life = float(safe_float(data["battery_calendar_lifetime_years"]))
    bat_wacc = float(safe_float(data["battery_wacc"]))
    ann_bat = cap_bat_kwh * bat_capex * _crf(bat_wacc, bat_life)
    annualized_capex += ann_bat
    annuity_rows.append({"Technology (lifetime)": f"Battery ({int(bat_life)}y)", "Annuity [/yr]": ann_bat})
    upfront_rows.append(
        {
            "Technology": "Battery",
            "Capacity": cap_bat_kwh,
            "Unit": "kWh",
            "Grant share": np.nan,
            "Upfront gross [thousand]": cap_bat_kwh * bat_capex / 1e3,
            "Upfront net [thousand]": cap_bat_kwh * bat_capex / 1e3,
        }
    )

    gen_capex = float(safe_float(data["generator_specific_investment_cost_per_kw"]))
    gen_life = float(safe_float(data["generator_lifetime_years"]))
    gen_wacc = float(safe_float(data["generator_wacc"]))
    ann_gen = cap_gen_kw * gen_capex * _crf(gen_wacc, gen_life)
    annualized_capex += ann_gen
    annuity_rows.append({"Technology (lifetime)": f"Generator ({int(gen_life)}y)", "Annuity [/yr]": ann_gen})
    upfront_rows.append(
        {
            "Technology": "Generator",
            "Capacity": cap_gen_kw,
            "Unit": "kW",
            "Grant share": np.nan,
            "Upfront gross [thousand]": cap_gen_kw * gen_capex / 1e3,
            "Upfront net [thousand]": cap_gen_kw * gen_capex / 1e3,
        }
    )

    bat_emb_exp = 0.0
    bat_emb_cost_exp = 0.0
    gen_emb_exp = 0.0
    gen_emb_cost_exp = 0.0
    for s in scenarios:
        em_price = scalarize(data["emission_cost_per_kgco2e"], scenario=s)
        bat_kg_s = cap_bat_kwh * scalarize(data["battery_embedded_emissions_kgco2e_per_kwh"], scenario=s) / max(bat_life, 1e-12)
        gen_kg_s = cap_gen_kw * scalarize(data["generator_embedded_emissions_kgco2e_per_kw"], scenario=s) / max(gen_life, 1e-12)
        bat_emb_exp += weights.get(s, 0.0) * bat_kg_s
        bat_emb_cost_exp += weights.get(s, 0.0) * bat_kg_s * em_price
        gen_emb_exp += weights.get(s, 0.0) * gen_kg_s
        gen_emb_cost_exp += weights.get(s, 0.0) * gen_kg_s * em_price
    embodied_rows.append({"Technology": "Generator", "Lifetime [y]": int(gen_life), "Embodied Emissions [kg/yr]": gen_emb_exp, "Embodied Cost [/yr]": gen_emb_cost_exp})
    embodied_rows.append({"Technology": "Battery", "Lifetime [y]": int(bat_life), "Embodied Emissions [kg/yr]": bat_emb_exp, "Embodied Cost [/yr]": bat_emb_cost_exp})

    kpi_rows: list[dict[str, Any]] = []
    for s in scenarios:
        scen_dispatch = dispatch[dispatch["scenario"] == s].sort_values("period").reset_index(drop=True)
        total_demand = float(scen_dispatch["load_demand"].sum())
        lost_load = float(scen_dispatch["lost_load"].sum())
        served = total_demand - lost_load
        total_res = float(scen_dispatch["res_generation_total"].sum())
        total_gen = float(scen_dispatch["generator_generation"].sum())
        fuel = float(scen_dispatch["fuel_consumption"].sum())
        grid_import_raw = float(scen_dispatch["grid_import"].sum())
        grid_import_delivered = float(scen_dispatch["grid_import_delivered"].sum())
        grid_export_raw = float(scen_dispatch["grid_export"].sum())
        grid_export_delivered = float(scen_dispatch["grid_export_delivered"].sum())
        grid_ren_share = scalarize(data["grid_renewable_share"], scenario=s) if "grid_renewable_share" in data else 0.0
        grid_renewable = grid_import_delivered * grid_ren_share
        ren_denom = total_res + total_gen + grid_import_delivered
        ren_num = total_res + grid_renewable
        ren_pen = safe_share(ren_num, ren_denom)

        res_potential = 0.0
        if "resource_availability" in data and "res_inverter_efficiency" in data:
            for r in resources:
                avail = np.asarray(data["resource_availability"].sel(scenario=s, resource=r).values, dtype=float)
                res_potential += float(avail.sum()) * res_caps[r] * scalarize(data["res_inverter_efficiency"], resource=r)
        res_curtailment = max(res_potential - total_res, 0.0)
        res_curtailment_share = safe_share(res_curtailment, res_potential)

        fuel_cost = fuel * scalarize(data["fuel_fuel_cost_per_unit_fuel"], scenario=s)
        grid_import_cost = 0.0
        if "grid_import_price" in data:
            prices = np.asarray(data["grid_import_price"].sel(scenario=s).values, dtype=float).reshape(-1)
            imports = scen_dispatch["grid_import"].to_numpy(dtype=float)
            grid_import_cost = float(np.sum(imports * prices))
        grid_export_revenue = 0.0
        if "grid_export_price" in data:
            prices = np.asarray(data["grid_export_price"].sel(scenario=s).values, dtype=float).reshape(-1)
            exports = scen_dispatch["grid_export"].to_numpy(dtype=float)
            grid_export_revenue = float(np.sum(exports * prices))
        res_subsidy_revenue = 0.0
        if "res_production_subsidy_per_kwh" in data:
            for r in resources:
                col = f"res_generation__{r}"
                if col in scen_dispatch.columns:
                    subsidy = scalarize(data["res_production_subsidy_per_kwh"], scenario=s, resource=r)
                    res_subsidy_revenue += float(np.sum(scen_dispatch[col].to_numpy(dtype=float) * subsidy))

        fixed_om = 0.0
        res_fom_s = 0.0
        for r in resources:
            res_capex = scalarize(data["res_specific_investment_cost_per_kw"], resource=r)
            fom_share = scalarize(data["res_fixed_om_share_per_year"], resource=r)
        res_fom_s += res_caps[r] * res_capex * fom_share
        bat_fom_s = cap_bat_kwh * bat_capex * scalarize(data["battery_fixed_om_share_per_year"])
        gen_fom_s = cap_gen_kw * gen_capex * scalarize(data["generator_fixed_om_share_per_year"])
        fixed_om = res_fom_s + bat_fom_s + gen_fom_s

        scope1 = fuel * scalarize(data["fuel_direct_emissions_kgco2e_per_unit_fuel"], scenario=s)
        grid_em_factor = scalarize(data["grid_emissions_factor_kgco2e_per_kwh"], scenario=s) if "grid_emissions_factor_kgco2e_per_kwh" in data else 0.0
        scope2 = grid_import_delivered * grid_em_factor
        scope3 = 0.0
        for r in resources:
            scope3 += res_caps[r] * scalarize(data["res_embedded_emissions_kgco2e_per_kw"], scenario=s, resource=r) / max(scalarize(data["res_lifetime_years"], resource=r), 1e-12)
        scope3 += cap_bat_kwh * scalarize(data["battery_embedded_emissions_kgco2e_per_kwh"], scenario=s) / max(bat_life, 1e-12)
        scope3 += cap_gen_kw * scalarize(data["generator_embedded_emissions_kgco2e_per_kw"], scenario=s) / max(gen_life, 1e-12)
        emissions = scope1 + scope2 + scope3
        lost_load_cost = lost_load * scalarize(data["lost_load_cost_per_kwh"], scenario=s)
        emissions_cost = emissions * scalarize(data["emission_cost_per_kgco2e"], scenario=s)
        annual_variable_cost = fuel_cost + grid_import_cost - grid_export_revenue - res_subsidy_revenue
        total_operating_cost = fixed_om + annual_variable_cost + lost_load_cost + emissions_cost
        reported_total_annual_cost = annualized_capex + total_operating_cost

        kpi_rows.append(
            {
                "scenario": s,
                "total_demand_kwh": total_demand,
                "served_energy_kwh": served,
                "lost_load_kwh": lost_load,
                "lost_load_fraction": safe_share(lost_load, total_demand),
                "total_res_kwh": total_res,
                "generator_generation_kwh": total_gen,
                "renewable_potential_kwh": res_potential,
                "renewable_curtailment_kwh": res_curtailment,
                "renewable_curtailment_share": res_curtailment_share,
                "grid_import_raw_kwh": grid_import_raw,
                "grid_import_delivered_kwh": grid_import_delivered,
                "grid_export_raw_kwh": grid_export_raw,
                "grid_export_delivered_kwh": grid_export_delivered,
                "grid_renewable_kwh": grid_renewable,
                "renewable_penetration": ren_pen,
                "fuel_consumption": fuel,
                "scope1_emissions_kgco2e": scope1,
                "scope2_emissions_kgco2e": scope2,
                "scope3_emissions_kgco2e": scope3,
                "emissions_kgco2e": emissions,
                "investment_annuity_cost": annualized_capex,
                "fixed_om_cost": fixed_om,
                "fuel_cost": fuel_cost,
                "grid_import_cost": grid_import_cost,
                "grid_export_revenue": grid_export_revenue,
                "grid_net_cost": grid_import_cost - grid_export_revenue,
                "res_subsidy_revenue": res_subsidy_revenue,
                "annual_variable_cost": annual_variable_cost,
                "lost_load_cost": lost_load_cost,
                "emissions_cost": emissions_cost,
                "total_operating_cost": total_operating_cost,
                "reported_total_annual_cost": reported_total_annual_cost,
                "solver_objective_value": safe_float(solver_objective_value),
                "objective_value": safe_float(solver_objective_value),
            }
        )

        expected_fom_rows.append({"scenario": s, "res_fom": res_fom_s, "bat_fom": bat_fom_s, "gen_fom": gen_fom_s})

    kpis = pd.DataFrame(kpi_rows)
    if not kpis.empty:
        kpis["weight"] = kpis["scenario"].map(weights).fillna(0.0)
        num_cols = [c for c in kpis.columns if c not in {"scenario"}]
        expected = {"scenario": "expected"}
        for c in num_cols:
            if c in {"objective_value", "solver_objective_value"}:
                expected[c] = safe_float(solver_objective_value)
            else:
                expected[c] = float((kpis[c] * kpis["weight"]).sum())
        kpis = pd.concat([kpis.drop(columns=["weight"]), pd.DataFrame([expected])], ignore_index=True)

    expected_row = select_kpi_row(kpis, data, mode="expected", scenario_label=None) if not kpis.empty else pd.Series(dtype=float)

    upfront = pd.DataFrame(upfront_rows)
    expected_cost_components = pd.DataFrame(
        [
            {"Component": "Annualized CAPEX (annuity)", "Value": float(safe_float(expected_row.get("investment_annuity_cost", 0.0))), "Unit": "/yr"},
            {"Component": "Fixed O&M", "Value": float(safe_float(expected_row.get("fixed_om_cost", 0.0))), "Unit": "/yr"},
            {"Component": "Fuel cost (expected)", "Value": float(safe_float(expected_row.get("fuel_cost", 0.0))), "Unit": "/yr"},
            {"Component": "Grid import cost (expected)", "Value": float(safe_float(expected_row.get("grid_import_cost", 0.0))), "Unit": "/yr"},
            {"Component": "Grid export revenue (expected)", "Value": -float(safe_float(expected_row.get("grid_export_revenue", 0.0))), "Unit": "/yr"},
            {"Component": "RES production subsidy (expected)", "Value": -float(safe_float(expected_row.get("res_subsidy_revenue", 0.0))), "Unit": "/yr"},
            {"Component": "Lost load penalty (expected)", "Value": float(safe_float(expected_row.get("lost_load_cost", 0.0))), "Unit": "/yr"},
            {"Component": "Emissions cost (scope 1 + 2 + 3, expected)", "Value": float(safe_float(expected_row.get("emissions_cost", 0.0))), "Unit": "/yr"},
            {"Component": "TOTAL (Expected)", "Value": float(safe_float(expected_row.get("reported_total_annual_cost", 0.0))), "Unit": "/yr"},
        ]
    )

    fom_df = pd.DataFrame(expected_fom_rows)
    if fom_df.empty:
        expected_fixed_om = pd.DataFrame(columns=["Technology", "Annual FOM [/yr]"])
    else:
        first = fom_df.iloc[0]
        expected_fixed_om = pd.DataFrame(
            [
                {"Technology": "Renewables", "Annual FOM [/yr]": float(safe_float(first.get("res_fom", 0.0)))},
                {"Technology": "Battery", "Annual FOM [/yr]": float(safe_float(first.get("bat_fom", 0.0)))},
                {"Technology": "Generator", "Annual FOM [/yr]": float(safe_float(first.get("gen_fom", 0.0)))},
            ]
        )

    annuities = pd.DataFrame(annuity_rows)
    embodied = pd.DataFrame(embodied_rows)

    scenario_variable_costs = pd.DataFrame(
        [
            {
                "Scenario": s,
                "Fuel cost": float(safe_float(kpis[kpis["scenario"] == s]["fuel_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Grid import cost": float(safe_float(kpis[kpis["scenario"] == s]["grid_import_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Grid export revenue": float(safe_float(kpis[kpis["scenario"] == s]["grid_export_revenue"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "RES subsidy revenue": float(safe_float(kpis[kpis["scenario"] == s]["res_subsidy_revenue"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Annual variable cost": float(safe_float(kpis[kpis["scenario"] == s]["annual_variable_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Weight": weights.get(s, 0.0),
            }
            for s in scenarios
        ]
    )
    scenario_emissions = pd.DataFrame(
        [
            {
                "Scenario": s,
                "Scope 1 emissions": float(safe_float(kpis[kpis["scenario"] == s]["scope1_emissions_kgco2e"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Scope 2 emissions": float(safe_float(kpis[kpis["scenario"] == s]["scope2_emissions_kgco2e"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Scope 3 emissions": float(safe_float(kpis[kpis["scenario"] == s]["scope3_emissions_kgco2e"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Total emissions": float(safe_float(kpis[kpis["scenario"] == s]["emissions_kgco2e"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Emissions cost": float(safe_float(kpis[kpis["scenario"] == s]["emissions_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Weight": weights.get(s, 0.0),
            }
            for s in scenarios
        ]
    )
    scenario_total_operating_costs = pd.DataFrame(
        [
            {
                "Scenario": s,
                "Fixed O&M": float(safe_float(kpis[kpis["scenario"] == s]["fixed_om_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Fuel cost": float(safe_float(kpis[kpis["scenario"] == s]["fuel_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Grid import cost": float(safe_float(kpis[kpis["scenario"] == s]["grid_import_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Grid export revenue": float(safe_float(kpis[kpis["scenario"] == s]["grid_export_revenue"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "RES subsidy revenue": float(safe_float(kpis[kpis["scenario"] == s]["res_subsidy_revenue"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Annual variable cost": float(safe_float(kpis[kpis["scenario"] == s]["annual_variable_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Lost load penalty": float(safe_float(kpis[kpis["scenario"] == s]["lost_load_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Emissions cost": float(safe_float(kpis[kpis["scenario"] == s]["emissions_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Total operating cost": float(safe_float(kpis[kpis["scenario"] == s]["total_operating_cost"].iloc[0])) if len(kpis[kpis["scenario"] == s]) else 0.0,
                "Weight": weights.get(s, 0.0),
            }
            for s in scenarios
        ]
    )

    return TypicalYearReportingTables(
        dispatch=dispatch,
        energy_balance=energy_balance,
        kpis=kpis,
        upfront=upfront,
        expected_cost_components=expected_cost_components,
        expected_fixed_om=expected_fixed_om,
        annuities=annuities,
        embodied=embodied,
        scenario_variable_costs=scenario_variable_costs,
        scenario_emissions=scenario_emissions,
        scenario_total_operating_costs=scenario_total_operating_costs,
    )
