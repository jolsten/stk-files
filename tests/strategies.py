import numpy as np
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays


def rss(a: np.ndarray) -> float:  # type: ignore[type-arg]
    """Root sum of squares."""
    return float(np.sqrt(np.sum(a**2)))


def axang2quat(axis: np.ndarray, angle: float) -> np.ndarray:  # type: ignore[type-arg]
    """Convert axis-angle to quaternion (scalar-last)."""
    axis = axis / np.linalg.norm(axis)
    s = np.sin(angle / 2)
    c = np.cos(angle / 2)
    return np.array([axis[0] * s, axis[1] * s, axis[2] * s, c])


@st.composite
def unit_vectors(draw: st.DrawFn) -> np.ndarray:  # type: ignore[type-arg]
    """Generate random unit vectors."""
    v = draw(arrays(np.float64, (3,), elements=st.floats(-1, 1, allow_nan=False)))
    norm = np.linalg.norm(v)
    if norm < 1e-10:
        return np.array([1.0, 0.0, 0.0])
    return v / norm  # type: ignore[no-any-return]


@st.composite
def quaternions(draw: st.DrawFn) -> np.ndarray:  # type: ignore[type-arg]
    """Generate valid unit quaternions (scalar-last)."""
    axis = draw(unit_vectors())
    angle = draw(st.floats(0, 2 * np.pi, allow_nan=False, allow_infinity=False))
    return axang2quat(axis, angle)


@st.composite
def angles(draw: st.DrawFn, lo: float = -180.0, hi: float = 360.0) -> float:
    """Generate random angles in range."""
    return draw(st.floats(lo, hi, allow_nan=False, allow_infinity=False))


@st.composite
def datetime64s(
    draw: st.DrawFn,
    start: str = "2000-01-01",
    end: str = "2030-01-01",
) -> np.datetime64:
    """Generate random datetime64[ms] values."""
    s = np.datetime64(start, "ms")
    e = np.datetime64(end, "ms")
    delta = int((e - s) / np.timedelta64(1, "ms"))
    offset = draw(st.integers(0, delta))
    return s + np.timedelta64(offset, "ms")


@st.composite
def sorted_datetime64_arrays(
    draw: st.DrawFn,
    min_size: int = 3,
    max_size: int = 50,
    start: str = "2000-01-01",
    end: str = "2030-01-01",
) -> np.ndarray:  # type: ignore[type-arg]
    """Generate sorted arrays of unique datetime64[ms] values."""
    n = draw(st.integers(min_size, max_size))
    times = sorted(set(draw(st.lists(datetime64s(start, end), min_size=n, max_size=n * 2))))
    if len(times) < min_size:
        base = np.datetime64(start, "ms")
        times = [base + np.timedelta64(i * 1000, "ms") for i in range(min_size)]
    return np.array(times[:max_size], dtype="datetime64[ms]")
