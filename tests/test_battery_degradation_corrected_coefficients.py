"""Phase A acceptance tests for the corrected battery-degradation coefficient layer.

Tiers 1-3 of BATTERY_DEGRADATION_PORT_PLAN.md, restricted to what the coefficient
module can answer on its own (no solver, no data pipeline).

Every expected number here is either a closed form, a value from the corrected
coefficient table in Appendix C of battery_degradation_report_v2.tex, or a published
measurement. None is copied from the implementation.
"""

from __future__ import annotations

import hashlib
import math
import warnings
from pathlib import Path

import numpy as np
import pytest

from microgridspy.data_pipeline.battery_degradation_coefficients import (
    CALENDAR_FADE_SOURCES,
    DEFAULT_CYCLE_LIFE_REFERENCE_DOD,
    DEFAULT_CYCLE_LIFE_REFERENCE_TEMPERATURE_C,
    InputValidationError,
    calendar_fade_fraction,
    calendar_rate_per_year,
    cycle_calibration_summary,
    cycle_fade_coefficient,
    cycle_life_scaling,
    implied_calendar_life,
    normalize_chemistry,
    raw_calendar_fade_fraction,
)

# Defaults of the shipped configuration, used throughout.
B = 0.2  # usable SoH budget = initial_soh - end_of_life_soh
N_RATED = 6000.0
DOD_REF = 0.8
T_REF = 25.0
SOC_MEAN = 0.6  # = 1 - dod/2 at dod = 0.8

# Gas constant used to turn the Arrhenius coefficient into an activation energy.
R_GAS = 8.314462618


def c_of(
    temperature_degc,
    *,
    chemistry: str = "LFP",
    dod: float = DOD_REF,
    user_cycle_life: float | None = N_RATED,
    **kwargs,
) -> np.ndarray:
    """Marginal cycle-fade coefficient at the given temperature(s)."""
    return cycle_fade_coefficient(
        chemistry=chemistry,
        depth_of_discharge=dod,
        temperature_degc=np.atleast_1d(np.asarray(temperature_degc, dtype=float)),
        user_cycle_life=user_cycle_life,
        usable_soh_budget=B,
        reference_dod=DOD_REF,
        reference_temperature_degc=T_REF,
        **kwargs,
    )["c"]


def psi_of(dod: float, temperature_degc: float = T_REF, *, chemistry: str = "LFP") -> float:
    """Per-cycle fade Psi(D, T) = c(D, T) * D, on the raw fitted shape (no re-pinning)."""
    return float(c_of(temperature_degc, chemistry=chemistry, dod=dod, user_cycle_life=None)[0]) * dod


# ===========================================================================
# Tier 1 - closed-form invariants
# ===========================================================================


def test_t1_1_cycle_coefficient_at_the_datasheet_point_is_exact() -> None:
    """T1.1: c(dod_ref, T_ref) == B / (N_rated * dod_ref), exactly.

    This single assertion is the whole of report Defect 7. The pre-audit code gave
    3.391e-5 here against the 4.1667e-5 its own datasheet inputs imply.
    """
    expected = B / (N_RATED * DOD_REF)
    assert expected == pytest.approx(4.1666667e-5, rel=1e-9)
    assert float(c_of(T_REF)[0]) == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("n_rated", [3000.0, 6000.0, 10000.0])
def test_t1_2_delivered_cycle_life_equals_the_rating(n_rated: float) -> None:
    """T1.2: N_rated cycles at (dod_ref, T_ref) consume exactly the budget B."""
    psi = float(c_of(T_REF, user_cycle_life=n_rated)[0]) * DOD_REF
    assert B / psi == pytest.approx(n_rated, rel=1e-9)


@pytest.mark.parametrize("soh_eol", [0.70, 0.80, 0.85])
def test_t1_3_budget_flows_into_the_calibration(soh_eol: float) -> None:
    """T1.3: the rating is honoured for any end-of-life SoH, i.e. B calibrates lambda_cyc."""
    budget = 1.0 - soh_eol
    res = cycle_fade_coefficient(
        chemistry="LFP",
        depth_of_discharge=DOD_REF,
        temperature_degc=np.array([T_REF]),
        user_cycle_life=N_RATED,
        usable_soh_budget=budget,
        reference_dod=DOD_REF,
        reference_temperature_degc=T_REF,
    )
    psi = float(res["c"][0]) * DOD_REF
    assert B / psi * (budget / B) == pytest.approx(N_RATED, rel=1e-9)
    assert budget / psi == pytest.approx(N_RATED, rel=1e-9)


def test_t1_4_calendar_anchor_is_reproduced() -> None:
    """T1.4: 10 y at 6 degC and 50 % SoC loses exactly 3 %.

    The measured anchor is 96-98 % retention (J. Power Sources 2025, S0378775325016155);
    the model is pinned to the 97 % midpoint. Report Defect 9.
    """
    got = float(calendar_fade_fraction("LFP", 0.5, np.array([6.0]), 10.0)[0])
    assert got == pytest.approx(0.03, rel=1e-9)


def test_t1_5_unanchored_fit_reproduces_the_published_figure() -> None:
    """T1.5: the raw fit gives ~7 % at 0 degC, SoC 0, 50 y, as published (Ali 2023 Fig. 5).

    This is the check that confirms the functional form, independently of the anchor.
    """
    raw = float(raw_calendar_fade_fraction("LFP", 0.0, np.array([0.0]), 50.0)[0])
    assert raw == pytest.approx(0.07, abs=0.002)


def test_t1_6_calendar_rate_matches_the_corrected_table() -> None:
    """T1.6: r_cal(25 degC) at L = 7 and L = 20, against report Appendix C."""
    assert float(calendar_rate_per_year("LFP", SOC_MEAN, np.array([T_REF]), reference_years=7.0)[0]) == pytest.approx(
        9.14275e-3, rel=1e-5
    )
    assert float(calendar_rate_per_year("LFP", SOC_MEAN, np.array([T_REF]), reference_years=20.0)[0]) == pytest.approx(
        5.29654e-3, rel=1e-5
    )


def test_t1_7_anchor_scale_is_applied_once() -> None:
    """T1.7: lambda_cal = 0.3672, i.e. the fit is 2.72x pessimistic and is divided down once."""
    anchored = float(calendar_fade_fraction("LFP", SOC_MEAN, np.array([T_REF]), 10.0)[0])
    raw = float(raw_calendar_fade_fraction("LFP", SOC_MEAN, np.array([T_REF]), 10.0)[0])
    assert anchored / raw == pytest.approx(0.36720, rel=1e-4)


def test_t1_8_calendar_soc_is_continuous_in_depth_of_discharge() -> None:
    """T1.8: no step at dod = 0.75.

    The pre-audit code selected a storage SoC band by a threshold at dod >= 0.75, which
    jumped calendar fade 30 % between 0.74 and 0.76. SoC_mean = 1 - dod/2 is continuous.
    Report Defect 4.
    """
    lo = float(calendar_rate_per_year("LFP", 1.0 - 0.74 / 2, np.array([T_REF]), reference_years=7.0)[0])
    hi = float(calendar_rate_per_year("LFP", 1.0 - 0.76 / 2, np.array([T_REF]), reference_years=7.0)[0])
    assert abs(hi / lo - 1.0) < 0.02


def test_t1_9_implied_activation_energy_is_physical() -> None:
    """T1.9: b2 = -Ea/R implies Ea = 29.0 kJ/mol for LFP, inside the 20-50 published range."""
    from microgridspy.data_pipeline.battery_degradation_coefficients import _CALENDAR_FIT

    b2 = _CALENDAR_FIT["LFP"][3]
    ea_kj = -b2 * R_GAS / 1000.0
    assert ea_kj == pytest.approx(29.0, abs=0.3)
    assert 20.0 <= ea_kj <= 50.0


def test_t1_10_calendar_fade_doubles_per_17_6_degrees() -> None:
    """T1.10: local doubling temperature of the calendar channel at 25 degC."""
    from microgridspy.data_pipeline.battery_degradation_coefficients import _CALENDAR_FIT

    b2 = _CALENDAR_FIT["LFP"][3]
    kelvin = T_REF + 273.15
    doubling_k = math.log(2.0) * kelvin**2 / abs(b2)
    assert doubling_k == pytest.approx(17.6, abs=0.3)


def test_t1_11_psi_is_monotone_and_vanishes_at_zero_depth() -> None:
    """T1.11: Psi(D, T) increases in D and in T, and Psi(0, T) = 0."""
    depths = np.linspace(0.05, 1.0, 20)
    psi = np.array([psi_of(float(d)) for d in depths])
    assert np.all(np.diff(psi) > 0.0)
    assert psi_of(1e-9) == pytest.approx(0.0, abs=1e-12)
    temps = np.array([10.0, 20.0, 30.0, 40.0, 45.0])
    assert np.all(np.diff(c_of(temps)) > 0.0)


@pytest.mark.parametrize(("chemistry", "expected"), [("LFP", 1.0166), ("NMC", 1.0306)])
def test_t1_12_depth_effect_is_small(chemistry: str, expected: float) -> None:
    """T1.12: deepest/shallowest marginal slice ratio.

    This is the measurement that justifies deleting the SOC-band LP: the fitted law is
    all but linear in depth, so per-band states resolve a 1.7 % (LFP) effect.
    """
    shallowest = psi_of(0.1, chemistry=chemistry) - psi_of(1e-9, chemistry=chemistry)
    deepest = psi_of(1.0, chemistry=chemistry) - psi_of(0.9, chemistry=chemistry)
    assert deepest / shallowest == pytest.approx(expected, rel=5e-3)


def test_t1_13_cycle_channel_temperature_span() -> None:
    """T1.13: c(45)/c(10) = 4.28, the shape property the pre-audit code already had right."""
    ratio = float(c_of(45.0)[0]) / float(c_of(10.0)[0])
    assert ratio == pytest.approx(4.279, rel=5e-3)


def test_t1_14a_total_fade_within_one_year_is_a_hard_error() -> None:
    """T1.14: a cell that dies inside a year raises, naming the levers.

    The pre-audit behaviour was to clamp the implied life to its lower bound. At L = 1
    every year is a commissioning year, so SoH resets annually, fade never accumulates
    and the degradation state silently switches itself off.
    """
    with pytest.raises(InputValidationError) as exc:
        implied_calendar_life(
            "LFP", SOC_MEAN, 25.0, cycle_fade_per_year=0.25, usable_soh_budget=B
        )
    message = str(exc.value)
    assert "enclosure_temperature_rise_c" in message
    assert "calendar_fade_scale" in message


def test_t1_14b_sub_two_year_life_is_a_hard_error() -> None:
    with pytest.raises(InputValidationError) as exc:
        implied_calendar_life(
            "LFP", SOC_MEAN, 70.0, cycle_fade_per_year=0.0, usable_soh_budget=B, scale=2.0
        )
    assert "2" in str(exc.value)


def test_t1_15_implied_life_is_monotone_in_its_stresses() -> None:
    """T1.15: hotter or harder-cycled gives a shorter life; bisection is consistent."""
    lives_t = [
        implied_calendar_life("LFP", SOC_MEAN, t, cycle_fade_per_year=0.014, usable_soh_budget=B)
        for t in (20.0, 25.0, 30.0, 35.0, 40.0, 45.0)
    ]
    assert all(b < a for a, b in zip(lives_t, lives_t[1:]))
    lives_cyc = [
        implied_calendar_life("LFP", SOC_MEAN, 35.0, cycle_fade_per_year=f, usable_soh_budget=B)
        for f in (0.005, 0.010, 0.015, 0.020)
    ]
    assert all(b < a for a, b in zip(lives_cyc, lives_cyc[1:]))


def test_t1_15b_implied_life_solves_its_own_equation() -> None:
    """T1.15: at the returned L, calendar + cycle fade equals the budget."""
    life = implied_calendar_life(
        "LFP", SOC_MEAN, 35.0, cycle_fade_per_year=0.01427, usable_soh_budget=B
    )
    total = float(calendar_fade_fraction("LFP", SOC_MEAN, np.array([35.0]), life)[0]) + life * 0.01427
    assert total == pytest.approx(B, rel=1e-6)
    # The reference cluster of the formulation document: 35 degC cell, 1.427 %/yr cycle fade.
    assert life == pytest.approx(7.3178, rel=5e-3)


def test_t1_17_nmc_outside_the_fitted_window_is_refused() -> None:
    """T1.17: report Defect 6 made loud.

    The NMC cubic turns negative below 10 degC and the implementation clips it at zero,
    so an NMC battery at a cool site silently gets zero cycle fade. Refuse instead.
    """
    with pytest.raises(InputValidationError) as exc:
        c_of(np.array([5.0, 20.0]), chemistry="NMC")
    assert "Defect 6" in str(exc.value) or "fitted" in str(exc.value)
    with pytest.raises(InputValidationError):
        c_of(np.array([60.0]), chemistry="NMC")
    # Inside the window NMC is allowed, but it warns about Defect 10.
    with pytest.warns(UserWarning, match="NMC"):
        assert float(c_of(np.array([25.0]), chemistry="NMC")[0]) > 0.0


def test_t1_17b_lfp_outside_the_fitted_window_warns() -> None:
    with pytest.warns(UserWarning, match="10"):
        c_of(np.array([5.0, 25.0]))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        c_of(np.array([10.0, 25.0, 45.0]))


def test_t1_18_cycle_test_duration_removes_double_counted_calendar() -> None:
    """T1.18: report Defect 11, opt-in.

    A datasheet cycle life is measured on cells that also age by calendar while the test
    runs. Attributing that to cycling makes c too large by B/(B - Q_cal(tau_test)). Opting
    in must make c SMALLER. For a two-year continuous test at 25 degC the published
    estimate is 18-23 %, so the uncorrected coefficient is ~1.21x the corrected one.
    """
    baseline = float(c_of(T_REF)[0])
    corrected = float(c_of(T_REF, cycle_test_duration_years=2.0)[0])
    assert corrected < baseline
    assert baseline / corrected == pytest.approx(1.213, rel=0.02)
    # Default is unchanged behaviour: no silent change for existing projects.
    assert float(c_of(T_REF, cycle_test_duration_years=None)[0]) == pytest.approx(baseline, rel=1e-12)
    # A test whose own calendar ageing exhausts the budget leaves nothing to pin against.
    # A 5 % budget (end_of_life_soh 0.95) against a five-year rating test does it: calendar fade
    # alone is 5.4 % there.
    with pytest.raises(InputValidationError, match="already reaches the usable SoH budget"):
        cycle_life_scaling(
            "LFP", N_RATED, usable_soh_budget=0.05, cycle_test_duration_years=5.0
        )
    with pytest.raises(InputValidationError):
        cycle_life_scaling("LFP", N_RATED, usable_soh_budget=B, cycle_test_duration_years=0.0)


# ===========================================================================
# Tier 1 - scope: lead-acid is out
# ===========================================================================


def test_lead_acid_is_refused_with_a_scope_message() -> None:
    """Dropped deliberately: the calendar fit has no lead-acid row and no long-duration
    anchor, and lead-acid depth banding needs the Schiffer model."""
    for alias in ("lead_acid", "lead-acid", "PbA", "lead"):
        with pytest.raises(InputValidationError) as exc:
            normalize_chemistry(alias)
        assert "LFP" in str(exc.value) and "NMC" in str(exc.value)


def test_chemistry_aliases_still_resolve_for_li_ion() -> None:
    assert normalize_chemistry("LFP") == "LFP"
    assert normalize_chemistry("lifepo4") == "LFP"
    assert normalize_chemistry("nmc") == "NMC"
    assert normalize_chemistry("NCA") == "NMC"
    assert normalize_chemistry(None, default="LFP") == "LFP"
    with pytest.raises(InputValidationError):
        normalize_chemistry("sodium_ion")


def test_defaults_follow_the_datasheet_convention() -> None:
    assert DEFAULT_CYCLE_LIFE_REFERENCE_DOD == 0.8
    assert DEFAULT_CYCLE_LIFE_REFERENCE_TEMPERATURE_C == 25.0
    assert "Ali" in CALENDAR_FADE_SOURCES
    assert "S0378775325016155" in CALENDAR_FADE_SOURCES


def test_cycle_life_scaling_requires_a_valid_budget() -> None:
    for bad in (0.0, -0.1, 1.5):
        with pytest.raises(InputValidationError):
            cycle_life_scaling("LFP", N_RATED, usable_soh_budget=bad)
    # No rating given -> the raw fitted shape, scaling 1.0.
    assert cycle_life_scaling("LFP", None, usable_soh_budget=B) == pytest.approx(1.0)
    # Halving the rating doubles the magnitude.
    full = cycle_life_scaling("LFP", N_RATED, usable_soh_budget=B)
    half = cycle_life_scaling("LFP", N_RATED / 2.0, usable_soh_budget=B)
    assert half == pytest.approx(2.0 * full, rel=1e-12)
    assert full == pytest.approx(1.22865, rel=1e-4)


def test_calendar_rate_scale_is_linear_and_non_negative() -> None:
    base = float(calendar_rate_per_year("LFP", SOC_MEAN, np.array([T_REF]), reference_years=7.0)[0])
    scaled = float(
        calendar_rate_per_year("LFP", SOC_MEAN, np.array([T_REF]), reference_years=7.0, scale=2.72)[0]
    )
    assert scaled == pytest.approx(2.72 * base, rel=1e-12)
    with pytest.raises(InputValidationError):
        calendar_rate_per_year("LFP", SOC_MEAN, np.array([T_REF]), reference_years=7.0, scale=-1.0)


def test_invalid_inputs_are_refused() -> None:
    with pytest.raises(InputValidationError):
        c_of(T_REF, dod=0.0)
    with pytest.raises(InputValidationError):
        c_of(T_REF, dod=1.5)
    with pytest.raises(InputValidationError):
        c_of(np.array([np.nan, 25.0]))
    with pytest.raises(InputValidationError):
        calendar_fade_fraction("LFP", 1.5, np.array([T_REF]), 10.0)
    with pytest.raises(InputValidationError):
        calendar_fade_fraction("LFP", 0.6, np.array([T_REF]), 0.0)


# ===========================================================================
# Tier 2 - cross-implementation equivalence with the corrected physics
# ===========================================================================

# Report Appendix C, LFP, dod 0.8, B 0.2, SoC_mean 0.6, phi_cal 1.
_APPENDIX_C_T = np.array([10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0])
_APPENDIX_C_C = np.array(
    [2.37996e-5, 2.85421e-5, 3.43808e-5, 4.16667e-5, 5.09158e-5, 6.29195e-5, 7.89563e-5, 1.01235e-4, 1.33934e-4]
)
_APPENDIX_C_RCAL_L7 = np.array(
    [4.91603e-3, 6.08909e-3, 7.48721e-3, 9.14275e-3, 1.10910e-2, 1.33704e-2, 1.60223e-2, 1.90913e-2, 2.26251e-2]
)
_APPENDIX_C_RCAL_L20 = np.array(
    [2.84793e-3, 3.52751e-3, 4.33746e-3, 5.29654e-3, 6.42521e-3, 7.74568e-3, 9.28197e-3, 1.10599e-2, 1.31071e-2]
)


def test_t2_1_cycle_coefficient_matches_the_corrected_physics_in_window() -> None:
    """T2.1: within the fitted window, agreement with the corrected physics is <= 2 %.

    The residual is the cubic temperature surrogate (report Defect 6). The lambda_cyc
    re-pinning at (dod_ref, T_ref) absorbs Defects 1, 2 and 5 as a level shift, which is
    why the shipped Psi shape needs no regeneration for LFP.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        got = c_of(_APPENDIX_C_T[:-1])
    deviation = np.abs(got / _APPENDIX_C_C[:-1] - 1.0)
    assert deviation.max() < 0.02, f"worst deviation {100 * deviation.max():.2f} % at {_APPENDIX_C_T[int(deviation.argmax())]} degC"


def test_t2_2_cycle_coefficient_at_fifty_degrees_is_the_known_surrogate_error() -> None:
    """T2.2: -3.5 % at 50 degC, recorded rather than hidden. Above 50 degC, do not use."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        got = float(c_of(50.0)[0])
    assert got / _APPENDIX_C_C[-1] - 1.0 == pytest.approx(-0.0346, abs=0.01)


def test_t2_3_calendar_rate_matches_the_corrected_physics_exactly() -> None:
    """T2.3: the calendar channel is not a surrogate, so it should agree to roundoff."""
    for years, reference in ((7.0, _APPENDIX_C_RCAL_L7), (20.0, _APPENDIX_C_RCAL_L20)):
        got = calendar_rate_per_year("LFP", SOC_MEAN, _APPENDIX_C_T, reference_years=years)
        assert np.abs(got / reference - 1.0).max() < 1e-4


def test_t1_24_t2_5_shipped_coefficient_file_is_pinned() -> None:
    """T2.5: regenerating the distilled Psi shape must be a deliberate act.

    This hash is shared with the reference engine. If it changes, Tier 2 tolerances and
    the lambda_cyc value in the documentation have to be revisited together.
    """
    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "microgridspy"
        / "data_pipeline"
        / "layer1_liion_coefficients.json"
    )
    digest = hashlib.md5(path.read_bytes()).hexdigest()
    assert digest == "e2428b5f202273f046c1e0b675fcc13c"


# ===========================================================================
# Tier 3 - literature benchmarks
# ===========================================================================


def test_t3_1_ten_year_shelf_test() -> None:
    """T3.1: Sony/Murata LFP/C, 10 y at 6 degC / 50 % SoC, 96-98 % retention."""
    retention = 1.0 - float(calendar_fade_fraction("LFP", 0.5, np.array([6.0]), 10.0)[0])
    assert 0.96 <= retention <= 0.98


def test_t3_2_published_fifty_year_point() -> None:
    """T3.2: Ali et al. 2023 Fig. 5 - 0 degC, SoC 0, 50 y -> 7 %."""
    assert float(raw_calendar_fade_fraction("LFP", 0.0, np.array([0.0]), 50.0)[0]) == pytest.approx(
        0.07, abs=0.002
    )


def test_t3_3_soc_sensitivity_is_recorded_as_a_known_discrepancy() -> None:
    """T3.3: the SoC term is 3.73x empty-to-full against ~2x measured by Naumann 2018.

    This is deliberately not an agreement test. The fit is 1.9x steeper than the one
    independent measurement of this term, and the model's fixed SoC_mean = 1 - dod/2
    under-represents a PV battery that sits near full charge through the dry season.
    The assertion pins the number so it cannot drift unnoticed.
    """
    empty = float(raw_calendar_fade_fraction("LFP", 0.0, np.array([T_REF]), 10.0)[0])
    full = float(raw_calendar_fade_fraction("LFP", 1.0, np.array([T_REF]), 10.0)[0])
    assert full / empty == pytest.approx(math.exp(1.317), rel=1e-6)
    assert full / empty == pytest.approx(3.73, rel=0.01)


def test_t3_4_calendar_rate_spans_the_literature_band() -> None:
    """T3.4: phi_cal in [1.0, 2.72] brackets 0.76-2.07 %/yr at 25 degC.

    1.0 is the anchored (central) model; 2.72 recovers the unscaled Ali envelope. Both ends
    should be reported in any study that uses the module.

    Note the horizon: because the law is sub-linear in time, the linear-equivalent rate depends
    on the linearisation window, and the two literature figures above are quoted at L = 10.
    The same pair at L = 7 is 0.91 / 2.49 %/yr and at L = 20 it is 0.53 / 1.44 %/yr. Any
    comparison of a %/yr calendar rate has to state its horizon.
    """
    anchored = float(calendar_rate_per_year("LFP", SOC_MEAN, np.array([T_REF]), reference_years=10.0)[0])
    unscaled = float(
        calendar_rate_per_year("LFP", SOC_MEAN, np.array([T_REF]), reference_years=10.0, scale=2.72)[0]
    )
    assert anchored == pytest.approx(0.0076, abs=1e-4)
    assert unscaled == pytest.approx(0.0207, abs=5e-4)
    assert unscaled / anchored == pytest.approx(2.72, rel=1e-9)
    # The horizon dependence itself, so a future change to the linearisation is visible.
    assert float(
        calendar_rate_per_year("LFP", SOC_MEAN, np.array([T_REF]), reference_years=7.0)[0]
    ) > anchored
    assert float(
        calendar_rate_per_year("LFP", SOC_MEAN, np.array([T_REF]), reference_years=20.0)[0]
    ) < anchored


def test_t3_7_throughput_to_end_of_life_is_flat_in_depth() -> None:
    """T3.7: equivalent full cycles to end of life, on the raw fitted shape.

    5892 at full depth against 5925 at 40 % depth: flat to 0.6 %. This is the finding
    behind the throughput-limited assumption - total kWh sets the lifetime, the depth of
    the individual cycles does not.
    """
    fec_full = B / float(c_of(T_REF, dod=1.0, user_cycle_life=None)[0])
    fec_shallow = B / float(c_of(T_REF, dod=0.4, user_cycle_life=None)[0])
    assert fec_full == pytest.approx(5892.0, rel=5e-3)
    assert fec_shallow == pytest.approx(5925.0, rel=5e-3)
    assert abs(fec_shallow / fec_full - 1.0) < 0.006


def test_t3_8_shallow_cycling_buys_cycles_not_kilowatt_hours() -> None:
    """T3.8: 14812 cycles at 40 % depth against 5892 at full depth - 2.5x the cycles,
    the same total throughput."""
    cycles_full = B / psi_of(1.0)
    cycles_shallow = B / psi_of(0.4)
    assert cycles_shallow == pytest.approx(14812.0, rel=5e-3)
    assert cycles_shallow / cycles_full == pytest.approx(2.51, rel=0.02)


# ===========================================================================
# Defect 11 -- the datasheet test also aged on the calendar (T1.19-T1.22)
# ===========================================================================


@pytest.mark.parametrize("tau", [1.5, 2.0, 3.0])
@pytest.mark.parametrize("phi", [1.0, 1.75])
def test_t1_19_rerun_datasheet_test_consumes_exactly_the_budget(tau: float, phi: float) -> None:
    """T1.19: replaying the datasheet test closes the budget exactly.

    N_rated cycles at (delta_ref, T_ref) consume N * delta_ref * c(T_ref) of capacity, and the
    test's own calendar ageing consumes phi * lambda_cal * Q_raw(SoC_mean, T_ref, 365 tau). Once
    the calendar share is removed from the cycle calibration, the two together must equal B --
    neither more (double count) nor less.
    """
    summary = cycle_calibration_summary(
        "LFP",
        N_RATED,
        usable_soh_budget=B,
        reference_dod=DOD_REF,
        reference_temperature_degc=T_REF,
        cycle_test_duration_years=tau,
        calendar_fade_scale=phi,
        calendar_mean_soc=SOC_MEAN,
    )
    replayed = N_RATED * DOD_REF * summary["c_at_tref"] + summary["test_time_calendar_fade"]
    assert abs(replayed - B) < 1e-9
    # and the calendar share is the anchored law scaled by phi, not something else
    expected_calendar = phi * float(calendar_fade_fraction("LFP", SOC_MEAN, np.array([T_REF]), tau)[0])
    assert summary["test_time_calendar_fade"] == pytest.approx(expected_calendar, rel=1e-12)


def test_t1_20_test_time_calendar_alone_exhausting_the_budget_is_refused() -> None:
    """T1.20: a test whose own calendar ageing reaches B leaves nothing to pin cycling to."""
    with pytest.raises(InputValidationError) as exc:
        cycle_life_scaling(
            "LFP", N_RATED, usable_soh_budget=B, cycle_test_duration_years=20.0,
            calendar_fade_scale=2.72, calendar_mean_soc=SOC_MEAN,
        )
    message = str(exc.value)
    assert "tau=20" in message
    assert "Q_cal(tau)" in message


def test_t1_21_null_duration_reproduces_the_old_coefficients() -> None:
    """T1.21: tau = null is the old behaviour, to round-off, over the whole temperature grid."""
    from microgridspy.data_pipeline.battery_degradation_coefficients import _psi_raw

    grid = np.linspace(10.0, 50.0, 81)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        new = c_of(grid, cycle_test_duration_years=None)
    old = _psi_raw("LFP", DOD_REF, grid) / DOD_REF * (
        B / (N_RATED * float(_psi_raw("LFP", DOD_REF, np.array([T_REF]))[0]))
    )
    assert np.max(np.abs(new - old)) < 1e-12


@pytest.mark.parametrize("bad", [0.0, -1.0, 25.0, "two years"])
def test_t1_22_test_duration_validation(bad) -> None:
    """T1.22: null or a number in (0, 20]; anything else names the key path."""
    from microgridspy.data_pipeline.battery_degradation_model import get_battery_degradation_settings

    formulation = {
        "core_formulation": "multi_year",
        "battery_model": {
            "loss_model": "convex_loss_epigraph",
            "degradation_model": {
                "coefficients_enabled": True,
                "end_of_life_soh": 0.8,
                "cycle_lifetime_to_eol_cycles": 6000,
                "cycle_test_duration_years": bad,
            },
        },
    }
    with pytest.raises(InputValidationError) as exc:
        get_battery_degradation_settings(formulation, battery_loss_model="convex_loss_epigraph")
    assert "battery_model.degradation_model.cycle_test_duration_years" in str(exc.value)


def test_t1_22b_valid_test_durations_pass() -> None:
    from microgridspy.data_pipeline.battery_degradation_model import get_battery_degradation_settings

    for good in (None, 0.5, 2.0, 20.0):
        formulation = {
            "core_formulation": "multi_year",
            "battery_model": {"degradation_model": {"cycle_test_duration_years": good}},
        }
        out = get_battery_degradation_settings(formulation, battery_loss_model="constant_efficiency")
        assert out["cycle_test_duration_years"] == good
