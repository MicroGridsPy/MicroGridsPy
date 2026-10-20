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


def _fake_solver(monkeypatch, sweep, *, first_life: float, rederive: dict[float, float],
                 battery_kwh: float = 800.0) -> list:
    """Replace run() and the derived-life solver; return the list of lives actually solved."""
    solved: list = []

    def fake_run(case, prov):
        life = first_life if case.service_life == "null" else float(case.service_life)
        solved.append(life)
        return {"case": case.name, "life_used": life, "battery_kwh": battery_kwh,
                "life_derived": first_life if case.service_life == "null" else np.nan}

    monkeypatch.setattr(sweep, "run", fake_run)
    monkeypatch.setattr(sweep, "derived_life_for_row", lambda row: rederive[row["life_used"]])
    return solved


def test_t6_1_refinement_converges(monkeypatch, sweep):
    # 8 -> re-derived 7.2 (7) -> re-derived 6.8 (7): converged at 7
    solved = _fake_solver(monkeypatch, sweep, first_life=8.0, rederive={8.0: 7.2, 7.0: 6.8})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert row["life_used"] == 7.0
    assert row["life_note"] == "converged"
    assert row["life_sequence"] == "8->7"
    assert row["life_iterations"] == 2
    assert solved == [8.0, 7.0]
    assert row["life_derived"] == 8.0  # the a-priori derivation is kept for traceability


def test_t6_1_refinement_oscillation_keeps_shorter(monkeypatch, sweep):
    # 8 -> 9 -> back to 8: oscillating, the shorter life is kept and re-solved
    solved = _fake_solver(monkeypatch, sweep, first_life=8.0, rederive={8.0: 8.6, 9.0: 8.4})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert row["life_used"] == 8.0
    assert row["life_note"] == "oscillating, shorter kept"
    assert row["life_sequence"] == "8->9->8"
    assert solved == [8.0, 9.0, 8.0]


def test_t6_1_refinement_uses_half_up_rounding(monkeypatch, sweep):
    _fake_solver(monkeypatch, sweep, first_life=9.0, rederive={9.0: 8.5})
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert row["life_note"] == "converged" and row["life_used"] == 9.0


def test_t6_1_refinement_iteration_budget(monkeypatch, sweep):
    # a run-away sequence 5 -> 6 -> 7 -> 8 -> 9 stops at the budget and keeps the shorter
    rederive = {float(L): L + 1.0 for L in range(5, 12)}
    solved = _fake_solver(monkeypatch, sweep, first_life=5.0, rederive=rederive)
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"), max_iter=2)
    assert row["life_note"] == "oscillating, shorter kept"
    assert len(solved) <= 4


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
    solved = _fake_solver(monkeypatch, sweep, first_life=8.0, rederive={8.0: 6.0, 7.0: 6.0})
    row = sweep.run_case(sweep.Case("x", "E", **case_kwargs), {})
    assert len(solved) == 1
    assert row["life_note"] == reason
    assert row["life_iterations"] == 1


def test_t6_1_no_battery_is_not_refined(monkeypatch, sweep):
    solved = _fake_solver(monkeypatch, sweep, first_life=8.0, rederive={8.0: 6.0},
                          battery_kwh=0.4)
    row = sweep.run_with_life_refinement(sweep.Case("x", "QC"))
    assert solved == [8.0]
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
