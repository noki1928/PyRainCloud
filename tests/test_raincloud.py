"""Integration tests: acceptance criteria US1–US3 and edge cases (WBS T8, T9)."""

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection, PolyCollection
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.patches import PathPatch

import pyraincloud as rc
from pyraincloud import RaincloudWarning

PALETTE = ["#66c2a5", "#fc8d62", "#8da0cb"]


def clouds(ax):
    return [c for c in ax.collections if isinstance(c, PolyCollection)]


def rain(ax):
    return [c for c in ax.collections if isinstance(c, PathCollection)]


def boxes(ax):
    return [p for p in ax.patches if isinstance(p, PathPatch)]


# --- Release metadata and defaults ----------------------------------------


def test_version_matches_package_metadata():
    from importlib.metadata import version

    assert rc.__version__ == version("pyraincloud") == "0.1.0"


def test_signature_defaults_come_from_style_defaults():
    import inspect

    from pyraincloud.style import DEFAULTS

    params = inspect.signature(rc.raincloud).parameters
    assert {k: params[k].default for k in DEFAULTS} == DEFAULTS


def test_jitter_stays_within_spec_band(df):
    """Spec, stage D: uniform(-j, j) jitter with j in 0.05-0.1 on the positive side."""
    from pyraincloud import style

    assert 0.05 <= style.RAIN_JITTER <= 0.1
    box_width = 0.15
    _, ax = rc.raincloud(data=df, x="condition", y="reaction_time", box_width=box_width)
    centre = box_width / 2 + style.RAIN_GAP + style.RAIN_JITTER
    for pos, points in enumerate(rain(ax)):
        offsets = points.get_offsets()[:, 0] - pos - centre
        assert np.all(np.abs(offsets) <= style.RAIN_JITTER + 1e-12)


# --- US1: basic plot -------------------------------------------------------


def test_us1_basic_plot(df):
    fig, ax = rc.raincloud(data=df, x="condition", y="reaction_time")
    assert isinstance(fig, Figure) and isinstance(ax, Axes)
    assert len(clouds(ax)) == 3 and len(rain(ax)) == 3 and len(boxes(ax)) == 3
    assert [t.get_text() for t in ax.get_xticklabels()] == ["Control", "Treatment A", "Treatment B"]
    assert ax.get_xlabel() == "condition" and ax.get_ylabel() == "reaction_time"
    assert all(len(c.get_offsets()) == 30 for c in rain(ax))


def test_layout_cloud_left_box_centre_rain_right(df):
    _, ax = rc.raincloud(data=df, x="condition", y="reaction_time", random_state=0)
    for pos, (cloud, points) in enumerate(zip(clouds(ax), rain(ax))):
        cloud_x = np.concatenate([p.vertices[:, 0] for p in cloud.get_paths()])
        assert cloud_x.max() <= pos + 1e-9 and cloud_x.min() < pos
        assert np.all(points.get_offsets()[:, 0] > pos)


@pytest.mark.parametrize("orient", ["v", "h"])
def test_cloud_does_not_overlap_box(df, orient):
    box_width = 0.2
    _, ax = rc.raincloud(
        data=df, x="condition", y="reaction_time", orient=orient, box_width=box_width
    )
    axis = 0 if orient == "v" else 1
    for pos, (cloud, box) in enumerate(zip(clouds(ax), boxes(ax))):
        cloud_c = np.concatenate([p.vertices[:, axis] for p in cloud.get_paths()])
        # extents in data coordinates: patch paths are stored differently across matplotlib versions
        ext = box.get_extents().transformed(ax.transData.inverted())
        box_c = np.array([ext.x0, ext.x1] if orient == "v" else [ext.y0, ext.y1])
        assert box_c.min() == pytest.approx(pos - box_width / 2, abs=0.01)
        if orient == "v":
            assert cloud_c.max() < box_c.min()
        else:
            assert cloud_c.min() > box_c.max()


def test_horizontal_orientation_mirrors_axes(df):
    _, ax = rc.raincloud(data=df, x="condition", y="reaction_time", orient="h", random_state=0)
    assert [t.get_text() for t in ax.get_yticklabels()] == ["Control", "Treatment A", "Treatment B"]
    assert ax.get_xlabel() == "reaction_time" and ax.get_ylabel() == "condition"
    for pos, (cloud, points) in enumerate(zip(clouds(ax), rain(ax))):
        cloud_y = np.concatenate([p.vertices[:, 1] for p in cloud.get_paths()])
        assert cloud_y.min() >= pos - 1e-9
        assert np.all(points.get_offsets()[:, 1] < pos)
        # values lie along X in horizontal mode
        assert points.get_offsets()[:, 0].mean() > 300


def test_palette_applied(df):
    _, ax = rc.raincloud(data=df, x="condition", y="reaction_time", palette=PALETTE)
    for cloud, points, color in zip(clouds(ax), rain(ax), PALETTE):
        assert cloud.get_facecolor()[0][:3] == pytest.approx(to_rgba(color)[:3])
        assert points.get_facecolor()[0][:3] == pytest.approx(to_rgba(color)[:3])


def test_longer_palette_is_truncated(df):
    _, ax = rc.raincloud(data=df, x="condition", y="reaction_time", palette=PALETTE + ["red"])
    assert len(clouds(ax)) == 3


# --- US2: customisation ----------------------------------------------------


def test_us2_custom_parameters(df):
    _, ax = rc.raincloud(
        data=df,
        x="condition",
        y="reaction_time",
        cloud_alpha=0.5,
        point_size=3,
        point_alpha=0.7,
        cloud_width=0.6,
    )
    for cloud in clouds(ax):
        assert cloud.get_alpha() == pytest.approx(0.5)
        widest = max(np.ptp(p.vertices[:, 0]) for p in cloud.get_paths())
        assert widest == pytest.approx(0.3, rel=1e-6)
    for points in rain(ax):
        assert points.get_alpha() == pytest.approx(0.7)
        assert points.get_sizes()[0] == pytest.approx(9.0)


@pytest.mark.parametrize(
    ("kwargs", "n_boxes", "n_rain"),
    [
        ({"add_boxes": False}, 0, 3),
        ({"add_points": False}, 3, 0),
        ({"add_boxes": False, "add_points": False}, 0, 0),
    ],
)
def test_layer_flags(df, kwargs, n_boxes, n_rain):
    _, ax = rc.raincloud(data=df, x="condition", y="reaction_time", **kwargs)
    assert len(boxes(ax)) == n_boxes and len(rain(ax)) == n_rain and len(clouds(ax)) == 3


def test_random_state_makes_jitter_reproducible(df):
    _, ax1 = rc.raincloud(data=df, x="condition", y="reaction_time", random_state=7)
    _, ax2 = rc.raincloud(data=df, x="condition", y="reaction_time", random_state=7)
    for a, b in zip(rain(ax1), rain(ax2)):
        np.testing.assert_array_equal(a.get_offsets(), b.get_offsets())


def test_generator_accepted_as_random_state(df):
    rc.raincloud(data=df, x="condition", y="reaction_time", random_state=np.random.default_rng(3))


# --- US3: further matplotlib customisation ---------------------------------


def test_us3_returned_axes_is_standard_matplotlib(df, tmp_path):
    fig, ax = rc.raincloud(data=df, x="condition", y="reaction_time")
    ax.annotate("p < 0.05", xy=(1, 600), xytext=(1, 620), arrowprops={"arrowstyle": "-"})
    ax.set_title("Reaction Time by Treatment Group")
    out = tmp_path / "plot.pdf"
    fig.savefig(out, bbox_inches="tight")
    assert out.stat().st_size > 0
    assert ax.get_title() == "Reaction Time by Treatment Group"


def test_existing_axes_is_used(df):
    fig, (left, right) = plt.subplots(1, 2)
    fig2, ax = rc.raincloud(data=df, x="condition", y="reaction_time", ax=right)
    assert fig2 is fig and ax is right
    assert not left.collections


def test_library_does_not_show_or_write_files(df, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(plt, "show", lambda *a, **k: pytest.fail("plt.show() called"))
    rc.raincloud(data=df, x="condition", y="reaction_time")
    assert list(tmp_path.iterdir()) == []


# --- Error contract & edge cases (T9) --------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "exc", "msg"),
    [
        ({"orient": "z"}, ValueError, "orient must be 'v' or 'h'"),
        ({"cloud_alpha": 1.5}, ValueError, r"cloud_alpha must be in \[0, 1\]"),
        ({"point_alpha": -0.1}, ValueError, r"point_alpha must be in \[0, 1\]"),
        ({"cloud_width": 0}, ValueError, "cloud_width must be > 0"),
        ({"point_size": -1}, ValueError, "point_size must be > 0"),
        ({"box_width": "wide"}, TypeError, "box_width must be a number"),
        ({"add_boxes": "yes"}, TypeError, "add_boxes must be bool"),
        ({"palette": ["#66c2a5"]}, ValueError, "palette has 1 colour"),
        ({"palette": "Set2"}, TypeError, "sequence of colours"),
        ({"palette": ["#66c2a5", "notacolour", "red"]}, ValueError, "invalid colour"),
        ({"ax": "axes"}, TypeError, "ax must be a matplotlib Axes"),
    ],
)
def test_invalid_parameters(df, kwargs, exc, msg):
    with pytest.raises(exc, match=msg):
        rc.raincloud(data=df, x="condition", y="reaction_time", **kwargs)


def test_missing_column(df):
    with pytest.raises(ValueError, match="Column 'group' not found in data"):
        rc.raincloud(data=df, x="group", y="reaction_time")


def test_single_observation_group_draws_box_and_point_without_cloud():
    df = pd.DataFrame({"g": ["a"] * 10 + ["b"], "v": list(np.linspace(0, 1, 10)) + [0.5]})
    with pytest.warns(RaincloudWarning, match="Group 'b'.*cloud is skipped"):
        _, ax = rc.raincloud(data=df, x="g", y="v")
    assert len(clouds(ax)) == 1 and len(boxes(ax)) == 2 and len(rain(ax)) == 2


def test_too_many_points_warns():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"g": rng.choice(["a", "b"], 50_001), "v": rng.normal(size=50_001)})
    with pytest.warns(RaincloudWarning, match="points will be drawn"):
        rc.raincloud(data=df, x="g", y="v", add_boxes=False)


def test_performance_10_groups_5000_points():
    """Non-functional requirement: ≤ 2 s for 10 groups × 5000 points."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "g": np.repeat([f"G{i}" for i in range(10)], 5000),
            "v": rng.normal(size=50_000),
        }
    )
    start = time.perf_counter()
    fig, _ = rc.raincloud(data=df, x="g", y="v")
    fig.canvas.draw()
    assert time.perf_counter() - start < 2.0
