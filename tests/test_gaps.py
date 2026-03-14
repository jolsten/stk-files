import io

import numpy as np

from stk_files._gaps import detect_availability, write_availability


class TestDetectAvailability:
    def test_no_gaps(self) -> None:
        times = np.array(
            ["2020-01-01T00:00:00", "2020-01-01T00:00:01", "2020-01-01T00:00:02"],
            dtype="datetime64[ms]",
        )
        max_gap = np.timedelta64(5, "s")
        spans = detect_availability(times, max_gap)
        assert len(spans) == 1
        assert spans[0][0] == times[0]
        assert spans[0][1] == times[-1]

    def test_single_gap(self) -> None:
        times = np.array(
            [
                "2020-01-01T00:00:00",
                "2020-01-01T00:00:01",
                "2020-01-01T00:01:00",
                "2020-01-01T00:01:01",
            ],
            dtype="datetime64[ms]",
        )
        max_gap = np.timedelta64(5, "s")
        spans = detect_availability(times, max_gap)
        assert len(spans) == 2
        assert spans[0] == (times[0], times[1])
        assert spans[1] == (times[2], times[3])

    def test_multiple_gaps(self) -> None:
        times = np.array(
            ["2020-01-01T00:00:00", "2020-01-01T00:01:00", "2020-01-01T00:02:00"],
            dtype="datetime64[ms]",
        )
        max_gap = np.timedelta64(30, "s")
        # Default min_points=2 filters out single-point spans
        spans = detect_availability(times, max_gap)
        assert len(spans) == 0
        # min_points=1 preserves all spans
        spans = detect_availability(times, max_gap, min_points=1)
        assert len(spans) == 3

    def test_empty(self) -> None:
        times = np.array([], dtype="datetime64[ms]")
        spans = detect_availability(times, np.timedelta64(5, "s"))
        assert spans == []

    def test_single_point_default_excluded(self) -> None:
        times = np.array(["2020-01-01T00:00:00"], dtype="datetime64[ms]")
        spans = detect_availability(times, np.timedelta64(5, "s"))
        assert len(spans) == 0

    def test_single_point_min_points_1(self) -> None:
        times = np.array(["2020-01-01T00:00:00"], dtype="datetime64[ms]")
        spans = detect_availability(times, np.timedelta64(5, "s"), min_points=1)
        assert len(spans) == 1
        assert spans[0][0] == spans[0][1]

    def test_gap_at_exact_threshold_not_split(self) -> None:
        """Gap equal to max_gap should NOT create a split."""
        times = np.array(
            ["2020-01-01T00:00:00", "2020-01-01T00:00:05"],
            dtype="datetime64[ms]",
        )
        max_gap = np.timedelta64(5, "s")
        spans = detect_availability(times, max_gap)
        assert len(spans) == 1

    def test_gap_just_over_threshold(self) -> None:
        """Gap just over max_gap should create a split."""
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T00:00:05.001"],
            dtype="datetime64[ms]",
        )
        max_gap = np.timedelta64(5, "s")
        # Default min_points=2 filters single-point spans
        spans = detect_availability(times, max_gap)
        assert len(spans) == 0
        # min_points=1 preserves them
        spans = detect_availability(times, max_gap, min_points=1)
        assert len(spans) == 2


class TestWriteAvailability:
    def test_produces_interval_file(self) -> None:
        times = np.array(
            [
                "2020-01-01T00:00:00",
                "2020-01-01T00:00:01",
                "2020-01-01T00:01:00",
                "2020-01-01T00:01:01",
            ],
            dtype="datetime64[ms]",
        )
        buf = io.StringIO()
        write_availability(buf, times, np.timedelta64(5, "s"))
        output = buf.getvalue()
        assert "BEGIN IntervalList" in output
        assert "END IntervalList" in output
        assert "BEGIN Intervals" in output
        # Should have 2 intervals
        interval_lines = [
            line for line in output.strip().split("\n") if line.strip().startswith('"')
        ]
        assert len(interval_lines) == 2

    def test_empty_times(self) -> None:
        buf = io.StringIO()
        write_availability(buf, np.array([], dtype="datetime64[ms]"), np.timedelta64(5, "s"))
        output = buf.getvalue()
        assert "BEGIN Intervals" in output
        assert "END Intervals" in output
