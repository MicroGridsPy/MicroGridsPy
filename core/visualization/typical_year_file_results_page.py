from __future__ import annotations

from typing import Optional

from core.export.typical_year_results import TypicalYearResults
from core.visualization.typical_year_results_page import render_typical_year_results


def render_typical_year_results_from_files(file_results: TypicalYearResults, project_name: Optional[str]) -> None:
    render_typical_year_results(file_results, project_name)
