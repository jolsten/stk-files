from typing import Optional

import numpy as np
from numpy.typing import NDArray

from stkfiles.files import AttitudeFile, EphemerisFile, IntervalFile
from stkfiles.typing import (
    AttitudeFileFormat,
    CoordinateAxes,
    DateTime,
    DateTimeArray,
    EphemerisFileFormat,
    IntervalList,
    PathLike,
    RotationSequence,
)


def attitude_file(
    filename: PathLike,
    format: AttitudeFileFormat,
    time: DateTimeArray,
    data: np.ndarray,
    axes: CoordinateAxes = "ICRF",
    axes_epoch: Optional[DateTime] = None,
    sequence: Optional[RotationSequence] = None,
) -> None:
    """Create an STK Attitude (.a) File

    Args:
        filename: Path to the output file.
        format:

    """
    with open(filename, "w") as file:
        a = AttitudeFile(
            file,
            format=format,
            coordinate_axes=axes,
            coordinate_axes_epoch=axes_epoch,
            sequence=sequence,
        )
        a.write(time, data)


def ephemeris_file(
    filename: PathLike,
    format: EphemerisFileFormat,
    time: DateTimeArray,
    data: np.ndarray,
    axes: CoordinateAxes = "ICRF",
    axes_epoch: Optional[DateTime] = None,
) -> None:
    """Create an STK Ephemeris (.e) File

    Args:
        filename: Path to the output file.
        format: Ephemeris file format.
        time: Time vector.
        data: Ephemeris data array.
        axes: Coordinate axes.
        axes_epoch: Coordinate axes epoch.
    """
    with open(filename, "w") as file:
        e = EphemerisFile(
            file,
            format=format,
            coordinate_axes=axes,
            coordinate_axes_epoch=axes_epoch,
        )
        e.write(time, data)


def interval_file(
    filename: PathLike,
    intervals: Optional[IntervalList] = None,
) -> None:
    """Create an STK Interval (.int) File.

    Args:
        filename: Path to the output file.
        intervals: An iterable of intervals (start, stop, data)
        start:
        stop:
        data:
    """
    with open(filename, "w") as file:
        i = IntervalFile(file)
        i.write(intervals)
