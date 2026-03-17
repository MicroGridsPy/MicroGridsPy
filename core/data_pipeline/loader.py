from __future__ import annotations

from typing import Literal

import xarray as xr

from core.data_pipeline.utils import as_str, validate_required_coords
from core.data_pipeline.multi_year_loader import load_multi_year_dataset
from core.data_pipeline.typical_year_loader import (
    load_typical_year_dataset,
)

class InputValidationError(RuntimeError):
    pass


def _coerce_sets(sets: dict | xr.Dataset) -> xr.Dataset:
    """
    Coerce `sets` to xarray.Dataset for compatibility with existing loaders.

    Notes:
    - Existing call sites currently pass xr.Dataset.
    - This helper keeps signature flexibility while preserving error style.
    """
    if isinstance(sets, xr.Dataset):
        return sets

    if isinstance(sets, dict):
        # Best effort for future call-sites that may pass {"coords": {...}}.
        if "coords" in sets and isinstance(sets["coords"], dict):
            try:
                return xr.Dataset(coords=sets["coords"])
            except Exception as e:
                raise InputValidationError(
                    f"initialize_data expects `sets` as an xarray.Dataset. Could not coerce dict['coords'] to Dataset: {e}"
                )

    raise InputValidationError("initialize_data expects `sets` as an xarray.Dataset.")


def _validate_sets_for_mode(sets: xr.Dataset, mode: str) -> None:
    required = ("period", "scenario", "year", "inv_step", "resource") if mode == "multi_year" else ("period", "scenario")
    validate_required_coords(
        sets,
        required=required,
        error_cls=InputValidationError,
        context="initialize_data_dynamic" if mode == "multi_year" else "initialize_data",
    )


def load_project_dataset(
    project_name: str,
    sets: dict,
    mode: Literal["typical_year", "multi_year"],
) -> xr.Dataset:
    """
    Shared project dataset loader (parallel implementation).

    Mode behavior:
    - typical_year: delegates to the current typical-year loader for strict parity.
    - multi_year: delegates to the current multi-year shared loader.
    """
    mode_s = as_str(mode, name="mode", default="", error_cls=ValueError)

    sets_ds = _coerce_sets(sets)

    if mode_s == "typical_year":
        _validate_sets_for_mode(sets_ds, mode_s)
        return load_typical_year_dataset(project_name, sets_ds)

    if mode_s == "multi_year":
        _validate_sets_for_mode(sets_ds, mode_s)
        return load_multi_year_dataset(project_name, sets_ds)

    raise ValueError(f"Unsupported mode: {mode!r}. Expected 'typical_year' or 'multi_year'.")
