from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def df() -> pd.DataFrame:
    """Acceptance dataset (spec, appendix A): 3 groups × 30 reaction times in ms."""
    return pd.read_csv(FIXTURES / "reaction_times.csv")
