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
