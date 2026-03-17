from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import xarray as xr

from core.export.plots import plot_8760, plot_daily_profile_band


@dataclass(frozen=True)
class TimeSeriesOption:
    variable: str
    label: str
    extra_dims: List[str]


def list_timeseries_options(ds: xr.Dataset) -> List[TimeSeriesOption]:
    """
    Return data variables that can be explored as time series.

    A plottable variable must include the canonical `period` dimension. Any
    additional non-scenario/year dims are exposed as extra selectors in the UI.
    """
    options: List[TimeSeriesOption] = []
    for name, da in ds.data_vars.items():
        if "period" not in da.dims:
            continue
        extra_dims = [d for d in da.dims if d not in {"period", "scenario", "year"}]
        label = name.replace("_", " ")
        if extra_dims:
            label = f"{label} ({', '.join(extra_dims)})"
        options.append(TimeSeriesOption(variable=name, label=label, extra_dims=extra_dims))

    options.sort(key=lambda item: item.variable)
    return options


def slice_timeseries(
    ds: xr.Dataset,
    *,
    variable: str,
    scenario: str | None = None,
    year: str | int | None = None,
    selectors: Dict[str, Any] | None = None,
) -> xr.DataArray:
    da = ds[variable]
    indexers: Dict[str, Any] = {}

    if scenario is not None and "scenario" in da.dims:
        indexers["scenario"] = scenario
    if year is not None and "year" in da.dims:
        indexers["year"] = year

    for dim, value in (selectors or {}).items():
        if dim in da.dims:
            indexers[dim] = value

    return da.sel(indexers)


def compute_series_stats(da: xr.DataArray) -> Dict[str, float | int | None]:
    values = np.asarray(da.values, dtype=float).reshape(-1)
    if values.size == 0:
        return {
            "n": 0,
            "missing_values": 0,
            "min": None,
            "max": None,
            "mean": None,
            "sum": None,
        }

    return {
        "n": int(values.size),
        "missing_values": int(np.isnan(values).sum()),
        "min": float(np.nanmin(values)),
        "max": float(np.nanmax(values)),
        "mean": float(np.nanmean(values)),
        "sum": float(np.nansum(values)),
    }


def build_timeseries_figures(da: xr.DataArray, *, title_prefix: str, y_label: str):
    values = np.asarray(da.values, dtype=float).reshape(-1)
    fig_hourly = plot_8760(values, title=f"{title_prefix} - hourly profile", y_label=y_label)
    fig_daily = plot_daily_profile_band(
        values,
        title=f"{title_prefix} - average daily profile",
        y_label=y_label,
    )
    return fig_hourly, fig_daily
