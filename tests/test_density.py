import numpy as np
import pytest

from pyraincloud import RaincloudWarning
from pyraincloud.density import GRID_SIZE, half_violin


def test_half_violin_shape_and_scale():
    values = np.random.default_rng(0).normal(0, 1, 200)
    curve = half_violin(values, width=0.8)
    assert curve is not None
    assert curve.grid.shape == curve.offset.shape == (GRID_SIZE,)
    assert np.all(curve.density >= 0)
    assert curve.offset.max() == pytest.approx(0.4)
    assert curve.grid.min() < values.min() and curve.grid.max() > values.max()


def test_density_peak_near_mode():
    values = np.random.default_rng(1).normal(10, 1, 2000)
    curve = half_violin(values, width=1.0)
    assert curve.grid[np.argmax(curve.density)] == pytest.approx(10, abs=0.3)


@pytest.mark.parametrize("values", [np.array([5.0]), np.array([3.0, 3.0, 3.0])])
def test_degenerate_samples_skip_cloud(values):
    with pytest.warns(RaincloudWarning, match="cloud is skipped"):
        assert half_violin(values, width=0.8) is None


def test_small_sample_warns_but_draws():
    with pytest.warns(RaincloudWarning, match="small sample"):
        assert half_violin(np.array([1.0, 2.0, 4.0]), width=0.8) is not None
