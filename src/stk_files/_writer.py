from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Iterator


class RowWriter:
    """Writes formatted time+data rows to a stream."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def write_row(self, formatted_time: str, formatted_data: str) -> None:
        print(formatted_time, formatted_data, file=self._stream)

    def write_block(
        self,
        time_strings: list[str],
        data_strings: list[str],
        batch_size: int = 50_000,
    ) -> None:
        """Write pre-formatted time+data string lists in batched I/O."""
        for start in range(0, len(time_strings), batch_size):
            end = min(start + batch_size, len(time_strings))
            chunk = "\n".join(
                f"{t} {d}" for t, d in zip(time_strings[start:end], data_strings[start:end])
            )
            self._stream.write(chunk)
            self._stream.write("\n")


@contextlib.contextmanager
def stk_writer(
    stream: TextIO,
    header_lines: list[str],
    footer_lines: list[str],
) -> Iterator[RowWriter]:
    """Context manager that writes header on enter, footer on exit."""
    writer = RowWriter(stream)
    for line in header_lines:
        print(line, file=stream)
    try:
        yield writer
    finally:
        for line in footer_lines:
            print(line, file=stream)
