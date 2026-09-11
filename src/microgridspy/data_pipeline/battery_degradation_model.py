from __future__ import annotations

from typing import Any

from microgridspy.data_pipeline.battery_loss_model import CONVEX_LOSS_EPIGRAPH


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


def get_battery_degradation_settings(
    formulation: dict[str, Any] | None,
    *,
    battery_loss_model: str,
) -> dict[str, Any]:
    """
    Resolve the multi-year (dynamic) battery cycle-fade degradation settings from the
    formulation. The coefficient source is the semi-empirical curve module
    (``battery_degradation_coefficients``); the actual temperature- and DoD-aware
    coefficients are evaluated in the data loader from ``ambient_temperature.csv`` and
    the battery chemistry. This function only validates the enabling flags and the SoH
    span inputs.
    """
    if not isinstance(formulation, dict):
        formulation = {}
    battery_model = formulation.get("battery_model", {}) or {}
    if not isinstance(battery_model, dict):
        battery_model = {}
    degradation_model = battery_model.get("degradation_model", {}) or {}
    if not isinstance(degradation_model, dict):
        degradation_model = {}

    cycle_fade_enabled = _coerce_bool(
        degradation_model.get("cycle_fade_enabled", False), default=False
    )

    # Cycle-fade representation:
    #   "single_beta"    -> flat-in-depth beta(T,DoD) throughput term (default, current behaviour)
    #   "marginal_bands" -> depth-resolved convex per-SOC-band marginals c_k(T) (emergent DoD)
    raw_mode = str(degradation_model.get("cycle_fade_mode", "single_beta")).strip().lower()
    if raw_mode not in {"single_beta", "marginal_bands"}:
        raise InputValidationError(
            "battery_model.degradation_model.cycle_fade_mode must be 'single_beta' or "
            f"'marginal_bands' (got {raw_mode!r})."
        )
    cycle_fade_mode = raw_mode
    n_soc_bands = degradation_model.get("n_soc_bands", 5)
    try:
        n_soc_bands = int(n_soc_bands)
    except Exception as exc:
        raise InputValidationError(
            "battery_model.degradation_model.n_soc_bands must be an integer."
        ) from exc
    if cycle_fade_mode == "marginal_bands" and n_soc_bands < 1:
        raise InputValidationError("n_soc_bands must be >= 1 for marginal_bands mode.")

    initial_soh = _read_optional_float(degradation_model.get("initial_soh", 1.0), "initial_soh", 1.0)
    end_of_life_soh = _read_optional_float(
        degradation_model.get("end_of_life_soh", None), "end_of_life_soh", None
    )
    cycle_lifetime_to_eol_cycles = _read_optional_float(
        degradation_model.get("cycle_lifetime_to_eol_cycles", None),
        "cycle_lifetime_to_eol_cycles",
        None,
    )

    if cycle_fade_enabled and battery_loss_model != CONVEX_LOSS_EPIGRAPH:
        raise InputValidationError(
            "battery_model.degradation_model requires "
            "battery_model.loss_model='convex_loss_epigraph' because the endogenous "
            "cycle-fade degradation layer is defined on the internal DC-side battery powers."
        )
    if initial_soh is not None and not (0.0 <= initial_soh <= 1.0):
        raise InputValidationError("Battery initial SoH must be within [0, 1].")
    if end_of_life_soh is not None and not (0.0 < end_of_life_soh <= initial_soh):
        raise InputValidationError("Battery end-of-life SoH must be within (0, initial_soh].")
    if cycle_lifetime_to_eol_cycles is not None and cycle_lifetime_to_eol_cycles <= 0.0:
        raise InputValidationError(
            "battery_model.degradation_model.cycle_lifetime_to_eol_cycles must be > 0."
        )

    return {
        "cycle_fade_enabled": cycle_fade_enabled,
        "cycle_fade_mode": cycle_fade_mode,
        "n_soc_bands": n_soc_bands,
        "initial_soh": initial_soh,
        "end_of_life_soh": end_of_life_soh,
        "cycle_lifetime_to_eol_cycles": cycle_lifetime_to_eol_cycles,
        "endogenous_degradation_enabled": bool(cycle_fade_enabled),
    }


def _read_optional_float(raw: Any, name: str, default: float | None) -> float | None:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return default
    try:
        return float(raw)
    except Exception as exc:
        raise InputValidationError(
            f"battery_model.degradation_model.{name} must be numeric."
        ) from exc
