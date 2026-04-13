from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from core.data_pipeline.battery_loss_model import (
    CONVEX_LOSS_EPIGRAPH,
    InputValidationError as BatteryLossInputValidationError,
    get_battery_loss_model_from_formulation,
    load_battery_loss_curve_dataset,
)
from core.data_pipeline.utils import coord_labels, merge_optional_datasets, validate_required_coords
from core.io.utils import project_paths, simulate_grid_availability_typical_year
from core.data_pipeline import typical_year_parsing as p


InputValidationError = p.InputValidationError


def _load_battery_loss_curve_if_needed(
    *,
    formulation: dict,
    battery_params_ds: xr.Dataset,
    inputs_dir,
) -> tuple[str, xr.Dataset | None, str | None]:
    loss_model = get_battery_loss_model_from_formulation(formulation)
    curve_file = battery_params_ds.attrs.get("efficiency_curve_file", None)

    if loss_model != CONVEX_LOSS_EPIGRAPH:
        return loss_model, None, curve_file

    if not curve_file:
        raise InputValidationError(
            "battery_model.loss_model='convex_loss_epigraph' requires "
            "`battery.technical.efficiency_curve_csv` in inputs/battery.yaml."
        )

    curve_path = Path(curve_file)
    if not curve_path.is_absolute():
        curve_path = inputs_dir / curve_path

    charge_efficiency_base_da = battery_params_ds["battery_charge_efficiency"]
    discharge_efficiency_base_da = battery_params_ds["battery_discharge_efficiency"]
    if "scenario" in charge_efficiency_base_da.dims:
        charge_efficiency_base_da = charge_efficiency_base_da.isel(scenario=0)
    if "scenario" in discharge_efficiency_base_da.dims:
        discharge_efficiency_base_da = discharge_efficiency_base_da.isel(scenario=0)
    charge_efficiency_base = float(charge_efficiency_base_da)
    discharge_efficiency_base = float(discharge_efficiency_base_da)

    try:
        curve_ds = load_battery_loss_curve_dataset(
            curve_path,
            charge_efficiency_base=charge_efficiency_base,
            discharge_efficiency_base=discharge_efficiency_base,
        )
    except BatteryLossInputValidationError as exc:
        raise InputValidationError(str(exc)) from exc

    return loss_model, curve_ds, str(curve_path)


def _validate_sets(sets: xr.Dataset) -> None:
    validate_required_coords(
        sets,
        required=("scenario", "period"),
        error_cls=InputValidationError,
        context="initialize_data",
    )


def _assemble_grid_block(
    *,
    project_name: str,
    sets: xr.Dataset,
    formulation: dict,
    data: xr.Dataset,
) -> xr.Dataset:
    """
    Preserve legacy on-grid behavior exactly:
    - same paths
    - same variable names/dims
    - same attrs structure
    - same generated grid_availability.csv side effect
    """
    scenario_coord = sets.coords["scenario"]
    period_coord = sets.coords["period"]
    on_grid = bool(formulation.get("on_grid", False))
    allow_export = bool(formulation.get("grid_allow_export", False))
    paths = project_paths(project_name)

    if on_grid:
        grid_yaml_path = paths.inputs_dir / "grid.yaml"
        grid_ds = p._load_grid_yaml(grid_yaml_path, scenario_coord=scenario_coord)

        imp_path = paths.inputs_dir / "grid_import_price.csv"
        grid_import_price = p._load_price_csv_typical_year(
            imp_path,
            period_coord=period_coord,
            scenario_coord=scenario_coord,
            var_name="grid_import_price",
            year_label="typical_year",
        )

        if allow_export:
            exp_path = paths.inputs_dir / "grid_export_price.csv"
            grid_export_price = p._load_price_csv_typical_year(
                exp_path,
                period_coord=period_coord,
                scenario_coord=scenario_coord,
                var_name="grid_export_price",
                year_label="typical_year",
            )
        else:
            exp_path = None
            grid_export_price = None

        grid_availability = regenerate_grid_availability_typical_year(project_name=project_name, sets=sets)
        grid_avail_csv_path = paths.inputs_dir / "grid_availability.csv"

        to_merge = [
            grid_ds,
            xr.Dataset({"grid_import_price": grid_import_price}),
            xr.Dataset({"grid_availability": grid_availability}),
        ]
        if grid_export_price is not None:
            to_merge.append(xr.Dataset({"grid_export_price": grid_export_price}))

        data = merge_optional_datasets(data, *to_merge, compat="override", join="exact")

        data.attrs.setdefault("settings", {})
        data.attrs["settings"]["grid"] = {
            "on_grid": True,
            "allow_export": allow_export,
            "inputs_loaded": {
                "grid_yaml": str(grid_yaml_path),
                "grid_import_price_csv": str(imp_path),
                "grid_export_price_csv": str(exp_path) if allow_export else None,
                "grid_availability_csv": str(grid_avail_csv_path),
            },
        }
    else:
        data.attrs.setdefault("settings", {})
        data.attrs["settings"]["grid"] = {"on_grid": False, "allow_export": False}

    return data


def regenerate_grid_availability_typical_year(
    *,
    project_name: str,
    sets: xr.Dataset,
) -> xr.DataArray:
    scenario_coord = sets.coords["scenario"]
    period_coord = sets.coords["period"]
    paths = project_paths(project_name)
    grid_yaml_path = paths.inputs_dir / "grid.yaml"
    grid_ds = p._load_grid_yaml(grid_yaml_path, scenario_coord=scenario_coord)

    avail_mat = np.zeros((int(period_coord.size), int(scenario_coord.size)), dtype=float)
    for j, s_lab in enumerate(coord_labels(scenario_coord)):
        ao = float(grid_ds["grid_avg_outages_per_year"].sel(scenario=s_lab).values)
        ad = float(grid_ds["grid_avg_outage_duration_minutes"].sel(scenario=s_lab).values)
        scale_od = float(grid_ds["grid_outage_scale_od_hours"].sel(scenario=s_lab).values)
        shape_od = float(grid_ds["grid_outage_shape_od"].sel(scenario=s_lab).values)
        seed = int(float(grid_ds["grid_outage_seed"].sel(scenario=s_lab).values))

        v = simulate_grid_availability_typical_year(
            ao,
            ad,
            periods_per_year=int(period_coord.size),
            scale_od=scale_od,
            shape_od=shape_od,
            rng=np.random.default_rng(seed),
        )
        avail_mat[:, j] = v

    grid_availability = xr.DataArray(
        avail_mat,
        coords={"period": period_coord, "scenario": scenario_coord},
        dims=("period", "scenario"),
        name="grid_availability",
        attrs={
            "units": "binary",
            "component": "grid",
            "generated_artifact": True,
            "notes": "Derived from grid.yaml outage statistics; not a primary user-maintained input.",
        },
    )

    grid_avail_csv_path = paths.inputs_dir / "grid_availability.csv"
    p._write_grid_availability_csv(
        grid_avail_csv_path, availability=grid_availability, year_label="typical_year"
    )
    return grid_availability


def load_typical_year_dataset(project_name: str, sets: xr.Dataset) -> xr.Dataset:
    """
    Canonical typical-year dataset loader with strict backward compatibility.

    Implementation mirrors the former core.typical_year_model.data.initialize_data
    behavior while keeping the pipeline entry in core.data_pipeline.loader.
    """
    _validate_sets(sets)

    scenario_coord = sets.coords["scenario"]
    period_coord = sets.coords["period"]
    n_scen = int(scenario_coord.size)

    paths = project_paths(project_name)
    formulation = p._read_json(paths.formulation_json)

    formulation_mode = p._as_str(formulation.get("core_formulation", "steady_state"), name="core_formulation")
    if formulation_mode != "steady_state":
        raise InputValidationError("This data initializer is for steady_state only.")

    uc_enabled = bool(formulation.get("unit_commitment", False))
    ms = formulation.get("multi_scenario", {}) or {}
    ms_enabled = bool(ms.get("enabled", False))

    if ms_enabled:
        raw_w = ms.get("scenario_weights") or []
        weights = p._normalize_weights(raw_w, n_scen)
    else:
        weights = [1.0] * n_scen

    scenario_weights = xr.DataArray(
        weights,
        coords={"scenario": scenario_coord},
        dims=("scenario",),
        name="scenario_weight",
    )

    optc = formulation.get("optimization_constraints", {}) or {}
    enforcement = p._as_str(optc.get("enforcement", None), name="optimization_constraints.enforcement")
    if not enforcement:
        enforcement = "expected" if ms_enabled else "scenario_wise"
    if enforcement not in ("expected", "scenario_wise"):
        raise InputValidationError(
            f"Invalid optimization_constraints.enforcement: {enforcement!r}. "
            "Allowed: 'expected' | 'scenario_wise'."
        )

    min_res_pen = p._as_float(
        optc.get("min_renewable_penetration", 0.0), name="min_renewable_penetration", default=0.0
    )
    max_ll_frac = p._as_float(optc.get("max_lost_load_fraction", 0.0), name="max_lost_load_fraction", default=0.0)
    lolc = p._as_float(optc.get("lost_load_cost_per_kwh", 0.0), name="lost_load_cost_per_kwh", default=0.0)
    land_m2 = p._as_float_or_nan(optc.get("land_availability_m2", None), name="land_availability_m2")
    em_cost = p._as_float(optc.get("emission_cost_per_kgco2e", 0.0), name="emission_cost_per_kgco2e", default=0.0)

    da_min_res_pen = xr.DataArray(min_res_pen, name="min_renewable_penetration")
    da_max_ll_frac = xr.DataArray(max_ll_frac, name="max_lost_load_fraction")
    da_lolc = xr.DataArray(lolc, name="lost_load_cost_per_kwh")
    da_land = xr.DataArray(land_m2, name="land_availability_m2")
    da_em_cost = xr.DataArray(em_cost, name="emission_cost_per_kgco2e")

    if enforcement == "scenario_wise":
        da_lolc = p._broadcast_to_scenario(da_lolc, scenario_coord)
        da_em_cost = p._broadcast_to_scenario(da_em_cost, scenario_coord)

    load_path = paths.inputs_dir / "load_demand.csv"
    load_demand = p._load_load_demand_csv(
        load_path, period_coord=sets.coords["period"], scenario_coord=sets.coords["scenario"]
    )
    resource_path = paths.inputs_dir / "resource_availability.csv"
    resource_avail_da = p._load_resource_availability_csv(
        resource_path,
        period_coord=sets.coords["period"],
        scenario_coord=sets.coords["scenario"],
        resource_coord=sets.coords["resource"],
    )

    data = xr.Dataset(
        data_vars={
            "scenario_weight": scenario_weights,
            "min_renewable_penetration": da_min_res_pen,
            "max_lost_load_fraction": da_max_ll_frac,
            "lost_load_cost_per_kwh": da_lolc,
            "land_availability_m2": da_land,
            "emission_cost_per_kgco2e": da_em_cost,
            "load_demand": load_demand,
            "resource_availability": resource_avail_da,
        }
    )

    renewables_path = paths.inputs_dir / "renewables.yaml"
    ren_params_ds = p._load_renewables_yaml(
        renewables_path, scenario_coord=sets.coords["scenario"], resource_coord=sets.coords["resource"]
    )
    battery_path = paths.inputs_dir / "battery.yaml"
    bat_params_ds = p._load_battery_yaml(battery_path, scenario_coord=sets.coords["scenario"])
    battery_loss_model, battery_curve_ds, battery_curve_path = _load_battery_loss_curve_if_needed(
        formulation=formulation,
        battery_params_ds=bat_params_ds,
        inputs_dir=paths.inputs_dir,
    )
    battery_degradation_settings = {
        "cycle_fade_enabled": False,
        "calendar_fade_enabled": False,
    }
    battery_calendar_curve_ds = None
    battery_calendar_curve_path = None
    genfuel_path = paths.inputs_dir / "generator.yaml"
    gen_ds, fuel_ds, curve_ds, genfuel_meta = p._load_generator_and_fuel_yaml(
        genfuel_path, inputs_dir=paths.inputs_dir, scenario_coord=scenario_coord
    )

    data = merge_optional_datasets(
        data,
        ren_params_ds,
        bat_params_ds,
        gen_ds,
        fuel_ds,
        curve_ds,
        battery_curve_ds,
        battery_calendar_curve_ds,
        compat="override",
    )

    data.attrs["settings"] = {
        "project_name": project_name,
        "formulation": formulation_mode,
        "unit_commitment": uc_enabled,
        "integer_sizing_enabled": uc_enabled,
        "multi_scenario": {"enabled": ms_enabled, "n_scenarios": n_scen},
        "resources": {
            "n_resources": int(sets.sizes.get("resource", 0)),
            "resource_labels": sets.coords.get("resource", []).values.tolist(),
        },
        "optimization_constraints": {"enforcement": enforcement},
        "modeling_notes": {
            "unit_commitment_semantics": "In typical-year mode, `unit_commitment` enables integer sizing variables only; chronological generator commitment binaries are not part of this formulation.",
            "land_constraint_semantics": "Land availability is enforced only when a finite non-negative `land_availability_m2` value is provided; omitted values leave the constraint inactive.",
        },
        "inputs_loaded": {"load_demand_csv": str(load_path), "renewable_availability_csv": str(resource_path)},
    }
    data.attrs["settings"]["inputs_loaded"]["renewables_yaml"] = str(renewables_path)
    data.attrs["settings"]["inputs_loaded"]["battery_yaml"] = str(battery_path)
    if battery_curve_path is not None:
        data.attrs["settings"]["inputs_loaded"]["battery_efficiency_curve_csv"] = str(battery_curve_path)
    if battery_calendar_curve_path is not None:
        data.attrs["settings"]["inputs_loaded"]["battery_calendar_fade_curve_csv"] = str(battery_calendar_curve_path)
    data.attrs["settings"]["battery_label"] = bat_params_ds.attrs.get("battery_label", "Battery")
    data.attrs["settings"]["battery_model"] = {
        "loss_model": battery_loss_model,
        "efficiency_curve_csv": battery_curve_path,
        "degradation_model": battery_degradation_settings,
    }
    data.attrs.setdefault("settings", {})
    data.attrs["settings"].setdefault("generator", {})
    data.attrs["settings"]["generator"]["partial_load_modelling_enabled"] = bool(
        genfuel_meta.get("partial_load_modelling_enabled", False)
    )
    data.attrs["settings"]["generator"]["efficiency_curve_file"] = genfuel_meta.get("efficiency_curve_file")
    data.attrs["settings"]["generator"]["label"] = genfuel_meta.get("generator_label", "Generator")
    data.attrs["settings"]["fuel"] = {"label": genfuel_meta.get("fuel_label", "Fuel")}
    data.attrs["settings"].setdefault("inputs_loaded", {})
    data.attrs["settings"]["inputs_loaded"]["generator_yaml"] = str(genfuel_path)

    data = _assemble_grid_block(project_name=project_name, sets=sets, formulation=formulation, data=data)

    return data
