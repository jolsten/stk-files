from typing import Literal, Optional, Tuple

import numpy as np
from dateutil.parser import parse as parse_datetime

InputDType = Literal["u1", "u2"]


def parse_line(
    value: str, sep: Optional[str] = None
) -> Tuple[np.datetime64, np.ndarray]:
    t, *d = value.split(sep)
    dt = parse_datetime(t)
    time = np.datetime64(dt.isoformat(sep="T", timespec="microseconds"))
    data = np.array(d, dtype=">f4")
    return time, data
