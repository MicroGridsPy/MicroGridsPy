from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import xarray as xr

from microgridspy.data_pipeline.battery_loss_model import CONVEX_LOSS_EPIGRAPH
from microgridspy.errors import InputValidationError
from microgridspy.io.formulation import MULTI_YEAR

# Defaults for the battery.yaml technical inputs the semi-empirical mode reads.
# See validate_degradation_technical_inputs for what each one does and how to choose it.
DEGRADATION_TECHNICAL_DEFAULTS: dict[str, float] = {
    "cycle_life_reference_dod": 0.8,
    "cycle_life_reference_temperature_c": 25.0,
    "enclosure_temperature_rise_c": 10.0,
    "calendar_fade_scale": 1.0,
}

# Reproduced in error messages: this is the module's most influential input and the one most
# likely to be left at its default without thought.
ENCLOSURE_RISE_GUIDANCE = (
    "0 K actively cooled / air-conditioned; 5-10 K ventilated, shaded battery room; "
    "15-20 K sealed metal container in full sun"
)


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


def _read_optional_float(raw: Any, name: str, default: float | None) -> float | None:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return default
    try:
        return float(raw)
    except Exception as exc:
        raise InputValidationError(
            f"battery_model.degradation_model.{name} must be numeric."
        ) from exc


def get_battery_degradation_settings(
    formulation: dict[str, Any] | None,
    *,
    battery_loss_model: str,
) -> dict[str, Any]:
    """
    Resolve the battery degradation settings from the formulation. There are two modes.

    **Linear capacity fade** -- the default, ``coefficients_enabled`` false. A flat exogenous
    yearly rate, ``battery.technical.capacity_degradation_rate_per_year``, scaling the
    availability ceiling: the same term the renewable and generator technologies carry, so
    battery ageing is treated consistently with the rest of the system. Set the rate to 0 to
    size without ageing. No extra parameters, no capacity state, no coefficients.

    **Semi-empirical degradation** -- ``coefficients_enabled`` true. A marginal cycle-fade cost
    ``c(T)`` on DC discharge throughput plus an explicit calendar rate ``r_cal`` on nameplate,
    both evaluated at cell temperature; the usable-energy state carries the two fades
    additively, a hard floor holds it above ``end_of_life_soh``, and the service life is
    derived from the physics unless the user asserts one. The flat linear rate is suppressed
    here, because calendar ageing is modelled explicitly.

    This validates the mode flag, the formulation gate, the loss-model gate and the SoH span.
    Range checks for the battery.yaml technical inputs live in
    ``validate_degradation_technical_inputs``, which the loader calls once it has read them.
    """
    if not isinstance(formulation, dict):
        formulation = {}
    core_formulation = str(formulation.get("core_formulation", "") or "").strip().lower()
    battery_model = formulation.get("battery_model", {}) or {}
    if not isinstance(battery_model, dict):
        battery_model = {}
    degradation_model = battery_model.get("degradation_model", {}) or {}
    if not isinstance(degradation_model, dict):
        degradation_model = {}

    coefficients_enabled = _coerce_bool(
        degradation_model.get("coefficients_enabled", False), default=False
    )

    # Ageing accumulates on the year axis, which a typical year does not have. The
    # typical-year loader refuses this independently, since it reads the flag directly;
    # this is the equivalent guard on the multi-year side.
    if coefficients_enabled and core_formulation not in ("", MULTI_YEAR):
        raise InputValidationError(
            "Semi-empirical battery degradation is supported only in the multi-year "
            f"formulation (core_formulation='{MULTI_YEAR}'), not in '{core_formulation}'. "
            "Ageing is accumulated across project years, which a typical-year model has no "
            "axis for. Set battery_model.degradation_model.coefficients_enabled=false, or "
            "switch the project to the multi-year formulation."
        )

    if coefficients_enabled and battery_loss_model != CONVEX_LOSS_EPIGRAPH:
        raise InputValidationError(
            "Semi-empirical battery degradation requires "
            "battery_model.loss_model='convex_loss_epigraph', because throughput is defined on "
            "the internal DC-side battery powers: with a constant round-trip efficiency there "
            "is no DC-side quantity for the cycle-fade coefficient to multiply."
        )

    end_of_life_soh = _read_optional_float(
        degradation_model.get("end_of_life_soh", None), "end_of_life_soh", None
    )
    cycle_lifetime_to_eol_cycles = _read_optional_float(
        degradation_model.get("cycle_lifetime_to_eol_cycles", None),
        "cycle_lifetime_to_eol_cycles",
        None,
    )
    cycle_test_duration_years = _read_optional_float(
        degradation_model.get("cycle_test_duration_years", None),
        "cycle_test_duration_years",
        None,
    )

    if end_of_life_soh is not None and not (0.0 < end_of_life_soh < 1.0):
        raise InputValidationError(
            "Battery end-of-life SoH must be within (0, 1). It is the health threshold the "
            "datasheet cycle count refers to, and the floor the capacity state may not cross; "
            "1.0 would leave no usable budget to degrade."
        )
    if cycle_lifetime_to_eol_cycles is not None and cycle_lifetime_to_eol_cycles <= 0.0:
        raise InputValidationError(
            "battery_model.degradation_model.cycle_lifetime_to_eol_cycles must be > 0."
        )
    if cycle_test_duration_years is not None and cycle_test_duration_years <= 0.0:
        raise InputValidationError(
            "battery_model.degradation_model.cycle_test_duration_years must be > 0 when set. "
            "Leave it unset (null) if the datasheet does not state how long the cycle-life test "
            "ran; the cycle channel is then knowingly 18-23 % pessimistic."
        )

    # The semi-empirical mode needs both ends of the SoH span and the rated cycle life: the
    # budget 1 - end_of_life_soh calibrates the cycle magnitude against the datasheet, sets
    # the end-of-life floor and bounds the derived service life.
    if coefficients_enabled:
        missing = [
            name
            for name, value in (
                ("end_of_life_soh", end_of_life_soh),
                ("cycle_lifetime_to_eol_cycles", cycle_lifetime_to_eol_cycles),
            )
            if value is None
        ]
        if missing:
            raise InputValidationError(
                "Semi-empirical battery degradation requires "
                f"{' and '.join(missing)} to be set. The usable SoH budget calibrates the "
                "cycle-fade magnitude against the datasheet cycle life, sets the end-of-life "
                "floor and bounds the derived service life, so the model cannot be assembled "
                "without them."
            )

    return {
        "coefficients_enabled": coefficients_enabled,
        # Fixed at a new battery, not a user input: second-life cells would need the fade
        # knee this linear model cannot represent, and a starting SoH below 1 also changes
        # what the datasheet cycle-life calibration means.
        "initial_soh": 1.0,
        "end_of_life_soh": end_of_life_soh,
        "cycle_lifetime_to_eol_cycles": cycle_lifetime_to_eol_cycles,
        "cycle_test_duration_years": cycle_test_duration_years,
        "endogenous_degradation_enabled": coefficients_enabled,
    }


def validate_degradation_technical_inputs(
    technical: dict[str, Any] | None,
    *,
    depth_of_discharge: float | None = None,
) -> dict[str, float]:
    """
    Validate and default the ``battery.yaml -> battery.technical`` inputs the semi-empirical
    mode reads, returning them as plain floats.

    ``cycle_life_reference_dod`` / ``cycle_life_reference_temperature_c``
        The depth and temperature the datasheet cycle count was measured at. Read them off the
        same datasheet line as the cycle count: calibrating at one depth and consuming at
        another is a 23 % error in the fade budget.

    ``enclosure_temperature_rise_c``
        Outdoor air to enclosure air. Temperature series are 2 m outdoor air, while cells sit
        inside a box that runs hotter, and the distilled cycle law already contains cell
        self-heating -- so the correct input is the air temperature around the pack. This is a
        design assumption rather than a fitted value, and it is the single most influential
        input in the module: run it as a sensitivity.

    ``calendar_fade_scale``
        Walks the honest 2.7x literature band on calendar magnitude: 1.0 is the model anchored
        to a ten-year shelf-ageing measurement, 2.72 recovers the unscaled published fit.
        Report both ends.
    """
    if technical is None:
        technical = {}
    if not isinstance(technical, dict):
        raise InputValidationError("battery.technical must be a mapping.")

    out: dict[str, float] = {}
    for name, default in DEGRADATION_TECHNICAL_DEFAULTS.items():
        raw = technical.get(name, None)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            out[name] = float(default)
            continue
        try:
            out[name] = float(raw)
        except Exception as exc:
            raise InputValidationError(f"battery.technical.{name} must be numeric.") from exc

    if not (0.0 < out["cycle_life_reference_dod"] <= 1.0):
        raise InputValidationError(
            "battery.technical.cycle_life_reference_dod must be within (0, 1]. It is the depth "
            "of discharge the datasheet cycle count was measured at -- read it off the same "
            "datasheet line as the cycle count, and do not leave it at 0.8 if yours quotes "
            "100 %."
        )
    if not np.isfinite(out["cycle_life_reference_temperature_c"]) or not (
        -50.0 <= out["cycle_life_reference_temperature_c"] <= 100.0
    ):
        raise InputValidationError(
            "battery.technical.cycle_life_reference_temperature_c must be finite and within "
            "[-50, 100] degC; datasheet cycle counts are almost always quoted at 25 degC."
        )
    rise = out["enclosure_temperature_rise_c"]
    if not np.isfinite(rise) or rise < 0.0:
        raise InputValidationError(
            "battery.technical.enclosure_temperature_rise_c must be finite and >= 0 "
            f"({ENCLOSURE_RISE_GUIDANCE}). A negative rise would mean the enclosure is cooler "
            "than outdoor air, which no passive installation achieves."
        )
    if rise > 30.0:
        raise InputValidationError(
            "battery.technical.enclosure_temperature_rise_c above 30 K is outside anything "
            f"reported for battery enclosures ({ENCLOSURE_RISE_GUIDANCE})."
        )
    if not np.isfinite(out["calendar_fade_scale"]) or out["calendar_fade_scale"] < 0.0:
        raise InputValidationError(
            "battery.technical.calendar_fade_scale must be finite and >= 0 (1.0 anchored, "
            "2.72 the unscaled published envelope)."
        )

    # A reference depth far from the operating depth is legal but worth saying out loud: the
    # calibration is exact at the reference point and the fitted law is only near-linear in
    # depth, so the further apart they are the more the depth residual matters.
    if depth_of_discharge is not None:
        try:
            dod = float(depth_of_discharge)
        except Exception:
            dod = float("nan")
        if np.isfinite(dod) and dod > 0.0 and abs(dod - out["cycle_life_reference_dod"]) > 0.25:
            warnings.warn(
                f"battery.technical.depth_of_discharge ({dod:g}) is far from "
                f"cycle_life_reference_dod ({out['cycle_life_reference_dod']:g}). The cycle-fade "
                "magnitude is pinned exactly at the reference depth; check that the reference "
                "matches the datasheet line the cycle count came from.",
                UserWarning,
                stacklevel=2,
            )

    return out


def suppress_exogenous_battery_capacity_degradation(
    degradation_rate: xr.DataArray | None,
    *,
    coefficients_enabled: bool,
) -> tuple[xr.DataArray | None, bool]:
    """
    Stop the two modes overlapping.

    ``battery.technical.capacity_degradation_rate_per_year`` (linear mode) and the
    semi-empirical calendar channel both represent background time-based ageing. In
    semi-empirical mode calendar fade is a state variable subtracted from usable energy, so
    applying the flat rate to the nameplate ceiling as well would remove the same capacity
    twice. The rate is therefore zeroed, and the caller is told whether a non-zero value was
    actually discarded so it can say so.
    """
    if degradation_rate is None:
        return None, False
    if not coefficients_enabled:
        return degradation_rate, False

    vals = np.asarray(degradation_rate.values, dtype=float)
    vals = vals[np.isfinite(vals)]
    ignored_nonzero = bool(vals.size > 0 and float(np.max(np.abs(vals))) > 0.0)
    return xr.zeros_like(degradation_rate, dtype=float), ignored_nonzero
