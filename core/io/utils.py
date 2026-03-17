from __future__ import annotations

import contextlib
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd

from core.io.paths import ProjectPaths
from core.io.jsonio import ensure_parent_dir


class _TeeTextStream:
    def __init__(self, *streams) -> None:
        self._streams = streams

    def write(self, data: str) -> int:
        for stream in self._streams:
            try:
                stream.write(data)
            except Exception:
                pass
        return len(data)

    def flush(self) -> None:
        for stream in self._streams:
            try:
                stream.flush()
            except Exception:
                pass


@contextlib.contextmanager
def tee_console_output(log_path: Path):
    ensure_parent_dir(log_path)
    with log_path.open("w", encoding="utf-8", errors="replace") as handle:
        stdout_tee = _TeeTextStream(sys.stdout, handle)
        stderr_tee = _TeeTextStream(sys.stderr, handle)
        with contextlib.redirect_stdout(stdout_tee), contextlib.redirect_stderr(stderr_tee):
            yield


def sanitize_project_name(name: str) -> str:
    """Sanitize a project name to be filesystem-friendly."""
    name = (name or "").strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9_\-]", "", name)
    return name


def get_projects_root(base_dir: Path | None = None) -> Path:
    """Get the root directory where projects are stored."""
    if base_dir is None:
        base_dir = Path.cwd()
    return base_dir / "projects"


def project_paths(project_name: str, base_dir: Path | None = None) -> ProjectPaths:
    """Get the paths for a given project."""
    projects_root = get_projects_root(base_dir)
    return ProjectPaths(root=projects_root / project_name)


def project_exists(project_name: str, base_dir: Path | None = None) -> bool:
    """Ensure that a project with the given name exists."""
    p = project_paths(project_name, base_dir).root
    return p.exists() and p.is_dir()


def ensure_project_structure(project_name: str, base_dir: Path | None = None) -> ProjectPaths:
    """Ensure that the project directory structure exists."""
    paths = project_paths(project_name, base_dir)
    for directory in (paths.root, paths.inputs_dir, paths.results_dir, paths.logs_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return paths


def simulate_grid_availability_typical_year(
    avg_outages_per_year: float,
    avg_outage_duration_min: float,
    *,
    periods_per_year: int = 8760,
    scale_tbo: float = 1620 / 60.0,
    shape_tbo: float = 0.77,
    scale_od: float = 36 / 60.0,
    shape_od: float = 0.56,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    Simulate grid availability for a single representative year (steady_state).

    Returns:
      np.ndarray shape (periods_per_year,) with values in {0.0, 1.0}.

    Logic (same spirit as your original Weibull approach):
      - Total outage hours = (avg_outages_per_year * avg_outage_duration_min / 60)
      - Sample outage durations from Weibull(scale_od, shape_od) until total outage time is reached
      - Sample times-between-outages from Weibull(scale_tbo, shape_tbo), then scale to fill remaining up-time
      - Build a 1D binary availability sequence over periods_per_year
    """
    if rng is None:
        rng = np.random.default_rng()

    # Edge cases: no outages (or nonsensical inputs) -> always available
    if avg_outages_per_year <= 0 or avg_outage_duration_min <= 0:
        return np.ones((periods_per_year,), dtype=float)

    total_outage_hours = (avg_outages_per_year * avg_outage_duration_min) / 60.0
    total_hours = float(periods_per_year)

    # Cap to avoid pathological inputs
    total_outage_hours = max(0.0, min(total_outage_hours, total_hours))

    if total_outage_hours == 0.0:
        return np.ones((periods_per_year,), dtype=float)

    # --- Sample outage durations until total outage hours is met ---
    samples_od: list[float] = []
    sum_od = 0.0

    # Avoid infinite loops in bad parameterization
    max_iter = 1_000_000
    it = 0
    while sum_od < total_outage_hours and it < max_iter:
        od = float(scale_od * rng.weibull(shape_od))
        # Guard: if od is 0 repeatedly, break to avoid infinite loop
        if od <= 0:
            it += 1
            continue
        samples_od.append(od)
        sum_od += od
        if sum_od > total_outage_hours:
            samples_od[-1] -= (sum_od - total_outage_hours)
            sum_od = total_outage_hours
        it += 1

    if not samples_od:
        # fallback: if Weibull produced nothing usable
        return np.ones((periods_per_year,), dtype=float)

    n_events = len(samples_od)

    # --- Sample time-between-outages (TBO) and scale to fit remaining uptime ---
    # Remaining uptime in hours = total_hours - total_outage_hours
    remaining_uptime = total_hours - total_outage_hours

    samples_tbo = scale_tbo * rng.weibull(shape_tbo, size=n_events)
    sum_tbo = float(np.sum(samples_tbo))

    if sum_tbo <= 0:
        # If all TBO are 0, just place outages back-to-back at start
        seq = [0.0] * int(round(total_outage_hours)) + [1.0] * int(round(remaining_uptime))
    else:
        k = remaining_uptime / sum_tbo
        samples_tbo = samples_tbo * max(k, 0.0)

        # --- Build the sequence as alternating up (1) and down (0) blocks ---
        seq: list[float] = []
        for tbo, od in zip(samples_tbo, samples_od):
            seq.extend([1.0] * int(round(tbo)))
            seq.extend([0.0] * int(round(od)))
            if len(seq) >= periods_per_year:
                seq = seq[:periods_per_year]
                break

        if len(seq) < periods_per_year:
            seq.extend([1.0] * (periods_per_year - len(seq)))

    return np.asarray(seq[:periods_per_year], dtype=float)

def simulate_grid_availability_dynamic(
    avg_outages_per_year: float,
    avg_outage_duration_min: float,
    *,
    years: int,
    periods_per_year: int = 8760,
    first_year_connection: int | None = None,
    # Weibull params (same meaning as steady_state)
    scale_tbo: float = 1620 / 60.0,
    shape_tbo: float = 0.77,
    scale_od: float = 36 / 60.0,
    shape_od: float = 0.56,
    # sampling behavior
    independent_years: bool = True,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    Simulate grid availability for a multi-year horizon (dynamic formulation).

    Returns:
      np.ndarray shape (periods_per_year, years) with values in {0.0, 1.0}.

    Interpretation:
      - Column k corresponds to year index (1..years).
      - If first_year_connection is set, grid is unavailable (all zeros) for years < first_year_connection.
        Example: first_year_connection=3 -> years 1-2 all zeros, years 3..Y simulated.

    Outage logic per connected year (same spirit as typical-year):
      - Total outage hours = (avg_outages_per_year * avg_outage_duration_min / 60)
      - Sample outage durations from Weibull(scale_od, shape_od) until total outage time is reached
      - Sample times-between-outages from Weibull(scale_tbo, shape_tbo), scale to fill remaining uptime
      - Build alternating up/down blocks into a binary sequence of length periods_per_year

    Sampling behavior:
      - independent_years=True  -> each year is a new random draw (recommended)
      - independent_years=False -> same typical-year availability repeated for all connected years
    """
    if rng is None:
        rng = np.random.default_rng()

    if years <= 0:
        raise ValueError("years must be > 0.")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be > 0.")

    # normalize first_year_connection
    if first_year_connection is not None:
        if first_year_connection < 1:
            raise ValueError("first_year_connection must be >= 1 if provided.")
        if first_year_connection > years:
            # grid never connects within horizon
            return np.zeros((periods_per_year, years), dtype=float)

    out = np.zeros((periods_per_year, years), dtype=float)

    # Helper: simulate one year (same as your steady_state core, kept local for clarity)
    def _one_year(rng_year: np.random.Generator) -> np.ndarray:
        # Edge cases: no outages (or nonsensical inputs) -> always available
        if avg_outages_per_year <= 0 or avg_outage_duration_min <= 0:
            return np.ones((periods_per_year,), dtype=float)

        total_outage_hours = (avg_outages_per_year * avg_outage_duration_min) / 60.0
        total_hours = float(periods_per_year)

        # Cap to avoid pathological inputs
        total_outage_hours = max(0.0, min(total_outage_hours, total_hours))
        if total_outage_hours == 0.0:
            return np.ones((periods_per_year,), dtype=float)

        # --- Sample outage durations until total outage hours is met ---
        samples_od: list[float] = []
        sum_od = 0.0

        max_iter = 1_000_000
        it = 0
        while sum_od < total_outage_hours and it < max_iter:
            od = float(scale_od * rng_year.weibull(shape_od))
            if od <= 0:
                it += 1
                continue
            samples_od.append(od)
            sum_od += od
            if sum_od > total_outage_hours:
                samples_od[-1] -= (sum_od - total_outage_hours)
                sum_od = total_outage_hours
            it += 1

        if not samples_od:
            return np.ones((periods_per_year,), dtype=float)

        n_events = len(samples_od)

        # --- Sample time-between-outages (TBO) and scale to fit remaining uptime ---
        remaining_uptime = total_hours - total_outage_hours

        samples_tbo = scale_tbo * rng_year.weibull(shape_tbo, size=n_events)
        sum_tbo = float(np.sum(samples_tbo))

        if sum_tbo <= 0:
            # place outages back-to-back at start (fallback)
            seq = [0.0] * int(round(total_outage_hours)) + [1.0] * int(round(remaining_uptime))
        else:
            k = remaining_uptime / sum_tbo
            samples_tbo = samples_tbo * max(k, 0.0)

            seq: list[float] = []
            for tbo, od in zip(samples_tbo, samples_od):
                seq.extend([1.0] * int(round(tbo)))
                seq.extend([0.0] * int(round(od)))
                if len(seq) >= periods_per_year:
                    seq = seq[:periods_per_year]
                    break

            if len(seq) < periods_per_year:
                seq.extend([1.0] * (periods_per_year - len(seq)))

        return np.asarray(seq[:periods_per_year], dtype=float)

    # If repeating the same year pattern, draw once (but still respect first_year_connection)
    if not independent_years:
        base = _one_year(rng)
        for y in range(1, years + 1):
            if first_year_connection is not None and y < first_year_connection:
                out[:, y - 1] = 0.0
            else:
                out[:, y - 1] = base
        return out

    # Independent draws per year
    # (Spawn child RNGs to avoid subtle correlations when users pass a seeded rng)
    # Note: Generator.spawn is available on NumPy 1.20+ (default in modern stacks).
    try:
        child_rngs = rng.spawn(years)
    except Exception:
        # fallback: derive seeds deterministically from rng
        seeds = rng.integers(low=0, high=2**32 - 1, size=years, dtype=np.uint32)
        child_rngs = [np.random.default_rng(int(s)) for s in seeds]

    for y in range(1, years + 1):
        if first_year_connection is not None and y < first_year_connection:
            out[:, y - 1] = 0.0
            continue
        out[:, y - 1] = _one_year(child_rngs[y - 1])

    return out
