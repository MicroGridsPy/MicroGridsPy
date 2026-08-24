"""MicroGridsPy: bottom-up optimization tool for planning mini-grids.

Public API::

    from microgridspy import SteadyStateModel, MultiYearModel

The Streamlit GUI lives in :mod:`microgridspy.app` and is installed only with
the ``[gui]`` extra; importing this package never imports Streamlit.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _version

from microgridspy.typical_year_model.model import SteadyStateModel
from microgridspy.multi_year_model.model import MultiYearModel

__all__ = ["SteadyStateModel", "MultiYearModel", "__version__"]

try:
    __version__ = _version("microgridspy")
except PackageNotFoundError:  # not installed (e.g. running from a source checkout)
    __version__ = "0.0.0+unknown"
