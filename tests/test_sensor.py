import io

import numpy as np
import pytest

from stk_files.sensor import SensorConfig, sensor_writer, write_sensor


class TestSensorConfig:
    def test_azel_config(self) -> None:
        config = SensorConfig(format="AzElAngles", sequence=323)
        lines = config.header_lines()
        assert lines[0] == "stk.v.11.0"
        assert lines[-1] == "AttitudeTimeAzElAngles"

    def test_azel_requires_sequence(self) -> None:
        with pytest.raises(ValueError, match="requires a sequence"):
            SensorConfig(format="AzElAngles")

    def test_quaternion_no_coordinate_axes(self) -> None:
        config = SensorConfig(format="Quaternions")
        lines = config.header_lines()
        assert not any("CoordinateAxes" in line for line in lines)

    def test_with_coordinate_axes(self) -> None:
        config = SensorConfig(format="Quaternions", coordinate_axes="J2000")
        lines = config.header_lines()
        assert any("CoordinateAxes" in line for line in lines)

    def test_uses_attitude_block_name(self) -> None:
        config = SensorConfig(format="Quaternions")
        assert config.footer_lines() == ["END Attitude"]


class TestWriteSensor:
    def test_azel_output(self) -> None:
        config = SensorConfig(format="AzElAngles", sequence=323)
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[45.0, 30.0]])
        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        output = buf.getvalue()
        assert "AttitudeTimeAzElAngles" in output
        assert "BEGIN Attitude" in output
        assert "END Attitude" in output

    def test_quaternion_output(self) -> None:
        config = SensorConfig(format="Quaternions")
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        output = buf.getvalue()
        assert "+1.000000000" in output

    def test_euler_angles_output(self) -> None:
        config = SensorConfig(format="EulerAngles", sequence=321)
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[10.0, 20.0, 30.0]])
        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        output = buf.getvalue()
        assert "AttitudeTimeEulerAngles" in output
        assert "Sequence            321" in output

    def test_ypr_angles_output(self) -> None:
        config = SensorConfig(format="YPRAngles", sequence=321)
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[10.0, 20.0, 30.0]])
        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        output = buf.getvalue()
        assert "AttitudeTimeYPRAngles" in output

    def test_dcm_output(self) -> None:
        config = SensorConfig(format="DCM")
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        # Identity DCM
        data = np.array([[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        output = buf.getvalue()
        assert "AttitudeTimeDCM" in output

    def test_all_invalid_raises_empty(self) -> None:
        config = SensorConfig(format="Quaternions")
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[2.0, 2.0, 2.0, 2.0]])
        buf = io.StringIO()
        with pytest.raises(ValueError, match="no valid data rows"):
            write_sensor(buf, config, times, data)

    def test_azel_max_rate_skipped(self) -> None:
        """AzElAngles should not error when max_rate is provided."""
        config = SensorConfig(format="AzElAngles", sequence=323)
        times = np.array(["2020-01-01T00:00:00", "2020-01-01T00:00:01"], dtype="datetime64[ms]")
        data = np.array([[45.0, 30.0], [180.0, 60.0]])
        buf = io.StringIO()
        write_sensor(buf, config, times, data, max_rate=0.1)
        output = buf.getvalue()
        assert "AttitudeTimeAzElAngles" in output
        # Both rows survive since rate checking is skipped for AzEl
        lines = [line for line in output.strip().split("\n") if "2020-01-01T" in line]
        assert len(lines) == 2

    def test_chunk_writer_cross_chunk_uses_filtered_times(self) -> None:
        config = SensorConfig(format="Quaternions")
        buf = io.StringIO()
        with sensor_writer(buf, config) as w:
            times1 = np.array(["2020-01-01T00:00:01"], dtype="datetime64[ms]")
            data1 = np.array([[0.0, 0.0, 0.0, 1.0]])
            w.write_chunk(times1, data1)
            # First row invalid (filtered), second valid and after chunk 1
            times2 = np.array(
                ["2020-01-01T00:00:00.500", "2020-01-01T00:00:02"], dtype="datetime64[ms]"
            )
            data2 = np.array(
                [
                    [np.nan, 0.0, 0.0, 1.0],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            )
            w.write_chunk(times2, data2)

    def test_epsec_format(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        config = SensorConfig(
            format="Quaternions",
            time_format="EpSec",
            scenario_epoch=epoch,
        )
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T01:00:00.000"], dtype="datetime64[ms]"
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        output = buf.getvalue()
        assert "EpSec" in output

    @pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
    def test_time_precision(self, unit: str) -> None:
        config = SensorConfig(format="Quaternions")
        times = np.array(
            ["2020-01-01T00:00:00", "2020-01-01T01:00:00"], dtype=f"datetime64[{unit}]"
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        write_sensor(buf, config, times, data)
        output = buf.getvalue()
        assert "2020-01-01T00:00:00.000" in output
        assert "2020-01-01T01:00:00.000" in output
