import argparse
import fileinput
import sys

from stkfiles.cli.utils import parse_line
from stkfiles.files import AttitudeFile

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="data2a")
    parser.add_argument("format", type=str, help="attitude data type")
    parser.add_argument("-a", "-axes", type=str, default="ICRF", help="coordinate axes")
    parser.add_argument(
        "-e", "--epoch", type=str, default=None, help="coordinate axes epoch"
    )
    args = parser.parse_args()

    stream = sys.stdout

    with AttitudeFile(
        stream,
        format=args.format,
        coordinate_axes=args.axes,
        coordinate_axes_epoch=args.epoch,
    ) as a:
        time, data = [], []
        for line in fileinput.input("-"):
            time, data = parse_line(line.strip())
            a.write_data(time, data)
