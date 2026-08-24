from __future__ import annotations

from pathlib import Path
from typing import Type

import numpy as np


def build_generator_partial_load_surrogate(
    *,
    rel: np.ndarray,
    eff: np.ndarray,
    path: Path,
    error_cls: Type[Exception] = RuntimeError,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Build an LP-safe convex generator fuel-use surrogate from sampled efficiency points.

    Inputs:
    - rel: relative output support points in [0, 1]
    - eff: absolute efficiencies at those support points

    Returns:
    - rel_full: zero-anchored relative output points
    - eff_full: zero-anchored absolute efficiency points
    - fuel_raw_full: raw relative fuel-use points phi(r) = r / eta(r)
    - fuel_surrogate_full: convex majorant used by the LP formulation

    Notes:
    - The raw fuel-use curve is derived from the user-facing efficiency curve.
    - The LP formulation needs a convex fuel-vs-output epigraph that never
      underestimates fuel, so we replace any non-convex raw curve with a
      conservative convex majorant built on the same support points.
    """
    rel = np.asarray(rel, dtype=float)
    eff = np.asarray(eff, dtype=float)

    if np.any(~np.isfinite(rel)) or np.any(~np.isfinite(eff)):
        raise error_cls(f"{path.name}: generator efficiency curve contains non-finite values.")
    if rel.size == 0:
        raise error_cls(f"{path.name}: generator efficiency curve is empty.")

    # Accept an explicit zero row for backward compatibility, but normalize the
    # internal representation to a single origin anchor.
    if np.isclose(rel[0], 0.0, atol=1e-10):
        rel = rel[1:]
        eff = eff[1:]

    if rel.size == 0:
        raise error_cls(
            f"{path.name}: generator efficiency curve must contain at least one positive-load point."
        )
    if np.any(rel <= 0.0) or np.any(rel > 1.0):
        raise error_cls(f"{path.name}: generator relative power points must lie in (0, 1].")
    if not np.isclose(rel[-1], 1.0, atol=1e-9):
        raise error_cls(f"{path.name}: the last generator relative-power point must be 1.0.")
    if np.any(np.diff(rel) <= 0.0):
        raise error_cls(
            f"{path.name}: generator partial-load curve must be strictly increasing after zero anchoring."
        )
    if np.any(eff <= 0.0):
        raise error_cls(
            f"{path.name}: generator efficiency values must be strictly positive for all positive-load points."
        )

    rel_full = np.concatenate(([0.0], rel))
    eff_full = np.concatenate(([0.0], eff))

    fuel_raw_full = np.zeros_like(rel_full, dtype=float)
    fuel_raw_full[1:] = rel / eff

    dx = np.diff(rel_full)
    if np.any(dx <= 0.0):
        raise error_cls(
            f"{path.name}: generator partial-load curve must be strictly increasing after zero anchoring."
        )
    if np.any(fuel_raw_full < -1e-10):
        raise error_cls(f"{path.name}: implied generator fuel curve contains negative values.")

    # Conservative LP-friendly surrogate:
    # enforce nondecreasing segment slopes by taking the cumulative maximum of
    # the raw segment slopes. This keeps the same support points, preserves
    # linearity, and guarantees fuel is never underestimated.
    raw_slopes = np.diff(fuel_raw_full) / dx
    if np.any(raw_slopes < -1e-8):
        raise error_cls(
            f"{path.name}: implied generator fuel curve decreases, which is not physical."
        )
    surrogate_slopes = np.maximum.accumulate(raw_slopes)
    fuel_surrogate_full = np.zeros_like(fuel_raw_full, dtype=float)
    fuel_surrogate_full[1:] = np.cumsum(surrogate_slopes * dx)

    return (
        rel_full.astype(float),
        eff_full.astype(float),
        fuel_raw_full.astype(float),
        fuel_surrogate_full.astype(float),
    )
