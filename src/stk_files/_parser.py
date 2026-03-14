"""Low-level parsing utilities for reading STK external data files."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


class STKParseError(ValueError):
    """Raised when an STK file cannot be parsed."""


def parse_datetime(value: str) -> np.datetime64:
    """Parse an ISO-YMD datetime string to ``np.datetime64[ms]``."""
    return np.datetime64(value.strip(), "ms")


def parse_header(
    lines: list[str],
    sentinel_prefix: str,
) -> tuple[dict[str, str], str, int]:
    """Parse an STK file header.

    Returns ``(header_dict, format_string, first_data_line_index)``.
    The *sentinel_prefix* is ``"AttitudeTime"`` for attitude/sensor files
    or ``"Ephemeris"`` for ephemeris files.
    """
    if not lines:
        raise STKParseError("empty file")

    if not lines[0].strip().startswith("stk.v."):
        raise STKParseError(
            f"line 1: expected 'stk.v.' version header, got {lines[0]!r}"
        )

    header: dict[str, str] = {}
    for idx in range(1, len(lines)):
        stripped = lines[idx].strip()
        if not stripped:
            continue
        if stripped.startswith("BEGIN "):
            continue
        if stripped.startswith(sentinel_prefix):
            fmt = stripped[len(sentinel_prefix) :]
            return header, fmt, idx + 1
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            header[parts[0]] = parts[1].strip()
        elif len(parts) == 1:
            header[parts[0]] = ""

    raise STKParseError(f"no '{sentinel_prefix}*' data sentinel found in header")


def parse_data_section(
    lines: list[str],
    start: int,
    time_format: str,
    expected_cols: int,
    scenario_epoch: np.datetime64 | None = None,
) -> tuple[NDArray[np.datetime64], NDArray[np.floating]]:
    """Parse the data rows of an STK file into numpy arrays.

    Reads from ``lines[start:]`` until a line starting with ``"END"``
    is encountered.
    """
    time_list: list[np.datetime64] = []
    data_list: list[list[float]] = []

    for idx in range(start, len(lines)):
        stripped = lines[idx].strip()
        if not stripped:
            continue
        if stripped.startswith("END"):
            break

        parts = stripped.split()
        if len(parts) < 1 + expected_cols:
            raise STKParseError(
                f"line {idx + 1}: expected {1 + expected_cols} columns, got {len(parts)}"
            )

        time_str = parts[0]
        if time_format == "EpSec":
            if scenario_epoch is None:
                raise STKParseError("EpSec data requires a ScenarioEpoch")
            ms = round(float(time_str) * 1000)
            time_list.append(scenario_epoch + np.timedelta64(ms, "ms"))
        else:
            time_list.append(np.datetime64(time_str, "ms"))

        try:
            data_list.append([float(x) for x in parts[1 : 1 + expected_cols]])
        except ValueError as exc:
            raise STKParseError(f"line {idx + 1}: invalid numeric value: {exc}") from None

    if not time_list:
        return (
            np.array([], dtype="datetime64[ms]"),
            np.empty((0, expected_cols), dtype=np.float64),
        )

    return (
        np.array(time_list, dtype="datetime64[ms]"),
        np.array(data_list, dtype=np.float64),
    )


_QUOTED_RE = re.compile(r'"([^"]*)"')


def parse_interval_file(
    lines: list[str],
) -> list[tuple[np.datetime64, np.datetime64, str]]:
    """Parse an STK interval list file.

    Returns a list of ``(start, end, data_string)`` tuples.
    """
    if not lines:
        raise STKParseError("empty file")

    if not lines[0].strip().startswith("stk.v."):
        raise STKParseError(
            f"line 1: expected 'stk.v.' version header, got {lines[0]!r}"
        )

    # Find BEGIN Intervals
    data_start = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "BEGIN Intervals":
            data_start = idx + 1
            break

    if data_start < 0:
        raise STKParseError("no 'BEGIN Intervals' found")

    result: list[tuple[np.datetime64, np.datetime64, str]] = []
    for idx in range(data_start, len(lines)):
        stripped = lines[idx].strip()
        if not stripped:
            continue
        if stripped.startswith("END"):
            break

        match_iter = _QUOTED_RE.finditer(stripped)
        first = next(match_iter, None)
        second = next(match_iter, None)
        if first is None or second is None:
            raise STKParseError(
                f"line {idx + 1}: expected two quoted timestamps"
            )
        start = np.datetime64(first.group(1), "ms")
        end = np.datetime64(second.group(1), "ms")
        after = stripped[second.end() :].strip()
        result.append((start, end, after))

    return result
