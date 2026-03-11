from click.testing import CliRunner

from stk_files.cli import main


class TestAttitudeCli:
    def test_quaternion_stdin(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000 0.0 0.0 0.0 1.0\n"
        result = runner.invoke(main, ["attitude", "Quaternions"], input=input_data)
        assert result.exit_code == 0
        assert "stk.v.11.0" in result.output
        assert "AttitudeTimeQuaternions" in result.output
        assert "END Attitude" in result.output

    def test_euler_with_sequence(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000 10.0 20.0 30.0\n"
        result = runner.invoke(
            main, ["attitude", "EulerAngles", "--sequence", "321"], input=input_data
        )
        assert result.exit_code == 0
        assert "AttitudeTimeEulerAngles" in result.output

    def test_output_to_file(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        runner = CliRunner()
        outfile = str(tmp_path / "test.a")
        input_data = "2020-01-01T00:00:00.000 0.0 0.0 0.0 1.0\n"
        result = runner.invoke(main, ["attitude", "Quaternions", "-o", outfile], input=input_data)
        assert result.exit_code == 0
        with open(outfile) as f:
            content = f.read()
        assert "stk.v.11.0" in content


class TestEphemerisCli:
    def test_timeposvel(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000 7000000.0 0.0 0.0 0.0 7500.0 0.0\n"
        result = runner.invoke(main, ["ephemeris", "TimePosVel"], input=input_data)
        assert result.exit_code == 0
        assert "EphemerisTimePosVel" in result.output
        assert "END Ephemeris" in result.output


class TestIntervalCli:
    def test_interval_pairs(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000 2020-01-01T01:00:00.000\n"
        result = runner.invoke(main, ["interval"], input=input_data)
        assert result.exit_code == 0
        assert "BEGIN IntervalList" in result.output
        assert '"2020-01-01T00:00:00.000"' in result.output


class TestSensorCli:
    def test_azel(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000 45.0 30.0\n"
        result = runner.invoke(
            main, ["sensor", "AzElAngles", "--sequence", "323"], input=input_data
        )
        assert result.exit_code == 0
        assert "AttitudeTimeAzElAngles" in result.output


class TestCliErrorHandling:
    def test_invalid_datetime(self) -> None:
        runner = CliRunner()
        input_data = "not-a-date 0.0 0.0 0.0 1.0\n"
        result = runner.invoke(main, ["attitude", "Quaternions"], input=input_data)
        assert result.exit_code != 0
        assert "invalid datetime" in result.output

    def test_invalid_number(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000 0.0 abc 0.0 1.0\n"
        result = runner.invoke(main, ["attitude", "Quaternions"], input=input_data)
        assert result.exit_code != 0
        assert "invalid number" in result.output

    def test_invalid_format_rejected(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000 0.0 0.0 0.0 1.0\n"
        result = runner.invoke(main, ["attitude", "BadFormat"], input=input_data)
        assert result.exit_code != 0
        assert "BadFormat" in result.output  # click shows invalid choice

    def test_invalid_interval_datetime(self) -> None:
        runner = CliRunner()
        input_data = "not-a-date 2020-01-01T01:00:00.000\n"
        result = runner.invoke(main, ["interval"], input=input_data)
        assert result.exit_code != 0
        assert "invalid datetime" in result.output

    def test_interval_single_column(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000\n"
        result = runner.invoke(main, ["interval"], input=input_data)
        assert result.exit_code != 0
        assert "at least 2 columns" in result.output

    def test_comments_and_blank_lines_skipped(self) -> None:
        runner = CliRunner()
        input_data = (
            "# comment line\n"
            "\n"
            "2020-01-01T00:00:00.000 0.0 0.0 0.0 1.0\n"
            "# another comment\n"
            "2020-01-01T01:00:00.000 0.0 0.0 0.0 1.0\n"
        )
        result = runner.invoke(main, ["attitude", "Quaternions"], input=input_data)
        assert result.exit_code == 0
        assert "AttitudeTimeQuaternions" in result.output

    def test_invalid_ephemeris_format_rejected(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000 1.0 2.0 3.0\n"
        result = runner.invoke(main, ["ephemeris", "NotAFormat"], input=input_data)
        assert result.exit_code != 0

    def test_invalid_sensor_format_rejected(self) -> None:
        runner = CliRunner()
        input_data = "2020-01-01T00:00:00.000 1.0 2.0\n"
        result = runner.invoke(main, ["sensor", "NotAFormat"], input=input_data)
        assert result.exit_code != 0
