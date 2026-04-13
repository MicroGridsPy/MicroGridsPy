from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


CSV_DELIMITER_OPTIONS = {
    "Comma (,)": ",",
    "Semicolon (;)": ";",
    "Tab": "\t",
}

CSV_DECIMAL_OPTIONS = {
    "Dot (.)": ".",
    "Comma (,)": ",",
}

DEFAULT_CSV_DELIMITER = ","
DEFAULT_CSV_DECIMAL = "."


def normalize_csv_delimiter(value: Any) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        ",": ",",
        "comma": ",",
        ";": ";",
        "semicolon": ";",
        "\\t": "\t",
        "tab": "\t",
    }
    return aliases.get(raw, DEFAULT_CSV_DELIMITER)


def normalize_csv_decimal(value: Any) -> str:
    raw = str(value or "").strip()
    return raw if raw in {".", ","} else DEFAULT_CSV_DECIMAL


def csv_format_from_mapping(payload: Mapping[str, Any] | None) -> dict[str, str]:
    payload = payload or {}
    csv_format = payload.get("csv_format", {}) if isinstance(payload, Mapping) else {}
    if not isinstance(csv_format, Mapping):
        csv_format = {}
    return {
        "sep": normalize_csv_delimiter(csv_format.get("delimiter")),
        "decimal": normalize_csv_decimal(csv_format.get("decimal")),
    }


def _find_nearest_formulation_json(path: Path) -> Path | None:
    for parent in [path.parent, *path.parents]:
        candidate = parent / "formulation.json"
        if candidate.exists():
            return candidate
    return None


def read_csv_with_format(
    path: Path,
    *,
    header: int | list[int] | None = "infer",
    csv_format: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    fmt = (
        csv_format_from_mapping(csv_format)
        if csv_format is not None
        else load_csv_format_from_formulation(_find_nearest_formulation_json(path))
    )
    return pd.read_csv(path, header=header, sep=fmt["sep"], decimal=fmt["decimal"], **kwargs)


def write_csv_with_format(
    df: pd.DataFrame,
    path: Path,
    *,
    csv_format: Mapping[str, Any] | None = None,
    index: bool = False,
    **kwargs: Any,
) -> None:
    fmt = (
        csv_format_from_mapping(csv_format)
        if csv_format is not None
        else load_csv_format_from_formulation(_find_nearest_formulation_json(path))
    )
    df.to_csv(path, index=index, sep=fmt["sep"], decimal=fmt["decimal"], **kwargs)


def load_csv_format_from_formulation(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return csv_format_from_mapping(None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return csv_format_from_mapping(None)
    return csv_format_from_mapping(payload)
