from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from stk_files._types import (
    ANGLE_FORMATS,
    AZEL_SEQUENCES,
    EPHEMERIS_COLUMNS,
    EPOCH_DEPENDENT_AXES,
    EULER_SEQUENCES,
    QUATERNION_FORMATS,
    YPR_SEQUENCES,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from stk_files._types import AzElSequence, EulerSequence, YPRSequence

DCM_FORMATS: frozenset[str] = frozenset({"DCM"})
VECTOR_FORMATS: frozenset[str] = frozenset({"ECFVector", "ECIVector"})


# ---------------------------------------------------------------------------
# Shape validation
# ---------------------------------------------------------------------------


def validate_shape(
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    expected_cols: int,
) -> None:
    """Raise ValueError if shapes are incompatible."""
    times = np.atleast_1d(times)
    data = np.atleast_2d(data)
    if times.shape[0] != data.shape[0]:
        raise ValueError(f"times has {times.shape[0]} rows but data has {data.shape[0]} rows")
    if data.shape[1] != expected_cols:
        raise ValueError(f"expected {expected_cols} data columns but got {data.shape[1]}")


# ---------------------------------------------------------------------------
# Sorting and time validation
# ---------------------------------------------------------------------------


def sort_by_time(
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
) -> tuple[NDArray[np.datetime64], NDArray[np.floating]]:
    """Sort both arrays by ascending time. Returns (times, data)."""
    order = np.argsort(times)
    return times[order], data[order]


def validate_times(times: NDArray[np.datetime64]) -> None:
    """Raise ValueError if times contain NaT or duplicates."""
    if np.any(np.isnat(times)):
        bad = np.where(np.isnat(times))[0]
        raise ValueError(f"NaT values at indices: {bad.tolist()}")
    if times.shape[0] > 1:
        diffs = np.diff(times)
        zero = np.timedelta64(0, "ms")
        dupes = np.where(diffs == zero)[0]
        if dupes.size > 0:
            raise ValueError(f"duplicate timestamps at indices: {(dupes + 1).tolist()}")


# ---------------------------------------------------------------------------
# Finite validation (NaN / Inf)
# ---------------------------------------------------------------------------


def validate_finite(
    data: NDArray[np.floating],
) -> None:
    """Raise ValueError if any value is NaN or Inf."""
    if not np.all(np.isfinite(data)):
        bad_rows = np.where(~np.all(np.isfinite(data), axis=1))[0]
        raise ValueError(f"non-finite values at rows: {bad_rows.tolist()}")


def filter_finite(
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
) -> tuple[NDArray[np.datetime64], NDArray[np.floating]]:
    """Drop rows containing NaN or Inf. Returns (times, data)."""
    mask = np.all(np.isfinite(data), axis=1)
    return times[mask], data[mask]


# ---------------------------------------------------------------------------
# Quaternion / angle validation (existing)
# ---------------------------------------------------------------------------


def validate_quaternions(
    data: NDArray[np.floating],
    tolerance: float = 1e-6,
) -> None:
    """Raise ValueError if any quaternion row is not unit-norm."""
    norms = np.sqrt(np.sum(data**2, axis=1))
    bad = np.abs(norms - 1.0) > tolerance
    if np.any(bad):
        bad_indices = np.where(bad)[0]
        raise ValueError(f"non-unit quaternions at rows: {bad_indices.tolist()}")


def filter_quaternions(
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    tolerance: float = 1e-6,
) -> tuple[NDArray[np.datetime64], NDArray[np.floating]]:
    """Drop rows where quaternion norm != 1. Returns (times, data)."""
    norms = np.sqrt(np.sum(data**2, axis=1))
    mask = np.abs(norms - 1.0) <= tolerance
    return times[mask], data[mask]


def validate_angles(
    data: NDArray[np.floating],
    lo: float = -180.0,
    hi: float = 360.0,
) -> None:
    """Raise ValueError if any angle is out of range."""
    bad = (data < lo) | (data > hi)
    if np.any(bad):
        bad_rows = np.where(np.any(bad, axis=1))[0]
        raise ValueError(f"angles out of range [{lo}, {hi}] at rows: {bad_rows.tolist()}")


def filter_angles(
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    lo: float = -180.0,
    hi: float = 360.0,
) -> tuple[NDArray[np.datetime64], NDArray[np.floating]]:
    """Drop rows where any angle is out of range. Returns (times, data)."""
    valid = np.all((data >= lo) & (data <= hi), axis=1)
    return times[valid], data[valid]


# ---------------------------------------------------------------------------
# Sequence / epoch validation (existing)
# ---------------------------------------------------------------------------


def validate_sequence(
    fmt: str,
    sequence: EulerSequence | YPRSequence | AzElSequence | None,
) -> None:
    """Raise ValueError if format requires a sequence and none given or invalid."""
    if fmt not in ANGLE_FORMATS:
        return
    if sequence is None:
        raise ValueError(f"format={fmt!r} requires a sequence value")
    if fmt == "EulerAngles" and sequence not in EULER_SEQUENCES:
        raise ValueError(
            f"sequence={sequence} not valid for format={fmt!r}; valid: {EULER_SEQUENCES}"
        )
    if fmt == "YPRAngles" and sequence not in YPR_SEQUENCES:
        raise ValueError(
            f"sequence={sequence} not valid for format={fmt!r}; valid: {YPR_SEQUENCES}"
        )
    if fmt == "AzElAngles" and sequence not in AZEL_SEQUENCES:
        raise ValueError(
            f"sequence={sequence} not valid for format={fmt!r}; valid: {AZEL_SEQUENCES}"
        )


def validate_epoch_axes(
    axes: str,
    axes_epoch: np.datetime64 | None,
) -> None:
    """Raise ValueError if epoch-dependent axes lacks epoch."""
    if axes in EPOCH_DEPENDENT_AXES and axes_epoch is None:
        raise ValueError(f"coordinate_axes={axes!r} requires a coordinate_axes_epoch value")


# ---------------------------------------------------------------------------
# Rotation conversions (for unified rate checking)
# ---------------------------------------------------------------------------


def _euler_to_quaternions(
    data: NDArray[np.floating],
    sequence: int,
) -> NDArray[np.floating]:
    """Convert Euler/YPR/AzEl angle rows (degrees) to scalar-last quaternions."""
    rad = np.deg2rad(data)
    axes = [int(d) - 1 for d in str(sequence)]  # e.g. 321 -> [2, 1, 0]
    result = np.zeros((data.shape[0], 4), dtype=np.float64)
    for i in range(data.shape[0]):
        q = np.array([0.0, 0.0, 0.0, 1.0])
        for j, ax in enumerate(axes):
            half = rad[i, j] / 2.0
            qi = np.array([0.0, 0.0, 0.0, np.cos(half)])
            qi[ax] = np.sin(half)
            q = _quat_multiply(q, qi)
        result[i] = q
    return result


def _dcm_to_quaternions(
    data: NDArray[np.floating],
) -> NDArray[np.floating]:
    """Convert 9-column DCM rows to scalar-last quaternions (Shepperd's method)."""
    n = data.shape[0]
    result = np.zeros((n, 4), dtype=np.float64)
    for i in range(n):
        m = data[i].reshape(3, 3)
        tr = np.trace(m)
        vals = np.array([tr, m[0, 0], m[1, 1], m[2, 2]])
        k = np.argmax(vals)
        if k == 0:
            s = 2.0 * np.sqrt(1.0 + tr)
            result[i] = [
                (m[2, 1] - m[1, 2]) / s,
                (m[0, 2] - m[2, 0]) / s,
                (m[1, 0] - m[0, 1]) / s,
                s / 4.0,
            ]
        elif k == 1:
            s = 2.0 * np.sqrt(1.0 + 2 * m[0, 0] - tr)
            result[i] = [
                s / 4.0,
                (m[0, 1] + m[1, 0]) / s,
                (m[0, 2] + m[2, 0]) / s,
                (m[2, 1] - m[1, 2]) / s,
            ]
        elif k == 2:
            s = 2.0 * np.sqrt(1.0 + 2 * m[1, 1] - tr)
            result[i] = [
                (m[0, 1] + m[1, 0]) / s,
                s / 4.0,
                (m[1, 2] + m[2, 1]) / s,
                (m[0, 2] - m[2, 0]) / s,
            ]
        else:
            s = 2.0 * np.sqrt(1.0 + 2 * m[2, 2] - tr)
            result[i] = [
                (m[0, 2] + m[2, 0]) / s,
                (m[1, 2] + m[2, 1]) / s,
                s / 4.0,
                (m[1, 0] - m[0, 1]) / s,
            ]
    return result


def _quat_multiply(q1: NDArray, q2: NDArray) -> NDArray:
    """Multiply two scalar-last quaternions."""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array(
        [
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        ]
    )


def _to_scalar_last_quaternions(
    fmt: str,
    data: NDArray[np.floating],
    sequence: EulerSequence | YPRSequence | AzElSequence | None = None,
) -> NDArray[np.floating]:
    """Convert any attitude/sensor data to scalar-last quaternions."""
    if fmt == "Quaternions":
        return data
    if fmt == "QuatScalarFirst":
        return data[:, [1, 2, 3, 0]]
    if fmt in ANGLE_FORMATS:
        if sequence is None:
            raise ValueError(f"format={fmt!r} requires a sequence value")
        return _euler_to_quaternions(data, sequence)
    if fmt == "DCM":
        return _dcm_to_quaternions(data)
    raise ValueError(f"cannot convert format {fmt!r} to quaternions")


# ---------------------------------------------------------------------------
# Rate validation
# ---------------------------------------------------------------------------


def _compute_rotation_rates(
    times: NDArray[np.datetime64],
    quats: NDArray[np.floating],
) -> NDArray[np.floating]:
    """Compute angular rate (rad/s) between consecutive quaternion rows."""
    dt = np.diff(times).astype("timedelta64[us]").astype(np.float64) / 1e6
    dots = np.abs(np.sum(quats[:-1] * quats[1:], axis=1))
    dots = np.clip(dots, 0.0, 1.0)
    angles = 2.0 * np.arccos(dots)
    # Avoid division by zero for simultaneous timestamps
    dt_safe = np.where(dt > 0, dt, np.inf)
    return angles / dt_safe


def _compute_vector_rates(
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
) -> NDArray[np.floating]:
    """Compute angular rate (rad/s) between consecutive direction vectors."""
    dt = np.diff(times).astype("timedelta64[us]").astype(np.float64) / 1e6
    norms1 = np.sqrt(np.sum(data[:-1] ** 2, axis=1))
    norms2 = np.sqrt(np.sum(data[1:] ** 2, axis=1))
    dots = np.sum(data[:-1] * data[1:], axis=1) / (norms1 * norms2)
    dots = np.clip(dots, -1.0, 1.0)
    angles = np.arccos(dots)
    dt_safe = np.where(dt > 0, dt, np.inf)
    return angles / dt_safe


def _compute_position_rates(
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    fmt: str,
) -> NDArray[np.floating]:
    """Compute position change rate (km/s) between consecutive rows."""
    dt = np.diff(times).astype("timedelta64[us]").astype(np.float64) / 1e6
    # Use only position columns (first 3)
    pos = data[:, :3]
    diffs = np.sqrt(np.sum((pos[1:] - pos[:-1]) ** 2, axis=1))
    dt_safe = np.where(dt > 0, dt, np.inf)
    return diffs / dt_safe


def _compute_rates(
    fmt: str,
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    sequence: EulerSequence | YPRSequence | AzElSequence | None = None,
) -> NDArray[np.floating]:
    """Compute rate of change between consecutive rows for any format."""
    if fmt in EPHEMERIS_COLUMNS:
        return _compute_position_rates(times, data, fmt)
    if fmt in VECTOR_FORMATS:
        return _compute_vector_rates(times, data)
    # All other attitude/sensor formats: convert to quaternions
    quats = _to_scalar_last_quaternions(fmt, data, sequence)
    return _compute_rotation_rates(times, quats)


def validate_rate(
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    max_rate: float,
    fmt: str,
    sequence: EulerSequence | YPRSequence | AzElSequence | None = None,
) -> None:
    """Raise ValueError if rate between consecutive rows exceeds max_rate."""
    if data.shape[0] < 2:
        return
    rates = _compute_rates(fmt, times, data, sequence)
    bad = np.where(rates > max_rate)[0]
    if bad.size > 0:
        raise ValueError(
            f"rate exceeds {max_rate} at transitions: {[(int(i), int(i + 1)) for i in bad]}"
        )


def filter_rate(
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    max_rate: float,
    fmt: str,
    sequence: EulerSequence | YPRSequence | AzElSequence | None = None,
) -> tuple[NDArray[np.datetime64], NDArray[np.floating]]:
    """Drop the second point of each transition exceeding max_rate (single pass)."""
    if data.shape[0] < 2:
        return times, data
    rates = _compute_rates(fmt, times, data, sequence)
    bad_second = np.where(rates > max_rate)[0] + 1
    mask = np.ones(data.shape[0], dtype=bool)
    mask[bad_second] = False
    return times[mask], data[mask]


# ---------------------------------------------------------------------------
# Interval validation
# ---------------------------------------------------------------------------


def validate_intervals(
    intervals: Sequence[Sequence[np.datetime64]],
) -> None:
    """Raise ValueError if any interval has NaT or start >= end."""
    for i, parts in enumerate(intervals):
        start, end = parts[0], parts[1]
        if np.isnat(start) or np.isnat(end):
            raise ValueError(f"NaT in interval at index {i}")
        if start >= end:
            raise ValueError(f"interval start >= end at index {i}: {start} >= {end}")


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------


def _finite_mask(data: NDArray[np.floating]) -> NDArray[np.bool_]:
    """Boolean mask: True where all columns are finite."""
    return np.all(np.isfinite(data), axis=1)


def _quaternion_mask(
    data: NDArray[np.floating],
    tolerance: float = 1e-6,
) -> NDArray[np.bool_]:
    """Boolean mask: True where quaternion norm is within tolerance of 1."""
    norms = np.sqrt(np.sum(data**2, axis=1))
    return np.abs(norms - 1.0) <= tolerance


def _angle_mask(
    data: NDArray[np.floating],
    lo: float = -180.0,
    hi: float = 360.0,
) -> NDArray[np.bool_]:
    """Boolean mask: True where all angles are in range."""
    return np.all((data >= lo) & (data <= hi), axis=1)


def validate_data(
    fmt: str,
    times: NDArray[np.datetime64],
    data: NDArray[np.floating],
    strict: bool = False,
    tolerance: float = 1e-6,
    max_rate: float | None = None,
    sequence: EulerSequence | YPRSequence | AzElSequence | None = None,
) -> tuple[NDArray[np.datetime64], NDArray[np.floating]]:
    """Validate or filter data based on format. Returns (times, data)."""
    # Rate checking is not supported for AzElAngles (2 columns cannot be
    # converted to quaternions without a third angle).
    _can_rate_check = fmt != "AzElAngles"

    if strict:
        validate_finite(data)
        if fmt in QUATERNION_FORMATS:
            validate_quaternions(data, tolerance)
        elif fmt in ANGLE_FORMATS:
            validate_angles(data)
        if max_rate is not None and _can_rate_check:
            validate_rate(times, data, max_rate, fmt, sequence)
    else:
        # Build combined mask for passes 1+2 (single array copy)
        mask = _finite_mask(data)
        if fmt in QUATERNION_FORMATS:
            mask &= _quaternion_mask(data, tolerance)
        elif fmt in ANGLE_FORMATS:
            mask &= _angle_mask(data)
        times, data = times[mask], data[mask]

        # Pass 3: rate filter (must be sequential — depends on neighbor rows)
        if max_rate is not None and _can_rate_check:
            times, data = filter_rate(times, data, max_rate, fmt, sequence)

    return times, data
