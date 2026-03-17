from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from core.export.typical_year_results import export_typical_year_results
from core.typical_year_model.data import initialize_data
from core.typical_year_model.sets import initialize_sets


class _VarStub:
    def __init__(self, solution: xr.DataArray) -> None:
        self.solution = solution


def _make_stub_vars(data: xr.Dataset) -> dict[str, _VarStub]:
    period = data.coords["period"]
    scenario = data.coords["scenario"]
    resource = data.coords["resource"]

    t = int(period.size)
    s = int(scenario.size)
    r = int(resource.size)

    shape_ps = (t, s)
    shape_psr = (t, s, r)

    res_generation = xr.DataArray(
        np.full(shape_psr, 0.1, dtype=float),
        dims=("period", "scenario", "resource"),
        coords={"period": period, "scenario": scenario, "resource": resource},
    )
    generator_generation = xr.DataArray(
        np.full(shape_ps, 0.05, dtype=float),
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
    )
    battery_charge = xr.DataArray(
        np.zeros(shape_ps, dtype=float),
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
    )
    battery_discharge = xr.DataArray(
        np.zeros(shape_ps, dtype=float),
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
    )
    battery_soc = xr.DataArray(
        np.zeros(shape_ps, dtype=float),
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
    )
    lost_load = xr.DataArray(
        np.zeros(shape_ps, dtype=float),
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
    )
    fuel_consumption = xr.DataArray(
        np.full(shape_ps, 0.01, dtype=float),
        dims=("period", "scenario"),
        coords={"period": period, "scenario": scenario},
    )

    vars_dict: dict[str, _VarStub] = {
        "res_generation": _VarStub(res_generation),
        "generator_generation": _VarStub(generator_generation),
        "battery_charge": _VarStub(battery_charge),
        "battery_discharge": _VarStub(battery_discharge),
        "battery_soc": _VarStub(battery_soc),
        "lost_load": _VarStub(lost_load),
        "fuel_consumption": _VarStub(fuel_consumption),
        "res_units": _VarStub(
            xr.DataArray(
                np.ones((r,), dtype=float),
                dims=("resource",),
                coords={"resource": resource},
            )
        ),
        "battery_units": _VarStub(xr.DataArray(1.0)),
        "generator_units": _VarStub(xr.DataArray(1.0)),
    }

    if "grid_import_price" in data.data_vars:
        vars_dict["grid_import"] = _VarStub(
            xr.DataArray(
                np.zeros(shape_ps, dtype=float),
                dims=("period", "scenario"),
                coords={"period": period, "scenario": scenario},
            )
        )
    if "grid_export_price" in data.data_vars:
        vars_dict["grid_export"] = _VarStub(
            xr.DataArray(
                np.zeros(shape_ps, dtype=float),
                dims=("period", "scenario"),
                coords={"period": period, "scenario": scenario},
            )
        )

    return vars_dict


def test_typical_year_export_smoke(tmp_path: Path) -> None:
    project_name = "test_typical"
    sets = initialize_sets(project_name)
    data = initialize_data(project_name, sets)
    vars_dict = _make_stub_vars(data)

    out = export_typical_year_results(
        project_name=project_name,
        sets=sets,
        data=data,
        model=None,
        vars=vars_dict,
        solution=None,
        out_dir=tmp_path / "typical_year",
    )

    expected_keys = {
        "dispatch_timeseries_csv",
        "energy_balance_csv",
        "design_summary_csv",
        "kpis_csv",
        "out_dir",
    }
    assert expected_keys.issubset(out.keys())

    dispatch = pd.read_csv(out["dispatch_timeseries_csv"])
    energy = pd.read_csv(out["energy_balance_csv"])
    design = pd.read_csv(out["design_summary_csv"])
    kpis = pd.read_csv(out["kpis_csv"])

    assert {"period", "scenario", "load_demand", "res_generation_total", "generator_generation"}.issubset(dispatch.columns)
    assert {"period", "scenario", "demand", "balance_lhs", "balance_residual"}.issubset(energy.columns)
    assert {"battery_units", "generator_units", "res_units_total"}.issubset(design.columns)
    assert {"scenario", "total_demand_kwh", "lost_load_kwh", "objective_value"}.issubset(kpis.columns)
