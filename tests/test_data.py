import numpy as np
import pandas as pd
import pytest

from pyraincloud import RaincloudWarning
from pyraincloud.data import group_data


def test_groups_in_order_of_appearance(df):
    groups = group_data(df, "condition", "reaction_time")
    assert [g.name for g in groups] == ["Control", "Treatment A", "Treatment B"]
    assert [g.n for g in groups] == [30, 30, 30]


def test_categorical_order_is_respected(df):
    df = df.copy()
    df["condition"] = pd.Categorical(
        df["condition"], categories=["Treatment B", "Control", "Treatment A"]
    )
    groups = group_data(df, "condition", "reaction_time")
    assert [g.name for g in groups] == ["Treatment B", "Control", "Treatment A"]


def test_unused_categories_are_skipped_with_warning(df):
    df = df.copy()
    df["condition"] = pd.Categorical(
        df["condition"], categories=["Control", "Treatment A", "Treatment B", "Placebo"]
    )
    with pytest.warns(RaincloudWarning, match="Placebo"):
        groups = group_data(df, "condition", "reaction_time")
    assert len(groups) == 3


def test_nan_values_dropped_with_warning():
    df = pd.DataFrame({"g": ["a", "a", "a", "b", "b"], "v": [1.0, np.nan, 3.0, 4.0, 5.0]})
    with pytest.warns(RaincloudWarning, match="dropped 1 NaN"):
        groups = group_data(df, "g", "v")
    assert groups[0].values.tolist() == [1.0, 3.0]


def test_missing_category_rows_dropped():
    df = pd.DataFrame({"g": ["a", None, "a"], "v": [1.0, 2.0, 3.0]})
    with pytest.warns(RaincloudWarning, match="missing category"):
        groups = group_data(df, "g", "v")
    assert [g.name for g in groups] == ["a"]


def test_numeric_strings_are_coerced():
    df = pd.DataFrame({"g": ["a", "a"], "v": ["1.5", "2.5"]})
    groups = group_data(df, "g", "v")
    assert groups[0].values.tolist() == [1.5, 2.5]


def test_non_numeric_values_coerced_to_nan_with_warning():
    """Spec, stage A: to_numeric(errors='coerce') and drop the resulting NaN."""
    df = pd.DataFrame({"g": ["a", "a", "a"], "v": ["1.5", "n/a", "2.5"]})
    with pytest.warns(RaincloudWarning, match="dropped 1 NaN"):
        with pytest.warns(RaincloudWarning, match="1 non-numeric value"):
            groups = group_data(df, "g", "v")
    assert groups[0].values.tolist() == [1.5, 2.5]


def test_input_frame_is_not_modified(df):
    before = df.copy()
    group_data(df, "condition", "reaction_time")
    pd.testing.assert_frame_equal(df, before)


@pytest.mark.parametrize(
    ("data", "x", "y", "exc", "msg"),
    [
        ([1, 2, 3], "g", "v", TypeError, "DataFrame"),
        (pd.DataFrame({"g": ["a"], "v": [1.0]}), "missing", "v", ValueError, "'missing' not found"),
        (pd.DataFrame({"g": ["a"], "v": [1.0]}), "g", "nope", ValueError, "'nope' not found"),
        (pd.DataFrame({"g": ["a"], "v": [1.0]}), 0, "v", TypeError, "column name"),
        (pd.DataFrame({"g": [], "v": []}), "g", "v", ValueError, "data is empty"),
        (pd.DataFrame({"g": ["a", "b"], "v": ["x", "y"]}), "g", "v", TypeError, "must be numeric"),
        (pd.DataFrame({"g": ["a", "b"], "v": [True, False]}), "g", "v", TypeError, "numeric"),
    ],
)
def test_invalid_input(data, x, y, exc, msg):
    with pytest.raises(exc, match=msg):
        group_data(data, x, y)


def test_all_nan_raises():
    df = pd.DataFrame({"g": ["a", "b"], "v": [np.nan, np.nan]})
    with pytest.warns(RaincloudWarning), pytest.raises(ValueError, match="No valid observations"):
        group_data(df, "g", "v")
