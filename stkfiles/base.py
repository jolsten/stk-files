import abc
import datetime
import functools
import io
import typing
from dataclasses import dataclass, field
from typing import Any, List, Literal, Optional, Sequence, Tuple, Type, Union

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


@dataclass
class DataStrategy(abc.ABC):
    number_format: str = "%8.6e"

    @abc.abstractmethod
    def validate(
        self, times: np.ndarray, data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        ...

    @abc.abstractmethod
    def format(self, times: np.ndarray, data: np.ndarray) -> List[str]:
        ...


@dataclass
class NoStrategy(DataStrategy):
    def validate(
        self, times: np.ndarray, data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        return times, data

    def format(self, times: np.ndarray, data: np.ndarray) -> List[str]:
        data = []
        for time, row in zip(times, data):
            row_text = " ".join([str(value) for value in row])
            line = f"{time} {row_text}"
            data.append(line)
        return data


@dataclass
class QuaternionStrategy(DataStrategy):
    tolerance: float = 1e-6

    def format(self, times: np.ndarray, data: np.ndarray) -> List[str]:
        ...

    def validate(
        self, times: np.ndarray, data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        rss = np.sqrt(
            data[:, 0] ** 2 + data[:, 1] ** 2 + data[:, 2] ** 2 + data[:, 3] ** 2
        )
        valid_indices = np.abs(1 - rss) <= self.tolerance
        return times[valid_indices], data[valid_indices]


attitude_strategies = {
    "Quaternions": QuaternionStrategy(),
    "QuatScalarFirst": QuaternionStrategy(),
}


def validate_time(dt: Any) -> np.datetime64:
    if isinstance(dt, np.datetime64):
        return dt
    elif isinstance(dt, str):
        return np.datetime64(dt)
    elif isinstance(dt, datetime.datetime):
        return np.datetime64(dt.isoformat(sep="T", timespec="milliseconds"))
    msg = f"could not convert {type(dt)} to np.datetime64"
    raise TypeError(msg)


def choice_validator(value: str, choice_class: Type) -> str:
    choices = {c.lower(): c for c in typing.get_args(choice_class)}
    try:
        return choices[value.lower()]
    except KeyError:
        msg = f"{value!r} was not a valid choice; valid choices: {', '.join(choices.values())}"
        raise ValueError(msg)


class StkFileBase:
    def __init__(
        self,
        stream: io.TextIOBase,
        *,
        message_level: Optional[MessageLevel] = None,
        time_format: Optional[TimeFormat] = "ISO-YMD",
        scenario_epoch: Optional[DateTime] = None,
    ) -> None:
        self.stream = stream
        self.message_level = None
        self.time_format = None
        self.scenario_epoch = None

        if message_level:
            self.message_level = choice_validator(message_level, MessageLevel)
        if time_format:
            self.time_format = choice_validator(time_format, TimeFormat)
        if scenario_epoch:
            self.scenario_epoch = validate_time(scenario_epoch)

        # Do more complicated argument validation here
        self._validate_time_format_with_epoch()

    def _validate_time_format_with_epoch(self) -> None:
        """Ensure the ScenarioEpoch keyword is provided only when the TimeFormat requires it."""
        epoch_time_formats = ["EpSec"]
        if self.time_format in epoch_time_formats and not self.scenario_epoch:
            msg = f"time_format={self.time_format!r} requires a scenario_epoch value"
            raise ValueError(msg)

        if self.scenario_epoch and self.time_format not in epoch_time_formats:
            msg = f"scenario_epoch argument is not applicable for time_format={self.time_format!r}"
            raise ValueError(msg)

    def make_header(self) -> List[str]:
        hdr = []
        if self.message_level:
            hdr.append(f"MessageLevel  {self.message_level}")
        if self.time_format:
            hdr.append(f"TimeFormat    {self.time_format}")
        if self.scenario_epoch:
            hdr.append(f"ScenarioEpoch {self.scenario_epoch}")
        return hdr


# @dataclass
# class AbstractStkFile:
#     message_level: Optional[MessageLevel] = "Errors"
#     time_format: Optional[TimeFormat] = "ISO-YMD"
#     scenario_epoch: Optional[DateTime] = None

#     _header: List[str] = field(default_factory=list, repr=False)
#     time_formatter: TimeFormatStrategy = field(repr=False, init=False)

#     def __post_init__(self) -> None:
#         if self.time_format == "ISO-YMD":
#             self.time_formatter = ISOYMD()
#         elif self.time_format == "EpSec":
#             self.time_formatter = EpSec(epoch=self.scenario_epoch)
#         else:
#             msg = f"TimeFormat {self.time_format!r} is not supported"
#             raise ValueError(msg)

#     def make_header(self) -> None:
#         if self.message_level:
#             self._header.append(f"MessageLevel  {self.message_level}")
#         if self.time_format:
#             self._header.append(f"TimeFormat    {self.time_format}")
#         if self.scenario_epoch:
#             epoch = self.time_formatter.format(np.asarray(self.scenario_epoch))[0]
#             self._header.append(f"ScenarioEpoch {epoch}")


# @dataclass
# class AttitudeFile(AbstractStkFile):
#     central_body: Optional[CentralBody] = None
#     coordinate_axes: CoordinateAxes = "ICRF"
#     coordinate_axes_epoch: Optional[DateTime] = None
#     interpolation_method: Optional[InterpolationMethod] = None
#     interpolation_order: Optional[int] = None
#     sequence: Optional[RotationSequence] = None

#     format: Optional[Literal[AttitudeFileFormat]] = None
#     data_strategy: Optional[DataStrategy] = None

#     def __post_init__(self) -> None:
#         super().__post_init__()
#         if self.format is None:
#             msg = "format kwarg must be provided"
#             raise ValueError(msg)

#         if self.data_strategy is None:
#             self.data_strategy = attitude_strategies.get(self.format, NoStrategy())

#     def make_header(self) -> str:
#         super().make_header()
#         if self.central_body:
#             self._header.append(f"CentralBody         {self.central_body}")
#         if self.coordinate_axes:
#             self._header.append(f"CoordinateAxes      {self.coordinate_axes}")
#             if self.coordinate_axes in ["TrueOfDate", "MeanOfDate", "TEMEOfDate"]:
#                 if self.coordinate_axes_epoch:
#                     coord_epoch = self.time_formatter.format(
#                         np.array(self.coordinate_axes_epoch)
#                     )
#                     self._header.append(f"CoordinateAxesEpoch {coord_epoch}")
#         if self.interpolation_method:
#             self._header.append(f"InterpolationMethod {self.interpolation_method}")
#         if self.interpolation_order:
#             self._header.append(f"InterpolationOrder  {self.interpolation_order}")
