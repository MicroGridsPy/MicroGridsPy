from __future__ import annotations

import numpy as np


def fit_generator_willans_from_curve(
    rel: np.ndarray,
    eff: np.ndarray,
    *,
    error_cls: type[Exception] = RuntimeError,
) -> tuple[float, float]:
    """
    Fit an affine Willans relative fuel-use line to a generator efficiency curve.

    The relative fuel-use is ``phi(r) = r / eta(r)``. A real diesel genset follows
    a Willans line (a no-load intercept plus a roughly constant marginal slope),
    so ``phi`` is represented as the affine function

        phi(r) = q0 + q1 * r

    where ``q0 >= 0`` is the relative no-load fuel use (per unit of nominal
    capacity) and ``q1 > 0`` is the marginal relative fuel use. This fit is paired
    with a unit-commitment variable that supplies the on/off origin behaviour, so
    it does NOT anchor the curve at the origin and therefore does not need to
    flatten a physical (efficiency-increasing) diesel curve.

    The line is anchored at the full-load point ``r = 1`` so the datasheet
    full-load efficiency is preserved exactly, and the slope is least-squares
    fitted to the remaining positive-load points.

    Inputs may include a leading zero anchor (``rel[0] == 0``); it is ignored.
    ``eff`` must be the absolute efficiency at each relative-power point.

    Returns:
        (q0, q1): intercept and slope of ``phi(r) = q0 + q1 * r``.
    """
    rel = np.asarray(rel, dtype=float)
    eff = np.asarray(eff, dtype=float)
    if rel.shape != eff.shape:
        raise error_cls("Generator efficiency curve rel/eff arrays must have the same shape.")

    mask = rel > 0.0
    r = rel[mask]
    e = eff[mask]
    if r.size == 0:
        raise error_cls("Generator efficiency curve must contain at least one positive-load point.")
    if np.any(~np.isfinite(r)) or np.any(~np.isfinite(e)) or np.any(e <= 0.0):
        raise error_cls(
            "Generator efficiency values must be finite and strictly positive at positive load."
        )
    if not np.isclose(r[-1], 1.0, atol=1e-9):
        raise error_cls("Generator efficiency curve must include the full-load point r=1.0.")

    phi = r / e  # relative fuel use phi(r) = r / eta(r)
    phi_full = float(phi[-1])  # = 1 / eta_full

    if r.size == 1:
        # Only the full-load point is known: fall back to constant full-load efficiency.
        return 0.0, phi_full

    # Anchor at full load (preserve datasheet full-load efficiency) and least-squares
    # fit the slope to the remaining points: phi(r) = phi_full + q1 * (r - 1).
    dr = r[:-1] - 1.0
    dphi = phi[:-1] - phi_full
    denom = float(np.dot(dr, dr))
    q1 = float(np.dot(dr, dphi) / denom) if denom > 0.0 else phi_full
    q0 = phi_full - q1

    if q1 <= 0.0:
        raise error_cls(
            "Implied generator fuel-use curve is non-increasing in output, which is not physical."
        )
    if q0 < 0.0:
        # No genuine no-load penalty implied by the curve; use constant full-load efficiency.
        return 0.0, phi_full
    return float(q0), float(q1)
