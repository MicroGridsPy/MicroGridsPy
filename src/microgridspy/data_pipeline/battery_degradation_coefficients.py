from __future__ import annotations

"""
Offline semi-empirical battery-degradation coefficients.

This module holds the **single, canonical** coefficient source for the endogenous
battery-degradation layer: a linearised semi-empirical decomposition that collapses a
physics-grade electro-thermal + semi-empirical ageing tandem into a per-timestep linear
recursion on battery energy capacity,

    E_t = E_{t-1} - alpha * E^B - beta * P^BE

where ``E^B`` is nameplate energy, ``P^BE`` the hourly DC energy exchange, ``alpha``
the calendar-ageing coefficient (always active) and ``beta`` the cycle-ageing
coefficient (active only when power flows).

Why this is the *only* coefficient source
-----------------------------------------
A flat ``gamma`` derived from a rated cycle life is **temperature- and depth-blind**:
it charges the same wear per kWh at 15 C and 45 C, and for a shallow or a deep cycle
alike. Temperature and depth-of-discharge are the two dominant cycle-ageing stress
factors, so a sizing model that ignores them is first-order wrong in hot siting. These
curves carry both — ``beta`` is a cubic in ambient temperature fitted per DoD band and
chemistry, ``alpha`` a cubic in temperature per SoC band and chemistry — yet they stay
**exogenous coefficients** (static within a solve), so the optimisation remains linear.
Keeping a single, physically-grounded source avoids a "choose your fidelity" switch
whose low-fidelity option silently discards the stress factors that drive the sizing.

Predefined shape, user-scalable magnitude
------------------------------------------
Exactly like the generator partial-load model (a fixed normalized efficiency *shape*
scaled by the user's nominal efficiency), the temperature *shape* of the curves is
predefined (the fitted cubics below), and the user retains flexibility through a
parameter they already provide:

  * ``beta`` is scaled by the **cycle-life ratio** ``N_ref / N_user``: the validated
    shape is ported to a battery of a different rated cycle life without re-fitting.
    ``N_user`` is ``battery.technical.cycle_lifetime_to_eol_cycles``.
  * ``alpha`` is assumed **unchanged** across cycle life, so it is used as-is once the
    SoC band is selected from the DoD.

The polynomial coefficients are literature-fitted per chemistry and stress band; see
the project documentation for their provenance and references.
"""

from typing import Any

import numpy as np

LFP = "LFP"
NMC = "NMC"
LEAD_ACID = "lead_acid"
VALID_CHEMISTRIES = (LFP, NMC, LEAD_ACID)


class InputValidationError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# alpha (calendar) cubic coefficients: alpha_hour = c1*y^3 + c2*y^2 + c3*y + c4,
# y = T_env[degC] / 10. Keyed by chemistry then SoC band ("20" / "40" for Li-ion).
# ---------------------------------------------------------------------------
_ALPHA_POLY: dict[str, dict[str, tuple[float, float, float, float]]] = {
    LFP: {
        "20": (3.446908e-10, 1.240398e-09, 1.053498e-08, 1.970248e-08),
        "40": (4.485623e-10, 1.614189e-09, 1.370967e-08, 2.563976e-08),
    },
    NMC: {
        "20": (8.323820e-11, 8.912264e-10, 6.706961e-09, 1.814235e-08),
        "40": (9.208524e-11, 9.854044e-10, 7.418433e-09, 2.006416e-08),
    },
    # Lead-acid: a single constant calendar coefficient (no temperature fit was
    # possible; taken from the manufacturer storage-degradation datasheet at 25 C).
    LEAD_ACID: {"const": (0.0, 0.0, 0.0, 2.283105e-06)},
}

# ---------------------------------------------------------------------------
# beta (cycle) cubic coefficients: beta_hour = d1*y^3 + d2*y^2 + d3*y + d4,
# y = T_env[degC]/10 for Li-ion; for lead-acid the argument is z = DoD*10 - 2.
# Keyed by chemistry then DoD band (fraction).
# ---------------------------------------------------------------------------
_BETA_POLY: dict[str, dict[float, tuple[float, float, float, float]]] = {
    LFP: {
        0.5: (9.085917e-07, -4.051845e-06, 1.325690e-05, 6.130398e-06),
        0.6: (8.528446e-07, -4.189309e-06, 1.323273e-05, 3.853120e-06),
        0.7: (7.549737e-07, -3.721425e-06, 1.167026e-05, 3.269498e-06),
        0.8: (6.337047e-07, -2.869914e-06, 9.192472e-06, 3.861381e-06),
        0.9: (6.070837e-07, -2.769339e-06, 8.701044e-06, 3.423667e-06),
    },
    NMC: {
        0.5: (2.044415e-06, -6.759912e-06, 1.917865e-05, -3.760983e-06),
        0.6: (1.746515e-06, -5.739906e-06, 1.640342e-05, -3.106159e-06),
        0.7: (1.543396e-06, -5.033520e-06, 1.451821e-05, -2.625175e-06),
        0.8: (1.403785e-06, -4.530322e-06, 1.324309e-05, -2.212139e-06),
        0.9: (1.326799e-06, -4.210170e-06, 1.256349e-05, -1.862879e-06),
    },
    # Lead-acid: a single DoD-based cubic in z = DoD*10 - 2 (dissertation eq. 3.40).
    LEAD_ACID: {0.0: (-1.012639e-07, 1.534911e-06, -8.427153e-06, 2.813216e-05)},
}

# Reference cycle life at which each shape was fitted (dissertation Table 3.8).
# beta is scaled by N_ref / N_user to port the shape to the user's battery.
_REFERENCE_CYCLE_LIFE: dict[str, float] = {LFP: 6000.0, NMC: 2500.0, LEAD_ACID: 3000.0}

# Li-ion DoD bands with a fitted beta curve.
_LI_DOD_BANDS = (0.5, 0.6, 0.7, 0.8, 0.9)


def normalize_chemistry(raw: Any, *, default: str | None = None) -> str:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        if default is not None:
            return default
        raise InputValidationError(
            "battery.technical.chemistry is required when battery degradation is active. "
            f"Allowed values: {list(VALID_CHEMISTRIES)}."
        )
    value = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "lfp": LFP,
        "lifepo4": LFP,
        "lithium_lfp": LFP,
        "nmc": NMC,
        "nca": NMC,
        "lithium_nmc": NMC,
        "lead_acid": LEAD_ACID,
        "leadacid": LEAD_ACID,
        "pba": LEAD_ACID,
        "lead": LEAD_ACID,
    }
    if value not in aliases:
        raise InputValidationError(
            f"Invalid battery.technical.chemistry {raw!r}. Allowed values: {list(VALID_CHEMISTRIES)}."
        )
    return aliases[value]


def _select_alpha_band_key(chemistry: str, dod: float) -> str:
    """
    Map the (fixed) DoD to the SoC band used for the calendar coefficient
    (dissertation §3.2.2): Li-ion DoD in [0.5, 0.7] -> 40 % SoC band; DoD in
    [0.8, 0.9] -> 20 % SoC band. Lead-acid has a single constant band.
    """
    if chemistry == LEAD_ACID:
        return "const"
    return "20" if float(dod) >= 0.75 else "40"


def select_dod_band(chemistry: str, dod: float) -> float:
    """Snap a continuous DoD to the nearest fitted Li-ion band; lead-acid is band-less."""
    if chemistry == LEAD_ACID:
        return 0.0
    d = float(dod)
    if not (0.0 < d <= 1.0):
        raise InputValidationError("battery.technical.depth_of_discharge must be within (0, 1].")
    return min(_LI_DOD_BANDS, key=lambda b: abs(b - d))


def _cubic(coeffs: tuple[float, float, float, float], x: np.ndarray) -> np.ndarray:
    c1, c2, c3, c4 = coeffs
    return c1 * x**3 + c2 * x**2 + c3 * x + c4


def alpha_hourly(chemistry: str, dod: float, temperature_degc: np.ndarray) -> np.ndarray:
    """
    Hourly calendar-ageing coefficient (fraction of nameplate energy lost per hour),
    broadcast over the ambient-temperature array. Clipped at 0 (no capacity gain).
    """
    chem = normalize_chemistry(chemistry)
    band = _select_alpha_band_key(chem, dod)
    y = np.asarray(temperature_degc, dtype=float) / 10.0
    alpha = _cubic(_ALPHA_POLY[chem][band], y)
    return np.clip(alpha, 0.0, None)


def beta_hourly(
    chemistry: str,
    dod: float,
    temperature_degc: np.ndarray,
    *,
    user_cycle_life: float | None = None,
) -> np.ndarray:
    """
    Hourly cycle-ageing coefficient (fraction of nameplate energy lost per unit of
    DC energy exchanged), broadcast over the ambient-temperature array and scaled by
    the cycle-life ratio ``N_ref / N_user``. Clipped at 0.
    """
    chem = normalize_chemistry(chemistry)
    temp = np.asarray(temperature_degc, dtype=float)
    if chem == LEAD_ACID:
        # Lead-acid: cubic in z = DoD*10 - 2 (constant in temperature).
        z = float(dod) * 10.0 - 2.0
        base = float(_cubic(_BETA_POLY[LEAD_ACID][0.0], np.asarray([z], dtype=float))[0])
        beta = np.full_like(temp, base, dtype=float)
    else:
        band = select_dod_band(chem, dod)
        y = temp / 10.0
        beta = _cubic(_BETA_POLY[chem][band], y)
    beta = beta * cycle_life_scaling(chem, user_cycle_life)
    return np.clip(beta, 0.0, None)


def cycle_life_scaling(chemistry: str, user_cycle_life: float | None) -> float:
    """Return N_ref / N_user (1.0 when the user leaves the rated cycle life unset)."""
    chem = normalize_chemistry(chemistry)
    n_ref = _REFERENCE_CYCLE_LIFE[chem]
    if user_cycle_life in (None, "") or float(user_cycle_life) <= 0.0:
        return 1.0
    return n_ref / float(user_cycle_life)


def reference_cycle_life(chemistry: str) -> float:
    return _REFERENCE_CYCLE_LIFE[normalize_chemistry(chemistry)]


def evaluate_degradation_coefficients(
    *,
    chemistry: str,
    depth_of_discharge: float,
    temperature_degc: np.ndarray,
    user_cycle_life: float | None = None,
) -> dict[str, Any]:
    """
    Evaluate the full per-timestep coefficient arrays for a given ambient-temperature
    series. Returns a dict with ``alpha`` and ``beta`` arrays (same shape as
    ``temperature_degc``) plus resolved metadata. This is the single entry point used
    by both the data pipeline (to build model coefficients) and the Streamlit preview.
    """
    chem = normalize_chemistry(chemistry)
    temp = np.asarray(temperature_degc, dtype=float)
    if temp.size and (np.isnan(temp).any() or not np.isfinite(temp).all()):
        raise InputValidationError("ambient temperature series contains non-finite values.")
    alpha = alpha_hourly(chem, depth_of_discharge, temp)
    beta = beta_hourly(chem, depth_of_discharge, temp, user_cycle_life=user_cycle_life)
    return {
        "alpha": alpha,
        "beta": beta,
        "chemistry": chem,
        "alpha_soc_band_percent": (
            None if chem == LEAD_ACID else int(_select_alpha_band_key(chem, depth_of_discharge))
        ),
        "beta_dod_band": (None if chem == LEAD_ACID else select_dod_band(chem, depth_of_discharge)),
        "reference_cycle_life": _REFERENCE_CYCLE_LIFE[chem],
        "cycle_life_scaling": cycle_life_scaling(chem, user_cycle_life),
    }


def coefficient_curve_preview(
    *,
    chemistry: str,
    depth_of_discharge: float,
    user_cycle_life: float | None = None,
    temp_min: float = 10.0,
    temp_max: float = 50.0,
    n_points: int = 41,
) -> dict[str, np.ndarray]:
    """Dense temperature grid + alpha/beta for the input-visualization curve preview."""
    grid = np.linspace(float(temp_min), float(temp_max), int(n_points))
    res = evaluate_degradation_coefficients(
        chemistry=chemistry,
        depth_of_discharge=depth_of_discharge,
        temperature_degc=grid,
        user_cycle_life=user_cycle_life,
    )
    return {"temperature_degc": grid, "alpha": res["alpha"], "beta": res["beta"]}
