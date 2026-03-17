from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import xarray as xr

from core.data_pipeline.loader import load_project_dataset
from core.data_pipeline.typical_year_loader import regenerate_grid_availability_typical_year
from core.export.yaml_reader import read_yaml
from core.io.utils import project_paths
from core.multi_year_model.data import regenerate_grid_availability_dynamic
from core.multi_year_model.sets import initialize_sets as initialize_multi_year_sets
from core.typical_year_model.sets import initialize_sets as initialize_typical_year_sets
from core.visualization.page_helpers import read_json_file, resolve_active_project_from_session
from core.visualization.input_plots import (
    build_timeseries_figures,
    compute_series_stats,
    list_timeseries_options,
    slice_timeseries,
)


REQUIRED_INPUTS: Dict[str, str] = {
    "formulation.json": "Project formulation and workflow settings.",
    "load_demand.csv": "Hourly demand time series template.",
    "resource_availability.csv": "Hourly renewable resource availability time series.",
    "renewables.yaml": "Renewable technology techno-economic parameters.",
    "battery.yaml": "Battery techno-economic parameters.",
    "generator.yaml": "Generator and fuel techno-economic parameters.",
}

OPTIONAL_INPUTS: Dict[str, str] = {
    "generator_efficiency_curve.csv": "Optional partial-load efficiency curve for the generator.",
    "grid.yaml": "Grid connection parameters for on-grid projects.",
    "grid_import_price.csv": "Hourly import tariff for on-grid projects.",
    "grid_export_price.csv": "Hourly export tariff when export is enabled.",
    "grid_availability.csv": "Backend-generated grid availability matrix.",
}

REQUIRED_SETTINGS_KEYS = [
    "project_name",
    "formulation",
    "unit_commitment",
    "multi_scenario",
    "resources",
    "optimization_constraints",
    "inputs_loaded",
    "generator",
    "fuel",
    "grid",
]

STATIC_PARAMETER_METADATA: Dict[str, Dict[str, str]] = {
    "scenario_weight": {
        "unit": "share",
        "description": "Probability weight assigned to each scenario.",
        "source": "formulation.json",
    },
    "min_renewable_penetration": {
        "unit": "share",
        "description": "Minimum renewable penetration target enforced by the optimization model.",
        "source": "formulation.json",
    },
    "max_lost_load_fraction": {
        "unit": "share",
        "description": "Maximum allowed fraction of unmet demand.",
        "source": "formulation.json",
    },
    "lost_load_cost_per_kwh": {
        "unit": "currency_per_kWh",
        "description": "Penalty or social cost assigned to unserved energy.",
        "source": "formulation.json",
    },
    "land_availability_m2": {
        "unit": "m2",
        "description": "Land availability limit used for renewable siting constraints.",
        "source": "formulation.json",
    },
    "emission_cost_per_kgco2e": {
        "unit": "currency_per_kgCO2e",
        "description": "Cost applied to scope 1, scope 2, and scope 3 emissions when enabled.",
        "source": "formulation.json",
    },
    "load_demand": {
        "unit": "kWh_per_hour",
        "description": "Hourly electricity demand time series.",
        "source": "load_demand.csv",
    },
    "resource_availability": {
        "unit": "capacity_factor",
        "description": "Hourly renewable resource availability time series.",
        "source": "resource_availability.csv",
    },
    "grid_import_price": {
        "unit": "currency_per_kWh",
        "description": "Hourly electricity import tariff from the grid.",
        "source": "grid_import_price.csv",
    },
    "grid_export_price": {
        "unit": "currency_per_kWh",
        "description": "Hourly electricity export tariff to the grid.",
        "source": "grid_export_price.csv",
    },
    "grid_availability": {
        "unit": "binary",
        "description": "Hourly grid availability matrix generated from outage inputs.",
        "source": "grid.yaml",
    },
    "grid_renewable_share": {
        "unit": "share",
        "description": "Share of delivered imported electricity counted as renewable in policy metrics.",
        "source": "grid.yaml",
    },
    "grid_emissions_factor_kgco2e_per_kwh": {
        "unit": "kgCO2e_per_kWh",
        "description": "Scope 2 emissions factor applied to delivered imported electricity.",
        "source": "grid.yaml",
    },
    "curve_relative_power_output": {
        "unit": "share",
        "description": "Generator efficiency-curve support points in relative output terms.",
        "source": "generator_efficiency_curve.csv",
    },
    "curve_efficiency": {
        "unit": "-",
        "description": "Generator efficiency-curve values corresponding to relative power output points.",
        "source": "generator_efficiency_curve.csv",
    },
}


def _build_file_table(paths, files: Dict[str, str]) -> pd.DataFrame:
    rows = []
    for name, description in files.items():
        rows.append(
            {
                "file": name,
                "status": "found" if (paths.inputs_dir / name).exists() else "missing",
                "description": description,
            }
        )
    return pd.DataFrame(rows)


def _required_missing_for_configuration(formulation: Dict[str, Any], paths) -> List[str]:
    missing = [name for name in REQUIRED_INPUTS if not (paths.inputs_dir / name).exists()]

    if bool(formulation.get("on_grid", False)):
        for name in ("grid.yaml", "grid_import_price.csv"):
            if not (paths.inputs_dir / name).exists():
                missing.append(name)
        if bool(formulation.get("grid_allow_export", False)) and not (paths.inputs_dir / "grid_export_price.csv").exists():
            missing.append("grid_export_price.csv")

    return sorted(set(missing))


def _load_sets_and_dataset(project_name: str, formulation: Dict[str, Any]) -> Tuple[xr.Dataset, xr.Dataset, str]:
    formulation_mode = str(formulation.get("core_formulation", "steady_state")).strip()
    loader_mode = "multi_year" if formulation_mode == "dynamic" else "typical_year"

    if loader_mode == "multi_year":
        sets = initialize_multi_year_sets(project_name)
    else:
        sets = initialize_typical_year_sets(project_name)

    ds = load_project_dataset(project_name, sets, mode=loader_mode)
    return sets, ds, loader_mode


def _build_project_summary(formulation: Dict[str, Any]) -> str:
    formulation_mode = str(formulation.get("core_formulation", "steady_state")).strip()
    mode_label = "Typical-year" if formulation_mode == "steady_state" else "Multi-year"
    system_label = "On-grid" if bool(formulation.get("on_grid", False)) else "Off-grid"
    export_label = "export enabled" if bool(formulation.get("grid_allow_export", False)) else None
    sizing_label = "Discrete sizing" if bool(formulation.get("unit_commitment", False)) else "Continuous sizing"
    ms = formulation.get("multi_scenario", {}) or {}
    n_scen = int(ms.get("n_scenarios", 1) or 1)
    scenario_label = f"Multi-scenario ({n_scen})" if bool(ms.get("enabled", False)) else "Single scenario"
    parts = [mode_label, system_label]
    if export_label:
        parts.append(export_label)
    parts.extend([sizing_label, scenario_label])

    if formulation_mode == "dynamic":
        horizon = formulation.get("time_horizon_years")
        if horizon:
            parts.append(f"{int(horizon)}-year horizon")
        if bool(formulation.get("capacity_expansion", False)):
            parts.append("capacity expansion")

    enforcement = ((formulation.get("optimization_constraints", {}) or {}).get("enforcement") or "").strip()
    if enforcement:
        parts.append(f"{enforcement} constraints")

    return " | ".join(parts)


def _load_yaml_parameter_metadata(paths) -> Dict[str, Dict[str, str]]:
    metadata: Dict[str, Dict[str, str]] = {}
    yaml_files = ("renewables.yaml", "battery.yaml", "generator.yaml", "grid.yaml")
    for name in yaml_files:
        path = paths.inputs_dir / name
        if not path.exists():
            continue
        try:
            payload = read_yaml(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        meta = payload.get("meta", {}) or {}
        units = meta.get("units", {}) or {}
        description_block = meta.get("description", {}) or {}
        parameters = description_block.get("parameters", {}) if isinstance(description_block, dict) else {}
        for key in set(units.keys()) | set(parameters.keys()):
            metadata[key] = {
                "unit": str(units.get(key, "")) if units.get(key) is not None else "",
                "description": str(parameters.get(key, "")) if parameters.get(key) is not None else "",
                "source": name,
            }
    return metadata


def _parameter_summary(ds: xr.Dataset, paths) -> pd.DataFrame:
    yaml_metadata = _load_yaml_parameter_metadata(paths)
    rows = []
    for name, da in ds.data_vars.items():
        meta = yaml_metadata.get(name, STATIC_PARAMETER_METADATA.get(name, {}))
        rows.append(
            {
                "parameter": name,
                "dims": ", ".join(da.dims) if da.dims else "(scalar)",
                "dtype": str(da.dtype),
                "unit": meta.get("unit", ""),
                "value": _format_parameter_value(da),
                "source": meta.get("source", "dataset"),
            }
        )
    return pd.DataFrame(rows).sort_values("parameter").reset_index(drop=True)


def _coordinates_summary(ds: xr.Dataset) -> pd.DataFrame:
    rows = []
    for name, coord in ds.coords.items():
        preview = ", ".join(map(str, coord.values[:5]))
        if coord.size > 5:
            preview += " ..."
        rows.append(
            {
                "coordinate": name,
                "size": int(coord.size),
                "dims": ", ".join(coord.dims) if coord.dims else "(scalar)",
                "preview": preview,
            }
        )
    return pd.DataFrame(rows)


def _format_scalar_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, (np.floating, float)):
        return f"{float(value):.6g}"
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.bool_, bool)):
        return "true" if bool(value) else "false"
    return str(value)


def _format_parameter_value(da: xr.DataArray) -> str:
    if da.ndim == 0:
        try:
            return _format_scalar_value(da.values.item())
        except Exception:
            return _format_scalar_value(da.values)

    values = np.asarray(da.values)
    flat = values.reshape(-1)
    preview = ", ".join(_format_scalar_value(v) for v in flat[:6])
    if flat.size > 6:
        preview += ", ..."

    if da.ndim == 1 and da.sizes[da.dims[0]] <= 6:
        dim = da.dims[0]
        labels = [str(v) for v in da.coords[dim].values.tolist()]
        labelled = ", ".join(
            f"{label}={_format_scalar_value(value)}"
            for label, value in zip(labels, flat.tolist())
        )
        return f"[{labelled}]"

    return f"array{tuple(int(v) for v in da.shape)} [{preview}]"


def _optimization_constraints_summary(ds: xr.Dataset) -> pd.DataFrame:
    settings = (ds.attrs or {}).get("settings", {}) or {}
    constraints = settings.get("optimization_constraints", {}) or {}
    if not isinstance(constraints, dict):
        constraints = {}

    descriptions = {
        "enforcement": "Constraint enforcement mode across scenarios.",
        "min_renewable_penetration": "Minimum renewable penetration target.",
        "max_lost_load_fraction": "Maximum allowed unmet demand share.",
        "lost_load_cost_per_kwh": "Penalty applied to unserved energy.",
        "land_availability_m2": "Maximum land available for renewable siting.",
        "emission_cost_per_kgco2e": "Carbon cost included in the objective function.",
    }
    units = {
        "enforcement": "",
        "min_renewable_penetration": "share",
        "max_lost_load_fraction": "share",
        "lost_load_cost_per_kwh": "currency_per_kWh",
        "land_availability_m2": "m2",
        "emission_cost_per_kgco2e": "currency_per_kgCO2e",
    }
    constraint_keys = [
        "enforcement",
        "min_renewable_penetration",
        "max_lost_load_fraction",
        "lost_load_cost_per_kwh",
        "land_availability_m2",
        "emission_cost_per_kgco2e",
    ]

    rows = []
    for key in constraint_keys:
        if key in ds.data_vars:
            value = _format_parameter_value(ds[key])
        else:
            value = constraints.get(key)
        if value is None:
            continue
        rows.append(
            {
                "constraint": key,
                "value": value if isinstance(value, str) else _format_scalar_value(value),
                "unit": units.get(key, ""),
                "description": descriptions.get(key, ""),
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def _soft_checks(ds: xr.Dataset) -> List[Tuple[str, str]]:
    checks: List[Tuple[str, str]] = []

    if "scenario_weight" in ds:
        wsum = float(np.sum(ds["scenario_weight"].values.astype(float)))
        if np.isclose(wsum, 1.0, atol=1e-8):
            checks.append(("success", f"`scenario_weight` sums to 1.0 (sum={wsum:.8f})."))
        else:
            checks.append(("warning", f"`scenario_weight` does not sum to 1.0 (sum={wsum:.8f})."))
    else:
        checks.append(("error", "`scenario_weight` variable is missing."))

    if "load_demand" in ds:
        load = np.asarray(ds["load_demand"].values, dtype=float)
        if np.nanmin(load) < 0:
            checks.append(("warning", f"`load_demand` contains negative values (min={np.nanmin(load):.6g})."))
        else:
            checks.append(("success", "`load_demand` is non-negative."))

    if "resource_availability" in ds:
        res = np.asarray(ds["resource_availability"].values, dtype=float)
        mn = float(np.nanmin(res))
        mx = float(np.nanmax(res))
        if mn < 0 or mx > 1:
            checks.append(("warning", f"`resource_availability` falls outside [0, 1] (min={mn:.6g}, max={mx:.6g})."))
        else:
            checks.append(("success", "`resource_availability` is within [0, 1]."))

    settings = (ds.attrs or {}).get("settings", {})
    missing_settings = [key for key in REQUIRED_SETTINGS_KEYS if key not in settings]
    if missing_settings:
        checks.append(("warning", f"Missing recommended settings keys: {', '.join(missing_settings)}."))
    else:
        checks.append(("success", "Required settings keys are present."))

    return checks


def _render_soft_check_warnings(ds: xr.Dataset) -> None:
    for level, message in _soft_checks(ds):
        if level == "warning":
            st.warning(message)
        elif level == "error":
            st.error(message)


def _render_file_section(project_root: Path, formulation: Dict[str, Any], paths) -> bool:
    st.subheader("Required Input Files")
    st.caption(f"Check that the active project contains the inputs required to construct the canonical dataset. Project path: `{project_root}`")

    required_df = _build_file_table(paths, REQUIRED_INPUTS)
    optional_df = _build_file_table(paths, OPTIONAL_INPUTS)
    missing = _required_missing_for_configuration(formulation, paths)

    present_required = int((required_df["status"] == "found").sum())
    st.metric("Required files present", f"{present_required}/{len(REQUIRED_INPUTS)}")

    st.markdown("**Required files**")
    st.dataframe(required_df, width="stretch", hide_index=True)

    st.markdown("**Optional files**")
    st.dataframe(optional_df, width="stretch", hide_index=True)

    if missing:
        st.error(f"Dataset cannot be constructed yet. Missing configuration-dependent inputs: {', '.join(missing)}")
        return False

    st.success("All configuration-dependent inputs required for dataset construction are present.")
    return True


def _render_dataset_section(ds: xr.Dataset, loader_mode: str, paths) -> None:
    st.subheader("Dataset Summary")
    st.caption("Load the canonical dataset through the shared pipeline and inspect its structure before optimization.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Loader mode", loader_mode)
    c2.metric("Dimensions", len(ds.sizes))
    c3.metric("Parameters", len(ds.data_vars))

    settings = (ds.attrs or {}).get("settings", {})
    if loader_mode == "multi_year" and isinstance(settings, dict):
        st.markdown("**Multi-Year Settings**")
        horizon_years = ds.sizes.get("year", 0)
        raw_discount = settings.get("social_discount_rate", None)
        try:
            discount_pct = f"{100.0 * float(raw_discount):.2f}%"
        except Exception:
            discount_pct = "n/a"

        inv_steps = settings.get("investment_steps", None)
        if isinstance(inv_steps, list):
            n_steps = len(inv_steps)
        else:
            n_steps = int(ds.sizes.get("inv_step", 0))

        c4, c5, c6 = st.columns(3)
        c4.metric("Time horizon", f"{int(horizon_years)} years")
        c5.metric("Investment steps", str(int(n_steps)))
        c6.metric("Social discount rate", discount_pct)

    st.markdown("**Coordinates**")
    st.dataframe(_coordinates_summary(ds), width="stretch", hide_index=True)

    st.markdown("**Parameters**")
    st.dataframe(_parameter_summary(ds, paths), width="stretch", hide_index=True)

    constraints_df = _optimization_constraints_summary(ds)
    if not constraints_df.empty:
        st.markdown("**Optimization System Constraints**")
        st.caption("Project-level optimization constraints loaded from `formulation.json` and attached to the canonical dataset metadata.")
        st.dataframe(constraints_df, width="stretch", hide_index=True)

    with st.expander("Dataset metadata", expanded=False):
        st.json(dict(ds.attrs or {}))

    _render_soft_check_warnings(ds)


def _render_grid_controls(project_name: str, formulation: Dict[str, Any], ds: xr.Dataset, paths) -> None:
    formulation_mode = str(formulation.get("core_formulation", "steady_state")).strip()
    if formulation_mode not in {"steady_state", "dynamic"}:
        return
    if not bool(formulation.get("on_grid", False)):
        return

    st.subheader("Grid Availability")
    st.caption(
        "`grid_availability.csv` is a derived artifact generated from `grid.yaml` during dataset loading. "
        "Edit outage parameters below, then regenerate to refresh the matrix."
    )

    grid_yaml_path = paths.inputs_dir / "grid.yaml"
    grid_csv_path = paths.inputs_dir / "grid_availability.csv"
    try:
        grid_payload = read_yaml(grid_yaml_path)
    except Exception as exc:
        st.error(f"Could not read grid configuration: {exc}")
        return

    by_scenario = ((grid_payload.get("grid", {}) or {}).get("by_scenario", {}) or {})
    rows = []
    for scenario, block in by_scenario.items():
        line = (block.get("line", {}) or {})
        outages = (block.get("outages", {}) or {})
        row = {
            "scenario": scenario,
            "line_capacity_kw": line.get("capacity_kw"),
            "transmission_efficiency": line.get("transmission_efficiency"),
            "renewable_share": line.get("renewable_share", 0.0),
            "emissions_factor_kgco2e_per_kwh": line.get("emissions_factor_kgco2e_per_kwh", 0.0),
            "avg_outages_per_year": outages.get("average_outages_per_year"),
            "avg_outage_duration_minutes": outages.get("average_outage_duration_minutes"),
            "outage_scale_od_hours": outages.get("outage_scale_od_hours"),
            "outage_shape_od": outages.get("outage_shape_od"),
            "outage_seed": outages.get("outage_seed", 0),
        }
        if formulation_mode == "dynamic":
            row["first_year_connection"] = block.get("first_year_connection")
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.caption(f"Derived file: `{grid_csv_path.name}`")
    if grid_csv_path.exists():
        st.caption(f"Last updated: {pd.Timestamp(grid_csv_path.stat().st_mtime, unit='s')}")
    if st.button("Regenerate grid availability from grid.yaml", key=f"regen_grid_{formulation_mode}", type="primary"):
        try:
            if formulation_mode == "dynamic":
                sets = initialize_multi_year_sets(project_name)
                regenerate_grid_availability_dynamic(project_name=project_name, sets=sets)
            else:
                sets = initialize_typical_year_sets(project_name)
                regenerate_grid_availability_typical_year(project_name=project_name, sets=sets)
            st.success("grid_availability.csv regenerated from grid.yaml.")
            st.rerun()
        except Exception as exc:
            st.error(f"Regeneration failed: {exc}")

    if "grid_availability" in ds:
        availability = ds["grid_availability"]
        availability_values = np.asarray(availability.values, dtype=float)
        unavailable_hours = int(np.sum(availability_values < 0.5))
        if "year" in availability.dims:
            preview_rows = []
            for scenario in availability.coords["scenario"].values.tolist():
                for year in availability.coords["year"].values.tolist():
                    series = availability.sel(scenario=scenario, year=year)
                    connected = int(np.sum(np.asarray(series.values, dtype=float) > 0.0))
                    unavailable = int(np.sum(np.asarray(series.values, dtype=float) < 0.5))
                    share = (unavailable / connected) if connected > 0 else float("nan")
                    preview_rows.append(
                        {
                            "scenario": str(scenario),
                            "year": str(year),
                            "connected_hours": connected,
                            "unavailable_hours": unavailable,
                            "share_unavailable": share,
                        }
                    )
            with st.expander("Scenario-year availability summary", expanded=False):
                st.dataframe(
                    pd.DataFrame(preview_rows).style.format({"share_unavailable": "{:.2%}"}),
                    width="stretch",
                    hide_index=True,
                )
        else:
            total_hours = int(availability_values.size)
            unavailable_share = (unavailable_hours / total_hours) if total_hours > 0 else float("nan")
            c21, c22 = st.columns(2)
            c21.metric("Share of year unavailable", f"{100.0 * unavailable_share:.2f}%")
            c22.metric("Unavailable hours", str(unavailable_hours))


def _format_selector_label(option) -> str:
    return option.label


def _selector_index(values: List[Any], preferred: Any) -> int:
    try:
        return values.index(preferred)
    except ValueError:
        return 0


def _infer_y_label(variable: str) -> str:
    name = variable.lower()
    if "availability" in name:
        return "Value [-]"
    if "load" in name or "generation" in name or "import" in name or "export" in name:
        return "Value [kWh/h]"
    if "price" in name or "cost" in name:
        return "Value [currency]"
    return "Value"


def _render_timeseries_section(ds: xr.Dataset) -> None:
    st.subheader("Time-Series Visualization")
    st.caption("Explore canonical time-series variables directly from the loaded dataset.")

    options = list_timeseries_options(ds)
    if not options:
        st.info("No time-series variables with a `period` dimension were found in the dataset.")
        return

    scenario = None
    if "scenario" in ds.coords:
        scenarios = [str(v) for v in ds.coords["scenario"].values.tolist()]
        scenario = st.selectbox("Scenario", options=scenarios, index=0, key="audit_ts_scenario")

    year = None
    if "year" in ds.coords:
        years = ds.coords["year"].values.tolist()
        year = st.selectbox("Year", options=years, index=0, key="audit_ts_year")

    variable = st.selectbox(
        "Variable",
        options=options,
        format_func=_format_selector_label,
        index=0,
        key="audit_ts_variable",
    )

    selectors: Dict[str, Any] = {}
    for dim in variable.extra_dims:
        values = ds.coords[dim].values.tolist() if dim in ds.coords else ds[variable.variable].coords[dim].values.tolist()
        selectors[dim] = st.selectbox(
            dim.replace("_", " ").title(),
            options=values,
            index=_selector_index(values, values[0]),
            key=f"audit_ts_{variable.variable}_{dim}",
        )

    series = slice_timeseries(
        ds,
        variable=variable.variable,
        scenario=scenario,
        year=year,
        selectors=selectors,
    )

    title_parts = [variable.variable]
    if scenario is not None and "scenario" in ds[variable.variable].dims:
        title_parts.append(f"scenario={scenario}")
    if year is not None and "year" in ds[variable.variable].dims:
        title_parts.append(f"year={year}")
    for dim, value in selectors.items():
        title_parts.append(f"{dim}={value}")

    fig_hourly, fig_daily = build_timeseries_figures(
        series,
        title_prefix=_format_plot_title(", ".join(title_parts)),
        y_label=_infer_y_label(variable.variable),
    )

    c1, c2 = st.columns([1.8, 1.0])
    with c1:
        st.pyplot(fig_hourly, width="stretch")
    with c2:
        st.pyplot(fig_daily, width="stretch")

    stats = compute_series_stats(series)
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Min", f"{stats['min']:.4g}" if stats["min"] is not None else "n/a")
    s2.metric("Max", f"{stats['max']:.4g}" if stats["max"] is not None else "n/a")
    s3.metric("Mean", f"{stats['mean']:.4g}" if stats["mean"] is not None else "n/a")
    s4.metric("Missing values", str(stats["missing_values"]))

    with st.expander("Series diagnostics", expanded=False):
        annual_total_label = "Total annual energy" if "availability" not in variable.variable else "Total annual sum"
        st.write(
            {
                "variable": variable.variable,
                "dims": list(series.dims),
                "shape": tuple(int(v) for v in series.shape),
                "n": stats["n"],
                "min": stats["min"],
                "max": stats["max"],
                "mean": stats["mean"],
                "missing_values": stats["missing_values"],
                annual_total_label: stats["sum"],
            }
        )


def _format_plot_title(text: str) -> str:
    return text.replace("_", " ")


def _comparison_options(ds: xr.Dataset) -> List[Any]:
    options = []
    for option in list_timeseries_options(ds):
        da = ds[option.variable]
        if "year" not in da.dims:
            continue
        if option.variable in {"load_demand", "resource_availability", "grid_import_price", "grid_export_price", "grid_availability"}:
            options.append(option)
    return options


def _daily_profile_frame(series: xr.DataArray) -> pd.DataFrame:
    values = np.asarray(series.values, dtype=float).reshape(-1)
    frame = pd.DataFrame(
        {
            "hour_of_day": (np.arange(values.size) % 24) + 1,
            "value": values,
        }
    )
    return frame.groupby("hour_of_day", as_index=False)["value"].mean()


def _style_bar_axis(ax: plt.Axes, labels: List[str]) -> None:
    if not labels:
        return

    tick_step = max(1, int(np.ceil(len(labels) / 10)))
    if len(labels) > 10:
        tick_positions = np.arange(0, len(labels), tick_step)
        ax.set_xticks(tick_positions, [labels[idx] for idx in tick_positions])
        rotation = 45
    else:
        ax.set_xticks(np.arange(len(labels)), labels)
        rotation = 0 if len(labels) <= 6 else 30

    ax.tick_params(axis="x", labelrotation=rotation, labelsize=9, pad=6)
    for tick in ax.get_xticklabels():
        tick.set_horizontalalignment("right" if rotation else "center")


def _render_bar_plot(df: pd.DataFrame, *, x: str, y: str, hue: str | None, title: str, y_label: str) -> None:
    x_labels = df[x].astype(str).unique().tolist()
    width_scale = max(10, min(14, len(x_labels) * 0.6))
    fig, ax = plt.subplots(figsize=(width_scale, 4.2))
    if hue is None:
        positions = np.arange(len(x_labels))
        values = df.set_index(df[x].astype(str)).reindex(x_labels)[y].to_numpy(dtype=float)
        ax.bar(positions, values, color="#1f7a8c", alpha=0.85)
        _style_bar_axis(ax, x_labels)
    else:
        hue_values = df[hue].astype(str).unique().tolist()
        x_values = x_labels
        width = 0.8 / max(len(hue_values), 1)
        positions = np.arange(len(x_values))
        for idx, hue_value in enumerate(hue_values):
            subset = df[df[hue].astype(str) == hue_value].copy()
            subset = subset.set_index(subset[x].astype(str)).reindex(x_values).reset_index(drop=True)
            ax.bar(
                positions + (idx - (len(hue_values) - 1) / 2.0) * width,
                subset[y].to_numpy(dtype=float),
                width=width,
                label=hue_value,
                alpha=0.85,
            )
        _style_bar_axis(ax, x_values)
        ax.legend(ncols=3, fontsize=9)
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel(y_label)
    ax.grid(True, axis="y", alpha=0.25, linestyle=":")
    fig.tight_layout()
    st.pyplot(fig, width="stretch")


def _render_multi_year_input_comparison(ds: xr.Dataset) -> None:
    if "year" not in ds.coords:
        return

    scenario = None
    if "scenario" in ds.coords:
        scenarios = [str(v) for v in ds.coords["scenario"].values.tolist()]
        scenario = st.selectbox("Scenario for year comparison", options=scenarios, index=0, key="audit_compare_year_scenario")

    years = ds.coords["year"].values.tolist()

    load_rows = []
    if "load_demand" in ds:
        for year in years:
            series = slice_timeseries(ds, variable="load_demand", scenario=scenario, year=year, selectors={})
            load_rows.append({"year": str(year), "value": float(np.nansum(series.values))})
        _render_bar_plot(
            pd.DataFrame(load_rows),
            x="year",
            y="value",
            hue=None,
            title="Yearly load demand",
            y_label="Total demand [kWh/year]",
        )

    if "resource_availability" in ds:
        res_rows = []
        resource_values = ds.coords["resource"].values.tolist() if "resource" in ds.coords else []
        for year in years:
            for resource in resource_values:
                series = slice_timeseries(
                    ds,
                    variable="resource_availability",
                    scenario=scenario,
                    year=year,
                    selectors={"resource": resource},
                )
                res_rows.append(
                    {
                        "year": str(year),
                        "resource": str(resource),
                        "value": float(np.nanmean(series.values)),
                    }
                )
        if res_rows:
            _render_bar_plot(
                pd.DataFrame(res_rows),
                x="year",
                y="value",
                hue="resource",
                title="Average renewable capacity factor by year",
                y_label="Average capacity factor [-]",
            )

    if "grid_import_price" in ds:
        price_rows = []
        for year in years:
            series = slice_timeseries(ds, variable="grid_import_price", scenario=scenario, year=year, selectors={})
            price_rows.append({"year": str(year), "value": float(np.nanmean(series.values))})
        _render_bar_plot(
            pd.DataFrame(price_rows),
            x="year",
            y="value",
            hue=None,
            title="Average yearly grid import price",
            y_label="Average price [currency/kWh]",
        )

    if "grid_export_price" in ds and bool(((ds.attrs.get("settings", {}) or {}).get("grid", {}) or {}).get("allow_export", False)):
        export_rows = []
        for year in years:
            series = slice_timeseries(ds, variable="grid_export_price", scenario=scenario, year=year, selectors={})
            export_rows.append({"year": str(year), "value": float(np.nanmean(series.values))})
        _render_bar_plot(
            pd.DataFrame(export_rows),
            x="year",
            y="value",
            hue=None,
            title="Average yearly grid export price",
            y_label="Average price [currency/kWh]",
        )

    if "grid_availability" in ds:
        availability_rows = []
        for year in years:
            series = slice_timeseries(ds, variable="grid_availability", scenario=scenario, year=year, selectors={})
            availability_rows.append({"year": str(year), "value": int(np.sum(np.asarray(series.values, dtype=float) > 0.5))})
        _render_bar_plot(
            pd.DataFrame(availability_rows),
            x="year",
            y="value",
            hue=None,
            title="Available grid hours by year",
            y_label="Available hours [h/year]",
        )

    if "scenario" in ds.coords and int(ds.sizes.get("scenario", 0)) > 1:
        st.markdown("**Scenario comparison for selected year**")
        st.caption("Compare scenario-level yearly summaries for one selected model year.")

        year = st.selectbox(
            "Year for scenario comparison",
            options=ds.coords["year"].values.tolist(),
            index=0,
            key="audit_compare_scenario_year",
        )
        metric = st.selectbox(
            "Metric for scenario comparison",
            options=[
                "Load demand",
                "Renewable capacity factor",
                "Grid import price",
                "Grid export price",
                "Grid availability",
            ],
            index=0,
            key="audit_compare_scenario_metric",
        )

        if metric == "Renewable capacity factor" and "resource" in ds.coords:
            resource = st.selectbox(
                "Resource for scenario comparison",
                options=ds.coords["resource"].values.tolist(),
                index=0,
                key="audit_compare_scenario_resource",
            )
        else:
            resource = None

        rows = []
        for scenario_label in ds.coords["scenario"].values.tolist():
            selectors = {"resource": resource} if resource is not None else {}
            if metric == "Load demand" and "load_demand" in ds:
                series = slice_timeseries(ds, variable="load_demand", scenario=str(scenario_label), year=year, selectors={})
                value = float(np.nansum(series.values))
                y_label = "Total demand [kWh/year]"
            elif metric == "Renewable capacity factor" and "resource_availability" in ds and resource is not None:
                series = slice_timeseries(ds, variable="resource_availability", scenario=str(scenario_label), year=year, selectors=selectors)
                value = float(np.nanmean(series.values))
                y_label = "Average capacity factor [-]"
            elif metric == "Grid import price" and "grid_import_price" in ds:
                series = slice_timeseries(ds, variable="grid_import_price", scenario=str(scenario_label), year=year, selectors={})
                value = float(np.nanmean(series.values))
                y_label = "Average price [currency/kWh]"
            elif metric == "Grid export price" and "grid_export_price" in ds:
                series = slice_timeseries(ds, variable="grid_export_price", scenario=str(scenario_label), year=year, selectors={})
                value = float(np.nanmean(series.values))
                y_label = "Average price [currency/kWh]"
            elif metric == "Grid availability" and "grid_availability" in ds:
                series = slice_timeseries(ds, variable="grid_availability", scenario=str(scenario_label), year=year, selectors={})
                value = int(np.sum(np.asarray(series.values, dtype=float) > 0.5))
                y_label = "Available hours [h/year]"
            else:
                continue
            rows.append({"scenario": str(scenario_label), "value": value})

        if rows:
            _render_bar_plot(
                pd.DataFrame(rows),
                x="scenario",
                y="value",
                hue=None,
                title=f"{metric} across scenarios - {year}",
                y_label=y_label,
            )


def render_page() -> None:
    st.title("Data Audit and Visualization")
    st.caption("Validate project inputs, load the canonical dataset, and inspect time-series data before optimization.")

    project_name, project_root = resolve_active_project_from_session()
    paths = project_paths(project_name)

    try:
        formulation = read_json_file(paths.formulation_json)
    except Exception as exc:
        st.error(f"Cannot read `formulation.json`: {exc}")
        st.stop()

    st.info(f"Active project: `{project_name}`")
    st.caption(_build_project_summary(formulation))

    can_load = _render_file_section(project_root, formulation, paths)

    ds = None
    loader_mode = None
    if can_load:
        try:
            _, ds, loader_mode = _load_sets_and_dataset(project_name, formulation)
        except Exception as exc:
            st.subheader("Dataset Loading + Summary")
            st.error(f"Dataset loading failed: {exc}")
            st.stop()

        _render_dataset_section(ds, loader_mode, paths)
        _render_grid_controls(project_name, formulation, ds, paths)

    if ds is not None:
        st.markdown("---")
        _render_timeseries_section(ds)
        if loader_mode == "multi_year":
            st.markdown("---")
            st.subheader("Multi-Year Input Comparison")
            st.caption("Compare compact yearly summaries of demand, renewable availability, and grid-related inputs.")
            _render_multi_year_input_comparison(ds)


render_page()
