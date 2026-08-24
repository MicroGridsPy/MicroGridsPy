from __future__ import annotations

from microgridspy.app.typical_year_results_page import render_typical_year_results
from microgridspy.export.typical_year_results import TypicalYearResults


def render_typical_year_results_from_files(
    file_results: TypicalYearResults, project_name: str | None
) -> None:
    render_typical_year_results(file_results, project_name)
