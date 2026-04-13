from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr


CONSTANT_EFFICIENCY = "constant_efficiency"
CONVEX_LOSS_EPIGRAPH = "convex_loss_epigraph"
VALID_BATTERY_LOSS_MODELS = {CONSTANT_EFFICIENCY, CONVEX_LOSS_EPIGRAPH}
MONOTONIC_TOL = 1e-10
CONVEXITY_TOL = 1e-8
EFFICIENCY_TOL = 1e-9

NORMALIZED_CURVE = "normalized_multiplier"
LEGACY_ABSOLUTE_CURVE = "absolute_efficiency_legacy"


class InputValidationError(RuntimeError):
    pass


def normalize_battery_loss_model(raw: Any, *, default: str = CONSTANT_EFFICIENCY) -> str:
    if raw is None:
        return default
    value = str(raw).strip().lower()
    if not value:
        return default
    if value not in VALID_BATTERY_LOSS_MODELS:
        raise InputValidationError(
            f"Invalid battery loss model {raw!r}. Allowed values: "
            f"{sorted(VALID_BATTERY_LOSS_MODELS)}."
        )
    return value


def get_battery_loss_model_from_formulation(formulation: dict[str, Any] | None) -> str:
    if not isinstance(formulation, dict):
        return CONSTANT_EFFICIENCY
    battery_model = formulation.get("battery_model", {}) or {}
    if not isinstance(battery_model, dict):
        battery_model = {}
    return normalize_battery_loss_model(
        battery_model.get("loss_model", CONSTANT_EFFICIENCY),
        default=CONSTANT_EFFICIENCY,
    )


def _strictly_increasing(values: np.ndarray, *, name: str, path: Path) -> None:
    if np.any(np.diff(values) <= MONOTONIC_TOL):
        raise InputValidationError(
            f"{path.name}: column '{name}' must be strictly increasing."
        )


def _validate_convex_piecewise_loss(
    *,
    loss_name: str,
    x: np.ndarray,
    y: np.ndarray,
    path: Path,
) -> tuple[np.ndarray, np.ndarray]:
    dx = np.diff(x)
    if np.any(dx <= MONOTONIC_TOL):
        raise InputValidationError(
            f"{path.name}: cannot derive {loss_name} epigraph because power points are not strictly increasing."
        )
    slopes = np.diff(y) / dx
    if np.any(y < -CONVEXITY_TOL):
        raise InputValidationError(
            f"{path.name}: derived {loss_name} loss curve has negative losses, which is not physically valid."
        )
    if np.any(slopes < -CONVEXITY_TOL):
        raise InputValidationError(
            f"{path.name}: derived {loss_name} loss curve is decreasing, which is not physically valid."
        )
    if np.any(np.diff(slopes) < -CONVEXITY_TOL):
        raise InputValidationError(
            f"{path.name}: derived {loss_name} loss curve is not convex. "
            "Provide a curve whose implied loss function has non-decreasing segment slopes."
        )
    intercepts = y[:-1] - slopes * x[:-1]
    return slopes.astype(float), intercepts.astype(float)


def resolve_efficiency_curve_values(
    curve_values: np.ndarray,
    *,
    base_efficiency: float,
    path: Path,
    column_name: str,
    allow_zero: bool = False,
) -> tuple[np.ndarray, np.ndarray, str]:
    values = np.asarray(curve_values, dtype=float)
    lower_bound = -EFFICIENCY_TOL if allow_zero else EFFICIENCY_TOL
    if np.any(values < lower_bound):
        comparator = "[0, +inf)" if allow_zero else "(0, +inf)"
        raise InputValidationError(
            f"{path.name}: '{column_name}' must be in {comparator} when interpreted as a normalized efficiency multiplier."
        )

    if not np.isfinite(base_efficiency) or base_efficiency <= 0.0 or base_efficiency > 1.0 + EFFICIENCY_TOL:
        raise InputValidationError(
            f"{path.name}: invalid baseline efficiency {base_efficiency!r} for '{column_name}'. "
            "The corresponding YAML scalar efficiency must be in (0, 1]."
        )

    if np.isclose(values[-1], 1.0, atol=EFFICIENCY_TOL):
        multipliers = values
        absolute = base_efficiency * multipliers
        if np.any(absolute < lower_bound) or np.any(absolute > 1.0 + EFFICIENCY_TOL):
            raise InputValidationError(
                f"{path.name}: '{column_name}' interpreted as a normalized multiplier yields efficiencies outside the valid range after scaling by the YAML baseline efficiency."
            )
        return absolute.astype(float), multipliers.astype(float), NORMALIZED_CURVE

    upper_ok = np.all(values <= 1.0 + EFFICIENCY_TOL)
    lower_ok = np.all(values >= lower_bound)
    if upper_ok and lower_ok:
        safe_base = max(base_efficiency, EFFICIENCY_TOL)
        multipliers = values / safe_base
        return values.astype(float), multipliers.astype(float), LEGACY_ABSOLUTE_CURVE

    raise InputValidationError(
        f"{path.name}: '{column_name}' must either be a normalized multiplier with a full-load point equal to 1.0 "
        "or a legacy absolute-efficiency curve with all values in the valid efficiency range."
    )


def load_battery_loss_curve_dataset(
    path: Path,
    *,
    charge_efficiency_base: float,
    discharge_efficiency_base: float,
) -> xr.Dataset:
    """
    Parse a user-provided battery efficiency curve and derive convex epigraph
    coefficients for charge/discharge losses.

    Interpretation:
    - `relative_power_pu` is the relative DC-side battery power in (0, 1].
    - `charge_efficiency` and `discharge_efficiency` are preferably normalized
      multipliers relative to the scalar efficiencies in `battery.yaml`, with the
      full-load point equal to 1.0.
    - Legacy absolute-efficiency curves are still accepted for backward compatibility.
    - The absolute one-way efficiencies used in the model are:
        eta_ch = battery.yaml charge_efficiency * charge_curve_multiplier
        eta_dis = battery.yaml discharge_efficiency * discharge_curve_multiplier
    - Charge loss uses L_ch(P_dc) = P_ac - P_dc = P_dc * (1 / eta_ch - 1).
    - Discharge loss uses L_dis(P_dc) = P_dc - P_ac = P_dc * (1 - eta_dis).
    - Segment slopes/intercepts are stored in per-unit form versus x = P_dc / P_ref
      and y = L / P_ref, so the absolute epigraph is:
        L >= m * P_dc + q * P_ref
      where P_ref is the formulation-side DC power reference used to normalize the curve.
    """
    if not path.exists():
        raise InputValidationError(
            f"Missing required battery efficiency curve file: {path}"
        )

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise InputValidationError(f"Cannot read battery curve CSV {path}: {exc}") from exc

    required = ["relative_power_pu", "charge_efficiency", "discharge_efficiency"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise InputValidationError(
            f"{path.name}: missing required column(s) {missing}. Expected columns: {required}."
        )

    if len(df.index) < 2:
        raise InputValidationError(
            f"{path.name}: at least 2 rows are required to build a piecewise loss model."
        )

    rel = pd.to_numeric(df["relative_power_pu"], errors="coerce").to_numpy(dtype=float)
    charge_curve = pd.to_numeric(df["charge_efficiency"], errors="coerce").to_numpy(dtype=float)
    discharge_curve = pd.to_numeric(df["discharge_efficiency"], errors="coerce").to_numpy(dtype=float)

    if np.isnan(rel).any() or np.isnan(charge_curve).any() or np.isnan(discharge_curve).any():
        raise InputValidationError(
            f"{path.name}: required columns contain missing or non-numeric values."
        )

    if np.any(rel <= 0.0) or np.any(rel > 1.0):
        raise InputValidationError(
            f"{path.name}: 'relative_power_pu' must be in (0, 1]."
        )
    _strictly_increasing(rel, name="relative_power_pu", path=path)
    if not np.isclose(rel[-1], 1.0, atol=1e-9):
        raise InputValidationError(
            f"{path.name}: the last 'relative_power_pu' point must be 1.0 so the curve covers full load."
        )

    eta_ch, charge_multiplier, charge_mode = resolve_efficiency_curve_values(
        charge_curve,
        base_efficiency=float(charge_efficiency_base),
        path=path,
        column_name="charge_efficiency",
        allow_zero=False,
    )
    eta_dis, discharge_multiplier, discharge_mode = resolve_efficiency_curve_values(
        discharge_curve,
        base_efficiency=float(discharge_efficiency_base),
        path=path,
        column_name="discharge_efficiency",
        allow_zero=False,
    )

    x = np.concatenate(([0.0], rel))
    eta_ch_full = np.concatenate(([1.0], eta_ch))
    eta_dis_full = np.concatenate(([1.0], eta_dis))
    charge_multiplier_full = np.concatenate(([1.0], charge_multiplier))
    discharge_multiplier_full = np.concatenate(([1.0], discharge_multiplier))

    charge_loss_pu = x * ((1.0 / eta_ch_full) - 1.0)
    discharge_loss_pu = x * (1.0 - eta_dis_full)

    ch_slope, ch_intercept = _validate_convex_piecewise_loss(
        loss_name="charge",
        x=x,
        y=charge_loss_pu,
        path=path,
    )
    dis_slope, dis_intercept = _validate_convex_piecewise_loss(
        loss_name="discharge",
        x=x,
        y=discharge_loss_pu,
        path=path,
    )

    curve_point = xr.IndexVariable("battery_curve_point", np.arange(x.size))
    segment = xr.IndexVariable("battery_loss_segment", np.arange(x.size - 1))

    ds = xr.Dataset(
        data_vars={
            "battery_efficiency_curve_rel_power": xr.DataArray(
                x,
                coords={"battery_curve_point": curve_point},
                dims=("battery_curve_point",),
                attrs={"units": "pu_dc_power", "source_file": str(path)},
            ),
            "battery_efficiency_curve_charge_efficiency": xr.DataArray(
                eta_ch_full,
                coords={"battery_curve_point": curve_point},
                dims=("battery_curve_point",),
                attrs={"units": "-", "source_file": str(path)},
            ),
            "battery_efficiency_curve_discharge_efficiency": xr.DataArray(
                eta_dis_full,
                coords={"battery_curve_point": curve_point},
                dims=("battery_curve_point",),
                attrs={"units": "-", "source_file": str(path)},
            ),
            "battery_efficiency_curve_charge_multiplier": xr.DataArray(
                charge_multiplier_full,
                coords={"battery_curve_point": curve_point},
                dims=("battery_curve_point",),
                attrs={"units": "-", "source_file": str(path)},
            ),
            "battery_efficiency_curve_discharge_multiplier": xr.DataArray(
                discharge_multiplier_full,
                coords={"battery_curve_point": curve_point},
                dims=("battery_curve_point",),
                attrs={"units": "-", "source_file": str(path)},
            ),
            "battery_charge_loss_curve_pu": xr.DataArray(
                charge_loss_pu,
                coords={"battery_curve_point": curve_point},
                dims=("battery_curve_point",),
                attrs={"units": "pu_loss_per_pu_dc_power", "source_file": str(path)},
            ),
            "battery_discharge_loss_curve_pu": xr.DataArray(
                discharge_loss_pu,
                coords={"battery_curve_point": curve_point},
                dims=("battery_curve_point",),
                attrs={"units": "pu_loss_per_pu_dc_power", "source_file": str(path)},
            ),
            "battery_charge_loss_slope": xr.DataArray(
                ch_slope,
                coords={"battery_loss_segment": segment},
                dims=("battery_loss_segment",),
                attrs={"units": "loss_per_dc_power", "source_file": str(path)},
            ),
            "battery_charge_loss_intercept": xr.DataArray(
                ch_intercept,
                coords={"battery_loss_segment": segment},
                dims=("battery_loss_segment",),
                attrs={"units": "loss_per_reference_power", "source_file": str(path)},
            ),
            "battery_discharge_loss_slope": xr.DataArray(
                dis_slope,
                coords={"battery_loss_segment": segment},
                dims=("battery_loss_segment",),
                attrs={"units": "loss_per_dc_power", "source_file": str(path)},
            ),
            "battery_discharge_loss_intercept": xr.DataArray(
                dis_intercept,
                coords={"battery_loss_segment": segment},
                dims=("battery_loss_segment",),
                attrs={"units": "loss_per_reference_power", "source_file": str(path)},
            ),
        }
    )
    ds.attrs["battery_curve_semantics"] = {
        "relative_power_pu": "relative DC-side battery power, normalized to the formulation power reference",
        "charge_efficiency": "absolute one-way charge efficiency eta_ch = P_dc / P_ac after scaling by battery.yaml charge_efficiency",
        "discharge_efficiency": "absolute one-way discharge efficiency eta_dis = P_ac / P_dc after scaling by battery.yaml discharge_efficiency",
        "charge_multiplier": "normalized one-way charge-efficiency multiplier relative to battery.yaml charge_efficiency",
        "discharge_multiplier": "normalized one-way discharge-efficiency multiplier relative to battery.yaml discharge_efficiency",
        "epigraph_coefficients": "stored in per-unit form for L >= m * P_dc + q * P_ref using the active formulation power reference",
    }
    ds.attrs["battery_curve_interpretation"] = {
        "charge_efficiency": charge_mode,
        "discharge_efficiency": discharge_mode,
    }
    ds.attrs["settings"] = {"inputs_loaded": {"battery_efficiency_curve_csv": str(path)}}
    return ds
