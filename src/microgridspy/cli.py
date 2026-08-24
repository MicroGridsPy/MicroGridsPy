"""Command-line interface: the ``microgridspy`` console command.

Registered in ``pyproject.toml`` as ``microgridspy = "microgridspy.cli:main"``.
It wraps the public API for common project operations from the terminal::

    microgridspy list
    microgridspy create my_site --resources solar wind
    microgridspy validate my_site
    microgridspy solve my_site --solver highs --export
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence


def _add_workspace_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workspace",
        metavar="DIR",
        help="workspace directory containing 'projects/' (default: current directory)",
    )


def _build_parser(version: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="microgridspy", description="MicroGridsPy command-line interface."
    )
    parser.add_argument("--version", action="version", version=f"microgridspy {version}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list projects in the workspace")
    _add_workspace_arg(p_list)

    p_create = sub.add_parser("create", help="create a new project and its input templates")
    p_create.add_argument("name")
    p_create.add_argument(
        "--formulation", choices=["steady_state", "dynamic"], default="steady_state"
    )
    p_create.add_argument("--system-type", choices=["off_grid", "on_grid"], default="off_grid")
    p_create.add_argument("--resources", nargs="+", default=["solar"])
    p_create.add_argument("--overwrite", action="store_true")
    _add_workspace_arg(p_create)

    p_val = sub.add_parser("validate", help="check a project's inputs")
    p_val.add_argument("name")
    _add_workspace_arg(p_val)

    p_solve = sub.add_parser("solve", help="build and solve a project")
    p_solve.add_argument("name")
    p_solve.add_argument("--solver", choices=["highs", "gurobi"], default="highs")
    p_solve.add_argument("--export", action="store_true", help="write results to the project folder")
    _add_workspace_arg(p_solve)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    import microgridspy as mgp

    args = _build_parser(mgp.__version__).parse_args(argv)

    if getattr(args, "workspace", None):
        mgp.set_workspace(args.workspace)

    try:
        if args.command == "list":
            projects = mgp.list_projects()
            print("\n".join(projects) if projects else "(no projects found)")
        elif args.command == "create":
            paths = mgp.create_project(
                args.name,
                formulation=args.formulation,
                system_type=args.system_type,
                resources=args.resources,
                overwrite=args.overwrite,
            )
            print(f"Created project at {paths.root}")
        elif args.command == "validate":
            mgp.validate_project(args.name)
            print(f"Project '{args.name}' is valid.")
        elif args.command == "solve":
            model = mgp.solve(args.name, solver=args.solver)
            results = model.results()
            print(
                f"Solved '{args.name}' with {args.solver}: "
                f"objective = {results.metadata.get('objective_value')}"
            )
            if args.export:
                written = mgp.export_results(results)
                print(f"Wrote {len(written)} result files.")
    except Exception as exc:  # surface a clean message, not a traceback
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
