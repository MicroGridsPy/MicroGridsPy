from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


CONVEXITY_TOL = 1e-8
MONOTONIC_TOL = 1e-10


class InputValidationError(RuntimeError):
    pass


def _validate_convex_curve(*, x: np.ndarray, y: np.ndarray, path: Path) -> tuple[np.ndarray, np.ndarray]:
    dx = np.diff(x)
    if np.any(dx <= MONOTONIC_TOL):
        raise InputValidationError(f"{path.name}: 'soc_pu' must be strictly increasing.")
    if np.any(y < -CONVEXITY_TOL):
        raise InputValidationError(
            f"{path.name}: calendar-fade coefficients must be non-negative."
        )
    slopes = np.diff(y) / dx
    if np.any(np.diff(slopes) < -CONVEXITY_TOL):
        raise InputValidationError(
            f"{path.name}: derived calendar-fade coefficient curve is not convex. "
            "Provide a curve with non-decreasing segment slopes."
        )
    intercepts = y[:-1] - slopes * x[:-1]
    return slopes.astype(float), intercepts.astype(float)


def load_battery_calendar_fade_curve_dataset(path: Path) -> xr.Dataset:
    """
    Parse a user-provided SoC-dependent battery calendar-fade curve.

    Interpretation:
    - `soc_pu` is the yearly average state of charge normalized by a fixed SoC reference.
    - Preferred column `calendar_fade_coefficient_per_year` gives the yearly fade
      coefficient applied to the configured yearly time increment.
    - Legacy column `calendar_fade_coefficient_per_step` is still accepted for
      backward compatibility and is interpreted using the same values.
    - The curve is represented as a convex piecewise-linear function of yearly average soc_pu.
    """
    if not path.exists():
        raise InputValidationError(f"Missing required battery calendar-fade curve file: {path}")

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise InputValidationError(f"Cannot read battery calendar-fade CSV {path}: {exc}") from exc

    coeff_column = None
    if "calendar_fade_coefficient_per_year" in df.columns:
        coeff_column = "calendar_fade_coefficient_per_year"
    elif "calendar_fade_coefficient_per_step" in df.columns:
        coeff_column = "calendar_fade_coefficient_per_step"
    required = ["soc_pu", coeff_column] if coeff_column is not None else ["soc_pu", "calendar_fade_coefficient_per_year"]
    missing = [c for c in required if c is not None and c not in df.columns]
    if coeff_column is None or missing:
        raise InputValidationError(
            f"{path.name}: missing required column(s) {missing}. Expected columns: "
            "['soc_pu', 'calendar_fade_coefficient_per_year'] (preferred) or "
            "['soc_pu', 'calendar_fade_coefficient_per_step'] (legacy)."
        )
    if len(df.index) < 2:
        raise InputValidationError(
            f"{path.name}: at least 2 rows are required to build the calendar-fade interpolation."
        )

    soc = pd.to_numeric(df["soc_pu"], errors="coerce").to_numpy(dtype=float)
    coeff = pd.to_numeric(df[coeff_column], errors="coerce").to_numpy(dtype=float)
    if np.isnan(soc).any() or np.isnan(coeff).any():
        raise InputValidationError(
            f"{path.name}: required columns contain missing or non-numeric values."
        )
    if np.any(soc < 0.0) or np.any(soc > 1.0):
        raise InputValidationError(f"{path.name}: 'soc_pu' must be within [0, 1].")

    if soc[0] > 0.0:
        soc = np.concatenate(([0.0], soc))
        coeff = np.concatenate(([coeff[0]], coeff))
    if not np.isclose(soc[-1], 1.0, atol=1e-9):
        raise InputValidationError(
            f"{path.name}: the last 'soc_pu' point must be 1.0 so the curve covers the full SoC range."
        )

    slope, intercept = _validate_convex_curve(x=soc, y=coeff, path=path)
    curve_point = xr.IndexVariable("battery_calendar_curve_point", np.arange(soc.size))
    segment = xr.IndexVariable("battery_calendar_segment", np.arange(soc.size - 1))

    ds = xr.Dataset(
        data_vars={
            "battery_calendar_soc_curve_pu": xr.DataArray(
                soc,
                coords={"battery_calendar_curve_point": curve_point},
                dims=("battery_calendar_curve_point",),
                attrs={"units": "pu_soc", "source_file": str(path)},
            ),
            "battery_calendar_fade_curve_coefficient_per_year": xr.DataArray(
                coeff,
                coords={"battery_calendar_curve_point": curve_point},
                dims=("battery_calendar_curve_point",),
                attrs={"units": "fade_per_year", "source_file": str(path)},
            ),
            "battery_calendar_fade_slope": xr.DataArray(
                slope,
                coords={"battery_calendar_segment": segment},
                dims=("battery_calendar_segment",),
                attrs={"units": "fade_per_year_per_pu_soc", "source_file": str(path)},
            ),
            "battery_calendar_fade_intercept": xr.DataArray(
                intercept,
                coords={"battery_calendar_segment": segment},
                dims=("battery_calendar_segment",),
                attrs={"units": "fade_per_year", "source_file": str(path)},
            ),
        }
    )
    ds.attrs["battery_calendar_curve_semantics"] = {
        "soc_pu": "battery yearly average state of charge normalized by the fixed calendar-fade SoC reference",
        "calendar_fade_coefficient_per_year": "calendar-ageing coefficient applied to the configured yearly time increment",
        "legacy_calendar_fade_coefficient_per_step": (
            "legacy alias still accepted on input; values are interpreted as yearly "
            "calendar-ageing coefficients in the updated multi-year surrogate"
        ),
    }
    ds.attrs["battery_calendar_curve_input_column"] = coeff_column
    return ds
