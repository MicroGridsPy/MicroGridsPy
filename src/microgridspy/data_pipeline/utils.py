from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

from microgridspy.errors import InputValidationError
from microgridspy.io.csv_format import read_csv_with_format


def read_csv_or_raise(
    path: Path,
    *,
    header: int | list[int],
    csv_format: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Read a CSV file with a fixed header shape."""
    if not path.exists():
        raise InputValidationError(f"Missing required file: {path}")
    try:
        return read_csv_with_format(path, header=header, csv_format=csv_format)
    except Exception as e:
        raise InputValidationError(f"Cannot parse CSV: {path}\nerror: {e}")


def as_float(x: Any, *, name: str, default: float = 0.0) -> float:
    """Convert x to float, with default if None."""
    if x is None:
        return float(default)
    try:
        return float(x)
    except Exception as e:
        raise InputValidationError(f"Invalid value for '{name}': {x!r} (error: {e})")


def as_float_or_nan(x: Any, *, name: str) -> float:
    """Convert x to float, or NaN if None."""
    if x is None:
        return float("nan")
    try:
        return float(x)
    except Exception as e:
        raise InputValidationError(f"Invalid numeric value for '{name}': {x!r} (error: {e})")


def as_str(x: Any, *, name: str, default: str = "") -> str:
    """Convert x to str, with default if None."""
    if x is None:
        return default
    try:
        return str(x)
    except Exception as e:
        raise InputValidationError(f"Invalid value for '{name}': {x!r} (error: {e})")


def normalize_weights(weights: Sequence[float], n: int) -> list[float]:
    """Normalize a list of weights to sum to 1.0 over n items."""
    if n <= 0:
        return [1.0]
    w = [float(x) for x in (weights or [])]
    if len(w) != n:
        w = [1.0 / n] * n
    s = float(sum(w))
    if s <= 0:
        return [1.0 / n] * n
    return [wi / s for wi in w]


def coord_labels(coord: xr.DataArray) -> list[str]:
    """Return coordinate labels coerced to strings."""
    return [str(v) for v in coord.values.tolist()]


def validate_required_coords(
    sets: xr.Dataset,
    *,
    required: Sequence[str],
    context: str = "initialize_data",
) -> None:
    """Validate that an xarray dataset contains the required coordinates."""
    if not isinstance(sets, xr.Dataset):
        raise InputValidationError(f"{context} expects `sets` as an xarray.Dataset.")
    for coord_name in required:
        if coord_name not in sets.coords:
            raise InputValidationError(f"Sets missing required coord: '{coord_name}'")


def validate_hour_column(
    hour_values: Any,
    *,
    path: Path,
    period_coord: xr.DataArray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Validate an hour column against the expected period coordinate.

    Returns:
      hour: integer numpy array from file
      expected: integer numpy array from period_coord
    """
    hour = pd.to_numeric(hour_values, errors="coerce")
    if hour.isna().any():
        raise InputValidationError(f"{path.name}: meta/hour contains non-numeric values.")

    hour = hour.astype(int).to_numpy()
    expected = np.asarray(period_coord.values, dtype=int)

    if hour.shape[0] != expected.shape[0]:
        raise InputValidationError(
            f"{path.name}: expected {expected.shape[0]} hours, got {hour.shape[0]}."
        )
    if not np.array_equal(hour, expected):
        mismatch_idx = int(np.where(hour != expected)[0][0])
        raise InputValidationError(
            f"{path.name}: meta/hour does not match sets.period. "
            f"First mismatch at row {mismatch_idx}: file={hour[mismatch_idx]} vs sets={expected[mismatch_idx]}."
        )

    return hour, expected


def coerce_numeric_array(values: Any) -> np.ndarray:
    """Best-effort conversion of an array-like to a numeric numpy array with NaNs for invalid entries."""
    return pd.DataFrame(values).apply(pd.to_numeric, errors="coerce").to_numpy()


def broadcast_to_scenario(value: xr.DataArray, scenario_coord: xr.DataArray) -> xr.DataArray:
    """Broadcast a scalar DataArray to scenario dimension."""
    if value.ndim != 0:
        return value
    return xr.DataArray(
        np.full((scenario_coord.size,), float(value.values)),
        coords={"scenario": scenario_coord},
        dims=("scenario",),
        name=value.name,
        attrs=dict(value.attrs or {}),
    )


def merge_optional_datasets(
    *datasets: xr.Dataset | None,
    compat: str = "override",
    join: str | None = None,
) -> xr.Dataset:
    """Merge non-null datasets while preserving xarray merge options."""
    present = [ds for ds in datasets if ds is not None]
    if not present:
        return xr.Dataset()
    kwargs: dict[str, Any] = {"compat": compat}
    if join is not None:
        kwargs["join"] = join
    return xr.merge(present, **kwargs)


def finite_nonnegative_scalar_limit(
    value: Any,
    *,
    name: str,
) -> float | None:
    """
    Return the first finite scalar limit if present and validate it is non-negative.

    None means the limit is inactive because no finite value was provided.
    """
    values = np.asarray(value, dtype=float).reshape(-1)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return None
    limit = float(values[0])
    if limit < 0.0:
        raise InputValidationError(f"{name} must be non-negative when provided.")
    return limit
