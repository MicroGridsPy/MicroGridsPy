from __future__ import annotations

from typing import Any

import numpy as np
import xarray as xr

from core.data_pipeline.battery_loss_model import CONVEX_LOSS_EPIGRAPH


class InputValidationError(RuntimeError):
    pass


def _coerce_bool(raw: Any, *, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"true", "1", "yes", "on"}:
            return True
        if value in {"false", "0", "no", "off", ""}:
            return False
    return bool(raw)


def derive_cycle_fade_coefficient_from_cycle_life(
    *,
    initial_soh: float,
    end_of_life_soh: float,
    cycle_lifetime_to_eol_cycles: float,
    reference_depth_of_discharge: float,
) -> float:
    try:
        initial_soh_f = float(initial_soh)
        end_of_life_soh_f = float(end_of_life_soh)
        cycle_lifetime_f = float(cycle_lifetime_to_eol_cycles)
        dod_f = float(reference_depth_of_discharge)
    except Exception as exc:
        raise InputValidationError(
            "Battery cycle-fade derivation inputs must be numeric."
        ) from exc

    if not (0.0 < initial_soh_f <= 1.0):
        raise InputValidationError("Battery initial SoH used for cycle-fade derivation must be within (0, 1].")
    if not (0.0 < end_of_life_soh_f <= initial_soh_f):
        raise InputValidationError(
            "Battery end-of-life SoH used for cycle-fade derivation must be within (0, initial_soh]."
        )
    if cycle_lifetime_f <= 0.0:
        raise InputValidationError("Battery cycle lifetime to end of life must be > 0.")
    if not (0.0 < dod_f <= 1.0):
        raise InputValidationError("Battery depth_of_discharge used for cycle-fade derivation must be within (0, 1].")

    return (initial_soh_f - end_of_life_soh_f) / (cycle_lifetime_f * dod_f * initial_soh_f)


def get_battery_degradation_settings(
    formulation: dict[str, Any] | None,
    *,
    battery_loss_model: str,
    battery_initial_soh_override: float | None = None,
    battery_cycle_fade_coefficient_override: float | None = None,
    battery_calendar_curve_csv_override: str | None = None,
    battery_calendar_time_increment_mode_override: str | None = None,
    battery_calendar_time_increment_per_step_override: float | None = None,
    battery_calendar_time_increment_per_year_override: float | None = None,
) -> dict[str, Any]:
    if not isinstance(formulation, dict):
        formulation = {}
    formulation_mode = str(formulation.get("core_formulation", "steady_state") or "steady_state").strip().lower()
    battery_model = formulation.get("battery_model", {}) or {}
    if not isinstance(battery_model, dict):
        battery_model = {}
    degradation_model = battery_model.get("degradation_model", {}) or {}
    if not isinstance(degradation_model, dict):
        degradation_model = {}

    cycle_fade_enabled = _coerce_bool(
        degradation_model.get("cycle_fade_enabled", False),
        default=False,
    )
    calendar_fade_enabled = _coerce_bool(
        degradation_model.get("calendar_fade_enabled", False),
        default=False,
    )
    if battery_cycle_fade_coefficient_override is not None:
        try:
            cycle_fade_coefficient = float(battery_cycle_fade_coefficient_override)
        except Exception as exc:
            raise InputValidationError(
                "battery.technical.cycle_fade_coefficient_per_kwh_throughput in inputs/battery.yaml must be numeric."
            ) from exc
    else:
        try:
            cycle_fade_coefficient = float(
                degradation_model.get("cycle_fade_coefficient_per_kwh_throughput", 0.0) or 0.0
            )
        except Exception as exc:
            raise InputValidationError(
                "battery_model.degradation_model.cycle_fade_coefficient_per_kwh_throughput "
                "must be numeric."
            ) from exc
    if battery_initial_soh_override is not None:
        try:
            initial_soh = float(battery_initial_soh_override)
        except Exception as exc:
            raise InputValidationError(
                "battery.technical.initial_soh in inputs/battery.yaml must be numeric."
            ) from exc
    else:
        try:
            initial_soh = float(degradation_model.get("initial_soh", 1.0) or 1.0)
        except Exception as exc:
            raise InputValidationError(
                "battery_model.degradation_model.initial_soh must be numeric."
            ) from exc
    if battery_calendar_curve_csv_override is not None:
        calendar_curve_csv = str(battery_calendar_curve_csv_override).strip() or None
    else:
        calendar_curve_csv = degradation_model.get("battery_calendar_fade_curve_csv", None)
        if calendar_curve_csv is not None:
            calendar_curve_csv = str(calendar_curve_csv).strip() or None

    if battery_calendar_time_increment_mode_override is not None:
        calendar_time_increment_mode = str(
            battery_calendar_time_increment_mode_override or "constant_per_year"
        ).strip().lower()
    else:
        calendar_time_increment_mode = str(
            degradation_model.get("battery_calendar_time_increment_mode", "constant_per_year") or "constant_per_year"
        ).strip().lower()
    if calendar_time_increment_mode == "constant_per_step":
        calendar_time_increment_mode = "constant_per_year"

    if battery_calendar_time_increment_per_year_override is not None:
        try:
            calendar_time_increment_per_year = float(battery_calendar_time_increment_per_year_override)
        except Exception as exc:
            raise InputValidationError(
                "battery.technical.calendar_time_increment_per_year in inputs/battery.yaml must be numeric."
            ) from exc
    elif battery_calendar_time_increment_per_step_override is not None:
        try:
            calendar_time_increment_per_year = float(battery_calendar_time_increment_per_step_override)
        except Exception as exc:
            raise InputValidationError(
                "battery.technical.calendar_time_increment_per_year in inputs/battery.yaml must be numeric."
            ) from exc
    else:
        try:
            calendar_time_increment_per_year = float(
                degradation_model.get(
                    "battery_calendar_time_increment_per_year",
                    degradation_model.get("battery_calendar_time_increment_per_step", 1.0),
                )
                or 1.0
            )
        except Exception as exc:
            raise InputValidationError(
                "battery_model.degradation_model.battery_calendar_time_increment_per_year must be numeric."
            ) from exc

    raw_end_of_life_soh = degradation_model.get("end_of_life_soh", None)
    end_of_life_soh = None
    if raw_end_of_life_soh not in (None, ""):
        try:
            end_of_life_soh = float(raw_end_of_life_soh)
        except Exception as exc:
            raise InputValidationError("battery_model.degradation_model.end_of_life_soh must be numeric.") from exc

    raw_cycle_lifetime = degradation_model.get("cycle_lifetime_to_eol_cycles", None)
    cycle_lifetime_to_eol_cycles = None
    if raw_cycle_lifetime not in (None, ""):
        try:
            cycle_lifetime_to_eol_cycles = float(raw_cycle_lifetime)
        except Exception as exc:
            raise InputValidationError(
                "battery_model.degradation_model.cycle_lifetime_to_eol_cycles must be numeric."
            ) from exc

    if (cycle_fade_enabled or calendar_fade_enabled) and battery_loss_model != CONVEX_LOSS_EPIGRAPH:
        raise InputValidationError(
            "battery_model.degradation_model requires "
            "battery_model.loss_model='convex_loss_epigraph' because throughput is "
            "defined on the internal DC-side battery powers and the degradation layer "
            "is attached to the advanced battery architecture."
        )
    if (cycle_fade_enabled or calendar_fade_enabled) and formulation_mode != "dynamic":
        raise InputValidationError(
            "Battery degradation tracking is currently supported only in the dynamic multi-year formulation. "
            "In steady_state typical-year projects, keep the battery loss model optional but leave "
            "cycle_fade_enabled=false and calendar_fade_enabled=false."
        )
    if cycle_fade_coefficient < 0.0:
        raise InputValidationError(
            "battery_model.degradation_model.cycle_fade_coefficient_per_kwh_throughput "
            "must be >= 0."
        )
    if not (0.0 <= initial_soh <= 1.0):
        raise InputValidationError(
            "Battery initial SoH must be within [0, 1]."
        )
    if end_of_life_soh is not None and not (0.0 < end_of_life_soh <= initial_soh):
        raise InputValidationError(
            "Battery end-of-life SoH must be within (0, initial_soh]."
        )
    if cycle_lifetime_to_eol_cycles is not None and cycle_lifetime_to_eol_cycles <= 0.0:
        raise InputValidationError(
            "battery_model.degradation_model.cycle_lifetime_to_eol_cycles must be > 0."
        )
    if calendar_time_increment_mode != "constant_per_year":
        raise InputValidationError(
            "battery_model.degradation_model.battery_calendar_time_increment_mode currently "
            "supports only 'constant_per_year'."
        )
    if calendar_time_increment_per_year < 0.0:
        raise InputValidationError(
            "battery_model.degradation_model.battery_calendar_time_increment_per_year must be >= 0."
        )

    return {
        "cycle_fade_enabled": cycle_fade_enabled,
        "cycle_fade_coefficient_per_kwh_throughput": cycle_fade_coefficient,
        "calendar_fade_enabled": calendar_fade_enabled,
        "battery_calendar_fade_curve_csv": calendar_curve_csv,
        "battery_calendar_time_increment_mode": calendar_time_increment_mode,
        "battery_calendar_time_increment_per_year": calendar_time_increment_per_year,
        "initial_soh": initial_soh,
        "end_of_life_soh": end_of_life_soh,
        "cycle_lifetime_to_eol_cycles": cycle_lifetime_to_eol_cycles,
        "endogenous_degradation_enabled": bool(cycle_fade_enabled or calendar_fade_enabled),
    }


def suppress_exogenous_battery_capacity_degradation_when_endogenous(
    degradation_rate: xr.DataArray | None,
    *,
    calendar_fade_enabled: bool,
) -> tuple[xr.DataArray | None, bool]:
    """
    Prevent double-counting battery degradation in the dynamic formulation.

    Calendar fade and the older exogenous yearly battery capacity-degradation
    term both represent background time-based ageing, so they must not be
    active together. Cycle fade, by contrast, can coexist with the exogenous
    yearly term because it captures throughput-driven ageing.
    """
    if degradation_rate is None:
        return None, False
    if not calendar_fade_enabled:
        return degradation_rate, False

    out = xr.zeros_like(degradation_rate, dtype=float)
    vals = np.asarray(degradation_rate.values, dtype=float)
    vals = vals[np.isfinite(vals)]
    ignored_nonzero = bool(vals.size > 0 and float(np.max(np.abs(vals))) > 0.0)
    return out, ignored_nonzero
