import argparse
import fileinput
import sys
from typing import Literal, Optional, Tuple

import numpy as np
from dateutil.parser import parse as parse_datetime

from stkfiles.files import AttitudeFile, EphemerisFile, IntervalFile

InputDType = Literal["u1", "u2"]


def parse_line(
    value: str, sep: Optional[str] = None
) -> Tuple[np.datetime64, np.ndarray]:
    t, *d = value.split(sep)
    dt = parse_datetime(t)
    time = np.datetime64(dt.isoformat(sep="T", timespec="microseconds"))
    data = np.array(d, dtype=">f4")
    return time, data


def main():
    parser = argparse.ArgumentParser(prog="data2stk")
    subparsers = parser.add_subparsers(required=True)

    parser_a = subparsers.add_parser("attitude", help="create an attitude (.a) file")
    parser_a.add_argument("format", type=str, help="attitude data type")
    parser_a.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        default=None,
        help="output file. default is stdout",
    )
    parser_a.add_argument(
        "-a", "--axes", type=str, default="ICRF", help="coordinate axes"
    )
    parser_a.add_argument(
        "-e",
        "--axes-epoch",
        type=parse_datetime,
        default=None,
        help="coordinate axes epoch",
    )
    parser_a.add_argument(
        "-s", "--sequence", type=str, default=None, help="rotation sequence"
    )
    parser_a.set_defaults(func=attitude)

    parser_e = subparsers.add_parser("ephemeris", help="create an ephemeris (.e) file")
    parser_e.add_argument("format", type=str, help="attitude data type")
    parser_e.add_argument(
        "-o",
        "--output",
        default=None,
        type=argparse.FileType("w"),
        help="output file. default is stdout",
    )
    parser_e.add_argument(
        "-a", "--axes", type=str, default="ICRF", help="coordinate axes"
    )
    parser_e.add_argument(
        "-e",
        "--axes-epoch",
        type=parse_datetime,
        default=None,
        help="coordinate axes epoch",
    )
    parser_e.set_defaults(func=ephemeris)

    parser_i = subparsers.add_parser("interval", help="create an interval (.int) file")
    parser_i.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("w"),
        help="output file. default is stdout",
    )
    parser_i.set_defaults(func=interval)

    args = parser.parse_args()
    if args.output:
        args.stream = args.output
    else:
        args.stream = sys.stdout
    args.func(args)  # Call the function for the selected subparser


def attitude(args):
    with AttitudeFile(
        args.stream,
        format=args.format,
        coordinate_axes=args.axes,
        coordinate_axes_epoch=args.axes_epoch,
        sequence=args.sequence,
    ) as a:
        time, data = [], []
        for line in fileinput.input("-"):
            time, data = parse_line(line.strip())
            a.write_batch(time, data)


def ephemeris(args):
    with EphemerisFile(
        args.stream,
        format=args.format,
        coordinate_axes=args.axes,
        coordinate_axes_epoch=args.epoch,
    ) as a:
        time, data = [], []
        for line in fileinput.input("-"):
            time, data = parse_line(line.strip())
            a.write_batch(time, data)


def interval(args):
    with IntervalFile(args.stream) as a:
        time, data = [], []
        for line in fileinput.input("-"):
            time, data = parse_line(line.strip())
            a.write_batch(time, data)


if __name__ == "__main__":
    main()
