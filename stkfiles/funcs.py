from typing import Optional

import numpy as np

from stkfiles.files import AttitudeFile
from stkfiles.typing import (
    AttitudeFileFormat,
    CoordinateAxes,
    PathLike,
    RotationSequence,
)


def attitude_file(
    filename: PathLike,
    format: AttitudeFileFormat,
    time: np.ndarray,
    data: np.ndarray,
    coordinate_axes: CoordinateAxes = "ICRF",
    sequence: Optional[RotationSequence] = None,
) -> None:
    with open(filename, "w") as file:
        a = AttitudeFile(
            file,
            format,
            coordinate_axes=coordinate_axes,
            sequence=sequence,
        )
        a.write(time, data)
