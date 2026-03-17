from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


def _to_1d_np(x) -> np.ndarray:
    arr = np.asarray(x).astype(float)
    return arr.reshape(-1)


def plot_8760(series, *, title: str, y_label: str):
    y = _to_1d_np(series)
    x = np.arange(len(y))
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.plot(x, y, linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel("Hour of year")
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def plot_daily_profile_band(series, *, title: str, y_label: str):
    y = _to_1d_np(series)
    if len(y) != 8760:
        hod = np.arange(len(y)) % 24
        mean = np.array([np.nanmean(y[hod == h]) for h in range(24)])
        vmin = np.array([np.nanmin(y[hod == h]) for h in range(24)])
        vmax = np.array([np.nanmax(y[hod == h]) for h in range(24)])
    else:
        mat = y.reshape(365, 24)
        mean = np.nanmean(mat, axis=0)
        vmin = np.nanmin(mat, axis=0)
        vmax = np.nanmax(mat, axis=0)

    h = np.arange(24)
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.fill_between(h, vmin, vmax, alpha=0.25)
    ax.plot(h, mean, linewidth=2.0)
    ax.set_title(title)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel(y_label)
    ax.set_xticks(h)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig

