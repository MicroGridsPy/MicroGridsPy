from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def inputs_dir(self) -> Path:
        return self.root / "inputs"

    @property
    def results_dir(self) -> Path:
        return self.root / "results"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def manifest_yaml(self) -> Path:
        return self.root / "project.yaml"

    @property
    def formulation_json(self) -> Path:
        return self.inputs_dir / "formulation.json"

    @property
    def parameters_yaml(self) -> Path:
        return self.inputs_dir / "parameters.yaml"

    @property
    def timeseries_csv(self) -> Path:
        return self.inputs_dir / "timeseries.csv"
