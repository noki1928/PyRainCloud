import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


@pytest.fixture
def df() -> pd.DataFrame:
    """Example dataset from the business hypothesis: 3 groups × 30 reaction times."""
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "condition": ["Control"] * 30 + ["Treatment A"] * 30 + ["Treatment B"] * 30,
            "reaction_time": np.concatenate(
                [rng.normal(500, 50, 30), rng.normal(450, 60, 30), rng.normal(480, 55, 30)]
            ),
        }
    )
