import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stk_files._formatting import (
    format_ep_sec,
    format_generic_row,
    format_iso_ymd,
    format_quaternion_row,
)
from tests.strategies import datetime64s

TIME_UNITS = ["s", "ms", "us", "ns"]


class TestFormatIsoYmd:
    def test_known_value(self) -> None:
        t = np.datetime64("2020-01-01T00:00:00.000", "ms")
        assert format_iso_ymd(t) == "2020-01-01T00:00:00.000"

    def test_length_is_23(self) -> None:
        t = np.datetime64("2020-06-15T12:30:45.123", "ms")
        assert len(format_iso_ymd(t)) == 23

    @given(t=datetime64s())
    @settings(max_examples=100)
    def test_matches_numpy_string(self, t: np.datetime64) -> None:
        result = format_iso_ymd(t)
        expected = str(t.astype("datetime64[ms]"))[:23]
        assert result == expected

    @pytest.mark.parametrize("unit", TIME_UNITS)
    def test_precision(self, unit: str) -> None:
        t = np.datetime64("2020-06-15T12:30:45", unit)
        result = format_iso_ymd(t)
        assert result == "2020-06-15T12:30:45.000"
        assert len(result) == 23

    @pytest.mark.parametrize("unit", ["ms", "us", "ns"])
    def test_sub_second_precision_preserved_to_ms(self, unit: str) -> None:
        t = np.datetime64("2020-01-01T00:00:00.123", unit)
        result = format_iso_ymd(t)
        assert result == "2020-01-01T00:00:00.123"

    def test_us_truncated_to_ms(self) -> None:
        t = np.datetime64("2020-01-01T00:00:00.123456", "us")
        result = format_iso_ymd(t)
        assert result == "2020-01-01T00:00:00.123"

    def test_ns_truncated_to_ms(self) -> None:
        t = np.datetime64("2020-01-01T00:00:00.123456789", "ns")
        result = format_iso_ymd(t)
        assert result == "2020-01-01T00:00:00.123"


class TestFormatEpSec:
    def test_zero_offset(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        result = format_ep_sec(epoch, epoch)
        assert float(result) == 0.0

    def test_one_hour(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        t = np.datetime64("2020-01-01T01:00:00.000", "ms")
        result = format_ep_sec(t, epoch)
        assert float(result) == 3600.0

    @given(
        base=datetime64s(start="2000-01-01", end="2020-01-01"),
        offset_ms=st.integers(0, 86400000),
    )
    @settings(max_examples=100)
    def test_offset_matches(self, base: np.datetime64, offset_ms: int) -> None:
        t = base + np.timedelta64(offset_ms, "ms")
        result = float(format_ep_sec(t, base))
        expected = offset_ms / 1000.0
        assert abs(result - expected) < 0.01

    @pytest.mark.parametrize("unit", TIME_UNITS)
    def test_precision(self, unit: str) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00", unit)
        t = np.datetime64("2020-01-01T01:00:00", unit)
        result = float(format_ep_sec(t, epoch))
        assert result == 3600.0

    def test_mixed_precision(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00", "s")
        t = np.datetime64("2020-01-01T01:00:00.000", "ms")
        assert float(format_ep_sec(t, epoch)) == 3600.0

    def test_us_sub_second(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00", "us")
        t = np.datetime64("2020-01-01T00:00:01.500000", "us")
        result = float(format_ep_sec(t, epoch))
        assert abs(result - 1.5) < 0.001

    def test_ns_sub_second(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00", "ns")
        t = np.datetime64("2020-01-01T00:00:01.500000000", "ns")
        result = float(format_ep_sec(t, epoch))
        assert abs(result - 1.5) < 0.001


class TestFormatQuaternionRow:
    def test_format(self) -> None:
        row = np.array([0.0, 0.0, 0.0, 1.0])
        result = format_quaternion_row(row)
        assert "+0.000000000" in result
        assert "+1.000000000" in result

    def test_negative_values(self) -> None:
        row = np.array([-0.5, 0.5, -0.5, 0.5])
        result = format_quaternion_row(row)
        assert "-0.500000000" in result
        assert "+0.500000000" in result


class TestFormatGenericRow:
    def test_format(self) -> None:
        row = np.array([1.0, 2.0, 3.0])
        result = format_generic_row(row)
        parts = result.split()
        assert len(parts) == 3
        assert float(parts[0]) == 1.0
