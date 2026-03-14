from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO, cast

from stk_files._formatting import format_iso_ymd
from stk_files._parser import STKParseError, parse_data_section, parse_datetime, parse_header
from stk_files._types import (
    EPHEMERIS_COLUMNS,
    CentralBody,
    EphemerisFormat,
    InterpolationMethod,
    MessageLevel,
    TimeFormat,
)
from stk_files._validation import validate_epoch_axes
from stk_files._writer import BaseChunkWriter, RowWriter, prepare_data, stk_writer, write_blocks

if TYPE_CHECKING:
    from collections.abc import Iterator

    import numpy as np
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


class EphemerisChunkWriter(BaseChunkWriter):
    """Streaming writer returned by :func:`ephemeris_writer`.

    Each call to :meth:`write_chunk` validates, formats, and appends one
    chunk of ephemeris data.  Cross-chunk time continuity is enforced on
    the *filtered* timestamps.
    """

    def __init__(
        self,
        writer: RowWriter,
        config: EphemerisConfig,
        *,
        strict: bool = False,
        max_rate: float | None = None,
    ) -> None:
        super().__init__(
            writer,
            fmt=config.format,
            expected_cols=EPHEMERIS_COLUMNS[config.format],
            time_format=config.time_format,
            scenario_epoch=config.scenario_epoch,
            strict=strict,
            max_rate=max_rate,
        )


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
    times, data = prepare_data(
        config.format,
        EPHEMERIS_COLUMNS,
        times,
        data,
        strict=strict,
        max_rate=max_rate,
        presorted=presorted,
    )
    write_blocks(
        stream,
        config.header_lines(num_points=len(times)),
        config.footer_lines(),
        config.time_format,
        config.scenario_epoch,
        config.format,
        times,
        data,
        chunk_size,
    )


def read_ephemeris(
    stream: TextIO,
) -> tuple[EphemerisConfig, NDArray[np.datetime64], NDArray[np.floating]]:
    """Read an STK ephemeris file and return ``(config, times, data)``."""
    lines = [line.rstrip("\n\r") for line in stream]
    header, fmt, data_start = parse_header(lines, "Ephemeris")

    if fmt not in EPHEMERIS_COLUMNS:
        raise STKParseError(f"unknown ephemeris format: {fmt!r}")

    time_format = header.get("TimeFormat", "ISO-YMD")
    scenario_epoch = (
        parse_datetime(header["ScenarioEpoch"]) if "ScenarioEpoch" in header else None
    )
    coord_epoch = (
        parse_datetime(header["CoordinateSystemEpoch"])
        if "CoordinateSystemEpoch" in header
        else None
    )

    config = EphemerisConfig(
        format=cast("EphemerisFormat", fmt),
        coordinate_system=header.get("CoordinateSystem", "ICRF"),
        message_level=cast("MessageLevel | None", header.get("MessageLevel")),
        time_format=cast("TimeFormat", time_format),
        scenario_epoch=scenario_epoch,
        central_body=cast("CentralBody | None", header.get("CentralBody")),
        coordinate_system_epoch=coord_epoch,
        interpolation_method=cast(
            "InterpolationMethod | None", header.get("InterpolationMethod")
        ),
        interpolation_order=(
            int(header["InterpolationSamplesM1"])
            if "InterpolationSamplesM1" in header
            else None
        ),
    )

    times, data = parse_data_section(
        lines, data_start, time_format, EPHEMERIS_COLUMNS[fmt], scenario_epoch
    )
    return config, times, data
