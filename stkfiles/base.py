import abc
import datetime
import io
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple, Union

import numpy as np

from stkfiles.times import ISOYMD, EpochTimeStrategy, EpSec, TimeFormatStrategy
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


@dataclass
class AbstractStkFile:
    message_level: Optional[MessageLevel] = "Errors"
    time_format: Optional[TimeFormat] = "ISO-YMD"
    scenario_epoch: Optional[DateTime] = None

    _header: List[str] = field(default_factory=list, repr=False)
    time_formatter: TimeFormatStrategy = field(repr=False, init=False)

    def __post_init__(self) -> None:
        if self.time_format == "ISO-YMD":
            self.time_formatter = ISOYMD()
        elif self.time_format == "EpSec":
            self.time_formatter = EpSec(epoch=self.scenario_epoch)
        else:
            msg = f"TimeFormat {self.time_format!r} is not supported"
            raise ValueError(msg)

    def _make_header(self) -> str:
        if self.message_level:
            self._header.append(f"MessageLevel  {self.message_level}")
        if self.time_format:
            self._header.append(f"TimeFormat    {self.time_format}")
        if self.scenario_epoch:
            epoch = self.time_formatter.format(np.asarray(self.scenario_epoch))[0]
            self._header.append(f"ScenarioEpoch {epoch}")


@dataclass
class AttitudeFile(AbstractStkFile):
    central_body: Optional[CentralBody] = None
    coordinate_axes: CoordinateAxes = "ICRF"
    coordinate_axes_epoch: Optional[DateTime] = None
    interpolation_method: Optional[InterpolationMethod] = None
    interpolation_order: Optional[int] = None
    sequence: Optional[RotationSequence] = None

    format: Optional[Literal[AttitudeFileFormat]] = None
    data_strategy: Optional[DataStrategy] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.format is None:
            msg = "format kwarg must be provided"
            raise ValueError(msg)

        if self.validator is None:
            self.validator = attitude_strategies.get(self.format, NoStrategy())

    def _make_header(self) -> str:
        super()._make_header()


# class StkDataFile(BaseModel):
#     data_keyword: ClassVar[BeginKeywords] = ...

#     version: FileVersion = Field(default="stk.v.12.0", alias=None)

#     message_level: Optional[MessageLevel] = Field(default=None, alias="MessageLevel")
#     scenario_epoch: Optional[StkDatetime] = Field(default=None, alias="ScenarioEpoch")
#     time_format: Optional[TimeFormat] = Field(default="ISO-YMD", alias="TimeFormat")
#     format_: DataFormat

#     _fh: Optional[io.TextIOBase] = PrivateAttr()

#     def make_header(self) -> List[Tuple[str, str]]:
#         header = [f"{self.version}"]

#         if self.message_level:
#             header.append(("MessageLevel", self.message_level))

#         lines = []
#         for field, attrs in self.model_fields.items():
#             value = getattr(self, field, None)
#             if value:
#                 lines.append((attrs.alias, value))

#         header.extend(self.header.to_lines())
#         header.append(f"BEGIN {self.data_keyword}")
#         return header

#     def make_trailer(self) -> List[str]:
#         trailer = [f"END {self.data_keyword}"]
#         return trailer

#     def _format_quaternions(
#         self, time: datetime.datetime, data: Iterable[float]
#     ) -> str:
#         ts = format_time(time, self.header.time_format)
#         data = [f"{value:+15.12e}" for value in data]
#         return f"""{ts} {" ".join(data)}"""

#     def _format_data(self, time: datetime.datetime, data: Iterable[float]) -> str:
#         return self._format_quaternions(time, data)

#     def _validate_data(self, time: datetime.datetime, data: Iterable[float]) -> str:
#         pass

#     def to_file(self, path: FilePath) -> None:
#         pass
#         # with open(path, "w") as file:
#         #     for line in self._make_header():
#         #         print(line, file=file)

#         #     for
