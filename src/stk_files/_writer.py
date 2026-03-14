from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, TextIO

import numpy as np

from stk_files._coerce import coerce_data, coerce_times
from stk_files._formatting import format_data_block, format_times
from stk_files._validation import (
    sort_by_time,
    validate_data,
    validate_shape,
    validate_times,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from numpy.typing import NDArray

    from stk_files._types import AzElSequence, EulerSequence, TimeFormat, YPRSequence


class RowWriter:
    """Writes formatted time+data rows to a stream."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def write_row(self, formatted_time: str, formatted_data: str) -> None:
        print(formatted_time, formatted_data, file=self._stream)

    def write_block(
        self,
        time_strings: list[str],
        data_strings: list[str],
        batch_size: int = 50_000,
    ) -> None:
        """Write pre-formatted time+data string lists in batched I/O."""
        for start in range(0, len(time_strings), batch_size):
            end = min(start + batch_size, len(time_strings))
            chunk = "\n".join(
                f"{t} {d}" for t, d in zip(time_strings[start:end], data_strings[start:end])
            )
            self._stream.write(chunk)
            self._stream.write("\n")


@contextlib.contextmanager
def stk_writer(
    stream: TextIO,
    header_lines: list[str],
    footer_lines: list[str],
) -> Iterator[RowWriter]:
    """Context manager that writes header on enter, footer on exit."""
    writer = RowWriter(stream)
    for line in header_lines:
        print(line, file=stream)
    try:
        yield writer
    finally:
        for line in footer_lines:
            print(line, file=stream)


# ---------------------------------------------------------------------------
# Shared chunk writer base class
# ---------------------------------------------------------------------------


class BaseChunkWriter:
    """Base class for streaming chunk writers.

    Subclasses should call ``super().__init__()`` with the format-specific
    parameters unpacked from their config dataclass.
    """

    def __init__(
        self,
        writer: RowWriter,
        *,
        fmt: str,
        expected_cols: int,
        time_format: TimeFormat,
        scenario_epoch: np.datetime64 | None = None,
        sequence: EulerSequence | YPRSequence | AzElSequence | None = None,
        strict: bool = False,
        max_rate: float | None = None,
    ) -> None:
        self._writer = writer
        self._fmt = fmt
        self._expected_cols = expected_cols
        self._time_format = time_format
        self._scenario_epoch = scenario_epoch
        self._sequence = sequence
        self._strict = strict
        self._max_rate = max_rate
        self._last_time: np.datetime64 | None = None

    def write_chunk(
        self,
        times: NDArray[np.datetime64],
        data: NDArray[np.floating],
    ) -> None:
        """Validate, format, and write a chunk of data."""
        times = np.atleast_1d(coerce_times(times))
        data = np.atleast_2d(coerce_data(data))
        if times.shape[0] == 0:
            return
        validate_shape(times, data, self._expected_cols)
        validate_times(times)

        times, data = validate_data(
            self._fmt,
            times,
            data,
            strict=self._strict,
            max_rate=self._max_rate,
            sequence=self._sequence,
        )
        if times.shape[0] == 0:
            return

        # Cross-chunk time continuity (checked after filtering)
        if self._last_time is not None and times[0] <= self._last_time:
            raise ValueError(
                f"chunk starts at {times[0]} but previous chunk ended at {self._last_time}"
            )

        time_strs = format_times(self._time_format, times, self._scenario_epoch)
        data_strs = format_data_block(self._fmt, data)
        self._writer.write_block(time_strs, data_strs)
        self._last_time = times[-1]


# ---------------------------------------------------------------------------
# Shared helpers for single-call write functions
# ---------------------------------------------------------------------------


def prepare_data(
    fmt: str,
    columns: dict[str, int],
    times: Any,
    data: Any,
    *,
    strict: bool = False,
    max_rate: float | None = None,
    presorted: bool = False,
    sequence: EulerSequence | YPRSequence | AzElSequence | None = None,
) -> tuple[NDArray[np.datetime64], NDArray[np.floating]]:
    """Coerce, validate, sort, and filter data arrays."""
    expected_cols = columns[fmt]
    times = np.atleast_1d(coerce_times(times))
    data = np.atleast_2d(coerce_data(data))
    validate_shape(times, data, expected_cols)
    if not presorted:
        times, data = sort_by_time(times, data)
    validate_times(times)
    times, data = validate_data(
        fmt, times, data, strict=strict, max_rate=max_rate, sequence=sequence
    )
    if times.shape[0] == 0:
        raise ValueError("no valid data rows after validation")
    return times, data


def write_blocks(
    stream: TextIO,
    header: list[str],
    footer: list[str],
    time_format: TimeFormat,
    scenario_epoch: np.datetime64 | None,
    fmt: str,
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    chunk_size: int | None = None,
) -> None:
    """Format and write data blocks with header/footer."""
    if chunk_size is not None:
        with stk_writer(stream, header, footer) as w:
            for start in range(0, len(times), chunk_size):
                end = min(start + chunk_size, len(times))
                time_strs = format_times(time_format, times[start:end], scenario_epoch)
                data_strs = format_data_block(fmt, data[start:end])
                w.write_block(time_strs, data_strs)
    else:
        time_strs = format_times(time_format, times, scenario_epoch)
        data_strs = format_data_block(fmt, data)
        with stk_writer(stream, header, footer) as w:
            w.write_block(time_strs, data_strs)
