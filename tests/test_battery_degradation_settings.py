"""Phase B acceptance tests: degradation settings parsing, gates and validation.

Covers BATTERY_DEGRADATION_PORT_PLAN.md Phase B and test T1.16. No solver, no loader --
these are the guards that decide whether a project is allowed to assemble at all.
"""

from __future__ import annotations

import warnings

import numpy as np
import pytest
import xarray as xr

from microgridspy.data_pipeline.battery_degradation_model import (
    DEGRADATION_TECHNICAL_DEFAULTS,
    get_battery_degradation_settings,
    suppress_exogenous_battery_capacity_degradation,
    validate_degradation_technical_inputs,
)
from microgridspy.errors import InputValidationError

CONVEX = "convex_loss_epigraph"
CONSTANT = "constant_efficiency"


def formulation(**degradation):
    """A minimal multi-year formulation with the given degradation_model keys."""
    return {
        "core_formulation": "multi_year",
        "battery_model": {"loss_model": CONVEX, "degradation_model": dict(degradation)},
    }


def settings(form, *, loss_model=CONVEX):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return get_battery_degradation_settings(form, battery_loss_model=loss_model)


# ===========================================================================
# Defaults and the off path
# ===========================================================================


def test_degradation_off_by_default() -> None:
    """Linear capacity fade is the default mode, and it needs nothing from this parser."""
    out = settings(formulation())
    assert out["coefficients_enabled"] is False
    assert out["endogenous_degradation_enabled"] is False
    assert out["initial_soh"] == 1.0


def test_missing_or_malformed_formulation_is_tolerated() -> None:
    for bad in (None, {}, {"battery_model": None}, {"battery_model": {"degradation_model": None}}):
        out = settings(bad, loss_model=CONSTANT)
        assert out["endogenous_degradation_enabled"] is False


def test_degradation_off_does_not_require_the_convex_loss_model() -> None:
    """Sizing without ageing must keep working on a constant round-trip efficiency."""
    out = settings(formulation(), loss_model=CONSTANT)
    assert out["endogenous_degradation_enabled"] is False


# ===========================================================================
# The coefficients gate
# ===========================================================================


def _coefficients_form(**overrides):
    keys = {"coefficients_enabled": True, "end_of_life_soh": 0.8, "cycle_lifetime_to_eol_cycles": 6000}
    keys.update(overrides)
    return formulation(**keys)


def test_coefficients_mode_resolves() -> None:
    out = settings(_coefficients_form())
    assert out["coefficients_enabled"] is True
    assert out["endogenous_degradation_enabled"] is True
    assert out["initial_soh"] == pytest.approx(1.0)
    assert out["end_of_life_soh"] == pytest.approx(0.8)
    assert out["cycle_lifetime_to_eol_cycles"] == pytest.approx(6000.0)
    assert out["cycle_test_duration_years"] is None


def test_t1_16_coefficients_mode_requires_the_convex_loss_model() -> None:
    """T1.16: throughput is defined on the DC-side powers, which a constant efficiency
    does not expose, so there would be nothing for c(T) to multiply."""
    with pytest.raises(InputValidationError) as exc:
        settings(_coefficients_form(), loss_model=CONSTANT)
    assert "convex_loss_epigraph" in str(exc.value)


def test_coefficients_mode_is_refused_outside_the_multi_year_formulation() -> None:
    form = _coefficients_form()
    form["core_formulation"] = "typical_year"
    with pytest.raises(InputValidationError) as exc:
        settings(form)
    message = str(exc.value)
    assert "multi-year" in message and "typical_year" in message


@pytest.mark.parametrize("missing", ["end_of_life_soh", "cycle_lifetime_to_eol_cycles"])
def test_coefficients_mode_requires_the_soh_budget_and_the_rating(missing: str) -> None:
    """The budget B calibrates the cycle magnitude, sets the floor and bounds the derived
    life, so the model cannot be assembled without both ends of the span."""
    form = _coefficients_form(**{missing: None})
    with pytest.raises(InputValidationError) as exc:
        settings(form)
    assert missing in str(exc.value)


def test_cycle_test_duration_must_be_positive_when_set() -> None:
    with pytest.raises(InputValidationError) as exc:
        settings(_coefficients_form(cycle_test_duration_years=0.0))
    assert "cycle_test_duration_years" in str(exc.value)
    out = settings(_coefficients_form(cycle_test_duration_years=1.8))
    assert out["cycle_test_duration_years"] == pytest.approx(1.8)


# ===========================================================================
# SoH span validation
# ===========================================================================


def test_end_of_life_soh_range_is_enforced() -> None:
    for bad in (0.0, 1.0, 1.2, -0.1):
        with pytest.raises(InputValidationError, match="end-of-life SoH"):
            settings(formulation(end_of_life_soh=bad))


def test_rated_cycle_life_must_be_positive() -> None:
    for bad in (0.0, -100.0):
        with pytest.raises(InputValidationError):
            settings(formulation(cycle_lifetime_to_eol_cycles=bad))


def test_non_numeric_scalars_are_refused_with_the_parameter_path() -> None:
    with pytest.raises(InputValidationError) as exc:
        settings(formulation(end_of_life_soh="most of it"))
    assert "end_of_life_soh" in str(exc.value)


def test_initial_soh_is_fixed_and_not_a_user_input() -> None:
    """Second-life cells would need the fade knee this linear model cannot represent, and a
    starting SoH below 1 also changes what the datasheet calibration means."""
    out = settings(_coefficients_form(initial_soh=0.9))
    assert out["initial_soh"] == 1.0


def test_technical_defaults_match_the_documented_values() -> None:
    out = validate_degradation_technical_inputs({})
    assert out["cycle_life_reference_dod"] == 0.8
    assert out["cycle_life_reference_temperature_c"] == 25.0
    assert out["enclosure_temperature_rise_c"] == 10.0
    assert out["calendar_fade_scale"] == 1.0
    assert out == {k: float(v) for k, v in DEGRADATION_TECHNICAL_DEFAULTS.items()}
    assert validate_degradation_technical_inputs(None) == out


def test_technical_values_are_read_and_coerced() -> None:
    out = validate_degradation_technical_inputs(
        {
            "cycle_life_reference_dod": "1.0",
            "cycle_life_reference_temperature_c": 23,
            "enclosure_temperature_rise_c": 0,
            "calendar_fade_scale": "2.72",
        }
    )
    assert out["cycle_life_reference_dod"] == 1.0
    assert out["cycle_life_reference_temperature_c"] == 23.0
    assert out["enclosure_temperature_rise_c"] == 0.0
    assert out["calendar_fade_scale"] == pytest.approx(2.72)


def test_blank_strings_fall_back_to_defaults() -> None:
    out = validate_degradation_technical_inputs({"enclosure_temperature_rise_c": "   "})
    assert out["enclosure_temperature_rise_c"] == 10.0


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("cycle_life_reference_dod", 0.0),
        ("cycle_life_reference_dod", 1.5),
        ("cycle_life_reference_temperature_c", 200.0),
        ("cycle_life_reference_temperature_c", float("nan")),
        ("enclosure_temperature_rise_c", -5.0),
        ("enclosure_temperature_rise_c", 45.0),
        ("calendar_fade_scale", -1.0),
        ("calendar_fade_scale", float("nan")),
    ],
)
def test_technical_ranges_are_enforced(key: str, value: float) -> None:
    with pytest.raises(InputValidationError) as exc:
        validate_degradation_technical_inputs({key: value})
    assert key in str(exc.value)


def test_non_numeric_technical_input_is_refused() -> None:
    with pytest.raises(InputValidationError) as exc:
        validate_degradation_technical_inputs({"enclosure_temperature_rise_c": "hot"})
    assert "enclosure_temperature_rise_c must be numeric" in str(exc.value)


def test_enclosure_guidance_is_in_the_error_message() -> None:
    """This is the module's most influential input and a pure judgement call, so a bad
    value should come back with the bracket to choose from rather than just a range."""
    with pytest.raises(InputValidationError) as exc:
        validate_degradation_technical_inputs({"enclosure_temperature_rise_c": -1.0})
    message = str(exc.value)
    assert "ventilated" in message and "sealed" in message


def test_reference_depth_far_from_the_operating_depth_warns() -> None:
    with pytest.warns(UserWarning, match="cycle_life_reference_dod"):
        validate_degradation_technical_inputs(
            {"cycle_life_reference_dod": 1.0}, depth_of_discharge=0.4
        )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        validate_degradation_technical_inputs(
            {"cycle_life_reference_dod": 0.8}, depth_of_discharge=0.8
        )


def test_technical_must_be_a_mapping() -> None:
    with pytest.raises(InputValidationError):
        validate_degradation_technical_inputs([("enclosure_temperature_rise_c", 10.0)])


# ===========================================================================
# Exogenous-rate suppression
# ===========================================================================


def _rate(value: float) -> xr.DataArray:
    return xr.DataArray(np.full(3, value), dims="inv_step", name="rate")


def test_exogenous_rate_is_zeroed_in_coefficients_mode() -> None:
    """The corrected model carries calendar ageing as a state variable, so applying a rate
    to the nameplate ceiling as well would remove the same capacity twice."""
    out, ignored = suppress_exogenous_battery_capacity_degradation(
        _rate(0.003), coefficients_enabled=True
    )
    assert float(np.max(np.abs(out.values))) == 0.0
    assert ignored is True


def test_a_zero_exogenous_rate_is_not_reported_as_ignored() -> None:
    out, ignored = suppress_exogenous_battery_capacity_degradation(
        _rate(0.0), coefficients_enabled=True
    )
    assert float(np.max(np.abs(out.values))) == 0.0
    assert ignored is False


def test_exogenous_rate_survives_outside_coefficients_mode() -> None:
    """Cycle fade is a different channel (throughput-driven) and does not conflict."""
    rate = _rate(0.003)
    out, ignored = suppress_exogenous_battery_capacity_degradation(
        rate, coefficients_enabled=False
    )
    assert out is rate
    assert ignored is False


def test_absent_exogenous_rate_is_passed_through() -> None:
    assert suppress_exogenous_battery_capacity_degradation(None, coefficients_enabled=True) == (
        None,
        False,
    )


def test_non_finite_entries_do_not_break_the_ignored_flag() -> None:
    rate = xr.DataArray(np.array([np.nan, 0.0, np.nan]), dims="inv_step")
    out, ignored = suppress_exogenous_battery_capacity_degradation(
        rate, coefficients_enabled=True
    )
    assert ignored is False
    assert out.shape == rate.shape
