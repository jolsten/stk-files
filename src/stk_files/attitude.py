from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO, cast

from stk_files._formatting import format_iso_ymd
from stk_files._parser import STKParseError, parse_data_section, parse_datetime, parse_header
from stk_files._types import (
    ATTITUDE_COLUMNS,
    AttitudeFormat,
    CentralBody,
    EulerSequence,
    InterpolationMethod,
    MessageLevel,
    TimeFormat,
    YPRSequence,
)
from stk_files._validation import validate_epoch_axes, validate_sequence
from stk_files._writer import BaseChunkWriter, RowWriter, prepare_data, stk_writer, write_blocks

if TYPE_CHECKING:
    from collections.abc import Iterator

    import numpy as np
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


class AttitudeChunkWriter(BaseChunkWriter):
    """Streaming writer returned by :func:`attitude_writer`.

    Each call to :meth:`write_chunk` validates, formats, and appends one
    chunk of attitude data.  Cross-chunk time continuity is enforced on
    the *filtered* timestamps so that non-strict filtering cannot cause
    spurious ordering errors.
    """

    def __init__(
        self,
        writer: RowWriter,
        config: AttitudeConfig,
        *,
        strict: bool = False,
        max_rate: float | None = None,
    ) -> None:
        super().__init__(
            writer,
            fmt=config.format,
            expected_cols=ATTITUDE_COLUMNS[config.format],
            time_format=config.time_format,
            scenario_epoch=config.scenario_epoch,
            sequence=config.sequence,
            strict=strict,
            max_rate=max_rate,
        )


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
    times, data = prepare_data(
        config.format,
        ATTITUDE_COLUMNS,
        times,
        data,
        strict=strict,
        max_rate=max_rate,
        presorted=presorted,
        sequence=config.sequence,
    )
    write_blocks(
        stream,
        config.header_lines(),
        config.footer_lines(),
        config.time_format,
        config.scenario_epoch,
        config.format,
        times,
        data,
        chunk_size,
    )


def read_attitude(
    stream: TextIO,
) -> tuple[AttitudeConfig, NDArray[np.datetime64], NDArray[np.floating]]:
    """Read an STK attitude file and return ``(config, times, data)``."""
    lines = [line.rstrip("\n\r") for line in stream]
    header, fmt, data_start = parse_header(lines, "AttitudeTime")

    if fmt not in ATTITUDE_COLUMNS:
        raise STKParseError(f"unknown attitude format: {fmt!r}")

    time_format = header.get("TimeFormat", "ISO-YMD")
    scenario_epoch = (
        parse_datetime(header["ScenarioEpoch"]) if "ScenarioEpoch" in header else None
    )
    axes_epoch = (
        parse_datetime(header["CoordinateAxesEpoch"])
        if "CoordinateAxesEpoch" in header
        else None
    )
    sequence = int(header["Sequence"]) if "Sequence" in header else None

    config = AttitudeConfig(
        format=cast("AttitudeFormat", fmt),
        coordinate_axes=header.get("CoordinateAxes", "ICRF"),
        message_level=cast("MessageLevel | None", header.get("MessageLevel")),
        time_format=cast("TimeFormat", time_format),
        scenario_epoch=scenario_epoch,
        central_body=cast("CentralBody | None", header.get("CentralBody")),
        coordinate_axes_epoch=axes_epoch,
        interpolation_method=cast(
            "InterpolationMethod | None", header.get("InterpolationMethod")
        ),
        interpolation_order=(
            int(header["InterpolationOrder"]) if "InterpolationOrder" in header else None
        ),
        sequence=cast("EulerSequence | YPRSequence | None", sequence),
    )

    times, data = parse_data_section(
        lines, data_start, time_format, ATTITUDE_COLUMNS[fmt], scenario_epoch
    )
    return config, times, data
