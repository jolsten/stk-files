import abc
from dataclasses import dataclass

import numpy as np


@dataclass
class TimeFormatStrategy(abc.ABC):
    @abc.abstractmethod
    def format(self, times: np.ndarray) -> np.ndarray:
        """np.ndarray[datetime64] -> np.ndarray[string]"""


@dataclass
class ISOYMD(TimeFormatStrategy):
    time_unit: str = "ns"

    def format(self, times: np.ndarray) -> np.ndarray:
        return np.datetime_as_string(times, unit=self.time_unit)


@dataclass
class EpochTimeStrategy(TimeFormatStrategy):
    epoch: np.datetime64

    def _epoch_seconds(self, times: np.ndarray) -> np.ndarray:
        delta = times - self.epoch
        epoch_sec = (delta / np.timedelta64(1, "ns")) / 1e9
        return epoch_sec

@dataclass
class EpSec(EpochTimeStrategy):
    number_format: str = "15.3f"

    def format(self, times: np.ndarray) -> np.ndarray:
        epoch_sec = self._epoch_seconds(times)
        return np.array([f"{delta:{self.number_format}}" for delta in epoch_sec])
