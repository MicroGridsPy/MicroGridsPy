"""Shared financial formulas.

These are used both when *building* the objective and when *reporting* the solved
costs, so they live in one place: if the optimisation and the results tables
computed an annuity differently, the number a user reads would not be the number
the model minimised.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

#: Rates below this magnitude are treated as zero. At exactly r = 0 the annuity
#: formula is 0/0, and for very small r it is numerically unstable, so both cases
#: fall back to the undiscounted limit 1/n.
ZERO_RATE_TOLERANCE = 1e-12


def crf(rate: xr.DataArray | float, lifetime: xr.DataArray | float) -> xr.DataArray | float:
    """Capital recovery factor — the annuity that repays 1 unit of capital.

    ``CRF = r (1+r)^n / ((1+r)^n - 1)``, with the limit ``1/n`` as ``r -> 0``.

    Accepts plain floats or `xarray.DataArray` and returns the same kind, so the
    same function serves the linopy objective and the pandas results tables.

    Args:
        rate: discount rate or WACC per period, as a decimal (0.08 is 8%).
        lifetime: number of periods to repay over. Must be positive; a
            non-positive lifetime has no defined annuity and yields ``nan``.
    """
    if isinstance(rate, xr.DataArray) or isinstance(lifetime, xr.DataArray):
        r = xr.DataArray(rate)
        n = xr.DataArray(lifetime)
        compound = (1.0 + r) ** n
        annuity = xr.where(
            np.abs(r) < ZERO_RATE_TOLERANCE,
            1.0 / n,
            (r * compound) / (compound - 1.0),
        )
        return xr.where(n > 0.0, annuity, np.nan)

    r = float(rate)
    n = float(lifetime)
    if n <= 0.0:
        return float("nan")
    if abs(r) < ZERO_RATE_TOLERANCE:
        return 1.0 / n
    compound = (1.0 + r) ** n
    return (r * compound) / (compound - 1.0)
