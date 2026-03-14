"""Runtime coercion of pandas/polars types to numpy arrays.

Both pandas and polars are optional dependencies. This module uses
``isinstance`` checks with lazy imports so that users who only work
with numpy never pay for the import cost.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _is_pandas_series(obj: Any) -> bool:
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return False
    return isinstance(obj, pd.Series)


def _is_pandas_dataframe(obj: Any) -> bool:
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return False
    return isinstance(obj, pd.DataFrame)


def _is_polars_series(obj: Any) -> bool:
    try:
        import polars as pl
    except ImportError:  # pragma: no cover
        return False
    return isinstance(obj, pl.Series)


def _is_polars_dataframe(obj: Any) -> bool:
    try:
        import polars as pl
    except ImportError:  # pragma: no cover
        return False
    return isinstance(obj, pl.DataFrame)


def coerce_times(times: Any) -> Any:
    """Convert *times* to a numpy datetime64 array.

    Accepted inputs:
    - ``numpy.ndarray`` of ``datetime64`` — returned as-is
    - ``pandas.Series`` of datetime — converted via ``.to_numpy(dtype="datetime64[ms]")``
    - ``polars.Series`` of Datetime/Date — converted via ``.to_numpy()`` then cast
    """
    if isinstance(times, np.ndarray):
        return times

    if _is_pandas_series(times):
        return times.to_numpy(dtype="datetime64[ms]")

    if _is_polars_series(times):
        arr = times.to_numpy()
        if not np.issubdtype(arr.dtype, np.datetime64):
            arr = arr.astype("datetime64[ms]")
        return arr

    # Fall through — let numpy try to coerce it
    return np.asarray(times, dtype="datetime64[ms]")


def coerce_data(data: Any) -> Any:
    """Convert *data* to a 2-D numpy floating-point array.

    Accepted inputs:
    - ``numpy.ndarray`` — returned as-is
    - ``pandas.DataFrame`` — converted via ``.to_numpy(dtype=float)``
    - ``pandas.Series`` — converted via ``.to_numpy(dtype=float)`` then reshaped to column
    - ``polars.DataFrame`` — converted via ``.to_numpy()`` then cast
    - ``polars.Series`` — converted via ``.to_numpy()`` then reshaped to column
    """
    if isinstance(data, np.ndarray):
        return data

    if _is_pandas_dataframe(data):
        return data.to_numpy(dtype=float)

    if _is_pandas_series(data):
        return data.to_numpy(dtype=float).reshape(-1, 1)

    if _is_polars_dataframe(data):
        return data.to_numpy().astype(float)

    if _is_polars_series(data):
        return data.to_numpy().astype(float).reshape(-1, 1)

    # Fall through — let numpy try
    return np.asarray(data, dtype=float)
