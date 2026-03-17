from __future__ import annotations

import warnings

import xarray as xr
from core.data_pipeline.utils import validate_required_coords

class InputValidationError(RuntimeError):
    pass


def _validate_sets(sets: xr.Dataset) -> None:
    validate_required_coords(
        sets,
        required=("period", "scenario", "year", "inv_step", "resource"),
        error_cls=InputValidationError,
        context="initialize_data_dynamic",
    )


def _transpose_if_present(ds: xr.Dataset, var_name: str, dims: tuple[str, ...]) -> xr.Dataset:
    if var_name not in ds.data_vars:
        return ds
    da = ds[var_name]
    if all(d in da.dims for d in dims):
        ds[var_name] = da.transpose(*dims)
    return ds


def _align_contract_dims(ds: xr.Dataset) -> xr.Dataset:
    """
    Keep legacy variables/names/values but align core time-series dimensions
    to the data contract ordering used by the shared pipeline.
    """
    ds = _transpose_if_present(ds, "load_demand", ("period", "year", "scenario"))
    ds = _transpose_if_present(ds, "resource_availability", ("period", "year", "scenario", "resource"))
    ds = _transpose_if_present(ds, "grid_import_price", ("period", "year", "scenario"))
    ds = _transpose_if_present(ds, "grid_export_price", ("period", "year", "scenario"))
    ds = _transpose_if_present(ds, "grid_availability", ("period", "year", "scenario"))
    return ds


def _soft_checks(ds: xr.Dataset) -> None:
    required_core = ("load_demand", "resource_availability", "scenario_weight")
    missing = [v for v in required_core if v not in ds.data_vars]
    if missing:
        raise InputValidationError(
            f"Dynamic loader missing required core variables: {missing}"
        )

    # Soft warning only: settings should be present for downstream feature flags.
    settings = (ds.attrs or {}).get("settings", None)
    if not isinstance(settings, dict):
        warnings.warn("Dynamic loader returned dataset without attrs['settings'] dict.", stacklevel=2)


def load_multi_year_dataset(project_name: str, sets: xr.Dataset) -> xr.Dataset:
    """
    Shared multi-year dataset loader (minimal disruption).

    Behavior:
    - Reuses the current dynamic loader implementation.
    - Applies contract-oriented dim ordering for core time series variables.
    - Keeps names, values, attrs keys, and file/path expectations unchanged.
    """
    _validate_sets(sets)
    # Import lazily to avoid module import cycle:
    # core.multi_year_model.data -> core.data_pipeline.loader
    # -> core.data_pipeline.multi_year_loader -> core.multi_year_model.data
    from core.multi_year_model.data import _initialize_data_legacy

    ds = _initialize_data_legacy(project_name, sets)
    ds = _align_contract_dims(ds)
    _soft_checks(ds)
    return ds
