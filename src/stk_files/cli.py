from __future__ import annotations

import contextlib
import sys
from typing import TYPE_CHECKING, TextIO, cast

import click
import numpy as np

if TYPE_CHECKING:
    from collections.abc import Iterator

    from numpy.typing import NDArray

from stk_files._types import (
    ATTITUDE_COLUMNS,
    EPHEMERIS_COLUMNS,
    SENSOR_COLUMNS,
    AttitudeFormat,
    CentralBody,
    EphemerisFormat,
    EulerSequence,
    InterpolationMethod,
    SensorFormat,
    TimeFormat,
    YPRSequence,
)
from stk_files.attitude import AttitudeConfig, write_attitude
from stk_files.ephemeris import EphemerisConfig, write_ephemeris
from stk_files.interval import Interval, write_interval
from stk_files.sensor import SensorConfig, write_sensor


def _parse_datetime(value: str, line_num: int) -> np.datetime64:
    """Parse a datetime string, raising ClickException on failure."""
    try:
        return np.datetime64(value, "ms")
    except ValueError as exc:
        raise click.ClickException(f"line {line_num}: invalid datetime {value!r}: {exc}") from None


def _parse_lines(
    delimiter: str | None,
) -> tuple[NDArray[np.datetime64], NDArray[np.floating]]:
    """Read stdin, return (times, data) arrays."""
    times: list[np.datetime64] = []
    rows: list[list[float]] = []
    for i, line in enumerate(sys.stdin, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(delimiter)  # None = whitespace
        times.append(_parse_datetime(parts[0], i))
        try:
            rows.append([float(x) for x in parts[1:]])
        except ValueError as exc:
            raise click.ClickException(f"line {i}: invalid number: {exc}") from None
    return np.array(times, dtype="datetime64[ms]"), np.array(rows)


def _parse_interval_lines(
    delimiter: str | None,
) -> list[Interval]:
    """Read stdin, return list of Interval objects."""
    intervals: list[Interval] = []
    for i, line in enumerate(sys.stdin, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(delimiter)  # None = whitespace
        if len(parts) < 2:
            raise click.ClickException(
                f"line {i}: expected at least 2 columns (start, end), got {len(parts)}"
            )
        t0 = _parse_datetime(parts[0], i)
        t1 = _parse_datetime(parts[1], i)
        if len(parts) > 2:
            intervals.append(Interval(t0, t1, " ".join(parts[2:])))
        else:
            intervals.append(Interval(t0, t1))
    return intervals


@contextlib.contextmanager
def _open_output(output: str | None) -> Iterator[TextIO]:
    """Context manager returning the output stream."""
    if output is None:
        yield sys.stdout
    else:
        f = open(output, "w")  # noqa: SIM115
        try:
            yield f
        finally:
            f.close()


def _as_attitude_format(value: str) -> AttitudeFormat:
    """Validate and narrow a CLI string to AttitudeFormat."""
    if value not in ATTITUDE_COLUMNS:
        raise click.ClickException(f"unknown attitude format: {value!r}")
    return cast("AttitudeFormat", value)


def _as_ephemeris_format(value: str) -> EphemerisFormat:
    """Validate and narrow a CLI string to EphemerisFormat."""
    if value not in EPHEMERIS_COLUMNS:
        raise click.ClickException(f"unknown ephemeris format: {value!r}")
    return cast("EphemerisFormat", value)


def _as_sensor_format(value: str) -> SensorFormat:
    """Validate and narrow a CLI string to SensorFormat."""
    if value not in SENSOR_COLUMNS:
        raise click.ClickException(f"unknown sensor format: {value!r}")
    return cast("SensorFormat", value)


@click.group()
def main() -> None:
    """Generate STK external data files from piped text data."""


@main.command()
@click.argument("format", type=click.Choice(sorted(ATTITUDE_COLUMNS)))
@click.option("-o", "--output", type=str, default=None, help="Output file (default: stdout)")
@click.option("-a", "--axes", type=str, default="ICRF", help="Coordinate axes")
@click.option("--axes-epoch", type=str, default=None, help="Coordinate axes epoch datetime")
@click.option("-b", "--central-body", type=str, default=None, help="Central body")
@click.option(
    "-t",
    "--time-format",
    type=click.Choice(["ISO-YMD", "EpSec"]),
    default="ISO-YMD",
)
@click.option("-e", "--scenario-epoch", type=str, default=None, help="Scenario epoch datetime")
@click.option(
    "--interpolation-method",
    type=click.Choice(["Lagrange", "Hermite"]),
    default=None,
)
@click.option("--interpolation-order", type=int, default=None)
@click.option("-s", "--sequence", type=int, default=None, help="Rotation sequence")
@click.option("-d", "--delimiter", type=str, default=None, help="Column delimiter")
def attitude(
    format: str,
    output: str | None,
    axes: str,
    axes_epoch: str | None,
    central_body: str | None,
    time_format: str,
    scenario_epoch: str | None,
    interpolation_method: str | None,
    interpolation_order: int | None,
    sequence: int | None,
    delimiter: str | None,
) -> None:
    """Generate an STK attitude file (.a) from stdin data."""
    times, data = _parse_lines(delimiter)
    config = AttitudeConfig(
        format=_as_attitude_format(format),
        coordinate_axes=axes,
        coordinate_axes_epoch=(np.datetime64(axes_epoch, "ms") if axes_epoch else None),
        central_body=cast("CentralBody | None", central_body),
        time_format=cast("TimeFormat", time_format),
        scenario_epoch=(np.datetime64(scenario_epoch, "ms") if scenario_epoch else None),
        interpolation_method=cast("InterpolationMethod | None", interpolation_method),
        interpolation_order=interpolation_order,
        sequence=cast("EulerSequence | YPRSequence | None", sequence),
    )
    with _open_output(output) as stream:
        write_attitude(stream, config, times, data, presorted=True)


@main.command()
@click.argument("format", type=click.Choice(sorted(EPHEMERIS_COLUMNS)))
@click.option("-o", "--output", type=str, default=None, help="Output file (default: stdout)")
@click.option("-a", "--axes", type=str, default="ICRF", help="Coordinate system")
@click.option("--axes-epoch", type=str, default=None, help="Coordinate system epoch datetime")
@click.option("-b", "--central-body", type=str, default=None, help="Central body")
@click.option(
    "-t",
    "--time-format",
    type=click.Choice(["ISO-YMD", "EpSec"]),
    default="ISO-YMD",
)
@click.option("-e", "--scenario-epoch", type=str, default=None, help="Scenario epoch datetime")
@click.option(
    "--interpolation-method",
    type=click.Choice(["Lagrange", "Hermite"]),
    default=None,
)
@click.option("--interpolation-order", type=int, default=None)
@click.option("-d", "--delimiter", type=str, default=None, help="Column delimiter")
def ephemeris(
    format: str,
    output: str | None,
    axes: str,
    axes_epoch: str | None,
    central_body: str | None,
    time_format: str,
    scenario_epoch: str | None,
    interpolation_method: str | None,
    interpolation_order: int | None,
    delimiter: str | None,
) -> None:
    """Generate an STK ephemeris file (.e) from stdin data."""
    times, data = _parse_lines(delimiter)
    config = EphemerisConfig(
        format=_as_ephemeris_format(format),
        coordinate_system=axes,
        coordinate_system_epoch=(np.datetime64(axes_epoch, "ms") if axes_epoch else None),
        central_body=cast("CentralBody | None", central_body),
        time_format=cast("TimeFormat", time_format),
        scenario_epoch=(np.datetime64(scenario_epoch, "ms") if scenario_epoch else None),
        interpolation_method=cast("InterpolationMethod | None", interpolation_method),
        interpolation_order=interpolation_order,
    )
    with _open_output(output) as stream:
        write_ephemeris(stream, config, times, data, presorted=True)


@main.command()
@click.option("-o", "--output", type=str, default=None, help="Output file (default: stdout)")
@click.option("-d", "--delimiter", type=str, default=None, help="Column delimiter")
def interval(
    output: str | None,
    delimiter: str | None,
) -> None:
    """Generate an STK interval list file (.int) from stdin data."""
    intervals = _parse_interval_lines(delimiter)
    with _open_output(output) as stream:
        write_interval(stream, intervals)


@main.command()
@click.argument("format", type=click.Choice(sorted(SENSOR_COLUMNS)))
@click.option("-o", "--output", type=str, default=None, help="Output file (default: stdout)")
@click.option("-a", "--axes", type=str, default=None, help="Coordinate axes")
@click.option("-b", "--central-body", type=str, default=None, help="Central body")
@click.option(
    "-t",
    "--time-format",
    type=click.Choice(["ISO-YMD", "EpSec"]),
    default="ISO-YMD",
)
@click.option("-e", "--scenario-epoch", type=str, default=None, help="Scenario epoch datetime")
@click.option("-s", "--sequence", type=int, default=None, help="Rotation sequence")
@click.option("-d", "--delimiter", type=str, default=None, help="Column delimiter")
def sensor(
    format: str,
    output: str | None,
    axes: str | None,
    central_body: str | None,
    time_format: str,
    scenario_epoch: str | None,
    sequence: int | None,
    delimiter: str | None,
) -> None:
    """Generate an STK sensor pointing file (.sp) from stdin data."""
    times, data = _parse_lines(delimiter)
    config = SensorConfig(
        format=_as_sensor_format(format),
        coordinate_axes=axes,
        central_body=cast("CentralBody | None", central_body),
        time_format=cast("TimeFormat", time_format),
        scenario_epoch=(np.datetime64(scenario_epoch, "ms") if scenario_epoch else None),
        sequence=cast("EulerSequence | YPRSequence | None", sequence),
    )
    with _open_output(output) as stream:
        write_sensor(stream, config, times, data, presorted=True)
