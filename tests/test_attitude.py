import datetime
import io

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from stk_files.files import AttitudeFile

from . import strategies as cst


def make_times(data: np.ndarray, start: datetime.datetime) -> np.ndarray:
    return (
        np.datetime64(start.isoformat(), "ns")
        + np.arange(data.shape[0], dtype="u8") * 1_000_000_000
    )


@given(
    st.datetimes(min_value=cst.MIN_DATETIME, max_value=cst.MAX_DATETIME),
    st.lists(cst.quaternions(), min_size=10, max_size=100),
)
def test_quaternions(start, data):
    data = np.array(data, dtype=">f4")
    time = make_times(data, start)
    stream = io.StringIO()
    a = AttitudeFile(stream, format="Quaternions", coordinate_axes="ICRF")
    a.write_complete(time, data)
    assert stream


@given(
    st.datetimes(min_value=cst.MIN_DATETIME, max_value=cst.MAX_DATETIME),
    st.lists(
        st.lists(st.floats(min_value=-180, max_value=180), min_size=3, max_size=3),
        min_size=10,
        max_size=100,
    ),
)
def test_eulerangles(start, data):
    sequence = 123
    data = np.array(data, dtype=">f4")
    time = make_times(data, start)
    stream = io.StringIO()
    a = AttitudeFile(
        stream, format="EulerAngles", coordinate_axes="VVLH", sequence=sequence
    )
    a.write_complete(time, data)
    assert stream


def test_sequence_missing():
    sequence = None
    stream = io.StringIO()
    with pytest.raises(ValueError):
        stream = io.StringIO()
        a = AttitudeFile(
            stream, format="EulerAngles", coordinate_axes="VVLH", sequence=sequence
        )
