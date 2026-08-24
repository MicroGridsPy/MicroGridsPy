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
    def formulation_json(self) -> Path:
        return self.inputs_dir / "formulation.json"
