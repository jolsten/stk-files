# Sensor Pointing Files (.sp)

Write and read STK sensor pointing data files using `write_sensor`,
`read_sensor`, and the streaming `sensor_writer`.

## SensorConfig

```python
from stk_files import SensorConfig

config = SensorConfig(
    format="AzElAngles",            # required — see Formats below
    coordinate_axes=None,           # e.g. "ICRF" (optional for sensor files)
    time_format="ISO-YMD",          # "ISO-YMD" (default) or "EpSec"
    scenario_epoch=None,            # required when time_format="EpSec"
    central_body=None,              # "Earth" or "Moon"
    message_level=None,             # "Errors", "Warnings", or "Verbose"
    sequence=None,                  # required for angle-based formats
)
```

The config is frozen (immutable) after creation.

Unlike `AttitudeConfig`, sensor configs do not support `coordinate_axes_epoch`
or interpolation settings.

## Formats

Sensor files support all attitude formats plus `AzElAngles`:

| Format | Data columns | Notes |
|--------|-------------|-------|
| `Quaternions` | 4 | Scalar-last (x, y, z, w) |
| `QuatScalarFirst` | 4 | Scalar-first (w, x, y, z) |
| `EulerAngles` | 3 | Degrees; requires `sequence` |
| `YPRAngles` | 3 | Degrees; requires `sequence` |
| `AzElAngles` | 2 | Azimuth and elevation in degrees; requires `sequence` |
| `DCM` | 9 | Row-major direction cosine matrix |
| `ECFVector` | 3 | Earth-centered fixed direction vector |
| `ECIVector` | 3 | Earth-centered inertial direction vector |

### Rotation sequences

- **EulerAngles**: `121`, `123`, `131`, `132`, `212`, `213`, `231`, `232`,
  `312`, `313`, `321`, `323`
- **YPRAngles**: `123`, `132`, `213`, `231`, `312`, `321`
- **AzElAngles**: `323`, `213`

## Writing

### One-shot

```python
import numpy as np
from stk_files import SensorConfig, write_sensor

times = np.array([
    "2024-01-01T00:00:00",
    "2024-01-01T00:01:00",
], dtype="datetime64[ms]")

azel = np.array([
    [45.0, 30.0],
    [46.0, 31.0],
])

config = SensorConfig(format="AzElAngles", sequence=323)

with open("sensor.sp", "w") as f:
    write_sensor(f, config, times, azel)
```

### Parameters

```python
write_sensor(
    stream,              # any text IO (file, StringIO, stdout)
    config,              # SensorConfig
    times,               # NDArray[datetime64[ms]]
    data,                # NDArray[floating] — shape (N, cols)
    strict=False,        # True: raise on invalid data; False: filter silently
    max_rate=None,       # max angular rate (rad/s) between consecutive rows
    presorted=False,     # True: skip sorting (data must already be time-sorted)
    chunk_size=None,     # rows per write chunk (None = all at once)
)
```

### Quaternion sensor pointing

```python
config = SensorConfig(format="Quaternions")

quats = np.array([
    [0.0, 0.0, 0.0, 1.0],
    [0.0, 0.0, 0.1, 0.995],
])

with open("sensor.sp", "w") as f:
    write_sensor(f, config, times, quats)
```

### Streaming (chunked writes)

```python
from stk_files import SensorConfig, sensor_writer

config = SensorConfig(format="AzElAngles", sequence=323)

with open("sensor.sp", "w") as f, sensor_writer(f, config) as writer:
    for times_chunk, data_chunk in data_source:
        writer.write_chunk(times_chunk, data_chunk)
```

## Reading

```python
from stk_files import read_sensor

with open("sensor.sp") as f:
    config, times, data = read_sensor(f)
```

Returns `(SensorConfig, times, data)`.

## Validation

By default, invalid rows are silently filtered out. Set `strict=True` to raise.

**Checks performed:**

- All values must be finite (no NaN or Inf)
- Quaternions must have unit norm (tolerance: 1e-6)
- Angles must be in range [-180, 360]
- If `max_rate` is set, angular rate between consecutive rows is checked
  (not supported for `AzElAngles`)
- Timestamps must not contain NaT or duplicates

> **Note:** Rate checking is not supported for `AzElAngles` because 2 columns
> cannot be converted to quaternions for angular rate computation.

## Pandas / Polars

Timestamps and data columns from DataFrames are automatically coerced to numpy:

```python
import polars as pl
from stk_files import SensorConfig, write_sensor

df = pl.read_csv("pointing.csv")
config = SensorConfig(format="AzElAngles", sequence=323)

with open("sensor.sp", "w") as f:
    write_sensor(f, config, df["time"], df[["az", "el"]])
```
