"""Console entry point: ``microgridspy-gui`` launches the Streamlit app from anywhere.

Registered in ``pyproject.toml`` under ``[project.scripts]`` as
``microgridspy-gui = "microgridspy.app.launcher:main"``. It locates the
packaged ``Home.py`` via :mod:`importlib.resources`, so it works regardless of
where the package was installed or which directory the user runs it from.
"""

from __future__ import annotations

import sys
from importlib import resources


def main() -> None:
    try:
        from streamlit.web import cli as stcli  # streamlit is only needed for the GUI
    except ModuleNotFoundError as exc:  # pragma: no cover - trivial guard
        raise SystemExit(
            "The MicroGridsPy GUI requires the optional 'gui' extra.\n"
            'Install it with:  pip install "microgridspy[gui]"'
        ) from exc

    # Locate the packaged Home.py regardless of install location.
    with resources.as_file(resources.files("microgridspy.app") / "Home.py") as home:
        sys.argv = ["streamlit", "run", str(home)]
        sys.exit(stcli.main())


if __name__ == "__main__":
    main()
