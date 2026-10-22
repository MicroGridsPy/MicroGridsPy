"""The exported multi-year NPC must equal the optimisation objective.

cashflows_discounted.csv (and the reporting_summary "Net Present Cost (Expected)" built from
it) used to carry only the inverter fixed O&M, while the objective also charges the PV,
battery and generator fixed O&M. The existing fixtures set every fixed O&M share to zero, so
the gap never showed; this test switches them on.
"""

from __future__ import annotations

import linopy as lp
import pytest
import xarray as xr
from test_multi_year_inverters import _base_data, _base_sets, _solve_with_highs_or_skip

from microgridspy.export.multi_year_results import build_multi_year_results
from microgridspy.multi_year_model.constraints import initialize_constraints
from microgridspy.multi_year_model.objective import initialize_objective
from microgridspy.multi_year_model.variables import initialize_vars


def _with_fixed_om(data: xr.Dataset) -> xr.Dataset:
    data = data.copy()
    for name, share in (("res_fixed_om_share_per_year", 0.02),
                        ("battery_fixed_om_share_per_year", 0.03),
                        ("generator_fixed_om_share_per_year", 0.04)):
        data[name] = xr.full_like(data[name], share)
    # a capital grant: the objective charges fixed O&M on the GROSS asset value
    data["res_grant_share_of_capex"] = xr.full_like(data["res_grant_share_of_capex"], 0.3)
    data["res_inverter_fixed_om_share_per_year"] = xr.full_like(
        data["res_inverter_fixed_om_share_per_year"], 0.01)
    return data


def _solved_results():
    sets = _base_sets()
    data = _with_fixed_om(_base_data())
    model = lp.Model()
    vars_dict = initialize_vars(sets, data, model)
    initialize_constraints(sets, data, vars_dict, model)
    initialize_objective(sets, data, vars_dict, model)
    solution = _solve_with_highs_or_skip(model)
    results = build_multi_year_results(
        project_name="cashflow_npc", sets=sets, data=data, vars=vars_dict, solution=solution,
        objective_value=float(model.objective.value), status="optimal", solver="highs",
        results_dir=None, source="session",
    )
    return model, results


def test_exported_npc_equals_objective_with_fixed_om():
    model, results = _solved_results()
    npc = float(results.cashflows_discounted["discounted_total"].sum())
    assert npc == pytest.approx(float(model.objective.value), rel=1e-5)


def test_opex_carries_every_fixed_om_term():
    _, results = _solved_results()
    costs = results.scenario_costs_yearly
    expected = costs[costs["scenario"] == "Expected"].set_index("year")
    cash = results.cashflows_discounted.set_index("year")
    fixed = expected[["fixed_om_res", "fixed_om_res_inverter", "fixed_om_battery",
                      "fixed_om_battery_inverter", "fixed_om_generator"]].sum(axis=1)
    assert (expected["fixed_om_res"] + expected["fixed_om_battery"]
            + expected["fixed_om_generator"]).sum() > 0  # the fixture really has fixed O&M
    pd_diff = cash["opex_expected"] - (expected["fuel_cost"] + fixed)
    assert pd_diff.abs().max() == pytest.approx(0.0, abs=1e-6)


def test_reported_npc_follows_the_cash_flows_without_objective_value():
    """mgp.solve -> export passes no objective value, so reporting_summary falls back on the
    cash-flow sum: that is the path every campaign result went through."""
    sets = _base_sets()
    data = _with_fixed_om(_base_data())
    model = lp.Model()
    vars_dict = initialize_vars(sets, data, model)
    initialize_constraints(sets, data, vars_dict, model)
    initialize_objective(sets, data, vars_dict, model)
    solution = _solve_with_highs_or_skip(model)
    results = build_multi_year_results(
        project_name="cashflow_npc", sets=sets, data=data, vars=vars_dict, solution=solution,
        objective_value=None, status="optimal", solver="highs", results_dir=None,
        source="session",
    )
    summary = results.reporting_summary.set_index("row_label")["value"]
    assert float(summary["Net Present Cost (Expected)"]) == pytest.approx(
        float(model.objective.value), rel=1e-5)
