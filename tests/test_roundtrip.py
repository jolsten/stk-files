"""Round-trip and integration tests.

Write STK files, parse the output back, and verify the data matches the input.
"""

import io
import re

import numpy as np
import pytest

from stk_files.attitude import AttitudeConfig, attitude_writer, write_attitude
from stk_files.ephemeris import EphemerisConfig, ephemeris_writer, write_ephemeris
from stk_files.interval import Interval, write_interval
from stk_files.sensor import SensorConfig, write_sensor


def _extract_data_lines(output: str) -> list[str]:
    """Extract data lines from an STK file (lines between format header and END)."""
    lines = output.strip().split("\n")
    data_lines: list[str] = []
    in_data = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^(AttitudeTime|EphemerisTime)", stripped):
            in_data = True
            continue
        if stripped.startswith("END"):
            break
        if in_data and stripped:
            data_lines.append(stripped)
    return data_lines


def _extract_interval_lines(output: str) -> list[str]:
    """Extract interval lines from an STK interval file."""
    lines = output.strip().split("\n")
    data_lines: list[str] = []
    in_data = False
    for line in lines:
        stripped = line.strip()
        if stripped == "BEGIN Intervals":
            in_data = True
            continue
        if stripped == "END Intervals":
            break
        if in_data and stripped:
            data_lines.append(stripped)
    return data_lines


class TestAttitudeRoundTrip:
    def test_quaternion_values_preserved(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T01:00:00.000"], dtype="datetime64[ms]"
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.5, 0.5, 0.5, 0.5]])
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()

        data_lines = _extract_data_lines(output)
        assert len(data_lines) == 2

        for i, line in enumerate(data_lines):
            parts = line.split()
            timestamp = parts[0]
            values = [float(x) for x in parts[1:]]
            assert timestamp == str(times[i].astype("datetime64[ms]"))[:23]
            np.testing.assert_allclose(values, data[i], atol=1e-6)

    def test_euler_values_preserved(self) -> None:
        config = AttitudeConfig(format="EulerAngles", sequence=321)
        times = np.array(["2020-06-15T12:30:00.000"], dtype="datetime64[ms]")
        data = np.array([[45.0, -10.5, 170.25]])
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()

        data_lines = _extract_data_lines(output)
        assert len(data_lines) == 1
        values = [float(x) for x in data_lines[0].split()[1:]]
        np.testing.assert_allclose(values, data[0], atol=1e-4)

    def test_epsec_values_preserved(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        config = AttitudeConfig(format="Quaternions", time_format="EpSec", scenario_epoch=epoch)
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T01:00:00.000"], dtype="datetime64[ms]"
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()

        data_lines = _extract_data_lines(output)
        assert len(data_lines) == 2
        assert float(data_lines[0].split()[0]) == pytest.approx(0.0)
        assert float(data_lines[1].split()[0]) == pytest.approx(3600.0)

    def test_chunked_write_matches_single_write(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(
            [
                "2020-01-01T00:00:00",
                "2020-01-01T01:00:00",
                "2020-01-01T02:00:00",
                "2020-01-01T03:00:00",
            ],
            dtype="datetime64[ms]",
        )
        data = np.tile([0.0, 0.0, 0.0, 1.0], (4, 1))

        buf_single = io.StringIO()
        write_attitude(buf_single, config, times, data)

        buf_chunked = io.StringIO()
        write_attitude(buf_chunked, config, times, data, chunk_size=2)

        single_data = _extract_data_lines(buf_single.getvalue())
        chunked_data = _extract_data_lines(buf_chunked.getvalue())
        assert single_data == chunked_data


class TestEphemerisRoundTrip:
    def test_timeposvel_values_preserved(self) -> None:
        config = EphemerisConfig(format="TimePosVel")
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T01:00:00.000"], dtype="datetime64[ms]"
        )
        data = np.array(
            [
                [7000000.0, 0.0, 0.0, 0.0, 7500.0, 0.0],
                [6999500.0, 450200.0, 10500.0, -100.0, 7400.0, 50.0],
            ]
        )
        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        output = buf.getvalue()

        data_lines = _extract_data_lines(output)
        assert len(data_lines) == 2

        for i, line in enumerate(data_lines):
            parts = line.split()
            values = [float(x) for x in parts[1:]]
            np.testing.assert_allclose(values, data[i], atol=1e-4)

    def test_point_count_matches_data(self) -> None:
        config = EphemerisConfig(format="TimePos")
        n = 5
        base = np.datetime64("2020-01-01T00:00:00", "ms")
        times = np.array([base + np.timedelta64(i * 60000, "ms") for i in range(n)])
        data = np.column_stack([np.arange(n) * 1000.0, np.zeros(n), np.zeros(n)])
        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        output = buf.getvalue()

        assert f"NumberOfEphemerisPoints  {n}" in output
        data_lines = _extract_data_lines(output)
        assert len(data_lines) == n


class TestSensorRoundTrip:
    def test_azel_values_preserved(self) -> None:
        config = SensorConfig(format="AzElAngles", sequence=323)
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T00:01:00.000"], dtype="datetime64[ms]"
        )
        data = np.array([[45.0, 30.0], [90.0, 60.0]])
        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        output = buf.getvalue()

        data_lines = _extract_data_lines(output)
        assert len(data_lines) == 2
        for i, line in enumerate(data_lines):
            values = [float(x) for x in line.split()[1:]]
            np.testing.assert_allclose(values, data[i], atol=1e-4)


class TestIntervalRoundTrip:
    def test_timestamps_preserved(self) -> None:
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

        data_lines = _extract_interval_lines(output)
        assert len(data_lines) == 2
        for i, line in enumerate(data_lines):
            # Extract quoted timestamps
            quoted = re.findall(r'"([^"]+)"', line)
            assert len(quoted) == 2
            assert quoted[0] == "2020-01-01T00:00:00.000" if i == 0 else "2020-01-02T00:00:00.000"

    def test_metadata_preserved(self) -> None:
        intervals = [
            Interval(
                np.datetime64("2020-01-01T00:00:00.000", "ms"),
                np.datetime64("2020-01-01T01:00:00.000", "ms"),
                "Color red Priority 1",
            ),
        ]
        buf = io.StringIO()
        write_interval(buf, intervals)
        output = buf.getvalue()

        data_lines = _extract_interval_lines(output)
        assert len(data_lines) == 1
        assert "Color red Priority 1" in data_lines[0]


class TestStreamingIntegration:
    def test_attitude_streaming_multi_chunk(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        buf = io.StringIO()
        with attitude_writer(buf, config) as w:
            for hour in range(3):
                t = np.array([f"2020-01-01T{hour:02d}:00:00.000"], dtype="datetime64[ms]")
                d = np.array([[0.0, 0.0, 0.0, 1.0]])
                w.write_chunk(t, d)

        output = buf.getvalue()
        assert "stk.v.11.0" in output
        assert "END Attitude" in output
        data_lines = _extract_data_lines(output)
        assert len(data_lines) == 3

    def test_ephemeris_streaming_multi_chunk(self) -> None:
        config = EphemerisConfig(format="TimePos")
        buf = io.StringIO()
        with ephemeris_writer(buf, config) as w:
            for i in range(4):
                t = np.array([f"2020-01-01T{i:02d}:00:00.000"], dtype="datetime64[ms]")
                d = np.array([[7000.0 + i * 100, 0.0, 0.0]])
                w.write_chunk(t, d)

        output = buf.getvalue()
        assert "BEGIN Ephemeris" in output
        assert "END Ephemeris" in output
        # Chunked mode omits NumberOfEphemerisPoints
        assert "NumberOfEphemerisPoints" not in output
        data_lines = _extract_data_lines(output)
        assert len(data_lines) == 4

    def test_validation_filtering_integration(self) -> None:
        """Full pipeline: unsorted data with some invalid rows → sorted, filtered output."""
        config = AttitudeConfig(format="Quaternions")
        times = np.array(
            [
                "2020-01-01T03:00:00",
                "2020-01-01T01:00:00",
                "2020-01-01T02:00:00",
                "2020-01-01T00:00:00",
            ],
            dtype="datetime64[ms]",
        )
        data = np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [np.nan, 0.0, 0.0, 1.0],  # will be filtered
                [2.0, 2.0, 2.0, 2.0],  # invalid quaternion, will be filtered
                [0.5, 0.5, 0.5, 0.5],
            ]
        )
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()

        data_lines = _extract_data_lines(output)
        # Only 2 valid rows remain
        assert len(data_lines) == 2
        # Should be sorted: T=0 first, T=3 second
        timestamps = [line.split()[0] for line in data_lines]
        assert timestamps[0] < timestamps[1]
        assert "2020-01-01T00:00:00.000" in timestamps[0]
        assert "2020-01-01T03:00:00.000" in timestamps[1]
