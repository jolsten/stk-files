from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Scalar formatters (kept for single-value use in headers, etc.)
# ---------------------------------------------------------------------------


def format_iso_ymd(time: np.datetime64) -> str:
    """Format as 'YYYY-MM-DDTHH:MM:SS.sss' (23 chars)."""
    return str(time.astype("datetime64[ms]"))[:23]


def format_ep_sec(time: np.datetime64, epoch: np.datetime64) -> str:
    """Format as epoch seconds with 15.3f width."""
    dt_ms = (time - epoch) / np.timedelta64(1, "ms")  # type: ignore[operator]
    return f"{float(dt_ms) / 1e3:15.3f}"


def format_quaternion_row(row: np.ndarray) -> str:
    """Format 4 quaternion components with {:+12.9f}."""
    return " ".join(f"{float(v):+12.9f}" for v in row)


def format_generic_row(row: np.ndarray) -> str:
    """Format numeric values with {:12f}."""
    return " ".join(f"{float(v):12f}" for v in row)


# ---------------------------------------------------------------------------
# Vectorized bulk formatters
# ---------------------------------------------------------------------------


def format_iso_ymd_array(times: NDArray[np.datetime64]) -> list[str]:
    """Vectorized ISO-YMD formatting for an entire array of times."""
    ms_times = times.astype("datetime64[ms]")
    return [s[:23] for s in np.datetime_as_string(ms_times, unit="ms").tolist()]


def format_ep_sec_array(
    times: NDArray[np.datetime64],
    epoch: np.datetime64,
) -> list[str]:
    """Vectorized epoch-seconds formatting for an entire array of times."""
    ms = (times - epoch) / np.timedelta64(1, "ms")
    return [f"{float(v) / 1e3:15.3f}" for v in ms]


def format_quaternion_block(data: NDArray[np.floating]) -> list[str]:
    """Vectorized quaternion formatting for an entire data array."""
    cols = [np.char.mod("%+12.9f", data[:, i]) for i in range(data.shape[1])]
    result = cols[0]
    for c in cols[1:]:
        result = np.char.add(np.char.add(result, " "), c)
    return result.tolist()  # type: ignore[no-any-return]


def format_generic_block(data: NDArray[np.floating]) -> list[str]:
    """Vectorized generic formatting for an entire data array."""
    cols = [np.char.mod("%12f", data[:, i]) for i in range(data.shape[1])]
    result = cols[0]
    for c in cols[1:]:
        result = np.char.add(np.char.add(result, " "), c)
    return result.tolist()  # type: ignore[no-any-return]
