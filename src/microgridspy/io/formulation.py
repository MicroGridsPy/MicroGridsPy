"""Canonical names for the two planning formulations.

``typical_year``
    One representative year, solved with an annualized (equivalent annual cost)
    objective. Implemented by `microgridspy.typical_year_model`.

``multi_year``
    An explicit multi-year horizon with discounted cash flows and optional staged
    capacity expansion. Implemented by `microgridspy.multi_year_model`.

These are the values written to and read from a project's ``formulation.json``.
"""

from __future__ import annotations

TYPICAL_YEAR = "typical_year"
MULTI_YEAR = "multi_year"

VALID_FORMULATIONS = (TYPICAL_YEAR, MULTI_YEAR)
