import abc
import datetime
import io
from typing import List, Literal, Optional, Union

import numpy as np

from stkfiles import formatters, validators
from stkfiles.typing import MessageLevel, TimeFormat

# from stkfiles.utils import format_time, root_sum_square

CentralBody = Literal["Earth", "Moon"]
CoordinateAxes = Literal[
    "Fixed", "J2000", "ICRF", "Inertial", "TrueOfDate", "MeanOfDate", "TEMEOfDate"
]
DateTime = datetime.datetime
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
    "EulerAnglesAndRates",
    "YPRAngles",
    # "YPRAngleRates",
    "YPRAnglesAndRates",
    "DCM",
    # "DCMAngVels",
    "ECFVector",
    "ECIVector",
]


EPOCH_TIME_FORMATS = ["EpSec"]
QUATERNION_FORMATS = ["Quaternions", "QuatScalarFirst"]
ANGLE_FORMATS = ["EulerAngles", "YPRAngles"]


class StkFileBase(abc.ABC):
    __version__: str = "stk.v.11.0"
    __name__: str = ...

    format_data: callable
    validate_data: callable

    def __init__(
        self,
        stream: io.TextIOBase,
        *,
        message_level: Optional[MessageLevel] = None,
        time_format: Optional[TimeFormat] = "ISO-YMD",
        scenario_epoch: Optional[DateTime] = None,
    ) -> None:
        self.stream = stream

        self.message_level = validators.choice(message_level, MessageLevel)
        self.time_format = validators.choice(time_format, TimeFormat)
        self.scenario_epoch = validators.time(scenario_epoch)

        if self.time_format == "ISO-YMD":
            self.format_time = formatters.iso_ymd
        elif self.time_format == "EpSec":
            self.format_time = formatters.ep_sec
        else:
            msg = f"time_format={self.time_format!r} is not supported"
            raise NotImplementedError(msg)

        # Do more complicated argument validation here
        self._validate_time_format_with_epoch()

    def _validate_time_format_with_epoch(self) -> None:
        """Ensure the ScenarioEpoch keyword is provided only when the TimeFormat requires it."""
        if self.time_format in EPOCH_TIME_FORMATS and not self.scenario_epoch:
            msg = f"time_format={self.time_format!r} requires a scenario_epoch value"
            raise ValueError(msg)

        if self.scenario_epoch and self.time_format not in EPOCH_TIME_FORMATS:
            msg = f"scenario_epoch argument is not applicable for time_format={self.time_format!r}"
            raise ValueError(msg)

    def make_header(self) -> List[str]:
        hdr = [self.__version__, f"BEGIN {self.__name__}"]
        if self.message_level:
            hdr.append(f"MessageLevel        {self.message_level}")
        if self.time_format:
            hdr.append(f"TimeFormat          {self.time_format}")
        if self.scenario_epoch:
            hdr.append(f"ScenarioEpoch       {self.format_time(self.scenario_epoch)}")
        return hdr

    def make_footer(self) -> List[str]:
        return [f"END {self.__name__}"]

    def write_header(self) -> None:
        """Write to the stream"""
        for line in self.make_header():
            print(line, file=self.stream)

    @abc.abstractmethod
    def write_data(self, time: np.ndarray, data: np.ndarray) -> None:
        ...

    def write_footer(self) -> None:
        """Write to the stream"""
        for line in self.make_footer():
            print(line, file=self.stream)


class AttitudeFile(StkFileBase):
    __name__ = "Attitude"

    def __init__(
        self,
        stream: io.TextIOBase,
        format: AttitudeFileFormat,
        *,
        message_level: Optional[MessageLevel] = None,
        time_format: Optional[TimeFormat] = "ISO-YMD",
        scenario_epoch: Optional[DateTime] = None,
        central_body: Optional[CentralBody] = None,
        coordinate_axes: CoordinateAxes = "ICRF",
        coordinate_axes_epoch: Optional[DateTime] = None,
        interpolation_method: Optional[InterpolationMethod] = None,
        interpolation_order: Optional[int] = None,
        sequence: Optional[RotationSequence] = None,
    ) -> None:
        super().__init__(
            stream,
            message_level=message_level,
            time_format=time_format,
            scenario_epoch=scenario_epoch,
        )
        self.format = validators.choice(format, AttitudeFileFormat)
        self.central_body = validators.choice(central_body, CentralBody)
        self.coordinate_axes = validators.choice(coordinate_axes, CoordinateAxes)
        self.coordinate_axes_epoch = validators.time(coordinate_axes_epoch)
        self.interpolation_method = validators.choice(
            interpolation_method, InterpolationMethod
        )
        self.interpolation_order = validators.integer(interpolation_order)
        self.sequence = validators.choice(sequence, RotationSequence)

        self._validate_coord_axes_with_epoch()

        self.validate_data = validators.none

        self.format_data = formatters.generic
        if self.format in QUATERNION_FORMATS:
            self.validate_data = validators.quaternion
            self.format_data = formatters.quaternions
        elif self.format in ANGLE_FORMATS:
            self.validate_data = validators.angles

    def _validate_coord_axes_with_epoch(self) -> None:
        epoch_required = [
            "MeanOfEpoch",
            "TrueOfEpoch",
            "TEMEOfEpoch",
            "AlignmentAtEpoch",
        ]
        if self.coordinate_axes in epoch_required and self.coordinate_axes is None:
            msg = f"coordinate_axes={self.coordinate_axes!r} requires a coordinate_axes_epoch value"
            raise ValueError(msg)

    def make_header(self) -> List[str]:
        hdr = []
        hdr.extend(super().make_header())
        if self.central_body:
            hdr.append(f"CentralBody         {self.central_body}")
        if self.coordinate_axes:
            hdr.append(f"CoordinateAxes      {self.coordinate_axes}")
        if self.coordinate_axes_epoch:
            hdr.append(
                f"CoordinateAxesEpoch {self.format_time(self.coordinate_axes_epoch)}"
            )
        if self.interpolation_method:
            hdr.append(f"InterpolationMethod {self.interpolation_method}")
        if self.interpolation_order:
            hdr.append(f"InterpolationOrder  {self.interpolation_order}")
        if self.sequence:
            hdr.append(f"Sequence {self.sequence}")

        hdr.append(f"AttitudeTime{self.format}")
        return hdr

    def write_data(self, time: np.ndarray, data: np.ndarray) -> None:
        time = np.atleast_1d(time)
        data = np.atleast_2d(data)

        time, data = self.validate_data(time, data)

        for t, row in zip(time, data):
            print(self.format_time(t), self.format_data(row), file=self.stream)
