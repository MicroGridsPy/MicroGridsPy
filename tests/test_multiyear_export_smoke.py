from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from core.export.multi_year_results import export_multi_year_results
from core.multi_year_model.data import initialize_data
from core.multi_year_model.sets import initialize_sets


class _VarStub:
    def __init__(self, solution: xr.DataArray) -> None:
        self.solution = solution


def _build_stub_vars(sets: xr.Dataset) -> dict[str, _VarStub]:
    period = sets.coords["period"]
    year = sets.coords["year"]
    scenario = sets.coords["scenario"]
    resource = sets.coords["resource"]
    inv_step = sets.coords["inv_step"]

    t, y, s, r, k = int(period.size), int(year.size), int(scenario.size), int(resource.size), int(inv_step.size)

    shape_pys = (t, y, s)
    shape_pysr = (t, y, s, r)

    res_generation = xr.DataArray(
        np.full(shape_pysr, 0.2, dtype=float),
        dims=("period", "year", "scenario", "resource"),
        coords={"period": period, "year": year, "scenario": scenario, "resource": resource},
    )
    generator_generation = xr.DataArray(
        np.full(shape_pys, 0.1, dtype=float),
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
    )
    battery_charge = xr.DataArray(
        np.zeros(shape_pys, dtype=float),
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
    )
    battery_discharge = xr.DataArray(
        np.zeros(shape_pys, dtype=float),
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
    )
    battery_soc = xr.DataArray(
        np.zeros(shape_pys, dtype=float),
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
    )
    lost_load = xr.DataArray(
        np.zeros(shape_pys, dtype=float),
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
    )
    fuel_consumption = xr.DataArray(
        np.full(shape_pys, 0.01, dtype=float),
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
    )
    grid_import = xr.DataArray(
        np.zeros(shape_pys, dtype=float),
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
    )
    grid_export = xr.DataArray(
        np.zeros(shape_pys, dtype=float),
        dims=("period", "year", "scenario"),
        coords={"period": period, "year": year, "scenario": scenario},
    )

    return {
        "res_units": _VarStub(
            xr.DataArray(
                np.ones((k, r), dtype=float),
                dims=("inv_step", "resource"),
                coords={"inv_step": inv_step, "resource": resource},
            )
        ),
        "battery_units": _VarStub(
            xr.DataArray(
                np.ones((k,), dtype=float),
                dims=("inv_step",),
                coords={"inv_step": inv_step},
            )
        ),
        "generator_units": _VarStub(
            xr.DataArray(
                np.ones((k,), dtype=float),
                dims=("inv_step",),
                coords={"inv_step": inv_step},
            )
        ),
        "res_generation": _VarStub(res_generation),
        "generator_generation": _VarStub(generator_generation),
        "battery_charge": _VarStub(battery_charge),
        "battery_discharge": _VarStub(battery_discharge),
        "battery_soc": _VarStub(battery_soc),
        "lost_load": _VarStub(lost_load),
        "fuel_consumption": _VarStub(fuel_consumption),
        "grid_import": _VarStub(grid_import),
        "grid_export": _VarStub(grid_export),
    }


def test_multiyear_export_smoke(tmp_path: Path) -> None:
    project_name = "test_multiyear"
    sets = initialize_sets(project_name)
    data = initialize_data(project_name, sets)
    vars_dict = _build_stub_vars(sets)

    out = export_multi_year_results(
        project_name=project_name,
        sets=sets,
        data=data,
        model=None,
        vars=vars_dict,
        solution=None,
        out_dir=tmp_path,
    )

    assert Path(out["dispatch_timeseries_csv"]).exists()
    assert Path(out["energy_balance_csv"]).exists()
    assert Path(out["design_by_step_csv"]).exists()
    assert Path(out["kpis_yearly_csv"]).exists()
    assert Path(out["cashflows_discounted_csv"]).exists()

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
