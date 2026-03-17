from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from core.data_pipeline.loader import load_project_dataset
from core.typical_year_model.sets import initialize_sets


PROJECT_NAME = "test_typical"

EXPECTED_DIMS = {
    "period": 8760,
    "scenario": 2,
    "resource": 1,
}

EXPECTED_COORDS = ["period", "resource", "scenario"]

EXPECTED_DATA_VARS = sorted(
    [
        "battery_calendar_lifetime_years",
        "battery_charge_efficiency",
        "battery_depth_of_discharge",
        "battery_discharge_efficiency",
        "battery_embedded_emissions_kgco2e_per_kwh",
        "battery_fixed_om_share_per_year",
        "battery_initial_soc",
        "battery_max_charge_time_hours",
        "battery_max_discharge_time_hours",
        "battery_max_installable_capacity_kwh",
        "battery_nominal_capacity_kwh",
        "battery_specific_investment_cost_per_kwh",
        "battery_wacc",
        "emission_cost_per_kgco2e",
        "fuel_direct_emissions_kgco2e_per_unit_fuel",
        "fuel_fuel_cost_per_unit_fuel",
        "fuel_lhv_kwh_per_unit_fuel",
        "generator_embedded_emissions_kgco2e_per_kw",
        "generator_fixed_om_share_per_year",
        "generator_lifetime_years",
        "generator_max_installable_capacity_kw",
        "generator_nominal_capacity_kw",
        "generator_nominal_efficiency_full_load",
        "generator_specific_investment_cost_per_kw",
        "generator_wacc",
        "land_availability_m2",
        "load_demand",
        "lost_load_cost_per_kwh",
        "max_lost_load_fraction",
        "min_renewable_penetration",
        "res_embedded_emissions_kgco2e_per_kw",
        "res_fixed_om_share_per_year",
        "res_grant_share_of_capex",
        "res_inverter_efficiency",
        "res_lifetime_years",
        "res_max_installable_capacity_kw",
        "res_nominal_capacity_kw",
        "res_production_subsidy_per_kwh",
        "res_specific_area_m2_per_kw",
        "res_specific_investment_cost_per_kw",
        "res_wacc",
        "resource_availability",
        "scenario_weight",
    ]
)

REQUIRED_SETTINGS_KEYS = [
    "project_name",
    "formulation",
    "unit_commitment",
    "multi_scenario",
    "resources",
    "optimization_constraints",
    "inputs_loaded",
    "battery_label",
    "generator",
    "fuel",
    "grid",
]

# Contract baseline.
# To regenerate once in a controlled environment:
#   UPDATE_TYPICAL_LOADER_FINGERPRINTS=1 pytest -q tests/test_typical_loader_contract.py
EXPECTED_FINGERPRINTS = {
    # Paste generated output here once baseline is locked.
}


def _var_fingerprint(da) -> dict:
    vals = np.asarray(da.values).reshape(-1)
    s = pd.Series(vals)
    hashed = pd.util.hash_pandas_object(s, index=False).values.tobytes()
    checksum = hashlib.sha256(hashed).hexdigest()
    return {
        "shape": tuple(int(x) for x in da.shape),
        "dtype": str(da.dtype),
        "nan_count": int(pd.isna(vals).sum()),
        "checksum": checksum,
    }


def _dataset_fingerprints(ds) -> dict:
    return {name: _var_fingerprint(ds[name]) for name in sorted(ds.data_vars)}


def test_typical_loader_contract_dims_coords_vars_and_settings():
    sets = initialize_sets(PROJECT_NAME)
    ds = load_project_dataset(PROJECT_NAME, sets, mode="typical_year")

    assert dict(ds.sizes) == EXPECTED_DIMS
    assert sorted(ds.coords) == EXPECTED_COORDS
    assert sorted(ds.data_vars) == EXPECTED_DATA_VARS

    settings = ds.attrs.get("settings", {})
    assert isinstance(settings, dict)
    for k in REQUIRED_SETTINGS_KEYS:
        assert k in settings, f"Missing settings key: {k}"


def test_typical_loader_contract_fingerprints():
    sets = initialize_sets(PROJECT_NAME)
    ds = load_project_dataset(PROJECT_NAME, sets, mode="typical_year")
    got = _dataset_fingerprints(ds)

    if os.getenv("UPDATE_TYPICAL_LOADER_FINGERPRINTS") == "1":
        out = Path(__file__).with_name("typical_loader_fingerprints.generated.json")
        out.write_text(json.dumps(got, indent=2, sort_keys=True), encoding="utf-8")

    assert EXPECTED_FINGERPRINTS, (
        "EXPECTED_FINGERPRINTS is empty. Generate once with "
        "UPDATE_TYPICAL_LOADER_FINGERPRINTS=1 and paste into this test."
    )
    assert got == EXPECTED_FINGERPRINTS

