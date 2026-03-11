import io

import numpy as np
import pytest

from stk_files.interval import Interval, IntervalConfig, write_interval


class TestWriteInterval:
    def test_basic_output(self) -> None:
        intervals = [
            Interval(
                np.datetime64("2020-01-01T00:00:00.000", "ms"),
                np.datetime64("2020-01-01T00:10:00.000", "ms"),
            ),
            Interval(
                np.datetime64("2020-01-02T00:00:00.000", "ms"),
                np.datetime64("2020-01-02T00:20:00.000", "ms"),
            ),
        ]
        buf = io.StringIO()
        write_interval(buf, intervals)
        output = buf.getvalue()
        assert "stk.v.12.0" in output
        assert "BEGIN IntervalList" in output
        assert "END IntervalList" in output
        assert "BEGIN Intervals" in output
        assert "END Intervals" in output
        assert "DateUnitAbrv ISO-YMD" in output
        assert '"2020-01-01T00:00:00.000"' in output

    def test_with_data_string(self) -> None:
        intervals = [
            Interval(
                np.datetime64("2020-01-01T00:00:00.000", "ms"),
                np.datetime64("2020-01-01T00:10:00.000", "ms"),
                "Color red",
            ),
        ]
        buf = io.StringIO()
        write_interval(buf, intervals)
        output = buf.getvalue()
        assert "Color red" in output

    def test_empty_intervals(self) -> None:
        buf = io.StringIO()
        write_interval(buf, [])
        output = buf.getvalue()
        assert "BEGIN Intervals" in output
        assert "END Intervals" in output

    @pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
    def test_time_precision(self, unit: str) -> None:
        intervals = [
            Interval(
                np.datetime64("2020-01-01T00:00:00", unit),
                np.datetime64("2020-01-01T00:10:00", unit),
            ),
        ]
        buf = io.StringIO()
        write_interval(buf, intervals)
        output = buf.getvalue()
        assert '"2020-01-01T00:00:00.000"' in output
        assert '"2020-01-01T00:10:00.000"' in output

    def test_start_after_end_raises(self) -> None:
        intervals = [
            Interval(
                np.datetime64("2020-01-02T00:00:00", "ms"),
                np.datetime64("2020-01-01T00:00:00", "ms"),
            ),
        ]
        buf = io.StringIO()
        with pytest.raises(ValueError, match="start >= end"):
            write_interval(buf, intervals)

    def test_nat_raises(self) -> None:
        intervals = [
            Interval(np.datetime64("NaT", "ms"), np.datetime64("2020-01-01T00:00:00", "ms")),
        ]
        buf = io.StringIO()
        with pytest.raises(ValueError, match="NaT"):
            write_interval(buf, intervals)

    def test_with_explicit_config(self) -> None:
        config = IntervalConfig()
        intervals = [
            Interval(
                np.datetime64("2020-01-01T00:00:00.000", "ms"),
                np.datetime64("2020-01-01T00:10:00.000", "ms"),
            ),
        ]
        buf = io.StringIO()
        write_interval(buf, intervals, config=config)
        output = buf.getvalue()
        assert "stk.v.12.0" in output
        assert "BEGIN IntervalList" in output


class TestIntervalConfig:
    def test_header_lines(self) -> None:
        config = IntervalConfig()
        hdr = config.header_lines()
        assert hdr[0] == "stk.v.12.0"
        assert "BEGIN IntervalList" in hdr

    def test_footer_lines(self) -> None:
        config = IntervalConfig()
        ftr = config.footer_lines()
        assert "END Intervals" in ftr
        assert "END IntervalList" in ftr
