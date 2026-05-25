from __future__ import annotations

import numpy as np
import xarray as xr


class InputValidationError(RuntimeError):
    pass


def year_ordinal(sets: xr.Dataset) -> xr.DataArray:
    year = sets.coords["year"]
    return xr.DataArray(
        np.arange(1, int(year.size) + 1, dtype=float),
        coords={"year": year},
        dims=("year",),
        name="year_ordinal",
    )


def inv_step_start_ordinal(sets: xr.Dataset) -> xr.DataArray:
    year_vals = [str(v) for v in sets.coords["year"].values.tolist()]
    inv_vals = [str(v) for v in sets["inv_step_start_year"].values.tolist()]
    idx_map = {y: i + 1 for i, y in enumerate(year_vals)}

    out = []
    for v in inv_vals:
        if v not in idx_map:
            raise InputValidationError(
                f"inv_step_start_year '{v}' not found in sets.year labels {year_vals}"
            )
        out.append(float(idx_map[v]))

    return xr.DataArray(
        out,
        coords={"inv_step": sets.coords["inv_step"]},
        dims=("inv_step",),
        name="inv_step_start_ordinal",
    )


def service_years_matrix(sets: xr.Dataset) -> xr.DataArray:
    y_ord = year_ordinal(sets)
    start_ord = inv_step_start_ordinal(sets)
    return (y_ord - start_ord + 1.0).transpose("inv_step", "year")


def map_inv_step_to_year(
    sets: xr.Dataset,
    da: xr.DataArray,
    *,
    name: str = "parameter",
) -> xr.DataArray:
    """
    Expand a step-indexed parameter into a year-indexed parameter using
    `sets.year_inv_step`.

    Example:
      da(inv_step, resource) -> da(year, resource)

    Any additional dimensions (for example `scenario` or `resource`) are
    preserved. Parameters that do not carry `inv_step` are returned unchanged.
    """
    if "inv_step" not in da.dims:
        return da
    if "year" not in sets.coords:
        raise InputValidationError(f"Cannot map '{name}' from inv_step to year: missing sets.year coord.")
    if "year_inv_step" not in sets:
        raise InputValidationError(f"Cannot map '{name}' from inv_step to year: missing sets.year_inv_step mapping.")

    year = sets.coords["year"]
    year_inv_step = sets["year_inv_step"].sel(year=year)

    try:
        mapped = da.sel(inv_step=year_inv_step)
    except Exception as exc:
        raise InputValidationError(
            f"Cannot map '{name}' from inv_step to year using sets.year_inv_step."
        ) from exc

    mapped = mapped.assign_coords(year=year)

    ordered_dims = []
    for dim in da.dims:
        if dim == "inv_step":
            ordered_dims.append("year")
        else:
            ordered_dims.append(dim)
    for dim in mapped.dims:
        if dim not in ordered_dims:
            ordered_dims.append(dim)
    return mapped.transpose(*ordered_dims)


def replacement_active_mask(sets: xr.Dataset) -> xr.DataArray:
    svc = service_years_matrix(sets)
    return (svc >= 1.0).astype(float)


def replacement_cycle_age(sets: xr.Dataset, lifetime_years: xr.DataArray | float) -> xr.DataArray:
    svc = service_years_matrix(sets)
    lt = xr.DataArray(lifetime_years)
    active = svc >= 1.0
    completed_cycles = xr.where(active, np.floor((svc - 1.0) / lt), 0.0)
    age = svc - completed_cycles * lt
    return xr.where(active, age, 0.0)


def replacement_commission_mask(sets: xr.Dataset, lifetime_years: xr.DataArray | float) -> xr.DataArray:
    active = replacement_active_mask(sets)
    age = replacement_cycle_age(sets, lifetime_years)
    return xr.where((active > 0.0) & (np.abs(age - 1.0) < 1e-9), 1.0, 0.0)


def repeating_degradation_factor(
    sets: xr.Dataset,
    lifetime_years: xr.DataArray | float,
    degradation_rate: xr.DataArray | None,
) -> xr.DataArray:
    active = replacement_active_mask(sets)
    if degradation_rate is None:
        return active

    rate = xr.DataArray(degradation_rate).clip(min=0.0)
    age = replacement_cycle_age(sets, lifetime_years)
    # Capacity is at nominal level in the commissioning year, then degrades within each cycle.
    factor = (1.0 - rate) ** (age - 1.0)
    return xr.where(active > 0.0, factor, 0.0)


def discounted_annuity_tail_memo(
    sets: xr.Dataset,
    annuity: xr.DataArray,
    lifetime_years: xr.DataArray | float,
    social_discount_rate: float,
) -> xr.DataArray:
    """
    Reporting-only memo: discounted value of the remaining annuity stream
    beyond the planning horizon for the last active replacement cycle of each
    cohort.

    This helper is intentionally aligned with the annuity-based accounting used
    by the current multi-year objective. It is not a classical salvage/book-
    value formula and it is not included in the optimization objective.
    """
    lt = xr.DataArray(lifetime_years)
    age_h = replacement_cycle_age(sets, lt).isel(year=-1, drop=True)
    active_h = replacement_active_mask(sets).isel(year=-1, drop=True)
    remaining = xr.where(active_h > 0.0, np.maximum(np.floor(lt - age_h), 0.0), 0.0)

    rs = float(social_discount_rate)
    H = float(int(sets.coords["year"].size))
    if abs(rs) < 1e-12:
        tail = annuity * remaining
    else:
        tail = annuity * (1.0 - (1.0 + rs) ** (-remaining)) / rs
    return tail / ((1.0 + rs) ** H)
