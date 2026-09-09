"""Unit tests for the battery convex-loss efficiency curve loader.

These pin the re-anchoring fix: the shipped default is a physically realistic
*peaked* absolute-efficiency curve (worse at both very low and very high power). The
key structural property is that the loss curve is fit through the sampled points only,
so the lowest segment carries a positive **no-load / standby loss** intercept -- which a
curve forced through the origin can never express. As a result the power-dependent model
is more efficient than the constant baseline only in a narrow mid-power band and *less*
efficient at both low and high power, instead of being uniformly more efficient.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from microgridspy.data_pipeline.battery_loss_model import (
    InputValidationError,
    NORMALIZED_CURVE,
    LEGACY_ABSOLUTE_CURVE,
    load_battery_loss_curve_dataset,
)
from microgridspy.io.templates import _write_battery_efficiency_curve_csv, TemplateSettings


BASE = 0.975  # one-way baseline -> round-trip ~0.9506


def _write_default_curve(tmp_path: Path) -> Path:
    """Write the shipped default battery efficiency curve via the template writer."""
    path = tmp_path / "battery_efficiency_curve.csv"
    settings = TemplateSettings(
        formulation="dynamic",
        system_type="off_grid",
        allow_export=False,
        multi_scenario=False,
        n_scenarios=1,
        scenario_labels=["scenario_1"],
        scenario_weights=[1.0],
        start_year_label="2026",
        horizon_years=10,
        capacity_expansion=False,
        investment_steps_years=None,
        n_res_sources=1,
        resource_labels=["Solar"],
        conversion_labels=["Solar PV"],
        battery_label="Battery",
        battery_loss_model="convex_loss_epigraph",
        battery_cycle_fade_enabled=False,
        battery_efficiency_curve_csv="battery_efficiency_curve.csv",
        battery_cycle_lifetime_to_eol_cycles=6000.0,
        battery_end_of_life_soh=0.8,
        generator_label="Generator",
        generator_efficiency_model="efficiency_curve",
        generator_efficiency_curve_csv="generator_efficiency_curve.csv",
        fuel_label="Fuel",
    )
    _write_battery_efficiency_curve_csv(path, settings=settings, overwrite=True)
    return path


def _one_way_eff(ds, side: str, x: float) -> float:
    """Reconstruct the one-way efficiency implied by the convex loss epigraph at power x."""
    slope = ds[f"battery_{side}_loss_slope"].values
    intercept = ds[f"battery_{side}_loss_intercept"].values
    loss = max(float(np.max(slope * x + intercept)), 0.0)  # epigraph + L >= 0
    if side == "charge":
        # L_ch = x * (1/eta - 1) -> eta = x / (x + L)
        return x / (x + loss)
    return 1.0 - loss / x  # discharge: L_dis = x * (1 - eta)


def test_default_curve_is_peaked_absolute_with_no_load_loss(tmp_path) -> None:
    path = _write_default_curve(tmp_path)
    ds = load_battery_loss_curve_dataset(
        path, charge_efficiency_base=BASE, discharge_efficiency_base=BASE
    )

    interp = ds.attrs["battery_curve_interpretation"]
    assert interp["charge_efficiency"] == LEGACY_ABSOLUTE_CURVE
    assert interp["discharge_efficiency"] == LEGACY_ABSOLUTE_CURVE

    # The defining structural fix: a genuine, strictly positive no-load loss on the
    # lowest segment (impossible with an origin-anchored curve).
    for side in ("charge", "discharge"):
        intercept = ds[f"battery_{side}_loss_intercept"].values
        no_load_loss = float(np.max(intercept))
        assert no_load_loss > 1e-4, f"{side}: expected a positive no-load loss, got {no_load_loss}"
        # Convex: segment slopes non-decreasing.
        slopes = ds[f"battery_{side}_loss_slope"].values
        assert np.all(np.diff(slopes) >= -1e-9)


def test_default_curve_crosses_the_constant_baseline(tmp_path) -> None:
    path = _write_default_curve(tmp_path)
    ds = load_battery_loss_curve_dataset(
        path, charge_efficiency_base=BASE, discharge_efficiency_base=BASE
    )
    baseline_rt = BASE * BASE

    def round_trip(x: float) -> float:
        return _one_way_eff(ds, "charge", x) * _one_way_eff(ds, "discharge", x)

    # Below the constant baseline at low power (standby-dominated) and at full power
    # (conversion/resistive), above it only in the mid-power sweet spot.
    assert round_trip(0.10) < baseline_rt
    assert round_trip(1.00) < baseline_rt
    assert round_trip(0.40) > baseline_rt
    # And realistic magnitudes for a modern LFP + inverter AC-to-AC system.
    assert 0.90 < round_trip(0.10) < 0.92
    assert 0.95 < round_trip(0.40) < 0.96
    assert 0.93 < round_trip(1.00) < 0.95


def test_monotone_normalized_curve_stays_backward_compatible(tmp_path) -> None:
    # A legacy monotonically-more-efficient-at-low-power curve (normalized multipliers,
    # full-load row 1.0) must still load and must NOT introduce a spurious no-load loss:
    # its extrapolated intercepts are <= 0 and stay non-binding (loss vars are L >= 0).
    path = tmp_path / "legacy.csv"
    pd.DataFrame(
        {
            "relative_power_pu": [0.05, 0.10, 0.25, 0.50, 0.75, 1.00],
            "charge_efficiency": [1.0368, 1.0332, 1.0263, 1.0168, 1.0074, 1.0000],
            "discharge_efficiency": [1.0302, 1.0271, 1.0219, 1.0135, 1.0052, 1.0000],
        }
    ).to_csv(path, index=False)
    ds = load_battery_loss_curve_dataset(
        path, charge_efficiency_base=0.95, discharge_efficiency_base=0.96
    )
    interp = ds.attrs["battery_curve_interpretation"]
    assert interp["charge_efficiency"] == NORMALIZED_CURVE
    for side in ("charge", "discharge"):
        intercept = ds[f"battery_{side}_loss_intercept"].values
        assert float(np.max(intercept)) <= 1e-9  # no positive no-load loss


def test_non_convex_peaked_curve_is_rejected(tmp_path) -> None:
    # A curve whose implied loss is not convex (efficiency rising too steeply then
    # falling) must still be rejected -- the epigraph can only represent convex losses.
    path = tmp_path / "nonconvex.csv"
    pd.DataFrame(
        {
            "relative_power_pu": [0.10, 0.20, 0.40, 1.00],
            "charge_efficiency": [0.80, 0.99, 0.985, 0.97],
            "discharge_efficiency": [0.80, 0.99, 0.985, 0.97],
        }
    ).to_csv(path, index=False)
    with pytest.raises(InputValidationError):
        load_battery_loss_curve_dataset(
            path, charge_efficiency_base=0.97, discharge_efficiency_base=0.97
        )
