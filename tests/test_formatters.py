import numpy as np

from stkfiles import formatters


def test_isoymd():
    N = 100
    t0 = np.datetime64("2020-01-01T00:00:00", "ns")
    dt = np.timedelta64(1, "s")
    times = t0 + np.arange(N, dtype=">u4") * dt

    assert [str(t) for t in times.astype("datetime64[ms]")] == [
        formatters.iso_ymd(t) for t in times
    ]


def test_ep_sec():
    N = 100
    t0 = np.datetime64("2020-01-01T00:00:00", "ns")
    dt = np.timedelta64(1, "s")
    times = t0 + np.arange(N, dtype=">u4") * dt

    milliseconds = (times - t0).astype("datetime64[ms]").view("u8") / 1_000_000_000

    assert [str(f"{t:.3f}") for t in milliseconds] == [
        formatters.ep_sec(t, epoch=t0).strip() for t in times
    ]
