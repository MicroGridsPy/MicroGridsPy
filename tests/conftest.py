"""Shared test configuration.

Solver preference
-----------------
Solved tests in this suite were written against HiGHS and name it explicitly. Gurobi is
several times faster on these models, which is what keeps the battery-degradation tests
usable as a pre-commit gate, so the requested solver is redirected here rather than
hard-coded in every test.

Override with ``MGP_TEST_SOLVER``:

    MGP_TEST_SOLVER=highs   reproduce the original behaviour
    MGP_TEST_SOLVER=keep    honour whatever each test asks for

If the preferred solver is not importable or has no usable licence, the request each test
made is passed through untouched, so the suite still runs (and still skips) as before.
"""

from __future__ import annotations

import os

_PREFERRED = os.environ.get("MGP_TEST_SOLVER", "gurobi").strip().lower()


def _is_usable(name: str) -> bool:
    if name == "gurobi":
        try:
            import gurobipy

            gurobipy.Env(params={"OutputFlag": 0})
        except Exception:
            return False
        return True
    if name == "highs":
        try:
            import highspy  # noqa: F401
        except Exception:
            return False
        return True
    return False


_ACTIVE = _PREFERRED if (_PREFERRED not in ("", "keep") and _is_usable(_PREFERRED)) else None


if _ACTIVE is not None:  # pragma: no branch - trivial
    import linopy

    _original_solve = linopy.Model.solve

    def _solve_with_preferred_solver(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        if args and isinstance(args[0], str):
            args = (_ACTIVE,) + tuple(args[1:])
        else:
            kwargs["solver_name"] = _ACTIVE
        return _original_solve(self, *args, **kwargs)

    linopy.Model.solve = _solve_with_preferred_solver  # type: ignore[method-assign]


def pytest_report_header() -> str:
    return f"solver: {_ACTIVE or 'as requested by each test'} (MGP_TEST_SOLVER={_PREFERRED})"
