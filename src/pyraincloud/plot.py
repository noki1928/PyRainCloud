"""Public facade: orchestration of validation, density and layer drawing."""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Literal, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from . import artists, style
from .data import group_data
from .density import half_violin
from .exceptions import RaincloudWarning

RandomState = Union[int, np.random.Generator, None]


def raincloud(
    data: pd.DataFrame,
    x: str,
    y: str,
    *,
    orient: Literal["v", "h"] = "v",
    palette: Sequence[str] | None = None,
    cloud_alpha: float = 0.5,
    cloud_width: float = 0.8,
    point_size: float = 3.0,
    point_alpha: float = 0.6,
    box_width: float = 0.15,
    add_boxes: bool = True,
    add_points: bool = True,
    ax: Axes | None = None,
    random_state: RandomState = None,
) -> tuple[Figure, Axes]:
    """Draw a rain cloud plot: half-violin ("cloud") + box plot + jittered raw points ("rain").

    Parameters
    ----------
    data : pandas.DataFrame
        Long-format table with one row per observation.
    x : str
        Name of the categorical column that defines the groups.
    y : str
        Name of the numeric column with the measured values.
    orient : {'v', 'h'}, default 'v'
        ``'v'`` — groups along X, values along Y; ``'h'`` — the other way round.
    palette : sequence of colours, optional
        One colour per group (at least as many as groups). ``None`` uses the
        active matplotlib colour cycle.
    cloud_alpha : float in [0, 1], default 0.5
        Opacity of the density cloud.
    cloud_width : float > 0, default 0.8
        Maximum width of the cloud and the rain band, in category units.
    point_size : float > 0, default 3.0
        Size of raw data points (``markersize`` semantics).
    point_alpha : float in [0, 1], default 0.6
        Opacity of raw data points.
    box_width : float > 0, default 0.15
        Width of the box plot.
    add_boxes, add_points : bool, default True
        Toggle the box and rain layers.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on; a new figure is created when omitted.
    random_state : int or numpy.random.Generator, optional
        Seed for the jitter, for reproducible plots.

    Returns
    -------
    (Figure, Axes)
        Standard matplotlib objects for further customisation
        (``ax.set_title``, ``ax.annotate``, ``fig.savefig`` ...).

    Raises
    ------
    ValueError
        Missing columns, empty data, out-of-range parameters, short palette.
    TypeError
        Wrong argument types or a non-numeric ``y`` column.
    """
    orient = style.check_orient(orient)
    cloud_alpha = style.check_unit("cloud_alpha", cloud_alpha)
    point_alpha = style.check_unit("point_alpha", point_alpha)
    cloud_width = style.check_positive("cloud_width", cloud_width)
    point_size = style.check_positive("point_size", point_size)
    box_width = style.check_positive("box_width", box_width)
    add_boxes = style.check_flag("add_boxes", add_boxes)
    add_points = style.check_flag("add_points", add_points)
    if ax is not None and not isinstance(ax, Axes):
        raise TypeError(f"ax must be a matplotlib Axes, got {type(ax).__name__}")
    rng = np.random.default_rng(random_state)

    groups = group_data(data, x, y)
    colors = style.resolve_palette(palette, len(groups))

    total = sum(g.n for g in groups)
    if add_points and total > style.MAX_POINTS:
        warnings.warn(
            f"{total} points will be drawn (> {style.MAX_POINTS}); rendering may be slow, "
            "consider add_points=False or sampling the data",
            RaincloudWarning,
            stacklevel=2,
        )

    if ax is None:
        if orient == "v":
            size = (max(6.0, 1.6 * len(groups)), 5.0)
        else:
            size = (7.0, max(4.0, 1.3 * len(groups)))
        fig, ax = plt.subplots(figsize=size, layout="constrained")
    else:
        fig = ax.figure

    # Vertical: cloud to the left, rain to the right. Horizontal: cloud above, rain below.
    cloud_side = -1 if orient == "v" else 1
    rain_side = -cloud_side
    # The cloud must not intersect the box at the category centre (spec, stage B).
    cloud_start = box_width / 2 + style.CLOUD_GAP if add_boxes else 0.0

    positions = np.arange(len(groups), dtype=float)
    for pos, group, color in zip(positions, groups, colors):
        group.color = color
        curve = half_violin(group.values, cloud_width, group.name)
        if curve is not None:
            artists.draw_cloud(ax, curve, pos, cloud_side, cloud_start, color, cloud_alpha, orient)
        if add_boxes:
            artists.draw_box(ax, group.values, pos, box_width, color, orient)
        if add_points:
            artists.draw_rain(
                ax,
                group.values,
                pos,
                rain_side,
                box_width,
                color,
                point_size,
                point_alpha,
                rng,
                orient,
            )

    labels = [str(g.name) for g in groups]
    margin = (
        max(cloud_start + cloud_width / 2, box_width / 2 + style.RAIN_GAP + style.RAIN_SPREAD) + 0.1
    )
    lims = (positions[0] - margin, positions[-1] + margin)
    if orient == "v":
        ax.set_xticks(positions, labels)
        ax.set_xlim(*lims)
        ax.set_xlabel(x)
        ax.set_ylabel(y)
    else:
        ax.set_yticks(positions, labels)
        ax.set_ylim(*lims)
        ax.set_ylabel(x)
        ax.set_xlabel(y)
    return fig, ax
