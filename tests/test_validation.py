import numpy as np
import pytest
from hypothesis import given, settings

from stk_files._validation import (
    filter_angles,
    filter_finite,
    filter_quaternions,
    filter_rate,
    sort_by_time,
    validate_angles,
    validate_data,
    validate_epoch_axes,
    validate_finite,
    validate_intervals,
    validate_quaternions,
    validate_rate,
    validate_sequence,
    validate_shape,
    validate_times,
)
from tests.strategies import quaternions


class TestValidateShape:
    def test_matching_shapes(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        validate_shape(times, data, 3)

    def test_row_mismatch(self) -> None:
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        with pytest.raises(ValueError, match="rows"):
            validate_shape(times, data, 3)

    def test_col_mismatch(self) -> None:
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[1.0, 2.0]])
        with pytest.raises(ValueError, match="columns"):
            validate_shape(times, data, 3)


class TestValidateQuaternions:
    def test_valid(self) -> None:
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.5, 0.5, 0.5, 0.5]])
        validate_quaternions(data)

    def test_invalid_raises(self) -> None:
        data = np.array([[1.0, 1.0, 1.0, 1.0]])  # norm = 2
        with pytest.raises(ValueError, match="non-unit"):
            validate_quaternions(data)

    @given(q=quaternions())
    @settings(max_examples=50)
    def test_hypothesis_valid(self, q: np.ndarray) -> None:  # type: ignore[type-arg]
        data = q.reshape(1, 4)
        validate_quaternions(data)


class TestFilterQuaternions:
    def test_filters_invalid(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02", "2020-01-03"], dtype="datetime64[ms]")
        data = np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [1.0, 1.0, 1.0, 1.0],  # invalid
                [0.5, 0.5, 0.5, 0.5],
            ]
        )
        ft, fd = filter_quaternions(times, data)
        assert ft.shape[0] == 2
        assert fd.shape[0] == 2

    def test_all_valid(self) -> None:
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[0.0, 0.0, 0.0, 1.0]])
        ft, _fd = filter_quaternions(times, data)
        assert ft.shape[0] == 1


class TestValidateAngles:
    def test_valid(self) -> None:
        data = np.array([[0.0, 90.0, 180.0]])
        validate_angles(data)

    def test_invalid_raises(self) -> None:
        data = np.array([[0.0, 400.0, 0.0]])
        with pytest.raises(ValueError, match="out of range"):
            validate_angles(data)


class TestFilterAngles:
    def test_filters_invalid(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[0.0, 90.0, 180.0], [0.0, 400.0, 0.0]])
        ft, _fd = filter_angles(times, data)
        assert ft.shape[0] == 1


class TestValidateSequence:
    def test_euler_requires_sequence(self) -> None:
        with pytest.raises(ValueError, match="requires a sequence"):
            validate_sequence("EulerAngles", None)

    def test_euler_invalid_sequence(self) -> None:
        with pytest.raises(ValueError, match="not valid"):
            validate_sequence("EulerAngles", 999)

    def test_euler_valid(self) -> None:
        validate_sequence("EulerAngles", 321)

    def test_ypr_valid(self) -> None:
        validate_sequence("YPRAngles", 321)

    def test_ypr_invalid(self) -> None:
        with pytest.raises(ValueError, match="not valid"):
            validate_sequence("YPRAngles", 121)

    def test_quaternions_no_sequence_needed(self) -> None:
        validate_sequence("Quaternions", None)


class TestValidateEpochAxes:
    def test_epoch_axes_without_epoch(self) -> None:
        with pytest.raises(ValueError, match="requires"):
            validate_epoch_axes("MeanOfEpoch", None)

    def test_epoch_axes_with_epoch(self) -> None:
        validate_epoch_axes("MeanOfEpoch", np.datetime64("2020-01-01"))

    def test_standard_axes_no_epoch(self) -> None:
        validate_epoch_axes("ICRF", None)


# ---------------------------------------------------------------------------
# New: sort_by_time
# ---------------------------------------------------------------------------


class TestSortByTime:
    def test_already_sorted(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02", "2020-01-03"], dtype="datetime64[ms]")
        data = np.array([[1.0], [2.0], [3.0]])
        ft, fd = sort_by_time(times, data)
        np.testing.assert_array_equal(ft, times)
        np.testing.assert_array_equal(fd, data)

    def test_unsorted(self) -> None:
        times = np.array(["2020-01-03", "2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[3.0], [1.0], [2.0]])
        ft, fd = sort_by_time(times, data)
        expected_times = np.array(
            ["2020-01-01", "2020-01-02", "2020-01-03"], dtype="datetime64[ms]"
        )
        np.testing.assert_array_equal(ft, expected_times)
        np.testing.assert_array_equal(fd, np.array([[1.0], [2.0], [3.0]]))

    def test_single_row(self) -> None:
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[1.0, 2.0]])
        ft, _fd = sort_by_time(times, data)
        assert ft.shape[0] == 1


# ---------------------------------------------------------------------------
# New: validate_times
# ---------------------------------------------------------------------------


class TestValidateTimes:
    def test_valid(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02", "2020-01-03"], dtype="datetime64[ms]")
        validate_times(times)

    def test_nat_raises(self) -> None:
        times = np.array(["2020-01-01", "NaT", "2020-01-03"], dtype="datetime64[ms]")
        with pytest.raises(ValueError, match="NaT"):
            validate_times(times)

    def test_duplicates_raise(self) -> None:
        times = np.array(["2020-01-01", "2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        with pytest.raises(ValueError, match="duplicate"):
            validate_times(times)

    def test_single_point(self) -> None:
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        validate_times(times)


# ---------------------------------------------------------------------------
# New: validate_finite / filter_finite
# ---------------------------------------------------------------------------


class TestValidateFinite:
    def test_valid(self) -> None:
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        validate_finite(data)

    def test_nan_raises(self) -> None:
        data = np.array([[1.0, np.nan], [3.0, 4.0]])
        with pytest.raises(ValueError, match="non-finite"):
            validate_finite(data)

    def test_inf_raises(self) -> None:
        data = np.array([[1.0, np.inf], [3.0, 4.0]])
        with pytest.raises(ValueError, match="non-finite"):
            validate_finite(data)


class TestFilterFinite:
    def test_filters_nan(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[1.0, 2.0], [np.nan, 4.0]])
        ft, fd = filter_finite(times, data)
        assert ft.shape[0] == 1
        assert fd[0, 0] == 1.0

    def test_filters_inf(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[np.inf, 2.0], [3.0, 4.0]])
        ft, fd = filter_finite(times, data)
        assert ft.shape[0] == 1
        assert fd[0, 0] == 3.0

    def test_all_valid(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        ft, _fd = filter_finite(times, data)
        assert ft.shape[0] == 2


# ---------------------------------------------------------------------------
# New: validate_rate / filter_rate
# ---------------------------------------------------------------------------


class TestValidateRate:
    def test_quaternion_slow_rotation_passes(self) -> None:
        """Two identity quaternions 1s apart: rate = 0."""
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        validate_rate(times, data, max_rate=1.0, fmt="Quaternions")

    def test_quaternion_fast_rotation_raises(self) -> None:
        """180 degree rotation in 1 second = pi rad/s."""
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array(
            [
                [0.0, 0.0, 0.0, 1.0],  # identity
                [1.0, 0.0, 0.0, 0.0],  # 180 deg about x
            ]
        )
        with pytest.raises(ValueError, match="rate exceeds"):
            validate_rate(times, data, max_rate=0.1, fmt="Quaternions")

    def test_single_row_passes(self) -> None:
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[0.0, 0.0, 0.0, 1.0]])
        validate_rate(times, data, max_rate=0.1, fmt="Quaternions")

    def test_ephemeris_position_rate(self) -> None:
        """1000 km in 1 second = 1000 km/s."""
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array([[0.0, 0.0, 0.0], [1000.0, 0.0, 0.0]])
        with pytest.raises(ValueError, match="rate exceeds"):
            validate_rate(times, data, max_rate=100.0, fmt="TimePos")

    def test_ephemeris_slow_rate_passes(self) -> None:
        """7.5 km/s is typical LEO velocity."""
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array([[7000.0, 0.0, 0.0], [7007.5, 0.0, 0.0]])
        validate_rate(times, data, max_rate=10.0, fmt="TimePos")

    def test_vector_rate(self) -> None:
        """Two perpendicular vectors 1s apart = pi/2 rad/s."""
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        with pytest.raises(ValueError, match="rate exceeds"):
            validate_rate(times, data, max_rate=0.1, fmt="ECFVector")


class TestFilterRate:
    def test_drops_fast_transition(self) -> None:
        s = np.sin(0.005)
        c = np.cos(0.005)
        times = np.array(
            [
                "2020-01-01T00:00:00",
                "2020-01-01T00:00:01",
                "2020-01-01T00:00:02",
                "2020-01-01T00:00:03",
            ],
            dtype="datetime64[ms]",
        )
        data = np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [s, 0.0, 0.0, c],  # ~0.01 rad/s — OK
                [1.0, 0.0, 0.0, 0.0],  # 180 deg jump — BAD
                [s, 0.0, 0.0, c],  # similar to row 1
            ]
        )
        ft, _fd = filter_rate(times, data, max_rate=0.5, fmt="Quaternions")
        # Single-pass: row 2 and possibly row 3 dropped
        assert ft.shape[0] < 4  # at least the spike is removed
        assert ft.shape[0] >= 2  # rows 0 and 1 survive

    def test_all_ok(self) -> None:
        times = np.array(
            ["2020-01-01T00:00:00", "2020-01-01T00:00:01"],
            dtype="datetime64[ms]",
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        ft, _fd = filter_rate(times, data, max_rate=1.0, fmt="Quaternions")
        assert ft.shape[0] == 2

    def test_ephemeris_filter(self) -> None:
        times = np.array(
            [
                "2020-01-01T00:00:00",
                "2020-01-01T00:00:01",
                "2020-01-01T00:00:02",
                "2020-01-01T00:00:03",
            ],
            dtype="datetime64[ms]",
        )
        data = np.array(
            [
                [7000.0, 0.0, 0.0],
                [7007.0, 0.0, 0.0],  # 7 km/s — OK
                [99000.0, 0.0, 0.0],  # huge jump — BAD
                [7014.0, 0.0, 0.0],  # reasonable
            ]
        )
        ft, _fd = filter_rate(times, data, max_rate=100.0, fmt="TimePos")
        assert ft.shape[0] < 4  # spike filtered
        assert ft.shape[0] >= 2  # first two survive


# ---------------------------------------------------------------------------
# New: validate_intervals
# ---------------------------------------------------------------------------


class TestValidateIntervals:
    def test_valid(self) -> None:
        intervals = [
            (np.datetime64("2020-01-01", "ms"), np.datetime64("2020-01-02", "ms")),
        ]
        validate_intervals(intervals)

    def test_start_equals_end_raises(self) -> None:
        intervals = [
            (np.datetime64("2020-01-01", "ms"), np.datetime64("2020-01-01", "ms")),
        ]
        with pytest.raises(ValueError, match="start >= end"):
            validate_intervals(intervals)

    def test_start_after_end_raises(self) -> None:
        intervals = [
            (np.datetime64("2020-01-02", "ms"), np.datetime64("2020-01-01", "ms")),
        ]
        with pytest.raises(ValueError, match="start >= end"):
            validate_intervals(intervals)

    def test_nat_raises(self) -> None:
        intervals = [
            (np.datetime64("NaT", "ms"), np.datetime64("2020-01-01", "ms")),
        ]
        with pytest.raises(ValueError, match="NaT"):
            validate_intervals(intervals)

    def test_empty_valid(self) -> None:
        validate_intervals([])


# ---------------------------------------------------------------------------
# New: validate_data dispatcher with new features
# ---------------------------------------------------------------------------


class TestValidateDataFinite:
    def test_strict_nan_raises(self) -> None:
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[np.nan, 0.0, 0.0, 1.0]])
        with pytest.raises(ValueError, match="non-finite"):
            validate_data("Quaternions", times, data, strict=True)

    def test_nonstrict_nan_filtered(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[np.nan, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        ft, _fd = validate_data("Quaternions", times, data, strict=False)
        assert ft.shape[0] == 1

    def test_ephemeris_nan_filtered(self) -> None:
        times = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[np.nan, 0.0, 0.0], [1.0, 2.0, 3.0]])
        ft, _fd = validate_data("TimePos", times, data, strict=False)
        assert ft.shape[0] == 1


class TestValidateDataRate:
    def test_rate_check_in_dispatcher(self) -> None:
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [1.0, 0.0, 0.0, 0.0],  # 180 deg
            ]
        )
        with pytest.raises(ValueError, match="rate exceeds"):
            validate_data(
                "Quaternions",
                times,
                data,
                strict=True,
                max_rate=0.1,
            )

    def test_azel_rate_skipped_strict(self) -> None:
        """AzElAngles should not raise even with strict + max_rate."""
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array([[45.0, 30.0], [180.0, 60.0]])
        # Would fail if rate checking were attempted (2 cols can't convert to quats)
        ft, _fd = validate_data(
            "AzElAngles", times, data, strict=True, max_rate=0.01, sequence=323
        )
        assert ft.shape[0] == 2

    def test_azel_rate_skipped_nonstrict(self) -> None:
        """AzElAngles non-strict with max_rate should not attempt rate filtering."""
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array([[45.0, 30.0], [180.0, 60.0]])
        ft, _fd = validate_data(
            "AzElAngles", times, data, strict=False, max_rate=0.01, sequence=323
        )
        assert ft.shape[0] == 2

    def test_rate_none_skips_check(self) -> None:
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [1.0, 0.0, 0.0, 0.0],
            ]
        )
        # No max_rate means no rate check
        ft, _fd = validate_data("Quaternions", times, data, strict=False)
        assert ft.shape[0] == 2
