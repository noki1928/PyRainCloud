"""Kernel density estimate and half-violin geometry (stage B of the algorithm)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy.stats import gaussian_kde

from .exceptions import RaincloudWarning

GRID_SIZE = 200
GRID_PADDING = 0.05
SMALL_SAMPLE = 5


@dataclass
class DensityCurve:
    """Density of one group on a grid along the value axis.

    ``offset`` is the scaled distance from the category position (>= 0); the
    side of the category axis it is drawn on is chosen by the caller.
    """

    grid: np.ndarray
    density: np.ndarray
    offset: np.ndarray


def estimate_density(
    values: np.ndarray, name: object = None
) -> tuple[np.ndarray, np.ndarray] | None:
    """Return ``(grid, density)`` or ``None`` when KDE is impossible (n < 2 or zero variance)."""
    values = np.asarray(values, dtype=float)
    if values.size < 2 or np.ptp(values) == 0:
        warnings.warn(
            f"Group '{name}': cannot estimate density (n={values.size}, zero variance); "
            "cloud is skipped",
            RaincloudWarning,
            stacklevel=4,
        )
        return None
    if values.size < SMALL_SAMPLE:
        warnings.warn(
            f"Group '{name}': small sample (n={values.size}), density estimate may be unreliable",
            RaincloudWarning,
            stacklevel=4,
        )
    try:
        kde = gaussian_kde(values)
    except np.linalg.LinAlgError:
        warnings.warn(
            f"Group '{name}': KDE failed on degenerate data; cloud is skipped",
            RaincloudWarning,
            stacklevel=4,
        )
        return None
    lo, hi = float(values.min()), float(values.max())
    pad = (hi - lo) * GRID_PADDING
    grid = np.linspace(lo - pad, hi + pad, GRID_SIZE)
    return grid, np.clip(kde(grid), 0.0, None)


def half_violin(values: np.ndarray, width: float, name: object = None) -> DensityCurve | None:
    """Density scaled so that the widest point of the cloud equals ``width / 2``."""
    est = estimate_density(values, name)
    if est is None:
        return None
    grid, density = est
    peak = density.max()
    offset = density / peak * (width / 2.0) if peak > 0 else np.zeros_like(density)
    return DensityCurve(grid=grid, density=density, offset=offset)
