"""Palette, sizes and transparency: defaults and parameter validation."""

from __future__ import annotations

import numbers
from collections.abc import Sequence
from itertools import cycle, islice

import matplotlib as mpl
from matplotlib.colors import is_color_like

DEFAULTS = {
    "orient": "v",
    "cloud_alpha": 0.5,
    "cloud_width": 0.8,
    "point_size": 3.0,
    "point_alpha": 0.6,
    "box_width": 0.15,
    "add_boxes": True,
    "add_points": True,
}

# Layout: cloud on one side of the category, box in the centre, rain on the other.
BOX_FACE = "white"
BOX_LINEWIDTH = 1.2
CLOUD_LINEWIDTH = 1.0
CLOUD_GAP = 0.03  # distance between box edge and the cloud base
RAIN_GAP = 0.05  # distance between box edge and the rain band
RAIN_SPREAD = 0.08  # jitter band width along the category axis
MAX_POINTS = 50_000


def _check_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    return float(value)


def check_unit(name: str, value: object) -> float:
    """Number in [0, 1] (alpha values)."""
    v = _check_number(name, value)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")
    return v


def check_positive(name: str, value: object) -> float:
    """Strictly positive number (widths and sizes)."""
    v = _check_number(name, value)
    if not v > 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    return v


def check_flag(name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool, got {type(value).__name__}")
    return value


def check_orient(orient: object) -> str:
    if orient not in ("v", "h"):
        raise ValueError(f"orient must be 'v' or 'h', got {orient!r}")
    return str(orient)


def resolve_palette(palette: Sequence[str] | None, n_groups: int) -> list[str]:
    """One colour per group.

    ``None`` cycles the active matplotlib colour cycle; an explicit palette must
    contain only valid colours and cover every group.
    """
    if palette is None:
        base = mpl.rcParams["axes.prop_cycle"].by_key().get("color", ["C0"])
        return list(islice(cycle(base), n_groups))
    if isinstance(palette, str) or not isinstance(palette, Sequence):
        raise TypeError("palette must be a sequence of colours, e.g. ['#66c2a5', '#fc8d62']")
    bad = [c for c in palette if not is_color_like(c)]
    if bad:
        raise ValueError(f"palette contains invalid colour(s): {bad}")
    if len(palette) < n_groups:
        raise ValueError(
            f"palette has {len(palette)} colour(s) but data has {n_groups} group(s); "
            "the palette must cover all groups"
        )
    return list(palette[:n_groups])
