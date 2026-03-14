"""Tests for read_* functions and the _parser module."""

import io

import numpy as np
import pytest

from stk_files._parser import (
    STKParseError,
    parse_data_section,
    parse_datetime,
    parse_header,
    parse_interval_file,
)
from stk_files.attitude import AttitudeConfig, read_attitude, write_attitude
from stk_files.ephemeris import EphemerisConfig, read_ephemeris, write_ephemeris
from stk_files.interval import Interval, read_interval, write_interval
from stk_files.sensor import SensorConfig, read_sensor, write_sensor

# ---------------------------------------------------------------------------
# _parser unit tests
# ---------------------------------------------------------------------------


class TestParseDateTime:
    def test_basic(self) -> None:
        dt = parse_datetime("2020-01-01T00:00:00.000")
        assert dt == np.datetime64("2020-01-01T00:00:00.000", "ms")

    def test_strips_whitespace(self) -> None:
        dt = parse_datetime("  2020-06-15T12:30:00.000  ")
        assert dt == np.datetime64("2020-06-15T12:30:00.000", "ms")


class TestParseHeader:
    def test_attitude_header(self) -> None:
        lines = [
            "stk.v.11.0",
            "BEGIN Attitude",
            "TimeFormat          ISO-YMD",
            "CoordinateAxes      ICRF",
            "AttitudeTimeQuaternions",
        ]
        header, fmt, start = parse_header(lines, "AttitudeTime")
        assert fmt == "Quaternions"
        assert header["TimeFormat"] == "ISO-YMD"
        assert header["CoordinateAxes"] == "ICRF"
        assert start == 5

    def test_ephemeris_header(self) -> None:
        lines = [
            "stk.v.12.0",
            "BEGIN Ephemeris",
            "TimeFormat              ISO-YMD",
            "CoordinateSystem        J2000",
            "NumberOfEphemerisPoints  2",
            "EphemerisTimePosVel",
        ]
        header, fmt, start = parse_header(lines, "Ephemeris")
        assert fmt == "TimePosVel"
        assert header["CoordinateSystem"] == "J2000"
        assert header["NumberOfEphemerisPoints"] == "2"
        assert start == 6

    def test_lla_ephemeris_sentinel(self) -> None:
        lines = [
            "stk.v.12.0",
            "BEGIN Ephemeris",
            "TimeFormat              ISO-YMD",
            "EphemerisLLATimePos",
        ]
        _, fmt, _ = parse_header(lines, "Ephemeris")
        assert fmt == "LLATimePos"

    def test_empty_file_raises(self) -> None:
        with pytest.raises(STKParseError, match="empty file"):
            parse_header([], "AttitudeTime")

    def test_bad_version_raises(self) -> None:
        with pytest.raises(STKParseError, match="version header"):
            parse_header(["not a version line"], "AttitudeTime")

    def test_missing_sentinel_raises(self) -> None:
        lines = [
            "stk.v.11.0",
            "BEGIN Attitude",
            "TimeFormat          ISO-YMD",
        ]
        with pytest.raises(STKParseError, match="no 'AttitudeTime\\*' data sentinel"):
            parse_header(lines, "AttitudeTime")

    def test_optional_fields(self) -> None:
        lines = [
            "stk.v.11.0",
            "BEGIN Attitude",
            "MessageLevel        Warnings",
            "TimeFormat          EpSec",
            "ScenarioEpoch       2020-01-01T00:00:00.000",
            "CentralBody         Earth",
            "CoordinateAxes      ICRF",
            "CoordinateAxesEpoch 2020-06-01T00:00:00.000",
            "InterpolationMethod Lagrange",
            "InterpolationOrder  5",
            "Sequence            321",
            "AttitudeTimeEulerAngles",
        ]
        header, fmt, _ = parse_header(lines, "AttitudeTime")
        assert fmt == "EulerAngles"
        assert header["MessageLevel"] == "Warnings"
        assert header["ScenarioEpoch"] == "2020-01-01T00:00:00.000"
        assert header["Sequence"] == "321"
        assert header["InterpolationOrder"] == "5"

    def test_blank_lines_skipped(self) -> None:
        lines = [
            "stk.v.11.0",
            "",
            "BEGIN Attitude",
            "",
            "TimeFormat          ISO-YMD",
            "",
            "AttitudeTimeQuaternions",
        ]
        header, fmt, _ = parse_header(lines, "AttitudeTime")
        assert fmt == "Quaternions"
        assert header["TimeFormat"] == "ISO-YMD"


class TestParseDataSection:
    def test_iso_ymd(self) -> None:
        lines = [
            "sentinel",  # index 0 (not parsed)
            "2020-01-01T00:00:00.000 1.0 2.0 3.0",
            "2020-01-01T01:00:00.000 4.0 5.0 6.0",
            "END Attitude",
        ]
        times, data = parse_data_section(lines, 1, "ISO-YMD", 3)
        assert times.shape == (2,)
        assert data.shape == (2, 3)
        np.testing.assert_array_equal(data[0], [1.0, 2.0, 3.0])
        np.testing.assert_array_equal(data[1], [4.0, 5.0, 6.0])

    def test_epsec(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        lines = [
            "sentinel",
            "    0.000 1.0 2.0",
            " 3600.000 3.0 4.0",
            "END Ephemeris",
        ]
        times, data = parse_data_section(lines, 1, "EpSec", 2, epoch)
        assert times[0] == epoch
        assert times[1] == epoch + np.timedelta64(3600000, "ms")
        np.testing.assert_array_equal(data[0], [1.0, 2.0])

    def test_epsec_missing_epoch_raises(self) -> None:
        lines = ["sentinel", "0.000 1.0 2.0", "END"]
        with pytest.raises(STKParseError, match="ScenarioEpoch"):
            parse_data_section(lines, 1, "EpSec", 2)

    def test_too_few_columns_raises(self) -> None:
        lines = ["sentinel", "2020-01-01T00:00:00.000 1.0", "END"]
        with pytest.raises(STKParseError, match="expected 4 columns"):
            parse_data_section(lines, 1, "ISO-YMD", 3)

    def test_empty_data_section(self) -> None:
        lines = ["sentinel", "END Attitude"]
        times, data = parse_data_section(lines, 1, "ISO-YMD", 4)
        assert times.shape == (0,)
        assert data.shape == (0, 4)

    def test_blank_lines_skipped(self) -> None:
        lines = [
            "sentinel",
            "",
            "2020-01-01T00:00:00.000 1.0 2.0",
            "",
            "END",
        ]
        times, _data = parse_data_section(lines, 1, "ISO-YMD", 2)
        assert times.shape == (1,)


class TestParseIntervalFile:
    def test_basic(self) -> None:
        lines = [
            "stk.v.12.0",
            "BEGIN IntervalList",
            "    DateUnitAbrv ISO-YMD",
            "BEGIN Intervals",
            '"2020-01-01T00:00:00.000" "2020-01-01T00:10:00.000"',
            "END Intervals",
            "END IntervalList",
        ]
        result = parse_interval_file(lines)
        assert len(result) == 1
        assert result[0][0] == np.datetime64("2020-01-01T00:00:00.000", "ms")
        assert result[0][1] == np.datetime64("2020-01-01T00:10:00.000", "ms")
        assert result[0][2] == ""

    def test_with_data(self) -> None:
        lines = [
            "stk.v.12.0",
            "BEGIN IntervalList",
            "    DateUnitAbrv ISO-YMD",
            "BEGIN Intervals",
            '"2020-01-01T00:00:00.000" "2020-01-01T01:00:00.000" Color red Priority 1',
            "END Intervals",
            "END IntervalList",
        ]
        result = parse_interval_file(lines)
        assert len(result) == 1
        assert result[0][2] == "Color red Priority 1"

    def test_missing_begin_intervals_raises(self) -> None:
        lines = [
            "stk.v.12.0",
            "BEGIN IntervalList",
            "END IntervalList",
        ]
        with pytest.raises(STKParseError, match="BEGIN Intervals"):
            parse_interval_file(lines)


# ---------------------------------------------------------------------------
# read_attitude round-trip tests
# ---------------------------------------------------------------------------


class TestReadAttitude:
    def test_quaternion_roundtrip(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T01:00:00.000"],
            dtype="datetime64[ms]",
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.5, 0.5, 0.5, 0.5]])

        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        buf.seek(0)
        cfg, t, d = read_attitude(buf)

        assert cfg.format == "Quaternions"
        assert cfg.coordinate_axes == "ICRF"
        assert cfg.time_format == "ISO-YMD"
        np.testing.assert_array_equal(t, times)
        np.testing.assert_allclose(d, data, atol=1e-6)

    def test_euler_roundtrip(self) -> None:
        config = AttitudeConfig(format="EulerAngles", sequence=321)
        times = np.array(["2020-06-15T12:30:00.000"], dtype="datetime64[ms]")
        data = np.array([[45.0, -10.5, 170.25]])

        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        buf.seek(0)
        cfg, t, d = read_attitude(buf)

        assert cfg.format == "EulerAngles"
        assert cfg.sequence == 321
        np.testing.assert_array_equal(t, times)
        np.testing.assert_allclose(d, data, atol=1e-4)

    def test_quat_scalar_first_roundtrip(self) -> None:
        config = AttitudeConfig(format="QuatScalarFirst")
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[1.0, 0.0, 0.0, 0.0]])

        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        buf.seek(0)
        cfg, _t, d = read_attitude(buf)

        assert cfg.format == "QuatScalarFirst"
        np.testing.assert_allclose(d, data, atol=1e-6)

    def test_epsec_roundtrip(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        config = AttitudeConfig(
            format="Quaternions", time_format="EpSec", scenario_epoch=epoch
        )
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T01:00:00.000"],
            dtype="datetime64[ms]",
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])

        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        buf.seek(0)
        cfg, t, d = read_attitude(buf)

        assert cfg.time_format == "EpSec"
        assert cfg.scenario_epoch == epoch
        np.testing.assert_array_equal(t, times)
        np.testing.assert_allclose(d, data, atol=1e-6)

    def test_full_config_roundtrip(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        config = AttitudeConfig(
            format="YPRAngles",
            coordinate_axes="J2000",
            message_level="Warnings",
            time_format="ISO-YMD",
            scenario_epoch=epoch,
            central_body="Earth",
            interpolation_method="Lagrange",
            interpolation_order=5,
            sequence=321,
        )
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[10.0, 20.0, 30.0]])

        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        buf.seek(0)
        cfg, _, _ = read_attitude(buf)

        assert cfg.format == "YPRAngles"
        assert cfg.coordinate_axes == "J2000"
        assert cfg.message_level == "Warnings"
        assert cfg.scenario_epoch == epoch
        assert cfg.central_body == "Earth"
        assert cfg.interpolation_method == "Lagrange"
        assert cfg.interpolation_order == 5
        assert cfg.sequence == 321

    def test_dcm_roundtrip(self) -> None:
        config = AttitudeConfig(format="DCM")
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        # Identity rotation
        data = np.array([[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]])

        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        buf.seek(0)
        cfg, _t, d = read_attitude(buf)

        assert cfg.format == "DCM"
        np.testing.assert_allclose(d, data, atol=1e-4)


# ---------------------------------------------------------------------------
# read_ephemeris round-trip tests
# ---------------------------------------------------------------------------


class TestReadEphemeris:
    def test_timepos_roundtrip(self) -> None:
        config = EphemerisConfig(format="TimePos")
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T01:00:00.000"],
            dtype="datetime64[ms]",
        )
        data = np.array([[7000.0, 0.0, 0.0], [6999.0, 450.0, 10.0]])

        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        buf.seek(0)
        cfg, t, d = read_ephemeris(buf)

        assert cfg.format == "TimePos"
        assert cfg.coordinate_system == "ICRF"
        np.testing.assert_array_equal(t, times)
        np.testing.assert_allclose(d, data, atol=1e-4)

    def test_timeposvel_roundtrip(self) -> None:
        config = EphemerisConfig(format="TimePosVel")
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[7000.0, 0.0, 0.0, 0.0, 7.5, 0.0]])

        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        buf.seek(0)
        cfg, _t, d = read_ephemeris(buf)

        assert cfg.format == "TimePosVel"
        np.testing.assert_allclose(d, data, atol=1e-4)

    def test_epsec_roundtrip(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        config = EphemerisConfig(
            format="TimePos", time_format="EpSec", scenario_epoch=epoch
        )
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T00:01:00.000"],
            dtype="datetime64[ms]",
        )
        data = np.array([[7000.0, 0.0, 0.0], [7001.0, 0.0, 0.0]])

        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        buf.seek(0)
        _cfg, t, _d = read_ephemeris(buf)

        np.testing.assert_array_equal(t, times)

    def test_full_config_roundtrip(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        config = EphemerisConfig(
            format="TimePosVel",
            coordinate_system="J2000",
            message_level="Errors",
            time_format="ISO-YMD",
            scenario_epoch=epoch,
            central_body="Earth",
            interpolation_method="Hermite",
            interpolation_order=7,
        )
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[7000.0, 0.0, 0.0, 0.0, 7.5, 0.0]])

        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        buf.seek(0)
        cfg, _, _ = read_ephemeris(buf)

        assert cfg.coordinate_system == "J2000"
        assert cfg.message_level == "Errors"
        assert cfg.central_body == "Earth"
        assert cfg.interpolation_method == "Hermite"
        assert cfg.interpolation_order == 7


# ---------------------------------------------------------------------------
# read_sensor round-trip tests
# ---------------------------------------------------------------------------


class TestReadSensor:
    def test_azel_roundtrip(self) -> None:
        config = SensorConfig(format="AzElAngles", sequence=323)
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T00:01:00.000"],
            dtype="datetime64[ms]",
        )
        data = np.array([[45.0, 30.0], [90.0, 60.0]])

        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        buf.seek(0)
        cfg, t, d = read_sensor(buf)

        assert cfg.format == "AzElAngles"
        assert cfg.sequence == 323
        np.testing.assert_array_equal(t, times)
        np.testing.assert_allclose(d, data, atol=1e-4)

    def test_quaternion_roundtrip(self) -> None:
        config = SensorConfig(format="Quaternions", coordinate_axes="ICRF")
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[0.0, 0.0, 0.0, 1.0]])

        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        buf.seek(0)
        cfg, _t, d = read_sensor(buf)

        assert cfg.format == "Quaternions"
        assert cfg.coordinate_axes == "ICRF"
        np.testing.assert_allclose(d, data, atol=1e-6)

    def test_no_axes_roundtrip(self) -> None:
        """Sensor config with coordinate_axes=None should round-trip."""
        config = SensorConfig(format="Quaternions")
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[0.0, 0.0, 0.0, 1.0]])

        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        buf.seek(0)
        cfg, _, _ = read_sensor(buf)

        assert cfg.coordinate_axes is None


# ---------------------------------------------------------------------------
# read_interval round-trip tests
# ---------------------------------------------------------------------------


class TestReadInterval:
    def test_basic_roundtrip(self) -> None:
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
        buf.seek(0)
        _, read_intervals = read_interval(buf)

        assert len(read_intervals) == 2
        assert read_intervals[0].start == intervals[0].start
        assert read_intervals[0].end == intervals[0].end
        assert read_intervals[1].start == intervals[1].start
        assert read_intervals[1].end == intervals[1].end

    def test_metadata_roundtrip(self) -> None:
        intervals = [
            Interval(
                np.datetime64("2020-01-01T00:00:00.000", "ms"),
                np.datetime64("2020-01-01T01:00:00.000", "ms"),
                "Color red Priority 1",
            ),
        ]
        buf = io.StringIO()
        write_interval(buf, intervals)
        buf.seek(0)
        _, read_intervals = read_interval(buf)

        assert len(read_intervals) == 1
        assert read_intervals[0].data == "Color red Priority 1"

    def test_empty_intervals(self) -> None:
        buf = io.StringIO()
        write_interval(buf, [])
        buf.seek(0)
        _, read_intervals = read_interval(buf)

        assert read_intervals == []

    def test_no_data_field(self) -> None:
        intervals = [
            Interval(
                np.datetime64("2020-01-01T00:00:00.000", "ms"),
                np.datetime64("2020-01-01T01:00:00.000", "ms"),
            ),
        ]
        buf = io.StringIO()
        write_interval(buf, intervals)
        buf.seek(0)
        _, read_intervals = read_interval(buf)

        assert read_intervals[0].data == ""


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestReadErrors:
    def test_read_attitude_bad_format(self) -> None:
        lines = "stk.v.11.0\nBEGIN Attitude\nAttitudeTimeInvalid\nEND Attitude\n"
        with pytest.raises(STKParseError, match="unknown attitude format"):
            read_attitude(io.StringIO(lines))

    def test_read_ephemeris_bad_format(self) -> None:
        lines = "stk.v.12.0\nBEGIN Ephemeris\nEphemerisInvalid\nEND Ephemeris\n"
        with pytest.raises(STKParseError, match="unknown ephemeris format"):
            read_ephemeris(io.StringIO(lines))

    def test_read_sensor_bad_format(self) -> None:
        lines = "stk.v.11.0\nBEGIN Attitude\nAttitudeTimeInvalid\nEND Attitude\n"
        with pytest.raises(STKParseError, match="unknown sensor format"):
            read_sensor(io.StringIO(lines))

    def test_read_empty_file(self) -> None:
        with pytest.raises(STKParseError, match="empty file"):
            read_attitude(io.StringIO(""))

    def test_stk_parse_error_is_value_error(self) -> None:
        """STKParseError should be catchable as ValueError."""
        with pytest.raises(ValueError):
            read_attitude(io.StringIO(""))
