from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

import numpy as np

from stk_files.interval import Interval, write_interval

if TYPE_CHECKING:
    from numpy.typing import NDArray


def detect_availability(
    times: NDArray[np.datetime64],
    max_gap: np.timedelta64,
    min_points: int = 2,
) -> list[tuple[np.datetime64, np.datetime64]]:
    """Identify contiguous data spans from a sorted time array.

    Returns a list of (start, end) tuples. A new span begins whenever
    the gap between consecutive timestamps exceeds *max_gap*.  Spans
    with fewer than *min_points* points are excluded (default 2).
    """
    if times.size == 0:
        return []

    if times.size == 1:
        if min_points <= 1:
            return [(times[0], times[0])]
        return []

    gaps = np.diff(times) > max_gap
    break_indices = np.where(gaps)[0]

    spans: list[tuple[np.datetime64, np.datetime64]] = []
    start_idx = 0
    for brk in break_indices:
        if brk - start_idx + 1 >= min_points:
            spans.append((times[start_idx], times[brk]))
        start_idx = brk + 1
    if len(times) - start_idx >= min_points:
        spans.append((times[start_idx], times[-1]))
    return spans


def write_availability(
    stream: TextIO,
    times: NDArray[np.datetime64],
    max_gap: np.timedelta64,
    min_points: int = 2,
) -> None:
    """Write an interval file expressing when data is available.

    Should be called on post-filter times so intervals reflect actual
    valid data coverage.  Spans with fewer than *min_points* points
    are excluded.
    """
    spans = detect_availability(times, max_gap, min_points=min_points)
    intervals: list[Interval] = [Interval(s, e) for s, e in spans]
    write_interval(stream, intervals)
