from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import xarray as xr

from core.export.multi_year_results import export_multi_year_results
from core.multi_year_model.model import MultiYearModel


def _reduce_problem_size(m: MultiYearModel, periods: int = 24, years: int = 2) -> None:
    if not isinstance(m.sets, xr.Dataset) or not isinstance(m.data, xr.Dataset):
        raise RuntimeError("Model sets/data must be initialized before shrinking.")
    m.sets = m.sets.isel(period=slice(0, periods), year=slice(0, years))
    m.data = m.data.isel(period=slice(0, periods), year=slice(0, years))


def test_multiyear_real_solve_and_export(tmp_path: Path) -> None:
    m = MultiYearModel(project_name="test_multiyear")
    m._initialize_sets()
    m._initialize_data()
    _reduce_problem_size(m, periods=24, years=2)

    try:
        sol_summary = m.solve_single_objective(
            solver="highs",
            solver_params={"presolve": "on", "time_limit": 20.0},
            problem_fn=None,
            log_file_path=tmp_path / "solve.log",
        )
    except Exception as e:
        msg = str(e).lower()
        if "highs" in msg and ("not found" in msg or "not installed" in msg or "executable" in msg):
            pytest.skip(f"HiGHS solver unavailable in test environment: {e}")
        raise

    assert isinstance(sol_summary, xr.Dataset)
    assert m.model is not None
    assert isinstance(getattr(m.model, "solution", None), xr.Dataset)
    assert len(m.model.solution.data_vars) > 0

    out = export_multi_year_results(
        project_name="test_multiyear",
        sets=m.sets,
        data=m.data,
        model=m.model,
        vars=m.vars,
        solution=m.model.solution,
        out_dir=tmp_path / "results",
    )

    expected_files = [
        "dispatch_timeseries_csv",
        "energy_balance_csv",
        "design_by_step_csv",
        "kpis_yearly_csv",
        "cashflows_discounted_csv",
    ]
    for k in expected_files:
        assert Path(out[k]).exists(), f"Missing exported file for key {k}"

    dispatch = pd.read_csv(out["dispatch_timeseries_csv"])
    balance = pd.read_csv(out["energy_balance_csv"])
    design = pd.read_csv(out["design_by_step_csv"])
    kpis = pd.read_csv(out["kpis_yearly_csv"])
    cash = pd.read_csv(out["cashflows_discounted_csv"])

    assert {"period", "year", "scenario", "load_demand", "res_generation_total"}.issubset(dispatch.columns)
    assert {"period", "year", "scenario", "balance_residual"}.issubset(balance.columns)
    assert {"inv_step", "technology", "installed_capacity"}.issubset(design.columns)
    assert {"year", "scenario", "total_demand_kwh", "renewable_penetration"}.issubset(kpis.columns)
    assert {"year", "discounted_total", "salvage_credit_discounted"}.issubset(cash.columns)
