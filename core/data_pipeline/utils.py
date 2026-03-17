from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Sequence, Type

import json
import numpy as np
import pandas as pd
import xarray as xr
import yaml


def read_json_or_raise(path: Path, *, error_cls: Type[Exception] = RuntimeError) -> Dict[str, Any]:
    """Read and parse JSON file, raising error_cls on failure."""
    if not path.exists():
        raise error_cls(f"Missing required file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise error_cls(f"Cannot parse JSON: {path}\nerror: {e}")


def read_yaml_or_raise(path: Path, *, error_cls: Type[Exception] = RuntimeError) -> Dict[str, Any]:
    """Read and parse YAML file, raising error_cls on failure."""
    if not path.exists():
        raise error_cls(f"Missing required file: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise error_cls(f"Cannot parse YAML: {path}\nerror: {e}")


def read_csv_or_raise(
    path: Path,
    *,
    header: int | list[int],
    error_cls: Type[Exception] = RuntimeError,
) -> pd.DataFrame:
    """Read a CSV file with a fixed header shape, raising error_cls on failure."""
    if not path.exists():
        raise error_cls(f"Missing required file: {path}")
    try:
        return pd.read_csv(path, header=header)
    except Exception as e:
        raise error_cls(f"Cannot parse CSV: {path}\nerror: {e}")


def as_float(x: Any, *, name: str, default: float = 0.0, error_cls: Type[Exception] = RuntimeError) -> float:
    """Convert x to float, with default if None. Raise error_cls on failure."""
    if x is None:
        return float(default)
    try:
        return float(x)
    except Exception as e:
        raise error_cls(f"Invalid value for '{name}': {x!r} (error: {e})")


def as_float_or_nan(x: Any, *, name: str, error_cls: Type[Exception] = RuntimeError) -> float:
    """Convert x to float, or NaN if None. Raise error_cls on failure."""
    if x is None:
        return float("nan")
    try:
        return float(x)
    except Exception as e:
        raise error_cls(f"Invalid numeric value for '{name}': {x!r} (error: {e})")


def as_str(x: Any, *, name: str, default: str = "", error_cls: Type[Exception] = RuntimeError) -> str:
    """Convert x to str, with default if None. Raise error_cls on failure."""
    if x is None:
        return default
    try:
        return str(x)
    except Exception as e:
        raise error_cls(f"Invalid value for '{name}': {x!r} (error: {e})")


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
    error_cls: Type[Exception] = RuntimeError,
    context: str = "initialize_data",
) -> None:
    """Validate that an xarray dataset contains the required coordinates."""
    if not isinstance(sets, xr.Dataset):
        raise error_cls(f"{context} expects `sets` as an xarray.Dataset.")
    for coord_name in required:
        if coord_name not in sets.coords:
            raise error_cls(f"Sets missing required coord: '{coord_name}'")


def validate_hour_column(
    hour_values: Any,
    *,
    path: Path,
    period_coord: xr.DataArray,
    error_cls: Type[Exception] = RuntimeError,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Validate an hour column against the expected period coordinate.

    Returns:
      hour: integer numpy array from file
      expected: integer numpy array from period_coord
    """
    hour = pd.to_numeric(hour_values, errors="coerce")
    if hour.isna().any():
        raise error_cls(f"{path.name}: meta/hour contains non-numeric values.")

    hour = hour.astype(int).to_numpy()
    expected = np.asarray(period_coord.values, dtype=int)

    if hour.shape[0] != expected.shape[0]:
        raise error_cls(f"{path.name}: expected {expected.shape[0]} hours, got {hour.shape[0]}.")
    if not np.array_equal(hour, expected):
        mismatch_idx = int(np.where(hour != expected)[0][0])
        raise error_cls(
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

