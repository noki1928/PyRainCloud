"""Validation and grouping of the input DataFrame (stage A of the algorithm)."""

from __future__ import annotations

import warnings
from collections.abc import Hashable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .exceptions import RaincloudWarning

MAX_GROUPS_READABLE = 50


@dataclass
class GroupData:
    """Clean observations of one category."""

    name: Hashable
    values: np.ndarray
    color: str | None = None

    @property
    def n(self) -> int:
        return int(self.values.size)


def _check_column(data: pd.DataFrame, name: object, role: str) -> None:
    if not isinstance(name, str):
        raise TypeError(f"{role} must be a column name (str), got {type(name).__name__}")
    if name not in data.columns:
        raise ValueError(f"Column '{name}' not found in data")


def _to_numeric(raw: pd.Series, y: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(raw):
        raise TypeError(f"Column '{y}' must be numeric")
    if pd.api.types.is_numeric_dtype(raw):
        return raw.astype(float)
    # Spec, stage A: coerce to numbers; unconvertible values become NaN and are dropped later.
    numeric = pd.to_numeric(raw, errors="coerce")
    coerced = numeric.isna() & raw.notna()
    if raw.notna().any() and numeric.notna().sum() == 0:
        raise TypeError(f"Column '{y}' must be numeric")
    if coerced.any():
        warnings.warn(
            f"Column '{y}': {int(coerced.sum())} non-numeric value(s) converted to NaN",
            RaincloudWarning,
            stacklevel=4,
        )
    return numeric.astype(float)


def group_data(data: pd.DataFrame, x: str, y: str) -> list[GroupData]:
    """Validate ``data`` and split column ``y`` by the categories of column ``x``.

    Group order follows ``Categorical.categories`` when ``x`` is categorical,
    otherwise the order of first appearance. NaN values of ``y`` are dropped with
    a warning; groups left empty are skipped with a warning.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"data must be a pandas DataFrame, got {type(data).__name__}")
    _check_column(data, x, "x")
    _check_column(data, y, "y")
    if data.empty:
        raise ValueError("data is empty")

    frame = data[[x, y]].copy()
    frame[y] = _to_numeric(frame[y], y)

    missing_x = frame[x].isna()
    if missing_x.any():
        warnings.warn(
            f"Dropped {int(missing_x.sum())} row(s) with missing category in column '{x}'",
            RaincloudWarning,
            stacklevel=3,
        )
        frame = frame[~missing_x]

    if isinstance(frame[x].dtype, pd.CategoricalDtype):
        order = list(frame[x].cat.categories)
    else:
        order = list(pd.unique(frame[x]))

    groups: list[GroupData] = []
    for name in order:
        values = frame.loc[frame[x] == name, y].to_numpy(dtype=float)
        n_nan = int(np.isnan(values).sum())
        values = values[~np.isnan(values)]
        if n_nan:
            warnings.warn(
                f"Group '{name}': dropped {n_nan} NaN value(s) in column '{y}'",
                RaincloudWarning,
                stacklevel=3,
            )
        if values.size == 0:
            warnings.warn(
                f"Group '{name}' has no valid observations and is skipped",
                RaincloudWarning,
                stacklevel=3,
            )
            continue
        groups.append(GroupData(name=name, values=values))

    if not groups:
        raise ValueError("No valid observations after dropping NaN")
    if len(groups) > MAX_GROUPS_READABLE:
        warnings.warn(
            f"{len(groups)} groups may be hard to read; consider filtering the data",
            RaincloudWarning,
            stacklevel=3,
        )
    return groups
