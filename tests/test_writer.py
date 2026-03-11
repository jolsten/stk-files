import io

from stk_files._writer import RowWriter, stk_writer


class TestRowWriter:
    def test_write_row(self) -> None:
        buf = io.StringIO()
        w = RowWriter(buf)
        w.write_row("2020-01-01T00:00:00.000", "+0.000 +0.000 +0.000 +1.000")
        assert buf.getvalue() == "2020-01-01T00:00:00.000 +0.000 +0.000 +0.000 +1.000\n"

    def test_multiple_rows(self) -> None:
        buf = io.StringIO()
        w = RowWriter(buf)
        w.write_row("t1", "d1")
        w.write_row("t2", "d2")
        lines = buf.getvalue().strip().split("\n")
        assert lines == ["t1 d1", "t2 d2"]


class TestStkWriter:
    def test_header_and_footer(self) -> None:
        buf = io.StringIO()
        with stk_writer(buf, ["HEADER1", "HEADER2"], ["FOOTER"]) as w:
            w.write_row("time", "data")
        output = buf.getvalue()
        lines = output.strip().split("\n")
        assert lines[0] == "HEADER1"
        assert lines[1] == "HEADER2"
        assert lines[2] == "time data"
        assert lines[3] == "FOOTER"

    def test_empty_body(self) -> None:
        buf = io.StringIO()
        with stk_writer(buf, ["H"], ["F"]):
            pass
        output = buf.getvalue()
        lines = output.strip().split("\n")
        assert lines == ["H", "F"]

    def test_footer_written_on_exception(self) -> None:
        buf = io.StringIO()
        try:
            with stk_writer(buf, ["H"], ["F"]) as w:
                w.write_row("t", "d")
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        output = buf.getvalue()
        assert "F" in output
