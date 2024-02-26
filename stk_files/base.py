import abc
import datetime
import io
from dataclasses import dataclass
from typing import Any, ClassVar, Iterable, List, Literal, Optional, Tuple, Union

import numpy as np

from stk_files.typing import MessageLevel, TimeFormat
from stk_files.utils import format_time, root_sum_square


@dataclass
class AbstractStkFile:
    message_level: Optional[MessageLevel] = "Errors"
    time_format: Optional[TimeFormat] = "ISO-YMD"

    def make_header(self) -> str:
        buffer = io.StringIO()
        if self.message_level:
            print("MessageLevel", self.message_level, file=buffer)
        if self.time_format:
            print("TimeFormat  ", self.time_format, file=buffer)
        return buffer.getvalue()


CentralBody = Literal["Earth", "Moon"]
CoordinateAxes = Literal["Fixed", "J2000", "ICRF", "Inertial", "TrueOfDate", "MeanOfDate", "TEMEOfDate"]
DateTime = datetime.datetime
InterpolationMethod = Literal["Lagrange", "Hermite"]
EulerRotationSequence = Literal[121, 123, 131, 132, 212, 213, 231, 232, 312, 313, 321, 323]
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
class AbstractValidator(abc.ABC):
    number_format: str = "%8.6e"

    @abc.abstractmethod
    def validate(self, times: np.ndarray, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        ...

    def write_to_buffer(self, buffer: io.TextIOBase, times: np.ndarray, data: np.ndarray) -> None:
        for time, row in zip(times, data):
            values = [f"{value:{self.number_format}}" for value in row]
            print(time, *values, file=buffer)


@dataclass
class NoValidation(AbstractValidator):
    def validate(self, times: np.ndarray, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        return times, data


@dataclass
class QuaternionValidation(AbstractValidator):
    tolerance: float = 1e-6

    def validate(self, times: np.ndarray, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        rss = np.sqrt(data[:, 0] ** 2 + data[:, 1] ** 2 + data[:, 2] ** 2 + data[:, 3] ** 2)
        valid = np.abs(1 - rss)
        return abs(1 - root_sum_square(data)) <= self.tolerance


attitude_strategies = {
    "Quaternions": QuaternionStrategy,
    "QuatScalarFirst": QuaternionStrategy,
}


class AttitudeFile(AbstractStkFile):
    scenario_epoch: Optional[DateTime] = None
    central_body: Optional[CentralBody] = None
    coordinate_axes: CoordinateAxes = "ICRF"
    coordinate_axes_epoch: Optional[DateTime] = None
    interpolation_method: Optional[InterpolationMethod] = None
    interpolation_order: Optional[int] = None
    sequence: Optional[RotationSequence] = None

    format: Literal[AttitudeFileFormat]

    def __post_init__(self) -> None:
        self.strategy = attitude_strategies.get(self.format, AttitudeDataStrategy)


class StkDataFile(BaseModel):
    data_keyword: ClassVar[BeginKeywords] = ...

    version: FileVersion = Field(default="stk.v.12.0", alias=None)

    message_level: Optional[MessageLevel] = Field(default=None, alias="MessageLevel")
    scenario_epoch: Optional[StkDatetime] = Field(default=None, alias="ScenarioEpoch")
    time_format: Optional[TimeFormat] = Field(default="ISO-YMD", alias="TimeFormat")
    format_: DataFormat

    _fh: Optional[io.TextIOBase] = PrivateAttr()

    def make_header(self) -> List[Tuple[str, str]]:
        header = [f"{self.version}"]

        if self.message_level:
            header.append(("MessageLevel", self.message_level))

        lines = []
        for field, attrs in self.model_fields.items():
            value = getattr(self, field, None)
            if value:
                lines.append((attrs.alias, value))

        header.extend(self.header.to_lines())
        header.append(f"BEGIN {self.data_keyword}")
        return header

    def make_trailer(self) -> List[str]:
        trailer = [f"END {self.data_keyword}"]
        return trailer

    def _format_quaternions(self, time: datetime.datetime, data: Iterable[float]) -> str:
        ts = format_time(time, self.header.time_format)
        data = [f"{value:+15.12e}" for value in data]
        return f"""{ts} {" ".join(data)}"""

    def _format_data(self, time: datetime.datetime, data: Iterable[float]) -> str:
        return self._format_quaternions(time, data)

    def _validate_data(self, time: datetime.datetime, data: Iterable[float]) -> str:
        pass

    def to_file(self, path: FilePath) -> None:
        pass
        # with open(path, "w") as file:
        #     for line in self._make_header():
        #         print(line, file=file)

        #     for
