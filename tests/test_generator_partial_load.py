"""Unit tests for the Willans generator partial-load fit (Stage 1 commitment model).

These pin the core correctness fix: a physically realistic (efficiency-increasing)
diesel curve must yield a positive no-load intercept and preserve the full-load
efficiency exactly, instead of being flattened to the worst part-load efficiency by
the old convex-majorant surrogate.
"""

from __future__ import annotations

import numpy as np
import pytest

from microgridspy.data_pipeline.generator_partial_load_model import (
    fit_generator_willans_from_curve,
)


def test_willans_fit_preserves_full_load_and_positive_intercept() -> None:
    # Shipped Kalobeyei-style curve: normalized multipliers scaled by the datasheet
    # full-load efficiency -> absolute efficiency at each relative-power point.
    eta_full = 0.34
    rel = np.array([0.0, 0.20, 0.40, 0.60, 0.80, 1.00])
    multiplier = np.array([0.0, 0.75, 0.82, 0.89, 0.95, 1.00])
    eff = eta_full * multiplier  # absolute efficiency, with a leading zero anchor

    q0, q1 = fit_generator_willans_from_curve(rel, eff, error_cls=ValueError)

    # A real no-load penalty and a positive marginal slope.
    assert q0 > 0.0
    assert q1 > 0.0

    # Full-load fuel-use phi(1) = q0 + q1 must equal 1/eta_full exactly (datasheet
    # full-load efficiency preserved), NOT the ~1/(eta_full*0.75) value the old
    # convex majorant produced (a 33% full-load fuel inflation).
    phi_full = 1.0 / eta_full
    assert q0 + q1 == pytest.approx(phi_full, rel=1e-9)
    flattened_phi_full = 1.0 / (eta_full * 0.75)
    assert (q0 + q1) < 0.98 * flattened_phi_full


def test_willans_fit_rejects_nonphysical_decreasing_fuel_curve() -> None:
    # Efficiency rising steeply enough that phi(r) = r/eta(r) DEcreases with load,
    # i.e. an implied fuel curve that falls as output rises -> non-physical.
    rel = np.array([0.0, 0.5, 1.0])
    eff = np.array([0.0, 0.10, 0.34])  # phi = [5.0, 2.94] -> decreasing
    with pytest.raises(ValueError):
        fit_generator_willans_from_curve(rel, eff, error_cls=ValueError)


def test_willans_fit_single_point_falls_back_to_constant_efficiency() -> None:
    # Only the full-load point known -> constant full-load efficiency (q0 == 0).
    q0, q1 = fit_generator_willans_from_curve(
        np.array([0.0, 1.0]), np.array([0.0, 0.34]), error_cls=ValueError
    )
    assert q0 == pytest.approx(0.0)
    assert q1 == pytest.approx(1.0 / 0.34, rel=1e-9)


# ---------------------------------------------------------------------------
# Template surface: enabling the generator efficiency curve must default to the
# meaningful "integer" unit-commitment mode (not the no-op "relaxed"), so the
# GUI/template "efficiency curve" choice actually penalizes part-load operation.
# ---------------------------------------------------------------------------
def _generator_template_settings(**overrides):
    from microgridspy.io.templates import TemplateSettings

    base = dict(
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
        battery_loss_model="constant_efficiency",
        battery_cycle_fade_enabled=False,
        battery_calendar_fade_enabled=False,
        battery_efficiency_curve_csv="battery_efficiency_curve.csv",
        battery_cycle_lifetime_to_eol_cycles=6000.0,
        battery_calendar_fade_curve_csv="battery_calendar_fade_curve.csv",
        battery_calendar_time_increment_per_step=1.0,
        battery_end_of_life_soh=0.8,
        generator_label="Generator",
        generator_efficiency_model="efficiency_curve",
        generator_efficiency_curve_csv="generator_efficiency_curve.csv",
        fuel_label="Fuel",
    )
    base.update(overrides)
    return TemplateSettings(**base)


def _written_generator_yaml(tmp_path, name, settings):
    import microgridspy as mgp

    mgp.set_workspace(tmp_path)
    mgp.create_project(
        name, formulation="dynamic", horizon_years=10, settings=settings, overwrite=True
    )
    return next(tmp_path.rglob("generator.yaml")).read_text(encoding="utf-8")


def test_generator_curve_template_defaults_to_integer_commitment(tmp_path) -> None:
    text = _written_generator_yaml(tmp_path, "gen_commit_default", _generator_template_settings())
    assert "partial_load_commitment: integer" in text
    assert "min_load_fraction:" in text


def test_generator_commitment_legacy_relaxed_normalizes_to_integer(tmp_path) -> None:
    # The LP relaxation was removed; a legacy "relaxed" value normalizes to "integer".
    text = _written_generator_yaml(
        tmp_path,
        "gen_commit_relaxed",
        _generator_template_settings(generator_partial_load_commitment="relaxed"),
    )
    assert "partial_load_commitment: integer" in text
    assert "relaxed" not in text
