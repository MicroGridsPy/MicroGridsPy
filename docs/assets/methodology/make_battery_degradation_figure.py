"""Regenerate docs/assets/methodology/battery_degradation_coefficients.png.

Plots the two coefficients that actually cross into the optimisation, straight from the
shipped coefficient module, so the figure cannot drift from the model it documents.

    python docs/assets/methodology/make_battery_degradation_figure.py
"""

from __future__ import annotations

import pathlib
import sys
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))

from microgridspy.data_pipeline.battery_degradation_coefficients import (  # noqa: E402
    calendar_rate_per_year,
    cycle_fade_coefficient,
)

OUT = pathlib.Path(__file__).with_name("battery_degradation_coefficients.png")

DOD = 0.8
BUDGET = 0.2
N_RATED = 6000.0
REF_DOD = 0.8
REF_T = 25.0
SOC_MEAN = 1.0 - DOD / 2.0
LIFE_YEARS = 10.0
FITTED_WINDOW = (10.0, 45.0)

INK = "#1f2933"
GRID = "#d8dee4"
LFP_COLOR = "#2f6f9f"
NMC_COLOR = "#c2694f"
BAND_COLOR = "#eef2f6"


def main() -> None:
    temperature = np.linspace(10.0, 50.0, 161)

    cycle = {}
    for chemistry in ("LFP", "NMC"):
        with warnings.catch_warnings():
            # The figure deliberately spans the edges of the fitted window.
            warnings.simplefilter("ignore")
            cycle[chemistry] = cycle_fade_coefficient(
                chemistry=chemistry,
                depth_of_discharge=DOD,
                temperature_degc=temperature,
                user_cycle_life=N_RATED,
                usable_soh_budget=BUDGET,
                reference_dod=REF_DOD,
                reference_temperature_degc=REF_T,
            )["c"]

    anchored = calendar_rate_per_year(
        "LFP", SOC_MEAN, temperature, reference_years=LIFE_YEARS, scale=1.0
    )
    unscaled = calendar_rate_per_year(
        "LFP", SOC_MEAN, temperature, reference_years=LIFE_YEARS, scale=2.72
    )

    fig, (left, right) = plt.subplots(1, 2, figsize=(11.0, 4.2))

    for axis in (left, right):
        axis.axvspan(*FITTED_WINDOW, color=BAND_COLOR, zorder=0)
        axis.grid(True, color=GRID, linewidth=0.7, zorder=1)
        axis.set_axisbelow(True)
        axis.set_xlabel("Cell temperature  [°C]")
        axis.set_xlim(temperature[0], temperature[-1])
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)

    left.plot(temperature, 1e6 * cycle["LFP"], color=LFP_COLOR, linewidth=2.0, label="LFP", zorder=3)
    left.plot(
        temperature,
        1e6 * cycle["NMC"],
        color=NMC_COLOR,
        linewidth=2.0,
        linestyle="--",
        label="NMC (uncalibrated — pessimistic)",
        zorder=3,
    )
    anchor = 1e6 * BUDGET / (N_RATED * REF_DOD)
    left.plot([REF_T], [anchor], "o", color=INK, markersize=6, zorder=4)
    left.annotate(
        f"datasheet anchor\n{N_RATED:.0f} cycles @ {REF_DOD:.0%} DoD, {REF_T:.0f} °C",
        xy=(REF_T, anchor),
        xytext=(REF_T + 1.5, anchor * 2.1),
        fontsize=8,
        color=INK,
        arrowprops={"arrowstyle": "-", "color": INK, "linewidth": 0.8},
    )
    left.set_yscale("log")
    left.set_ylabel("$c(T)$   [10$^{-6}$ of nameplate per kWh discharged]")
    left.set_title("Cycle fade — per kWh discharged", fontsize=10, color=INK)
    left.legend(frameon=False, fontsize=8, loc="upper left")

    right.plot(
        temperature,
        100.0 * anchored,
        color=LFP_COLOR,
        linewidth=2.0,
        label="anchored  (calendar_fade_scale = 1.0)",
        zorder=3,
    )
    right.plot(
        temperature,
        100.0 * unscaled,
        color=LFP_COLOR,
        linewidth=1.4,
        linestyle=":",
        label="unscaled envelope  (2.72)",
        zorder=3,
    )
    right.fill_between(
        temperature, 100.0 * anchored, 100.0 * unscaled, color=LFP_COLOR, alpha=0.10, zorder=2
    )
    right.set_ylabel("$r^{\\mathrm{cal}}(T)$   [% of nameplate per year]")
    right.set_title(
        f"Calendar fade — per year, linearised over {LIFE_YEARS:.0f} y", fontsize=10, color=INK
    )
    right.legend(frameon=False, fontsize=8, loc="upper left")

    fig.text(
        0.5,
        0.005,
        "Shaded band: the 10–45 °C window the cycle coefficients were fitted in. "
        "LFP, 80 % depth of discharge, mean SoC 0.6.",
        ha="center",
        fontsize=8,
        color="#5a6672",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT, dpi=160)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
