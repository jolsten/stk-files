import abc
import datetime
import io
import typing
from typing import Any, List, Literal, Optional, Tuple, Type, Union

import numpy as np

from stkfiles.times import ISOYMD, EpSec, TimeFormatStrategy
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

# @dataclass
# class DataStrategy(abc.ABC):
#     number_format: str = "%8.6e"

#     @abc.abstractmethod
#     def validate(
#         self, times: np.ndarray, data: np.ndarray
#     ) -> Tuple[np.ndarray, np.ndarray]:
#         ...

#     @abc.abstractmethod
#     def format(self, times: np.ndarray, data: np.ndarray) -> List[str]:
#         ...


# @dataclass
# class NoStrategy(DataStrategy):
#     def validate(
#         self, times: np.ndarray, data: np.ndarray
#     ) -> Tuple[np.ndarray, np.ndarray]:
#         return times, data

#     def format(self, times: np.ndarray, data: np.ndarray) -> List[str]:
#         data = []
#         for time, row in zip(times, data):
#             row_text = " ".join([str(value) for value in row])
#             line = f"{time} {row_text}"
#             data.append(line)
#         return data


# @dataclass
# class QuaternionStrategy(DataStrategy):
#     tolerance: float = 1e-6

#     def format(self, times: np.ndarray, data: np.ndarray) -> List[str]:
#         ...

#     def validate(
#         self, times: np.ndarray, data: np.ndarray
#     ) -> Tuple[np.ndarray, np.ndarray]:
#         rss = np.sqrt(
#             data[:, 0] ** 2 + data[:, 1] ** 2 + data[:, 2] ** 2 + data[:, 3] ** 2
#         )
#         valid_indices = np.abs(1 - rss) <= self.tolerance
#         return times[valid_indices], data[valid_indices]


# attitude_strategies = {
#     "Quaternions": QuaternionStrategy(),
#     "QuatScalarFirst": QuaternionStrategy(),
# }


def validate_time(dt: Any) -> Optional[np.datetime64]:
    if dt is None:
        return None
    elif isinstance(dt, np.datetime64):
        return dt
    elif isinstance(dt, str):
        return np.datetime64(dt)
    elif isinstance(dt, datetime.datetime):
        return np.datetime64(dt.isoformat(sep="T", timespec="milliseconds"))
    msg = f"could not convert {type(dt)} to np.datetime64"
    raise TypeError(msg)


def validate_integer(value: Any) -> int:
    if value is None:
        return None
    return int(value)


def validate_choice(value: str, choice_class: Type) -> Optional[str]:
    if value is None:
        return None

    choices = {c.lower(): c for c in typing.get_args(choice_class)}
    try:
        return choices[value.lower()]
    except KeyError:
        msg = f"{value!r} was not a valid choice; valid choices: {', '.join(choices.values())}"
        raise ValueError(msg)


def no_validation(time: np.ndarray, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    time = np.atleast_1d(time)
    data = np.atleast_2d(data)
    return time, data


def validate_quaternion(
    time: np.ndarray, data: np.ndarray, tolerance: float = 1e-6
) -> Tuple[np.ndarray, np.ndarray]:
    time = np.atleast_1d(time)
    data = np.atleast_2d(data)
    rss = np.sqrt(data[:, 0] ** 2 + data[:, 1] ** 2 + data[:, 2] ** 2 + data[:, 3] ** 2)
    valid = np.abs(rss - 1) <= tolerance
    return time[valid], data[valid, :]


def validate_angles(
    time: np.ndarray,
    data: np.ndarray,
    min_angle: float = -180,
    max_angle: float = 360,
) -> Tuple[np.ndarray, np.ndarray]:
    time = np.atleast_1d(time)
    data = np.atleast_2d(data)

    for i in range(3):
        valid = min_angle <= data[i] and data[0] <= max_angle
        time = time[valid]
        data = data[valid, :]
    return time, data


def format_iso_ymd(time: Union[datetime.datetime, np.datetime64]) -> str:
    if isinstance(time, datetime.datetime):
        time = np.datetime64(time.isoformat(timespec="milliseconds"))
    return str(time)[0:23]


def format_ep_sec(
    time: Union[datetime.datetime, np.datetime64], *, epoch: np.datetime64
) -> str:
    if isinstance(time, datetime.datetime):
        time = np.datetime64(time.isoformat(timespec="milliseconds"))
    dt = (time - epoch) / np.timedelta64(1, "ns") / 1_000_000_000
    return f"{dt:15.3f}"


def format_data(row: np.ndarray) -> str:
    return f'{" ".join([f"{value:12f}" for value in row])}'


def format_quaternions(row: np.ndarray) -> str:
    return f"{row[0]:+12.9f} {row[1]:+12.9f} {row[2]:+12.9f} {row[3]:+12.9f}"


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

        self.message_level = validate_choice(message_level, MessageLevel)
        self.time_format = validate_choice(time_format, TimeFormat)
        self.scenario_epoch = validate_time(scenario_epoch)

        if self.time_format == "ISO-YMD":
            self.format_time = format_iso_ymd
        elif self.time_format == "EpSec":
            self.format_time = format_ep_sec
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
        self.format = validate_choice(format, AttitudeFileFormat)
        self.central_body = validate_choice(central_body, CentralBody)
        self.coordinate_axes = validate_choice(coordinate_axes, CoordinateAxes)
        self.coordinate_axes_epoch = validate_time(coordinate_axes_epoch)
        self.interpolation_method = validate_choice(
            interpolation_method, InterpolationMethod
        )
        self.interpolation_order = validate_integer(interpolation_order)
        self.sequence = validate_choice(sequence, RotationSequence)

        self._validate_coord_axes_with_epoch()

        self.validate_data = no_validation
        self.format_data = format_data
        if self.format in QUATERNION_FORMATS:
            self.validate_data = validate_quaternion
            self.format_data = format_quaternions
        elif self.format in ANGLE_FORMATS:
            self.validate_data = validate_angles

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
