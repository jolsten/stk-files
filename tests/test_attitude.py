import io

import numpy as np
import pytest
from hypothesis import given, settings

from stk_files.attitude import AttitudeConfig, attitude_writer, write_attitude
from tests.strategies import sorted_datetime64_arrays


class TestAttitudeConfig:
    def test_basic_quaternion_config(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        lines = config.header_lines()
        assert lines[0] == "stk.v.11.0"
        assert lines[1] == "BEGIN Attitude"
        assert lines[-1] == "AttitudeTimeQuaternions"

    def test_euler_requires_sequence(self) -> None:
        with pytest.raises(ValueError, match="requires a sequence"):
            AttitudeConfig(format="EulerAngles")

    def test_euler_with_sequence(self) -> None:
        config = AttitudeConfig(format="EulerAngles", sequence=321)
        lines = config.header_lines()
        assert any("Sequence" in line for line in lines)
        assert lines[-1] == "AttitudeTimeEulerAngles"

    def test_epsec_requires_epoch(self) -> None:
        with pytest.raises(ValueError, match="scenario_epoch"):
            AttitudeConfig(format="Quaternions", time_format="EpSec")

    def test_epoch_dependent_axes_requires_epoch(self) -> None:
        with pytest.raises(ValueError, match="coordinate_axes_epoch"):
            AttitudeConfig(format="Quaternions", coordinate_axes="MeanOfEpoch")

    def test_footer(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        assert config.footer_lines() == ["END Attitude"]


class TestWriteAttitude:
    def test_quaternion_output(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T01:00:00.000"], dtype="datetime64[ms]"
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.5, 0.5, 0.5, 0.5]])
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()
        assert "stk.v.11.0" in output
        assert "BEGIN Attitude" in output
        assert "END Attitude" in output
        assert "AttitudeTimeQuaternions" in output

    def test_filters_invalid_quaternions_by_default(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(["2020-01-01", "2020-01-02", "2020-01-03"], dtype="datetime64[ms]")
        data = np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [2.0, 2.0, 2.0, 2.0],  # invalid
                [0.5, 0.5, 0.5, 0.5],
            ]
        )
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()
        lines = [
            line
            for line in output.strip().split("\n")
            if line
            and not line.startswith(
                (
                    "stk",
                    "BEGIN",
                    "END",
                    "Time",
                    "Coordinate",
                    "Attitude",
                    "Message",
                    "Interpolation",
                    "Sequence",
                    "Scenario",
                    "Central",
                )
            )
        ]
        assert len(lines) == 2  # only valid rows

    def test_strict_raises_on_invalid(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[2.0, 2.0, 2.0, 2.0]])
        buf = io.StringIO()
        with pytest.raises(ValueError, match="non-unit"):
            write_attitude(buf, config, times, data, strict=True)

    @given(
        times=sorted_datetime64_arrays(min_size=5, max_size=20),
    )
    @settings(max_examples=20)
    def test_hypothesis_quaternions(self, times: np.ndarray) -> None:  # type: ignore[type-arg]
        n = len(times)
        # Generate valid quaternions
        data = np.zeros((n, 4))
        data[:, 3] = 1.0  # identity quaternion
        config = AttitudeConfig(format="Quaternions")
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()
        assert "stk.v.11.0" in output
        assert "END Attitude" in output

    def test_euler_angles(self) -> None:
        config = AttitudeConfig(format="EulerAngles", sequence=123)
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[10.0, 20.0, 30.0]])
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()
        assert "AttitudeTimeEulerAngles" in output
        assert "Sequence" in output

    def test_epsec_format(self) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00.000", "ms")
        config = AttitudeConfig(
            format="Quaternions",
            time_format="EpSec",
            scenario_epoch=epoch,
        )
        times = np.array(
            ["2020-01-01T00:00:00.000", "2020-01-01T01:00:00.000"], dtype="datetime64[ms]"
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()
        assert "EpSec" in output

    @pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
    def test_iso_ymd_time_precision(self, unit: str) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(
            ["2020-01-01T00:00:00", "2020-01-01T01:00:00"], dtype=f"datetime64[{unit}]"
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()
        assert "2020-01-01T00:00:00.000" in output
        assert "2020-01-01T01:00:00.000" in output

    @pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
    def test_epsec_time_precision(self, unit: str) -> None:
        epoch = np.datetime64("2020-01-01T00:00:00", unit)
        config = AttitudeConfig(
            format="Quaternions",
            time_format="EpSec",
            scenario_epoch=epoch,
        )
        times = np.array(
            ["2020-01-01T00:00:00", "2020-01-01T01:00:00"], dtype=f"datetime64[{unit}]"
        )
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()
        lines = output.strip().split("\n")
        data_lines = [line for line in lines if line.strip() and line.strip()[0].isdigit()]
        assert len(data_lines) == 2
        assert float(data_lines[0].split()[0]) == 0.0
        assert float(data_lines[1].split()[0]) == 3600.0

    def test_unsorted_data_gets_sorted(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(
            ["2020-01-01T02:00:00", "2020-01-01T00:00:00", "2020-01-01T01:00:00"],
            dtype="datetime64[ms]",
        )
        data = np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [0.0, 0.0, 0.0, 1.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()
        lines = [line for line in output.strip().split("\n") if "2020-01-01T" in line]
        timestamps = [line.split()[0] for line in lines]
        assert timestamps == sorted(timestamps)

    def test_nat_raises(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(["2020-01-01", "NaT"], dtype="datetime64[ms]")
        data = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        with pytest.raises(ValueError, match="NaT"):
            write_attitude(buf, config, times, data)

    def test_nan_filtered_nonstrict(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[np.nan, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        buf = io.StringIO()
        write_attitude(buf, config, times, data)
        output = buf.getvalue()
        lines = [line for line in output.strip().split("\n") if "2020-01-0" in line]
        assert len(lines) == 1

    def test_all_invalid_raises_empty(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[2.0, 2.0, 2.0, 2.0]])  # all invalid
        buf = io.StringIO()
        with pytest.raises(ValueError, match="no valid data rows"):
            write_attitude(buf, config, times, data)

    def test_chunk_writer_cross_chunk_uses_filtered_times(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        buf = io.StringIO()
        with attitude_writer(buf, config) as w:
            # Chunk 1: valid row at T=1
            times1 = np.array(["2020-01-01T00:00:01"], dtype="datetime64[ms]")
            data1 = np.array([[0.0, 0.0, 0.0, 1.0]])
            w.write_chunk(times1, data1)
            # Chunk 2: first row is invalid (will be filtered), second is valid at T=2
            times2 = np.array(
                ["2020-01-01T00:00:00.500", "2020-01-01T00:00:02"], dtype="datetime64[ms]"
            )
            data2 = np.array(
                [
                    [np.nan, 0.0, 0.0, 1.0],  # filtered out
                    [0.0, 0.0, 0.0, 1.0],  # valid, after chunk 1
                ]
            )
            # Should succeed because after filtering, first surviving time is T=2 > T=1
            w.write_chunk(times2, data2)

    def test_max_rate_filters(self) -> None:
        config = AttitudeConfig(format="Quaternions")
        # Small rotation (~0.01 rad) over 1s, then a huge 180 deg jump, then same small
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
        buf = io.StringIO()
        write_attitude(buf, config, times, data, max_rate=0.5)
        output = buf.getvalue()
        lines = [line for line in output.strip().split("\n") if "2020-01-01T" in line]
        # Row 2 (the spike) dropped; row 3 may also be dropped due to single-pass
        assert len(lines) < 4  # at least the spike is filtered
