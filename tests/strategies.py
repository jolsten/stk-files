import datetime
import math
from typing import List, Sequence, Tuple

from hypothesis import strategies as st

MIN_DATETIME = datetime.datetime(2000, 1, 1)
MAX_DATETIME = datetime.datetime(2030, 1, 1)


@st.composite
def intervals(
    draw,
    min_start: datetime.datetime = MIN_DATETIME,
    max_start: datetime.datetime = MAX_DATETIME,
    min_dur: int = 60,
    max_dur: int = 300,
) -> Tuple[datetime.datetime, datetime.datetime]:
    start = draw(st.datetimes(min_value=min_start, max_value=max_start))
    dur = draw(st.floats(min_value=min_dur, max_value=max_dur))
    stop = start + datetime.timedelta(seconds=dur)
    return start, stop


@st.composite
def interval_lists(
    draw,
    min_size: int = 1,
    max_size: int = 100,
    min_start: datetime.datetime = MIN_DATETIME,
    max_start: datetime.datetime = MAX_DATETIME,
    min_dur: int = 60,
    max_dur: int = 300,
) -> List[Tuple[datetime.datetime, datetime.datetime]]:
    interval_list = draw(
        st.lists(
            intervals(
                min_start=min_start,
                max_start=max_start,
                min_dur=min_dur,
                max_dur=max_dur,
            ),
            min_size=min_size,
            max_size=max_size,
        )
    )
    return interval_list


def axang2quat(
    axis: Tuple[float, float, float], theta_deg: float
) -> Tuple[float, float, float, float]:
    theta = theta_deg * math.pi / 180
    q0 = math.cos(theta / 2)
    q1 = math.sin(theta / 2) * axis[0]
    q2 = math.sin(theta / 2) * axis[1]
    q3 = math.sin(theta / 2) * axis[2]
    return q0, q1, q2, q3


def rss(parts: Sequence[float]) -> float:
    return math.sqrt(sum([x**2 for x in parts]))


@st.composite
def angles(draw, min_value: float = 0.0, max_value: float = 360.0) -> float:
    return draw(st.floats(min_value=min_value, max_value=max_value))


@st.composite
def unit_vectors(draw) -> Tuple[float, float, float]:
    axis = st.tuples(st.floats(min_value=-1, max_value=1))
    rss_ = rss(axis)
    axis = [x / rss_ for x in axis]
    return axis


@st.composite
def quaternions(draw) -> Tuple[float, float, float, float]:
    axis = draw(unit_vectors())
    angle = draw(angles())
    q0, q1, q2, q3 = axang2quat(axis, angle)
    return q1, q2, q3, q0
