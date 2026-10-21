"""Campaign-script tests for the service-life refinement (correction plan, T6.1-T6.2).

The refinement lives in scripts/run_degradation_sweep.py, outside the model, so these tests
drive it with a fake solve: they check the iteration logic and the row schema, not physics.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_degradation_sweep.py"

pytestmark = pytest.mark.skipif(not SCRIPT.exists(), reason="campaign script not present")


@pytest.fixture(scope="module")
def sweep():
    spec = importlib.util.spec_from_file_location("run_degradation_sweep", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve string annotations through sys.modules
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def _fake_solver(monkeypatch, sweep, *, a_priori: float, soh_end: dict[int, float],
                 rederive: dict[int, float], battery_kwh: float = 800.0) -> list:
    """Replace the a-priori loader, run() and the derived-life solver.

    ``soh_end[L]`` is the end-of-cohort SoH a solve at life L returns (0.80 = floor binding),
    ``rederive[L]`` the unrounded life re-derived from that solve. Returns the lives solved.
    """
    solved: list = []

    def fake_run(case, prov):
        life = a_priori if case.service_life == "null" else int(case.service_life)
        solved.append(life)
        return {"case": case.name, "life_used": float(life), "battery_kwh": battery_kwh,
                "soh_end_of_cohort": soh_end.get(life, 0.80), "end_of_life_soh": 0.80,
                "life_derived": np.nan}

    monkeypatch.setattr(sweep, "a_priori_life", lambda case: a_priori)
    monkeypatch.setattr(sweep, "run", fake_run)
    monkeypatch.setattr(sweep, "derived_life_for_row",
                        lambda row: rederive[int(row["life_used"])])
    return solved


def test_t6_1_binding_start_steps_down_then_rederives(monkeypatch, sweep):
    # The Kalobeyei QC shape: a priori 8.57 -> start at 8, which binds; 7 is slack and its
    # own cycling re-derives 7.8 -> 8, already solved and binding: a consistent fixed point.
    solved = _fake_solver(monkeypatch, sweep, a_priori=8.57,
                          soh_end={8: 0.80, 7: 0.815}, rederive={7: 7.8})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert row["life_used"] == 8.0
    assert row["case"] == "x" and row["results_project"] == "x__L8"
    assert row["life_sequence"] == "8->7->8"
    assert row["life_note"] == "converged from below (floor binding)"
    assert row["life_iterations"] == 2
    assert solved == [8, 7]  # 8 is not solved twice
    assert row["life_derived"] == 8.57 and row["life_rederived"] == 7.8


def test_t6_1_slack_start_that_rederives_to_itself(monkeypatch, sweep):
    solved = _fake_solver(monkeypatch, sweep, a_priori=8.4,
                          soh_end={7: 0.81}, rederive={7: 7.3})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert solved == [7]
    assert row["life_used"] == 7.0
    assert row["life_note"] == "converged from below (floor slack)"


def test_t6_1_slack_start_climbs_to_a_binding_life(monkeypatch, sweep):
    solved = _fake_solver(monkeypatch, sweep, a_priori=6.2,
                          soh_end={5: 0.83, 7: 0.80}, rederive={5: 6.6})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert solved == [5, 7]
    assert row["life_sequence"] == "5->7"
    assert row["life_note"] == "converged from below (floor binding)"


def test_t6_1_climb_through_slack_lives(monkeypatch, sweep):
    solved = _fake_solver(monkeypatch, sweep, a_priori=6.2,
                          soh_end={5: 0.83, 7: 0.805}, rederive={5: 6.6, 7: 7.2})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert solved == [5, 7]
    assert row["life_used"] == 7.0
    assert row["life_note"] == "converged from below (floor slack)"


def test_t6_1_refinement_uses_half_up_rounding(monkeypatch, sweep):
    solved = _fake_solver(monkeypatch, sweep, a_priori=9.2,
                          soh_end={8: 0.82, 9: 0.80}, rederive={8: 8.5})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert solved == [8, 9]
    assert row["life_used"] == 9.0


def test_t6_1_floor_binding_down_to_two_years(monkeypatch, sweep):
    solved = _fake_solver(monkeypatch, sweep, a_priori=3.4, soh_end={}, rederive={})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert solved == [2]
    assert row["life_note"] == "floor binds even at 2 y"


def test_t6_1_solve_budget(monkeypatch, sweep):
    solved = _fake_solver(monkeypatch, sweep, a_priori=9.0, soh_end={}, rederive={})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"), max_iter=2)
    assert solved == [8, 7]
    assert row["life_used"] == 7.0
    assert row["life_note"] == "solve budget exhausted, last kept"


@pytest.mark.parametrize(
    "case_kwargs, reason",
    [
        ({"service_life": 7}, "fixed life, not refined"),
        ({"coefficients": False, "linear_rate": 0.0, "service_life": 8},
         "linear/no-ageing mode, not refined"),
        ({"coefficients": False, "linear_rate": 0.025}, "linear/no-ageing mode, not refined"),
        ({"steps": [10, 10]}, "multi-step, not refined"),
        ({"refine_life": False}, "refinement off"),
    ],
)
def test_t6_1_excluded_cases_do_not_iterate(monkeypatch, sweep, case_kwargs, reason):
    solved = _fake_solver(monkeypatch, sweep, a_priori=8.0, soh_end={8: 0.85}, rederive={8: 6.0})
    row = sweep.run_case(sweep.Case("x", "E", **case_kwargs), {})
    assert len(solved) == 1
    assert row["life_note"] == reason
    assert row["life_iterations"] == 1


def test_t6_1_no_battery_is_not_refined(monkeypatch, sweep):
    solved = _fake_solver(monkeypatch, sweep, a_priori=8.0, soh_end={}, rederive={},
                          battery_kwh=0.4)
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert solved == [7]
    assert row["life_note"] == "no battery, not refined"


def test_t6_1_matrix_exclusions(sweep):
    by_name = {c.name: c for c in sweep.matrix()}
    for name in ("E5_life_7", "E0_linear", "E0_no_ageing", "E7_linear_0.02",
                 "E8_growth_no_ageing", "E9_steps2_flat", "E9_steps4_growth"):
        assert sweep.refinement_exclusion(by_name[name]) is not None, name
    assert sweep.refinement_exclusion(by_name["baseline"]) is None


# ---------------------------------------------------------------------------- T6.2

NEW_COLUMNS = (
    "cycle_test_duration_years", "lambda_cyc", "c_at_tref", "test_time_calendar_fade",
    "soh_end_of_cohort", "f_cyc_realised", "life_sequence", "life_iterations", "life_note",
    "floor_convention",
)


def _write_fake_results(project: Path, *, nameplate: float, years: int, periods: int) -> None:
    out, inputs = project / "results", project / "inputs"
    out.mkdir(parents=True)
    inputs.mkdir(parents=True)
    pd.DataFrame([
        {"section": "summary_metrics", "row_label": "Net Present Cost (Expected)", "value": 1e6},
        {"section": "summary_metrics", "row_label": "LCOE", "value": 0.3},
    ]).to_csv(out / "reporting_summary.csv", index=False)
    pd.DataFrame({"technology": ["renewable", "battery", "generator"],
                  "installed_capacity": [500.0, nameplate, 100.0]}).to_csv(
        out / "design_by_step.csv", index=False)
    rows = []
    for y in range(years):
        for t in range(periods):
            rows.append({"year": 2026 + y, "battery_discharge_dc": 10.0,
                         "battery_cycle_fade": 1.0, "battery_calendar_fade": 0.5,
                         "battery_soh": 1.0 - 0.01 * y, "lost_load": 0.0})
    pd.DataFrame(rows).to_csv(out / "dispatch_timeseries.csv", index=False)
    pd.DataFrame({"year": [2026 + y for y in range(years)], "renewable_penetration": 0.8,
                  "renewable_curtailment_share": 0.1, "generator_generation_kwh": 100.0,
                  "served_energy_kwh": 1000.0}).to_csv(out / "kpis_yearly.csv", index=False)
    pd.DataFrame({"year": [2026 + y for y in range(years)], "scenario": "1", "inv_step": "1",
                  "nominal_kwh": nameplate,
                  "soh_start_of_year": [1.0 - 0.01 * y for y in range(years)],
                  "soh_end_of_year": [0.99 - 0.01 * y for y in range(years)]}).to_csv(
        out / "battery_soh_by_year.csv", index=False)
    (inputs / "battery.yaml").write_text(
        yaml.safe_dump({"battery": {"technical": {"depth_of_discharge": 0.8}}}), encoding="utf-8")
    (inputs / "ambient_temperature.csv").write_text(
        "period;T\n-;degC\n" + "".join(f"{t};25,0\n" for t in range(periods)), encoding="utf-8")


def test_t6_2_new_columns_present_and_filled(monkeypatch, sweep, tmp_path):
    import microgridspy as mgp

    _write_fake_results(tmp_path, nameplate=800.0, years=4, periods=3)
    monkeypatch.setattr(mgp, "export_results", lambda *a, **k: None)
    settings = {
        "coefficients_enabled": True, "cycle_test_duration_years": 2.0, "lambda_cyc": 1.01317,
        "c_at_tref": 3.436e-5, "test_time_calendar_fade": 0.035, "chemistry": "LFP",
        "calendar_mean_soc": 0.6, "calendar_fade_scale": 1.0, "end_of_life_soh": 0.8,
        "calendar_lifetime_years_used": 2.0, "mean_cell_temperature_c": 35.0,
    }
    model = SimpleNamespace(
        results=lambda: None,
        data=SimpleNamespace(attrs={"settings": {"battery_model": {"degradation_model": settings}}}),
    )
    row = sweep.collect(sweep.Case("x", "QC"), tmp_path, model, 1.0, [])
    row.update(life_sequence="2", life_note="converged")
    for column in NEW_COLUMNS:
        assert column in row, column
        value = row[column]
        assert value is not None and value != "" and not (
            isinstance(value, float) and math.isnan(value)), column
    assert row["soh_end_of_cohort"] == pytest.approx(0.96)
    # per-cohort means: 3 periods x 1.0 kWh per year over the two full 2-year cohorts
    assert row["f_cyc_realised"] == pytest.approx(3.0 / 800.0)
    assert row["fade_mean_basis"] == "2 full cohort(s)"
    assert row["diesel_share"] == pytest.approx(0.1)

    # the CSV writer keeps every column, also when later rows bring new ones
    out = tmp_path / "rows.csv"
    sweep.append_row(out, {"case": "a", "npc": 1.0})
    sweep.append_row(out, {"case": "b", "npc": 2.0, **{c: row[c] for c in NEW_COLUMNS}})
    frame = pd.read_csv(out)
    assert list(frame["case"]) == ["a", "b"]
    assert set(NEW_COLUMNS) <= set(frame.columns)
    assert frame.loc[1, "life_note"] == "converged"


def test_t6_2_qc_block(sweep):
    cases = {c.name: c for c in sweep.qc_cases()}
    assert cases["QC_A_tau2_start_of_year_floor"].floor_convention == "start_of_year"
    assert cases["QC_B_tau_null"].test_duration is None
    assert cases["QC_D_tau2_refined"].refine_life
    assert [cases[f"QC_F{L}"].service_life for L in (7, 8, 9)] == [7, 8, 9]
    assert sweep.QC_RESULTS.name == "qc_results.csv"
    assert sweep.RESULTS.name == "sweep_results_v2.csv"


def test_t6_2_rerun_replaces_the_case_row(sweep, tmp_path):
    out = tmp_path / "rows.csv"
    sweep.append_row(out, {"case": "a", "npc": 1.0})
    sweep.append_row(out, {"case": "b", "npc": 2.0})
    sweep.append_row(out, {"case": "a", "npc": 3.0, "life_note": "converged"})
    frame = pd.read_csv(out)
    assert sorted(frame["case"]) == ["a", "b"]
    assert frame.set_index("case").loc["a", "npc"] == 3.0


def test_t6_2_reduced_campaign_names_exist(sweep):
    names = {c.name for c in sweep.matrix()}
    assert set(sweep.REDUCED) <= names
    assert len(sweep.REDUCED) == len(set(sweep.REDUCED))
    tau = {c.name: c for c in sweep.matrix()}["E12_tau_1.5"]
    assert tau.test_duration == 1.5 and sweep.refinement_exclusion(tau) is None
