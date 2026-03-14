# Interval List Files (.int)

Write and read STK interval list files using `write_interval` and
`read_interval`.

## IntervalConfig

`IntervalConfig` has no configurable fields -- it produces the standard STK
interval list header. You can omit it entirely:

```python
from stk_files import write_interval

# config is optional — a default is created automatically
write_interval(f, intervals)
```

## Interval

Each interval is represented by an `Interval` dataclass:

```python
from stk_files import Interval

interval = Interval(
    start=np.datetime64("2024-01-01T00:00:00", "ms"),  # required
    end=np.datetime64("2024-01-01T01:00:00", "ms"),    # required
    data="",                                            # optional metadata string
)
```

## Writing

```python
import numpy as np
from stk_files import Interval, write_interval

intervals = [
    Interval(
        start=np.datetime64("2024-01-01T00:00:00", "ms"),
        end=np.datetime64("2024-01-01T01:00:00", "ms"),
    ),
    Interval(
        start=np.datetime64("2024-01-01T02:00:00", "ms"),
        end=np.datetime64("2024-01-01T03:00:00", "ms"),
    ),
]

with open("access.int", "w") as f:
    write_interval(f, intervals)
```

### With metadata

Each interval can carry an optional `data` string that is written after the
time range:

```python
intervals = [
    Interval(
        start=np.datetime64("2024-01-01T00:00:00", "ms"),
        end=np.datetime64("2024-01-01T01:00:00", "ms"),
        data="Ground Station Alpha",
    ),
]

with open("access.int", "w") as f:
    write_interval(f, intervals)
```

## Reading

```python
from stk_files import read_interval

with open("access.int") as f:
    config, intervals = read_interval(f)

for iv in intervals:
    print(iv.start, iv.end, iv.data)
```

Returns `(IntervalConfig, list[Interval])`.

## Validation

Intervals are validated before writing:

- Neither `start` nor `end` may be NaT
- `start` must be strictly before `end`

Invalid intervals always raise `ValueError` (there is no filter mode for
intervals).

## Availability detection

`detect_availability` and `write_availability` build interval lists from
timestamp arrays by detecting gaps in the data:

```python
import numpy as np
from stk_files import detect_availability, write_availability

times = np.array([...], dtype="datetime64[ms]")  # sorted timestamps
max_gap = np.timedelta64(60, "s")

# Get spans as (start, end) tuples
spans = detect_availability(times, max_gap)

# Or write directly to an interval file
with open("availability.int", "w") as f:
    write_availability(f, times, max_gap)
```

### Parameters

```python
detect_availability(
    times,               # NDArray[datetime64] — must be sorted
    max_gap,             # timedelta64 — gap threshold for splitting spans
    min_points=2,        # minimum points for a span to be included
)
```

A new span starts whenever the gap between consecutive timestamps exceeds
`max_gap`. Spans with fewer than `min_points` data points are excluded.
