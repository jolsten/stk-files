# Attitude Files (.a)

Write and read STK attitude data files using `write_attitude`, `read_attitude`,
and the streaming `attitude_writer`.

## AttitudeConfig

All attitude operations require an `AttitudeConfig`:

```python
from stk_files import AttitudeConfig

config = AttitudeConfig(
    format="Quaternions",           # required — see Formats below
    coordinate_axes="ICRF",         # default: "ICRF"
    time_format="ISO-YMD",          # "ISO-YMD" (default) or "EpSec"
    scenario_epoch=None,            # required when time_format="EpSec"
    central_body=None,              # "Earth" or "Moon"
    coordinate_axes_epoch=None,     # required for epoch-dependent axes
    interpolation_method=None,      # "Lagrange" or "Hermite"
    interpolation_order=None,       # integer
    message_level=None,             # "Errors", "Warnings", or "Verbose"
    sequence=None,                  # required for EulerAngles/YPRAngles
)
```

The config is frozen (immutable) after creation.

### Coordinate axes

Any string is accepted. Epoch-dependent axes (`MeanOfEpoch`, `TrueOfEpoch`,
`TEMEOfEpoch`, `AlignmentAtEpoch`) require `coordinate_axes_epoch` to be set.

### Time format

- **ISO-YMD** (default) — timestamps written as `2024-01-01T00:00:00.000`.
- **EpSec** — seconds since `scenario_epoch`. The epoch must be provided.

## Formats

| Format | Data columns | Notes |
|--------|-------------|-------|
| `Quaternions` | 4 | Scalar-last (x, y, z, w) |
| `QuatScalarFirst` | 4 | Scalar-first (w, x, y, z) |
| `EulerAngles` | 3 | Degrees; requires `sequence` |
| `YPRAngles` | 3 | Degrees; requires `sequence` |
| `DCM` | 9 | Row-major direction cosine matrix |
| `ECFVector` | 3 | Earth-centered fixed direction vector |
| `ECIVector` | 3 | Earth-centered inertial direction vector |

### Rotation sequences

Angle-based formats require a `sequence` parameter:

- **EulerAngles**: `121`, `123`, `131`, `132`, `212`, `213`, `231`, `232`,
  `312`, `313`, `321`, `323`
- **YPRAngles**: `123`, `132`, `213`, `231`, `312`, `321`

## Writing

### One-shot

```python
import numpy as np
from stk_files import AttitudeConfig, write_attitude

times = np.array([
    "2024-01-01T00:00:00",
    "2024-01-01T00:01:00",
    "2024-01-01T00:02:00",
], dtype="datetime64[ms]")

quats = np.array([
    [0.0, 0.0, 0.0, 1.0],
    [0.0, 0.0, 0.1, 0.995],
    [0.0, 0.0, 0.2, 0.980],
])

config = AttitudeConfig(format="Quaternions")

with open("satellite.a", "w") as f:
    write_attitude(f, config, times, quats)
```

### Parameters

```python
write_attitude(
    stream,              # any text IO (file, StringIO, stdout)
    config,              # AttitudeConfig
    times,               # NDArray[datetime64[ms]]
    data,                # NDArray[floating] — shape (N, cols)
    strict=False,        # True: raise on invalid data; False: filter silently
    max_rate=None,       # max angular rate (rad/s) between consecutive rows
    presorted=False,     # True: skip sorting (data must already be time-sorted)
    chunk_size=None,     # rows per write chunk (None = all at once)
)
```

### Euler angles

```python
config = AttitudeConfig(format="EulerAngles", sequence=321)

angles = np.array([
    [10.0, 20.0, 30.0],
    [11.0, 21.0, 31.0],
])

with open("euler.a", "w") as f:
    write_attitude(f, config, times, angles)
```

### EpSec time format

```python
epoch = np.datetime64("2024-01-01T00:00:00", "ms")
config = AttitudeConfig(
    format="Quaternions",
    time_format="EpSec",
    scenario_epoch=epoch,
)

with open("epsec.a", "w") as f:
    write_attitude(f, config, times, quats)
```

### Streaming (chunked writes)

For large datasets, use `attitude_writer` to write data in chunks:

```python
from stk_files import AttitudeConfig, attitude_writer

config = AttitudeConfig(format="Quaternions")

with open("satellite.a", "w") as f, attitude_writer(f, config) as writer:
    for times_chunk, data_chunk in data_source:
        writer.write_chunk(times_chunk, data_chunk)
```

Each `write_chunk` call validates, formats, and appends one block of data.
Cross-chunk time ordering is enforced.

## Reading

```python
from stk_files import read_attitude

with open("satellite.a") as f:
    config, times, data = read_attitude(f)
```

Returns a tuple of `(AttitudeConfig, times, data)`. The config is reconstructed
from the file header, so round-tripping preserves all settings.

## Validation

By default, invalid rows are silently filtered out. Set `strict=True` to raise
instead.

**Checks performed:**

- All values must be finite (no NaN or Inf)
- Quaternions must have unit norm (tolerance: 1e-6)
- Angles must be in range [-180, 360]
- If `max_rate` is set, angular rate between consecutive rows is checked
- Timestamps must not contain NaT or duplicates

```python
# Strict: raises ValueError on first invalid row
write_attitude(f, config, times, quats, strict=True)

# Non-strict (default): filters invalid rows, writes the rest
write_attitude(f, config, times, quats)

# Rate limiting: flag rows where rotation exceeds 5 rad/s
write_attitude(f, config, times, quats, max_rate=5.0)
```

## Pandas / Polars

Timestamps and data columns from DataFrames are automatically coerced to numpy:

```python
import pandas as pd
from stk_files import AttitudeConfig, write_attitude

df = pd.read_csv("attitude.csv", parse_dates=["time"])
config = AttitudeConfig(format="Quaternions")

with open("satellite.a", "w") as f:
    write_attitude(f, config, df["time"], df[["q1", "q2", "q3", "q4"]])
```

Polars DataFrames and Series work the same way.
