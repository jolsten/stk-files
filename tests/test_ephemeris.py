import io

import numpy as np
import pytest

from stk_files.ephemeris import EphemerisConfig, write_ephemeris


class TestEphemerisConfig:
    def test_basic_config(self) -> None:
        config = EphemerisConfig(format="TimePosVel")
        lines = config.header_lines(num_points=10)
        assert lines[0] == "stk.v.12.0"
        assert lines[1] == "BEGIN Ephemeris"
        assert any("NumberOfEphemerisPoints" in x for x in lines)
        assert lines[-1] == "EphemerisTimePosVel"

    def test_uses_coordinate_system(self) -> None:
        config = EphemerisConfig(format="TimePos")
        lines = config.header_lines()
        assert any("CoordinateSystem" in x for x in lines)
        assert not any("CoordinateAxes" in x for x in lines)

    def test_epsec_requires_epoch(self) -> None:
        with pytest.raises(ValueError, match="scenario_epoch"):
            EphemerisConfig(format="TimePos", time_format="EpSec")

    def test_footer(self) -> None:
        config = EphemerisConfig(format="TimePos")
        assert config.footer_lines() == ["END Ephemeris"]


class TestWriteEphemeris:
    def test_timeposvel_output(self) -> None:
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
        assert "stk.v.12.0" in output
        assert "BEGIN Ephemeris" in output
        assert "END Ephemeris" in output
        assert "EphemerisTimePosVel" in output
        assert "NumberOfEphemerisPoints  2" in output

    def test_timepos_output(self) -> None:
        config = EphemerisConfig(format="TimePos", coordinate_system="Fixed")
        times = np.array(["2020-01-01T00:00:00.000"], dtype="datetime64[ms]")
        data = np.array([[7000000.0, 0.0, 0.0]])
        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        output = buf.getvalue()
        assert "EphemerisTimePos" in output
        assert "CoordinateSystem        Fixed" in output

    def test_wrong_columns_raises(self) -> None:
        config = EphemerisConfig(format="TimePosVel")
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[1.0, 2.0, 3.0]])  # 3 cols, need 6
        buf = io.StringIO()
        with pytest.raises(ValueError, match="columns"):
            write_ephemeris(buf, config, times, data)

    @pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
    def test_time_precision(self, unit: str) -> None:
        config = EphemerisConfig(format="TimePos")
        times = np.array(
            ["2020-01-01T00:00:00", "2020-01-01T01:00:00"], dtype=f"datetime64[{unit}]"
        )
        data = np.array([[7e6, 0.0, 0.0], [7e6, 1e3, 0.0]])
        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        output = buf.getvalue()
        assert "2020-01-01T00:00:00.000" in output
        assert "2020-01-01T01:00:00.000" in output

    def test_unsorted_data_gets_sorted(self) -> None:
        config = EphemerisConfig(format="TimePos")
        times = np.array(
            ["2020-01-01T02:00:00", "2020-01-01T00:00:00", "2020-01-01T01:00:00"],
            dtype="datetime64[ms]",
        )
        data = np.array([[3.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        output = buf.getvalue()
        lines = [line for line in output.strip().split("\n") if "2020-01-01T" in line]
        timestamps = [line.split()[0] for line in lines]
        assert timestamps == sorted(timestamps)

    def test_nan_filtered_nonstrict(self) -> None:
        config = EphemerisConfig(format="TimePos")
        times = np.array(["2020-01-01", "2020-01-02"], dtype="datetime64[ms]")
        data = np.array([[np.nan, 0.0, 0.0], [1.0, 2.0, 3.0]])
        buf = io.StringIO()
        write_ephemeris(buf, config, times, data)
        output = buf.getvalue()
        assert "NumberOfEphemerisPoints  1" in output

    def test_strict_nan_raises(self) -> None:
        config = EphemerisConfig(format="TimePos")
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[np.nan, 0.0, 0.0]])
        buf = io.StringIO()
        with pytest.raises(ValueError, match="non-finite"):
            write_ephemeris(buf, config, times, data, strict=True)

    def test_all_invalid_raises_empty(self) -> None:
        config = EphemerisConfig(format="TimePos")
        times = np.array(["2020-01-01"], dtype="datetime64[ms]")
        data = np.array([[np.nan, 0.0, 0.0]])
        buf = io.StringIO()
        with pytest.raises(ValueError, match="no valid data rows"):
            write_ephemeris(buf, config, times, data)

    def test_max_rate_filters(self) -> None:
        config = EphemerisConfig(format="TimePos")
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
        buf = io.StringIO()
        write_ephemeris(buf, config, times, data, max_rate=100.0)
        output = buf.getvalue()
        # At least the spike row is filtered out
        assert "NumberOfEphemerisPoints  4" not in output
