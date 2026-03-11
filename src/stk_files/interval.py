from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Iterable

    import numpy as np

from stk_files._formatting import format_iso_ymd
from stk_files._validation import validate_intervals
from stk_files._writer import stk_writer


@dataclass(frozen=True)
class Interval:
    """A time interval with optional metadata."""

    start: np.datetime64
    end: np.datetime64
    data: str = ""


@dataclass(frozen=True)
class IntervalConfig:
    """Configuration for an STK Interval List (.int) file."""

    def header_lines(self) -> list[str]:
        return [
            "stk.v.12.0",
            "BEGIN IntervalList",
            "    DateUnitAbrv ISO-YMD",
            "BEGIN Intervals",
        ]

    def footer_lines(self) -> list[str]:
        return [
            "END Intervals",
            "END IntervalList",
        ]


def write_interval(
    stream: TextIO,
    intervals: Iterable[Interval],
    config: IntervalConfig | None = None,
) -> None:
    """Write a complete interval list file to a stream."""
    if config is None:
        config = IntervalConfig()
    interval_list = list(intervals)
    validate_intervals([(iv.start, iv.end) for iv in interval_list])

    with stk_writer(stream, config.header_lines(), config.footer_lines()) as w:
        for iv in interval_list:
            t0 = format_iso_ymd(iv.start)
            t1 = format_iso_ymd(iv.end)
            if iv.data:
                w.write_row(f'"{t0}" "{t1}"', iv.data)
            else:
                w.write_row(f'"{t0}"', f'"{t1}"')
