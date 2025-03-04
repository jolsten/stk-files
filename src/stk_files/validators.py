import datetime
import typing
from typing import Any, Optional, Tuple, Type

import numpy as np


def time(dt: Any) -> Optional[np.datetime64]:
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


def integer(value: Any) -> int:
    if value is None:
        return None
    return int(value)


def choice(value: str, choice_class: Type) -> Optional[str]:
    if value is None:
        return None

    choices = {str(c).lower(): c for c in typing.get_args(choice_class)}
    try:
        return choices[str(value).lower()]
    except KeyError:
        msg = f"{value!r} was not a valid choice; valid choices: {', '.join(choices.values())}"
        raise ValueError(msg)


def none(time: np.ndarray, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    time = np.atleast_1d(time)
    data = np.atleast_2d(data)
    return time, data


def quaternion(
    time: np.ndarray, data: np.ndarray, tolerance: float = 1e-6
) -> Tuple[np.ndarray, np.ndarray]:
    time = np.atleast_1d(time)
    data = np.atleast_2d(data)
    rss = np.sqrt(data[:, 0] ** 2 + data[:, 1] ** 2 + data[:, 2] ** 2 + data[:, 3] ** 2)
    valid = np.abs(rss - 1) <= tolerance
    return time[valid], data[valid, :]


def angles(
    time: np.ndarray,
    data: np.ndarray,
    min_angle: float = -180,
    max_angle: float = 360,
) -> Tuple[np.ndarray, np.ndarray]:
    time = np.atleast_1d(time)
    data = np.atleast_2d(data)

    for i in range(3):
        valid = np.logical_and(min_angle <= data[:, i], data[:, i] <= max_angle)
        time = time[valid]
        data = data[valid, :]
    return time, data
