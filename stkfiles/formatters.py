import datetime
from typing import Union

import numpy as np


def iso_ymd(time: Union[datetime.datetime, np.datetime64]) -> str:
    if isinstance(time, datetime.datetime):
        time = np.datetime64(time.isoformat(timespec="milliseconds"))
    return str(time)[0:23]


def ep_sec(
    time: Union[datetime.datetime, np.datetime64], *, epoch: np.datetime64
) -> str:
    if isinstance(time, datetime.datetime):
        time = np.datetime64(time.isoformat(timespec="milliseconds"))
    dt = (time - epoch) / np.timedelta64(1, "ns") / 1_000_000_000
    return f"{dt:15.3f}"


def generic(row: np.ndarray) -> str:
    return f'{" ".join([f"{value:12f}" for value in row])}'


def quaternions(row: np.ndarray) -> str:
    return f"{row[0]:+12.9f} {row[1]:+12.9f} {row[2]:+12.9f} {row[3]:+12.9f}"
