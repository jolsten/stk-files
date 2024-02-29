import numpy as np

from stkfiles import validators


def test_quaternion_all_pass():
    N, M = 100, 4
    time = np.datetime64("2020-01-01", "ns") + np.arange(N, dtype="u8") * 1_000_000_000
    data = np.ones((N, M), dtype="f8")
    data = data / 2  # normalize to rss = 1

    t2, d2 = validators.quaternion(time, data)

    assert time.tolist() == t2.tolist()
    assert data.tolist() == d2.tolist()


def test_quaternion_all_fail():
    N, M = 100, 4
    time = np.datetime64("2020-01-01", "ns") + np.arange(N, dtype="u8") * 1_000_000_000
    data = np.ones((N, M), dtype="f8")  # rss = 2

    t2, d2 = validators.quaternion(time, data)

    assert len(t2) == 0
    assert len(d2) == 0


def test_angles_all_pass():
    N, M = 100, 3
    time = np.datetime64("2020-01-01", "ns") + np.arange(N, dtype="u8") * 1_000_000_000
    data = np.ones((N, M), dtype="f8")

    t2, d2 = validators.angles(time, data)
    assert time.tolist() == t2.tolist()
    assert data.tolist() == d2.tolist()
