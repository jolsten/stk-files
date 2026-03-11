from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

import numpy as np

from stk_files.interval import Interval, write_interval

if TYPE_CHECKING:
    from numpy.typing import NDArray


def detect_availability(
    times: NDArray[np.datetime64],
    max_gap: np.timedelta64,
) -> list[tuple[np.datetime64, np.datetime64]]:
    """Identify contiguous data spans from a sorted time array.

    Returns a list of (start, end) tuples. A new span begins whenever
    the gap between consecutive timestamps exceeds *max_gap*.
    """
    if times.size == 0:
        return []
    if times.size == 1:
        return [(times[0], times[0])]

    gaps = np.diff(times) > max_gap
    break_indices = np.where(gaps)[0]

    spans: list[tuple[np.datetime64, np.datetime64]] = []
    start_idx = 0
    for brk in break_indices:
        spans.append((times[start_idx], times[brk]))
        start_idx = brk + 1
    spans.append((times[start_idx], times[-1]))
    return spans


def write_availability(
    stream: TextIO,
    times: NDArray[np.datetime64],
    max_gap: np.timedelta64,
) -> None:
    """Write an interval file expressing when data is available.

    Should be called on post-filter times so intervals reflect actual
    valid data coverage.
    """
    spans = detect_availability(times, max_gap)
    intervals: list[Interval] = [Interval(s, e) for s, e in spans]
    write_interval(stream, intervals)
