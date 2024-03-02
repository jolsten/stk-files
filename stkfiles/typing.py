import datetime
from typing import Literal, Union

import numpy as np

MessageLevel = Literal["Errors", "Warnings", "Verbose"]
TimeFormat = Literal["ISO-YMD", "EpSec"]

CentralBody = Literal["Earth", "Moon"]
CoordinateAxes = Literal[
    "Fixed", "J2000", "ICRF", "Inertial", "TrueOfDate", "MeanOfDate", "TEMEOfDate"
]
DateTime = Union[datetime.datetime, np.datetime64]
InterpolationMethod = Literal["Lagrange", "Hermite"]
EulerRotationSequence = Literal[
    121, 123, 131, 132, 212, 213, 231, 232, 312, 313, 321, 323
]
YPRRotationSequence = Literal[123, 132, 213, 231, 312, 321]
RotationSequence = Union[EulerRotationSequence, YPRRotationSequence]

AttitudeFileFormat = Literal[
    "Quaternions",
    "QuatScalarFirst",
    # "QuatAngVels",
    # "AngVels",
    "EulerAngles",
    # "EulerAngleRates",
    # "EulerAnglesAndRates",
    "YPRAngles",
    # "YPRAngleRates",
    # "YPRAnglesAndRates",
    "DCM",
    # "DCMAngVels",
    "ECFVector",
    "ECIVector",
]
