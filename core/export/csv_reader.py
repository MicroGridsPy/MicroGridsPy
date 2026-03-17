from __future__ import annotations

from pathlib import Path
import pandas as pd
import xarray as xr


def read_csv_2level_timeseries(path: Path) -> xr.DataArray:
    df = pd.read_csv(path, header=[0, 1])
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["scenario", "year"])

    if ("meta", "hour") not in df.columns:
        raise ValueError(f"{path.name}: missing required meta column ('meta','hour').")

    hour = pd.to_numeric(df[("meta", "hour")], errors="coerce")
    if hour.isna().any():
        raise ValueError(f"{path.name}: meta/hour contains non-numeric or NaN values.")

    df = df.drop(columns=[("meta", "hour")])
    df.index = hour.astype(int).to_numpy()
    df.index.name = "hour"
    df = df.apply(pd.to_numeric, errors="coerce")

    s = df.stack(["scenario", "year"]).rename("value")
    da = s.to_xarray().astype(float)
    return da.transpose("hour", "scenario", "year")


def read_csv_3level_timeseries(path: Path) -> xr.DataArray:
    df = pd.read_csv(path, header=[0, 1, 2])
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["scenario", "year", "resource"])

    meta_col = None
    for c in df.columns:
        if len(c) == 3 and str(c[0]) == "meta" and str(c[1]) == "hour":
            meta_col = c
            break
    if meta_col is None:
        cols_preview = list(df.columns[:5])
        raise ValueError(
            f"{path.name}: missing required meta/hour column. "
            f"Expected something like ('meta','hour','') but found columns like: {cols_preview}"
        )

    hour = pd.to_numeric(df[meta_col], errors="coerce")
    if hour.isna().any():
        raise ValueError(f"{path.name}: meta/hour contains non-numeric or NaN values.")

    df = df.drop(columns=[meta_col])
    df.index = hour.astype(int).to_numpy()
    df.index.name = "hour"
    df = df.apply(pd.to_numeric, errors="coerce")

    s = df.stack(["scenario", "year", "resource"]).rename("value")
    da = s.to_xarray().astype(float)
    return da.transpose("hour", "scenario", "year", "resource")

