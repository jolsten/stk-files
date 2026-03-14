from __future__ import annotations

from typing import Literal, Union

import numpy as np
from numpy.typing import NDArray

DateTimeArray = NDArray[np.datetime64]

MessageLevel = Literal["Errors", "Warnings", "Verbose"]
TimeFormat = Literal["ISO-YMD", "EpSec"]
CentralBody = Literal["Earth", "Moon"]

CoordinateAxes = Literal[
    "Fixed",
    "J2000",
    "ICRF",
    "Inertial",
    "TrueOfDate",
    "MeanOfDate",
    "TEMEOfDate",
    "MeanOfEpoch",
    "TrueOfEpoch",
    "TEMEOfEpoch",
    "AlignmentAtEpoch",
]

InterpolationMethod = Literal["Lagrange", "Hermite"]

AttitudeFormat = Literal[
    "Quaternions",
    "QuatScalarFirst",
    "EulerAngles",
    "YPRAngles",
    "DCM",
    "ECFVector",
    "ECIVector",
]

SensorFormat = Literal[
    "Quaternions",
    "QuatScalarFirst",
    "EulerAngles",
    "YPRAngles",
    "AzElAngles",
    "DCM",
    "ECFVector",
    "ECIVector",
]

EphemerisFormat = Literal[
    "TimePos",
    "TimePosVel",
    "TimePosVelAcc",
    "LLATimePos",
    "LLATimePosVel",
]

EulerSequence = Literal[121, 123, 131, 132, 212, 213, 231, 232, 312, 313, 321, 323]
YPRSequence = Literal[123, 132, 213, 231, 312, 321]
AzElSequence = Literal[323, 213]
RotationSequence = Union[EulerSequence, YPRSequence]

EPOCH_DEPENDENT_AXES: frozenset[str] = frozenset(
    {
        "MeanOfEpoch",
        "TrueOfEpoch",
        "TEMEOfEpoch",
        "AlignmentAtEpoch",
    }
)

QUATERNION_FORMATS: frozenset[str] = frozenset({"Quaternions", "QuatScalarFirst"})
ANGLE_FORMATS: frozenset[str] = frozenset({"EulerAngles", "YPRAngles", "AzElAngles"})

ATTITUDE_COLUMNS: dict[str, int] = {
    "Quaternions": 4,
    "QuatScalarFirst": 4,
    "EulerAngles": 3,
    "YPRAngles": 3,
    "DCM": 9,
    "ECFVector": 3,
    "ECIVector": 3,
}

SENSOR_COLUMNS: dict[str, int] = {
    **ATTITUDE_COLUMNS,
    "AzElAngles": 2,
}

EPHEMERIS_COLUMNS: dict[str, int] = {
    "TimePos": 3,
    "TimePosVel": 6,
    "TimePosVelAcc": 9,
    "LLATimePos": 3,
    "LLATimePosVel": 6,
}

EULER_SEQUENCES = (121, 123, 131, 132, 212, 213, 231, 232, 312, 313, 321, 323)
YPR_SEQUENCES = (123, 132, 213, 231, 312, 321)
AZEL_SEQUENCES = (323, 213)
