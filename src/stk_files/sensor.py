from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO, cast

from stk_files._formatting import format_iso_ymd
from stk_files._parser import STKParseError, parse_data_section, parse_datetime, parse_header
from stk_files._types import (
    SENSOR_COLUMNS,
    AzElSequence,
    CentralBody,
    EulerSequence,
    MessageLevel,
    SensorFormat,
    TimeFormat,
    YPRSequence,
)
from stk_files._validation import validate_sequence
from stk_files._writer import BaseChunkWriter, RowWriter, prepare_data, stk_writer, write_blocks

if TYPE_CHECKING:
    from collections.abc import Iterator

    import numpy as np
    from numpy.typing import NDArray


@dataclass(frozen=True)
class SensorConfig:
    """Configuration for an STK Sensor Pointing (.sp) file."""

    format: SensorFormat
    coordinate_axes: str | None = None
    message_level: MessageLevel | None = None
    time_format: TimeFormat = "ISO-YMD"
    scenario_epoch: np.datetime64 | None = None
    central_body: CentralBody | None = None
    sequence: EulerSequence | YPRSequence | AzElSequence | None = None

    def __post_init__(self) -> None:
        validate_sequence(self.format, self.sequence)
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
        if self.coordinate_axes is not None:
            hdr.append(f"CoordinateAxes      {self.coordinate_axes}")
        if self.sequence is not None:
            hdr.append(f"Sequence            {self.sequence}")
        hdr.append(f"AttitudeTime{self.format}")
        return hdr

    def footer_lines(self) -> list[str]:
        return ["END Attitude"]


class SensorChunkWriter(BaseChunkWriter):
    """Streaming writer returned by :func:`sensor_writer`.

    Each call to :meth:`write_chunk` validates, formats, and appends one
    chunk of sensor pointing data.  Cross-chunk time continuity is
    enforced on the *filtered* timestamps.
    """

    def __init__(
        self,
        writer: RowWriter,
        config: SensorConfig,
        *,
        strict: bool = False,
        max_rate: float | None = None,
    ) -> None:
        super().__init__(
            writer,
            fmt=config.format,
            expected_cols=SENSOR_COLUMNS[config.format],
            time_format=config.time_format,
            scenario_epoch=config.scenario_epoch,
            sequence=config.sequence,
            strict=strict,
            max_rate=max_rate,
        )


@contextlib.contextmanager
def sensor_writer(
    stream: TextIO,
    config: SensorConfig,
    *,
    strict: bool = False,
    max_rate: float | None = None,
) -> Iterator[SensorChunkWriter]:
    """Context manager for streaming sensor data in chunks."""
    with stk_writer(stream, config.header_lines(), config.footer_lines()) as w:
        yield SensorChunkWriter(w, config, strict=strict, max_rate=max_rate)


def write_sensor(
    stream: TextIO,
    config: SensorConfig,
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    *,
    strict: bool = False,
    max_rate: float | None = None,
    presorted: bool = False,
    chunk_size: int | None = None,
) -> None:
    """Write a complete sensor pointing file to a stream."""
    times, data = prepare_data(
        config.format,
        SENSOR_COLUMNS,
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


def read_sensor(
    stream: TextIO,
) -> tuple[SensorConfig, NDArray[np.datetime64], NDArray[np.floating]]:
    """Read an STK sensor pointing file and return ``(config, times, data)``."""
    lines = [line.rstrip("\n\r") for line in stream]
    header, fmt, data_start = parse_header(lines, "AttitudeTime")

    if fmt not in SENSOR_COLUMNS:
        raise STKParseError(f"unknown sensor format: {fmt!r}")

    time_format = header.get("TimeFormat", "ISO-YMD")
    scenario_epoch = (
        parse_datetime(header["ScenarioEpoch"]) if "ScenarioEpoch" in header else None
    )
    sequence = int(header["Sequence"]) if "Sequence" in header else None

    config = SensorConfig(
        format=cast("SensorFormat", fmt),
        coordinate_axes=header.get("CoordinateAxes"),
        message_level=cast("MessageLevel | None", header.get("MessageLevel")),
        time_format=cast("TimeFormat", time_format),
        scenario_epoch=scenario_epoch,
        central_body=cast("CentralBody | None", header.get("CentralBody")),
        sequence=cast("EulerSequence | YPRSequence | AzElSequence | None", sequence),
    )

    times, data = parse_data_section(
        lines, data_start, time_format, SENSOR_COLUMNS[fmt], scenario_epoch
    )
    return config, times, data
