import abc
import datetime
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple, Union

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

    def make_header(self) -> None:
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

        if self.data_strategy is None:
            self.data_strategy = attitude_strategies.get(self.format, NoStrategy())

    def make_header(self) -> str:
        super().make_header()
        if self.central_body:
            self._header.append(f"CentralBody         {self.central_body}")
        if self.coordinate_axes:
            self._header.append(f"CoordinateAxes      {self.coordinate_axes}")
            if self.coordinate_axes in ["TrueOfDate", "MeanOfDate", "TEMEOfDate"]:
                if self.coordinate_axes_epoch:
                    coord_epoch = self.time_formatter.format(
                        np.array(self.coordinate_axes_epoch)
                    )
                    self._header.append(f"CoordinateAxesEpoch {coord_epoch}")
        if self.interpolation_method:
            self._header.append(f"InterpolationMethod {self.interpolation_method}")
        if self.interpolation_order:
            self._header.append(f"InterpolationOrder  {self.interpolation_order}")
