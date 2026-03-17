from __future__ import annotations

from pathlib import Path
import pandas as pd
import yaml


def read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def flatten_yaml_placeholder(path: Path) -> pd.DataFrame:
    payload = read_yaml(path)
    return pd.DataFrame([{"path": str(path), "top_keys": list(payload.keys()) if isinstance(payload, dict) else None}])

