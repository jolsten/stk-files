from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO

import numpy as np

from stk_files._formatting import (
    format_ep_sec_array,
    format_generic_block,
    format_iso_ymd,
    format_iso_ymd_array,
)
from stk_files._types import (
    EPHEMERIS_COLUMNS,
    CentralBody,
    EphemerisFormat,
    InterpolationMethod,
    MessageLevel,
    TimeFormat,
)
from stk_files._validation import (
    sort_by_time,
    validate_data,
    validate_epoch_axes,
    validate_shape,
    validate_times,
)
from stk_files._writer import stk_writer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from numpy.typing import NDArray


@dataclass(frozen=True)
class EphemerisConfig:
    """Configuration for an STK Ephemeris (.e) file."""

    format: EphemerisFormat
    coordinate_system: str = "ICRF"
    message_level: MessageLevel | None = None
    time_format: TimeFormat = "ISO-YMD"
    scenario_epoch: np.datetime64 | None = None
    central_body: CentralBody | None = None
    coordinate_system_epoch: np.datetime64 | None = None
    interpolation_method: InterpolationMethod | None = None
    interpolation_order: int | None = None

    def __post_init__(self) -> None:
        validate_epoch_axes(self.coordinate_system, self.coordinate_system_epoch)
        if self.time_format == "EpSec" and self.scenario_epoch is None:
            raise ValueError("EpSec time format requires scenario_epoch")

    def header_lines(self, num_points: int | None = None) -> list[str]:
        hdr: list[str] = ["stk.v.12.0", "BEGIN Ephemeris"]
        if self.message_level is not None:
            hdr.append(f"MessageLevel            {self.message_level}")
        hdr.append(f"TimeFormat              {self.time_format}")
        if self.scenario_epoch is not None:
            hdr.append(f"ScenarioEpoch           {format_iso_ymd(self.scenario_epoch)}")
        if self.central_body is not None:
            hdr.append(f"CentralBody             {self.central_body}")
        hdr.append(f"CoordinateSystem        {self.coordinate_system}")
        if self.coordinate_system_epoch is not None:
            hdr.append(f"CoordinateSystemEpoch   {format_iso_ymd(self.coordinate_system_epoch)}")
        if self.interpolation_method is not None:
            hdr.append(f"InterpolationMethod     {self.interpolation_method}")
        if self.interpolation_order is not None:
            hdr.append(f"InterpolationSamplesM1  {self.interpolation_order}")
        if num_points is not None:
            hdr.append(f"NumberOfEphemerisPoints  {num_points}")
        hdr.append(f"Ephemeris{self.format}")
        return hdr

    def footer_lines(self) -> list[str]:
        return ["END Ephemeris"]


def _format_times(
    config: EphemerisConfig,
    times: NDArray[np.datetime64],
) -> list[str]:
    if config.time_format == "EpSec":
        epoch = config.scenario_epoch
        if epoch is None:
            raise ValueError("EpSec time format requires scenario_epoch")
        return format_ep_sec_array(times, epoch)
    return format_iso_ymd_array(times)


class EphemerisChunkWriter:
    """Streaming writer returned by :func:`ephemeris_writer`.

    Each call to :meth:`write_chunk` validates, formats, and appends one
    chunk of ephemeris data.  Cross-chunk time continuity is enforced on
    the *filtered* timestamps.
    """

    def __init__(
        self,
        writer: object,
        config: EphemerisConfig,
        *,
        strict: bool = False,
        max_rate: float | None = None,
    ) -> None:
        self._writer = writer
        self._config = config
        self._strict = strict
        self._max_rate = max_rate
        self._expected_cols = EPHEMERIS_COLUMNS[config.format]
        self._last_time: np.datetime64 | None = None

    def write_chunk(
        self,
        times: NDArray[np.datetime64],
        data: NDArray[np.floating],
    ) -> None:
        """Validate, format, and write a chunk of ephemeris data."""
        times = np.atleast_1d(times)
        data = np.atleast_2d(data)
        if times.shape[0] == 0:
            return
        validate_shape(times, data, self._expected_cols)
        validate_times(times)

        times, data = validate_data(
            self._config.format,
            times,
            data,
            strict=self._strict,
            max_rate=self._max_rate,
        )
        if times.shape[0] == 0:
            return

        # Cross-chunk time continuity (checked after filtering)
        if self._last_time is not None and times[0] <= self._last_time:
            raise ValueError(
                f"chunk starts at {times[0]} but previous chunk ended at {self._last_time}"
            )

        time_strs = _format_times(self._config, times)
        data_strs = format_generic_block(data)
        self._writer.write_block(time_strs, data_strs)  # type: ignore[attr-defined]
        self._last_time = times[-1]


@contextlib.contextmanager
def ephemeris_writer(
    stream: TextIO,
    config: EphemerisConfig,
    *,
    strict: bool = False,
    max_rate: float | None = None,
) -> Iterator[EphemerisChunkWriter]:
    """Context manager for streaming ephemeris data in chunks.

    ``NumberOfEphemerisPoints`` is omitted from the header in chunked
    mode because the total count is unknown upfront.  STK treats this
    field as optional and will read the file without it.
    """
    header = config.header_lines(num_points=None)
    with stk_writer(stream, header, config.footer_lines()) as w:
        yield EphemerisChunkWriter(w, config, strict=strict, max_rate=max_rate)


def write_ephemeris(
    stream: TextIO,
    config: EphemerisConfig,
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    *,
    strict: bool = False,
    max_rate: float | None = None,
    presorted: bool = False,
    chunk_size: int | None = None,
) -> None:
    """Write a complete ephemeris file to a stream."""
    expected_cols = EPHEMERIS_COLUMNS[config.format]
    times = np.atleast_1d(times)
    data = np.atleast_2d(data)
    validate_shape(times, data, expected_cols)
    if not presorted:
        times, data = sort_by_time(times, data)
    validate_times(times)
    times, data = validate_data(
        config.format,
        times,
        data,
        strict=strict,
        max_rate=max_rate,
    )
    if times.shape[0] == 0:
        raise ValueError("no valid data rows after validation")

    header = config.header_lines(num_points=len(times))

    if chunk_size is not None:
        with stk_writer(stream, header, config.footer_lines()) as w:
            for start in range(0, len(times), chunk_size):
                end = min(start + chunk_size, len(times))
                time_strs = _format_times(config, times[start:end])
                data_strs = format_generic_block(data[start:end])
                w.write_block(time_strs, data_strs)
    else:
        time_strs = _format_times(config, times)
        data_strs = format_generic_block(data)
        with stk_writer(stream, header, config.footer_lines()) as w:
            w.write_block(time_strs, data_strs)
