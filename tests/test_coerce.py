"""Tests for pandas/polars coercion in write functions."""

import io

import numpy as np
import pandas as pd
import polars as pl
import pytest

from stk_files.attitude import AttitudeConfig, write_attitude
from stk_files.ephemeris import EphemerisConfig, write_ephemeris
from stk_files.sensor import SensorConfig, write_sensor


@pytest.fixture()
def times_np() -> np.ndarray:
    return np.array(
        ["2024-01-01T00:00:00.000", "2024-01-01T01:00:00.000"],
        dtype="datetime64[ms]",
    )


@pytest.fixture()
def quat_np() -> np.ndarray:
    return np.array([[0.0, 0.0, 0.0, 1.0], [0.5, 0.5, 0.5, 0.5]])


@pytest.fixture()
def pos_np() -> np.ndarray:
    return np.array([[1000.0, 2000.0, 3000.0], [4000.0, 5000.0, 6000.0]])


# --- coerce_times / coerce_data unit tests ---

class TestCoerceTimes:
    def test_pandas_series(self, times_np: np.ndarray) -> None:
        from stk_files._coerce import coerce_times

        ts = pd.Series(pd.to_datetime(["2024-01-01T00:00:00", "2024-01-01T01:00:00"]))
        result = coerce_times(ts)
        assert isinstance(result, np.ndarray)
        assert np.issubdtype(result.dtype, np.datetime64)
        assert result.shape == (2,)

    def test_polars_series(self, times_np: np.ndarray) -> None:
        from stk_files._coerce import coerce_times

        from datetime import datetime

        ts = pl.Series(
            "t",
            [datetime(2024, 1, 1), datetime(2024, 1, 1, 1, 0, 0)],
            dtype=pl.Datetime("ms"),
        )
        result = coerce_times(ts)
        assert isinstance(result, np.ndarray)
        assert np.issubdtype(result.dtype, np.datetime64)
        assert result.shape == (2,)

    def test_numpy_passthrough(self, times_np: np.ndarray) -> None:
        from stk_files._coerce import coerce_times

        result = coerce_times(times_np)
        assert result is times_np


class TestCoerceData:
    def test_pandas_dataframe(self, quat_np: np.ndarray) -> None:
        from stk_files._coerce import coerce_data

        df = pd.DataFrame(quat_np, columns=["q1", "q2", "q3", "q4"])
        result = coerce_data(df)
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 4)
        np.testing.assert_array_almost_equal(result, quat_np)

    def test_pandas_series(self) -> None:
        from stk_files._coerce import coerce_data

        s = pd.Series([1.0, 2.0, 3.0])
        result = coerce_data(s)
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 1)

    def test_polars_dataframe(self, quat_np: np.ndarray) -> None:
        from stk_files._coerce import coerce_data

        df = pl.DataFrame({"q1": quat_np[:, 0], "q2": quat_np[:, 1],
                           "q3": quat_np[:, 2], "q4": quat_np[:, 3]})
        result = coerce_data(df)
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 4)
        np.testing.assert_array_almost_equal(result, quat_np)

    def test_polars_series(self) -> None:
        from stk_files._coerce import coerce_data

        s = pl.Series("x", [1.0, 2.0, 3.0])
        result = coerce_data(s)
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 1)

    def test_numpy_passthrough(self, quat_np: np.ndarray) -> None:
        from stk_files._coerce import coerce_data

        result = coerce_data(quat_np)
        assert result is quat_np


# --- Integration: pandas input to write functions ---

class TestPandasIntegration:
    def test_write_attitude_pandas(self, times_np: np.ndarray, quat_np: np.ndarray) -> None:
        config = AttitudeConfig(format="Quaternions")
        times_pd = pd.Series(pd.to_datetime(times_np))
        data_pd = pd.DataFrame(quat_np, columns=["q1", "q2", "q3", "q4"])

        buf = io.StringIO()
        write_attitude(buf, config, times_pd, data_pd)
        output = buf.getvalue()
        assert "BEGIN Attitude" in output
        assert "END Attitude" in output

    def test_write_ephemeris_pandas(self, times_np: np.ndarray, pos_np: np.ndarray) -> None:
        config = EphemerisConfig(format="TimePos")
        times_pd = pd.Series(pd.to_datetime(times_np))
        data_pd = pd.DataFrame(pos_np, columns=["x", "y", "z"])

        buf = io.StringIO()
        write_ephemeris(buf, config, times_pd, data_pd)
        output = buf.getvalue()
        assert "BEGIN Ephemeris" in output
        assert "END Ephemeris" in output

    def test_write_sensor_pandas(self, times_np: np.ndarray, quat_np: np.ndarray) -> None:
        config = SensorConfig(format="Quaternions")
        times_pd = pd.Series(pd.to_datetime(times_np))
        data_pd = pd.DataFrame(quat_np, columns=["q1", "q2", "q3", "q4"])

        buf = io.StringIO()
        write_sensor(buf, config, times_pd, data_pd)
        output = buf.getvalue()
        assert "BEGIN Attitude" in output
        assert "END Attitude" in output


# --- Integration: polars input to write functions ---

class TestPolarsIntegration:
    def test_write_attitude_polars(self, times_np: np.ndarray, quat_np: np.ndarray) -> None:
        config = AttitudeConfig(format="Quaternions")
        times_pl = pl.Series("t", times_np, dtype=pl.Datetime("ms"))
        data_pl = pl.DataFrame({"q1": quat_np[:, 0], "q2": quat_np[:, 1],
                                "q3": quat_np[:, 2], "q4": quat_np[:, 3]})

        buf = io.StringIO()
        write_attitude(buf, config, times_pl, data_pl)
        output = buf.getvalue()
        assert "BEGIN Attitude" in output
        assert "END Attitude" in output

    def test_write_ephemeris_polars(self, times_np: np.ndarray, pos_np: np.ndarray) -> None:
        config = EphemerisConfig(format="TimePos")
        times_pl = pl.Series("t", times_np, dtype=pl.Datetime("ms"))
        data_pl = pl.DataFrame({"x": pos_np[:, 0], "y": pos_np[:, 1], "z": pos_np[:, 2]})

        buf = io.StringIO()
        write_ephemeris(buf, config, times_pl, data_pl)
        output = buf.getvalue()
        assert "BEGIN Ephemeris" in output
        assert "END Ephemeris" in output

    def test_write_sensor_polars(self, times_np: np.ndarray, quat_np: np.ndarray) -> None:
        config = SensorConfig(format="Quaternions")
        times_pl = pl.Series("t", times_np, dtype=pl.Datetime("ms"))
        data_pl = pl.DataFrame({"q1": quat_np[:, 0], "q2": quat_np[:, 1],
                                "q3": quat_np[:, 2], "q4": quat_np[:, 3]})

        buf = io.StringIO()
        write_sensor(buf, config, times_pl, data_pl)
        output = buf.getvalue()
        assert "BEGIN Attitude" in output
        assert "END Attitude" in output


# --- Verify output matches numpy baseline ---

class TestOutputParity:
    def test_pandas_matches_numpy(self, times_np: np.ndarray, quat_np: np.ndarray) -> None:
        config = AttitudeConfig(format="Quaternions")

        buf_np = io.StringIO()
        write_attitude(buf_np, config, times_np, quat_np)

        times_pd = pd.Series(pd.to_datetime(times_np))
        data_pd = pd.DataFrame(quat_np)
        buf_pd = io.StringIO()
        write_attitude(buf_pd, config, times_pd, data_pd)

        assert buf_np.getvalue() == buf_pd.getvalue()

    def test_polars_matches_numpy(self, times_np: np.ndarray, quat_np: np.ndarray) -> None:
        config = AttitudeConfig(format="Quaternions")

        buf_np = io.StringIO()
        write_attitude(buf_np, config, times_np, quat_np)

        times_pl = pl.Series("t", times_np, dtype=pl.Datetime("ms"))
        data_pl = pl.DataFrame({"q1": quat_np[:, 0], "q2": quat_np[:, 1],
                                "q3": quat_np[:, 2], "q4": quat_np[:, 3]})
        buf_pl = io.StringIO()
        write_attitude(buf_pl, config, times_pl, data_pl)

        assert buf_np.getvalue() == buf_pl.getvalue()
