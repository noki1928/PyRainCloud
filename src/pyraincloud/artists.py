"""Drawing of the three layers: cloud, box and rain (stages B–D of the algorithm).

All functions work in "category / value" coordinates and map them to x/y
according to ``orient``: for ``'v'`` categories are on X, for ``'h'`` on Y.
"""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.cbook import boxplot_stats

from . import style
from .density import DensityCurve


def draw_cloud(
    ax: Axes,
    curve: DensityCurve,
    pos: float,
    side: int,
    start: float,
    color: str,
    alpha: float,
    orient: str,
) -> None:
    """Half-violin towards ``side`` (-1 or +1), its flat base ``start`` away from ``pos``.

    ``start`` keeps the cloud clear of the box drawn at the category centre.
    """
    base = pos + side * start
    edge = base + side * curve.offset
    if orient == "v":
        ax.fill_betweenx(curve.grid, base, edge, facecolor=color, alpha=alpha, edgecolor="none")
        ax.plot(edge, curve.grid, color=color, linewidth=style.CLOUD_LINEWIDTH)
    else:
        ax.fill_between(curve.grid, base, edge, facecolor=color, alpha=alpha, edgecolor="none")
        ax.plot(curve.grid, edge, color=color, linewidth=style.CLOUD_LINEWIDTH)


def draw_box(
    ax: Axes, values: np.ndarray, pos: float, width: float, color: str, orient: str
) -> None:
    """Box plot (median, quartiles, 1.5·IQR whiskers) without fliers: raw points show them."""
    stats = boxplot_stats(values)
    line = {"color": color, "linewidth": style.BOX_LINEWIDTH}
    kwargs = {
        "positions": [pos],
        "widths": width,
        "patch_artist": True,
        "showfliers": False,
        "manage_ticks": False,
        "boxprops": {
            "facecolor": style.BOX_FACE,
            "edgecolor": color,
            "linewidth": style.BOX_LINEWIDTH,
        },
        "medianprops": line,
        "whiskerprops": line,
        "capprops": line,
        "zorder": 3,
    }
    # matplotlib >= 3.10 replaced ``vert`` with ``orientation``.
    try:
        ax.bxp(stats, orientation="vertical" if orient == "v" else "horizontal", **kwargs)
    except TypeError:
        ax.bxp(stats, vert=(orient == "v"), **kwargs)


def draw_rain(
    ax: Axes,
    values: np.ndarray,
    pos: float,
    side: int,
    box_width: float,
    color: str,
    size: float,
    alpha: float,
    rng: np.random.Generator,
    orient: str,
) -> None:
    """Raw observations jittered along the category axis on the ``side`` of the box.

    Spec, stage D: ``offset = rng.uniform(-j, j)`` around the centre of the rain band.
    """
    centre = box_width / 2 + style.RAIN_GAP + style.RAIN_JITTER
    offset = rng.uniform(-style.RAIN_JITTER, style.RAIN_JITTER, size=values.size)
    cat = pos + side * (centre + offset)
    xs, ys = (cat, values) if orient == "v" else (values, cat)
    # ``point_size`` follows ``markersize`` semantics; scatter expects points².
    ax.scatter(xs, ys, s=size**2, color=color, alpha=alpha, linewidths=0, zorder=2)
