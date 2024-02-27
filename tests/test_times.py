import numpy as np

from stkfiles.times import ISOYMD, EpSec


def test_isoymd():
    t0 = np.datetime64("2020-01-01T00:00:00", "ns")
    dt = np.timedelta64(1, "s")
    times = t0 + np.arange(2, dtype=">u4") * dt

    strategy = ISOYMD()
    out = strategy.format(times)
    assert [str(t) for t in times] == list(out)


def test_ep_sec():
    t0 = np.datetime64("2020-01-01T00:00:00", "ns")
    dt = np.timedelta64(1, "s")
    times = t0 + np.arange(2, dtype=">u4") * dt
    td = (times - t0).view("uint64") / 1_000_000_000

    strategy = EpSec(epoch=t0)
    out = strategy.format(times)
    assert [f"{t:15.3f}" for t in td] == list(out)
