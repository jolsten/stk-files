from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO

import numpy as np

from stk_files._coerce import coerce_data, coerce_times
from stk_files._formatting import (
    format_ep_sec_array,
    format_generic_block,
    format_iso_ymd,
    format_iso_ymd_array,
    format_quaternion_block,
)
from stk_files._types import (
    ATTITUDE_COLUMNS,
    QUATERNION_FORMATS,
    AttitudeFormat,
    CentralBody,
    EulerSequence,
    InterpolationMethod,
    MessageLevel,
    TimeFormat,
    YPRSequence,
)
from stk_files._validation import (
    sort_by_time,
    validate_data,
    validate_epoch_axes,
    validate_sequence,
    validate_shape,
    validate_times,
)
from stk_files._writer import stk_writer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from numpy.typing import NDArray


@dataclass(frozen=True)
class AttitudeConfig:
    """Configuration for an STK Attitude (.a) file."""

    format: AttitudeFormat
    coordinate_axes: str = "ICRF"
    message_level: MessageLevel | None = None
    time_format: TimeFormat = "ISO-YMD"
    scenario_epoch: np.datetime64 | None = None
    central_body: CentralBody | None = None
    coordinate_axes_epoch: np.datetime64 | None = None
    interpolation_method: InterpolationMethod | None = None
    interpolation_order: int | None = None
    sequence: EulerSequence | YPRSequence | None = None

    def __post_init__(self) -> None:
        validate_sequence(self.format, self.sequence)
        validate_epoch_axes(self.coordinate_axes, self.coordinate_axes_epoch)
        if self.time_format == "EpSec" and self.scenario_epoch is None:
            raise ValueError("EpSec time format requires scenario_epoch")

    def header_lines(self) -> list[str]:
        hdr: list[str] = ["stk.v.11.0", "BEGIN Attitude"]
        if self.message_level is not None:
            hdr.append(f"MessageLevel        {self.message_level}")
        hdr.append(f"TimeFormat          {self.time_format}")
        if self.scenario_epoch is not None:
            hdr.append(f"ScenarioEpoch       {format_iso_ymd(self.scenario_epoch)}")
        if self.central_body is not None:
            hdr.append(f"CentralBody         {self.central_body}")
        hdr.append(f"CoordinateAxes      {self.coordinate_axes}")
        if self.coordinate_axes_epoch is not None:
            hdr.append(f"CoordinateAxesEpoch {format_iso_ymd(self.coordinate_axes_epoch)}")
        if self.interpolation_method is not None:
            hdr.append(f"InterpolationMethod {self.interpolation_method}")
        if self.interpolation_order is not None:
            hdr.append(f"InterpolationOrder  {self.interpolation_order}")
        if self.sequence is not None:
            hdr.append(f"Sequence            {self.sequence}")
        hdr.append(f"AttitudeTime{self.format}")
        return hdr

    def footer_lines(self) -> list[str]:
        return ["END Attitude"]


def _format_times(
    config: AttitudeConfig,
    times: NDArray[np.datetime64],
) -> list[str]:
    if config.time_format == "EpSec":
        epoch = config.scenario_epoch
        if epoch is None:
            raise ValueError("EpSec time format requires scenario_epoch")
        return format_ep_sec_array(times, epoch)
    return format_iso_ymd_array(times)


def _format_data(fmt: str, data: NDArray[np.floating]) -> list[str]:
    if fmt in QUATERNION_FORMATS:
        return format_quaternion_block(data)
    return format_generic_block(data)


class AttitudeChunkWriter:
    """Streaming writer returned by :func:`attitude_writer`.

    Each call to :meth:`write_chunk` validates, formats, and appends one
    chunk of attitude data.  Cross-chunk time continuity is enforced on
    the *filtered* timestamps so that non-strict filtering cannot cause
    spurious ordering errors.
    """

    def __init__(
        self,
        writer: object,
        config: AttitudeConfig,
        *,
        strict: bool = False,
        max_rate: float | None = None,
    ) -> None:
        self._writer = writer  # RowWriter
        self._config = config
        self._strict = strict
        self._max_rate = max_rate
        self._expected_cols = ATTITUDE_COLUMNS[config.format]
        self._last_time: np.datetime64 | None = None

    def write_chunk(
        self,
        times: NDArray[np.datetime64],
        data: NDArray[np.floating],
    ) -> None:
        """Validate, format, and write a chunk of attitude data."""
        times = np.atleast_1d(coerce_times(times))
        data = np.atleast_2d(coerce_data(data))
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
            sequence=self._config.sequence,
        )
        if times.shape[0] == 0:
            return

        # Cross-chunk time continuity (checked after filtering)
        if self._last_time is not None and times[0] <= self._last_time:
            raise ValueError(
                f"chunk starts at {times[0]} but previous chunk ended at {self._last_time}"
            )

        time_strs = _format_times(self._config, times)
        data_strs = _format_data(self._config.format, data)
        self._writer.write_block(time_strs, data_strs)  # type: ignore[attr-defined]
        self._last_time = times[-1]


@contextlib.contextmanager
def attitude_writer(
    stream: TextIO,
    config: AttitudeConfig,
    *,
    strict: bool = False,
    max_rate: float | None = None,
) -> Iterator[AttitudeChunkWriter]:
    """Context manager for streaming attitude data in chunks."""
    with stk_writer(stream, config.header_lines(), config.footer_lines()) as w:
        yield AttitudeChunkWriter(w, config, strict=strict, max_rate=max_rate)


def write_attitude(
    stream: TextIO,
    config: AttitudeConfig,
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    *,
    strict: bool = False,
    max_rate: float | None = None,
    presorted: bool = False,
    chunk_size: int | None = None,
) -> None:
    """Write a complete attitude file to a stream."""
    expected_cols = ATTITUDE_COLUMNS[config.format]
    times = np.atleast_1d(coerce_times(times))
    data = np.atleast_2d(coerce_data(data))
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
        sequence=config.sequence,
    )
    if times.shape[0] == 0:
        raise ValueError("no valid data rows after validation")

    if chunk_size is not None:
        # Chunked write — data is already validated, just format in chunks
        with stk_writer(stream, config.header_lines(), config.footer_lines()) as w:
            for start in range(0, len(times), chunk_size):
                end = min(start + chunk_size, len(times))
                time_strs = _format_times(config, times[start:end])
                data_strs = _format_data(config.format, data[start:end])
                w.write_block(time_strs, data_strs)
    else:
        time_strs = _format_times(config, times)
        data_strs = _format_data(config.format, data)
        with stk_writer(stream, config.header_lines(), config.footer_lines()) as w:
            w.write_block(time_strs, data_strs)
