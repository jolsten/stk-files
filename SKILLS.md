# stk-files — User Skill File

## What is stk-files?

A Python library for generating and reading STK (Systems Tool Kit) external data files. It supports four file types: attitude (`.a`), ephemeris (`.e`), sensor pointing (`.sp`), and interval lists (`.int`).

## Installation

```bash
pip install stk-files               # base (numpy + click)
pip install stk-files[pandas]       # + pandas support
pip install stk-files[polars]       # + polars support
```

Requires Python >=3.9, numpy >=2.0.

## Public API at a Glance

All imports come from `stk_files`:

```python
from stk_files import (
    # Attitude
    AttitudeConfig, write_attitude, read_attitude, attitude_writer,
    # Ephemeris
    EphemerisConfig, write_ephemeris, read_ephemeris, ephemeris_writer,
    # Sensor
    SensorConfig, write_sensor, read_sensor, sensor_writer,
    # Intervals
    Interval, IntervalConfig, write_interval, read_interval,
    # Availability
    detect_availability, write_availability,
    # Errors
    STKParseError,
    # Type literals (for type hints)
    AttitudeFormat, EphemerisFormat, SensorFormat, TimeFormat,
    CoordinateAxes, CentralBody, MessageLevel, InterpolationMethod,
    EulerSequence, YPRSequence, AzElSequence, RotationSequence,
)
```

---

## Attitude Files (.a)

### Formats and Column Counts

| Format | Columns | Column Order | Notes |
|--------|---------|--------------|-------|
| `"Quaternions"` | 4 | x, y, z, w | Scalar-last; validated for unit norm |
| `"QuatScalarFirst"` | 4 | w, x, y, z | Scalar-first; validated for unit norm |
| `"EulerAngles"` | 3 | rotA, rotB, rotC | Degrees. Requires `sequence`. Columns map to axes via sequence (e.g. sequence=321 means rotA=axis3, rotB=axis2, rotC=axis1) |
| `"YPRAngles"` | 3 | yaw, pitch, roll | Degrees. Requires `sequence`. Data is always Y-P-R order; sequence controls rotation order, not column order |
| `"DCM"` | 9 | m11, m12, m13, m21, m22, m23, m31, m32, m33 | Row-major, ref-to-body. No orthogonality validation |
| `"ECFVector"` | 3 | x, y, z | Earth-Centered Fixed unit vector |
| `"ECIVector"` | 3 | x, y, z | Earth-Centered Inertial unit vector |

### AttitudeConfig Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `format` | str | *required* | One of the formats above |
| `coordinate_axes` | str | `"ICRF"` | e.g. `"Fixed"`, `"J2000"`, `"ICRF"`, `"TrueOfDate"` |
| `time_format` | str | `"ISO-YMD"` | `"ISO-YMD"` or `"EpSec"` |
| `scenario_epoch` | `np.datetime64 \| None` | `None` | Required when `time_format="EpSec"` |
| `central_body` | `str \| None` | `None` | `"Earth"` or `"Moon"` |
| `coordinate_axes_epoch` | `np.datetime64 \| None` | `None` | Required for epoch-dependent axes (`MeanOfEpoch`, `TrueOfEpoch`, `TEMEOfEpoch`, `AlignmentAtEpoch`) |
| `interpolation_method` | `str \| None` | `None` | `"Lagrange"` or `"Hermite"` |
| `interpolation_order` | `int \| None` | `None` | Interpolation samples minus 1 |
| `sequence` | `int \| None` | `None` | **Required** for `EulerAngles` and `YPRAngles`. Raises `ValueError` if omitted. |
| `message_level` | `str \| None` | `None` | `"Errors"`, `"Warnings"`, or `"Verbose"` |

### Euler Sequences (for EulerAngles)
121, 123, 131, 132, 212, 213, 231, 232, 312, 313, 321, 323

### YPR Sequences (for YPRAngles)
123, 132, 213, 231, 312, 321

### Example: Write Quaternion Attitude

```python
import numpy as np
from stk_files import AttitudeConfig, write_attitude

times = np.array(["2024-01-01T00:00:00", "2024-01-01T01:00:00"], dtype="datetime64[ms]")
quats = np.array([
    [0.0, 0.0, 0.0, 1.0],      # scalar-last: x, y, z, w
    [0.1, 0.0, 0.0, 0.995],
])

config = AttitudeConfig(format="Quaternions", coordinate_axes="ICRF")

with open("attitude.a", "w") as f:
    write_attitude(f, config, times, quats)
```

### Example: Write EulerAngles Attitude

```python
import numpy as np
from stk_files import AttitudeConfig, write_attitude

base = np.datetime64("2024-01-01T00:00:00", "ms")
times = base + np.arange(30) * np.timedelta64(1, "m")  # 30 points, 1-minute spacing
angles = np.column_stack([
    np.linspace(0, 45, 30),   # rotA (degrees)
    np.linspace(0, 10, 30),   # rotB
    np.linspace(0, 5, 30),    # rotC
])

config = AttitudeConfig(format="EulerAngles", sequence=321, coordinate_axes="Fixed")

with open("euler.a", "w") as f:
    write_attitude(f, config, times, angles)
```

### write_attitude Signature

```python
write_attitude(
    stream,       # file object or StringIO
    config,       # AttitudeConfig
    times,        # (N,) datetime64[ms] array
    data,         # (N, cols) float array — cols must match format
    *,
    strict=False,     # True: raise ValueError on invalid rows; False: filter them
    max_rate=None,    # max angular rate (rad/s) between consecutive rows
    presorted=False,  # skip sorting if times already sorted
    chunk_size=None,  # rows per write block
)
```

---

## Ephemeris Files (.e)

### Formats and Column Counts

| Format | Columns | Column Order | Units |
|--------|---------|--------------|-------|
| `"TimePos"` | 3 | x, y, z | km (or m, depending on STK scenario) |
| `"TimePosVel"` | 6 | x, y, z, vx, vy, vz | km, km/s |
| `"TimePosVelAcc"` | 9 | x, y, z, vx, vy, vz, ax, ay, az | km, km/s, km/s^2 |
| `"LLATimePos"` | 3 | lat, lon, alt | **deg, deg, meters** |
| `"LLATimePosVel"` | 6 | lat, lon, alt, latDot, lonDot, altDot | deg, deg, m, deg/s, deg/s, m/s |

### EphemerisConfig Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `format` | str | *required* | One of the formats above |
| `coordinate_system` | str | `"ICRF"` | **Note: `coordinate_system`**, not `coordinate_axes` |
| `time_format` | str | `"ISO-YMD"` | `"ISO-YMD"` or `"EpSec"` |
| `scenario_epoch` | `np.datetime64 \| None` | `None` | Required when `time_format="EpSec"` |
| `central_body` | `str \| None` | `None` | `"Earth"` or `"Moon"` |
| `coordinate_system_epoch` | `np.datetime64 \| None` | `None` | Optional epoch reference |
| `interpolation_method` | `str \| None` | `None` | `"Lagrange"` or `"Hermite"` |
| `interpolation_order` | `int \| None` | `None` | Interpolation samples minus 1 |
| `message_level` | `str \| None` | `None` | `"Errors"`, `"Warnings"`, or `"Verbose"` |

### Example: Write Ephemeris

```python
import numpy as np
from stk_files import EphemerisConfig, write_ephemeris

times = np.array(["2024-01-01T00:00:00", "2024-01-01T01:00:00"], dtype="datetime64[ms]")
data = np.array([
    [7000.0, 0.0, 0.0, 0.0, 7.5, 0.0],      # x,y,z (km), vx,vy,vz (km/s)
    [6999.0, 100.0, 0.0, -0.1, 7.5, 0.0],
])

config = EphemerisConfig(format="TimePosVel", coordinate_system="ICRF")
with open("satellite.e", "w") as f:
    write_ephemeris(f, config, times, data)
```

### Example: Write LLA Ephemeris

```python
import numpy as np
from stk_files import EphemerisConfig, write_ephemeris

base = np.datetime64("2024-01-01T00:00:00", "ms")
times = base + np.arange(20) * np.timedelta64(60, "s")
data = np.column_stack([
    np.linspace(40.0, 41.0, 20),     # latitude (degrees)
    np.linspace(-74.0, -73.0, 20),   # longitude (degrees)
    np.full(20, 400_000.0),          # altitude (meters)
])

config = EphemerisConfig(format="LLATimePos")
with open("ground_track.e", "w") as f:
    write_ephemeris(f, config, times, data)
```

---

## Sensor Pointing Files (.sp)

### Formats
All attitude formats plus `"AzElAngles"` (2 columns: azimuth, elevation in degrees).

### SensorConfig Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `format` | str | *required* | Any attitude format + `"AzElAngles"` |
| `coordinate_axes` | `str \| None` | `None` | Optional (unlike AttitudeConfig where it defaults to `"ICRF"`) |
| `time_format` | str | `"ISO-YMD"` | `"ISO-YMD"` or `"EpSec"` |
| `scenario_epoch` | `np.datetime64 \| None` | `None` | Required when `time_format="EpSec"` |
| `central_body` | `str \| None` | `None` | `"Earth"` or `"Moon"` |
| `sequence` | `int \| None` | `None` | **Required** for all angle formats including `AzElAngles`. Valid AzEl sequences: 323, 213. Raises `ValueError` if omitted. |
| `message_level` | `str \| None` | `None` | `"Errors"`, `"Warnings"`, or `"Verbose"` |

### Example: Write Sensor

```python
import numpy as np
from stk_files import SensorConfig, write_sensor

times = np.array(["2024-01-01T00:00:00", "2024-01-01T01:00:00"], dtype="datetime64[ms]")
data = np.array([[45.0, 30.0], [46.0, 31.0]])  # azimuth, elevation (degrees)

config = SensorConfig(format="AzElAngles", sequence=323)
with open("sensor.sp", "w") as f:
    write_sensor(f, config, times, data)
```

---

## Interval Lists (.int)

### Interval Dataclass

```python
from stk_files import Interval
import numpy as np

interval = Interval(
    start=np.datetime64("2024-01-01T00:00:00", "ms"),
    end=np.datetime64("2024-01-01T01:00:00", "ms"),
    data="Optional metadata string",  # defaults to ""
)
```

### Example: Write Intervals

```python
from stk_files import Interval, write_interval
import numpy as np

intervals = [
    Interval(
        start=np.datetime64("2024-01-01T00:00:00", "ms"),
        end=np.datetime64("2024-01-01T01:00:00", "ms"),
    ),
    Interval(
        start=np.datetime64("2024-01-01T02:00:00", "ms"),
        end=np.datetime64("2024-01-01T03:00:00", "ms"),
        data="Contact window",
    ),
]

with open("access.int", "w") as f:
    write_interval(f, intervals)
```

---

## Availability Detection

Detect contiguous data spans from timestamps:

```python
from stk_files import detect_availability, write_availability
import numpy as np

times = np.array([...], dtype="datetime64[ms]")

# Returns list of (start, end) tuples — list[tuple[np.datetime64, np.datetime64]]
spans = detect_availability(times, max_gap=np.timedelta64(60, "s"), min_points=2)

# Or write directly as an interval file (also accepts min_points, default=2)
with open("availability.int", "w") as f:
    write_availability(f, times, max_gap=np.timedelta64(60, "s"), min_points=2)
```

### write_availability Signature

```python
write_availability(
    stream,       # file object
    times,        # (N,) datetime64[ms] array
    max_gap,      # np.timedelta64 — max gap before splitting into new span
    min_points=2, # minimum data points required per span
)
```

Internally calls `detect_availability` then `write_interval`.

---

## Reading Files

All file types support reading. Raises `STKParseError` on malformed files.

```python
from stk_files import read_attitude, read_ephemeris, read_sensor, read_interval, STKParseError

with open("attitude.a") as f:
    config, times, data = read_attitude(f)      # returns (AttitudeConfig, ndarray, ndarray)

with open("ephemeris.e") as f:
    config, times, data = read_ephemeris(f)

with open("sensor.sp") as f:
    config, times, data = read_sensor(f)

with open("access.int") as f:
    config, intervals = read_interval(f)        # returns (IntervalConfig, list[Interval])
```

---

## Streaming / Chunked Writes

For large datasets, use the context-manager writers to avoid loading everything into memory:

```python
from stk_files import AttitudeConfig, attitude_writer

config = AttitudeConfig(format="Quaternions")

with open("large.a", "w") as f, attitude_writer(f, config) as writer:
    for chunk_times, chunk_data in data_source:
        writer.write_chunk(chunk_times, chunk_data)
```

Same pattern for `ephemeris_writer` and `sensor_writer`.

**Cross-chunk constraint:** Times must be strictly increasing across chunks. If a chunk starts at or before the previous chunk's last time, `ValueError` is raised with the message: `"chunk starts at {t} but previous chunk ended at {prev_t}"`.

---

## DataFrame Support

pandas and polars Series/DataFrames are accepted directly for `times` and `data` — automatic coercion to numpy:

```python
import pandas as pd
from stk_files import EphemerisConfig, write_ephemeris

df = pd.read_csv("orbit.csv", parse_dates=["time"])
config = EphemerisConfig(format="TimePosVel")

with open("sat.e", "w") as f:
    write_ephemeris(f, config, df["time"], df[["x", "y", "z", "vx", "vy", "vz"]])
```

Works the same with polars DataFrames/Series.

---

## Validation

- **`strict=False`** (default): invalid rows silently filtered out
- **`strict=True`**: raises `ValueError` on any invalid data

Validation checks per format:
- **Quaternions**: unit norm (±1e-6)
- **Angles** (Euler, YPR, AzEl): -180 <= angle <= 360 degrees
- **DCM**: shape only (9 columns); no orthogonality check
- **All formats**: NaN/Inf filtered, NaT/duplicate times raise errors, row count must match between times and data, column count must match format

### Config Validation (raises ValueError on construction)

```python
AttitudeConfig(format="EulerAngles")                     # ValueError: requires sequence
AttitudeConfig(format="Quaternions", time_format="EpSec") # ValueError: requires scenario_epoch
AttitudeConfig(format="Quaternions", coordinate_axes="MeanOfEpoch")  # ValueError: requires coordinate_axes_epoch
SensorConfig(format="AzElAngles")                        # ValueError: requires sequence
```

---

## Time Generation Tips

```python
import numpy as np

# Generate N evenly-spaced timestamps
base = np.datetime64("2024-01-01T00:00:00", "ms")
times = base + np.arange(100) * np.timedelta64(1, "s")     # 100 points, 1-second spacing
times = base + np.arange(50) * np.timedelta64(60, "s")     # 50 points, 1-minute spacing

# From ISO strings
times = np.array(["2024-01-01T00:00:00", "2024-01-01T01:00:00"], dtype="datetime64[ms]")
```

---

## CLI

```bash
stk-files attitude Quaternions -o out.a < data.txt
stk-files ephemeris TimePosVel -o out.e --axes ICRF < data.txt
stk-files sensor AzElAngles -o out.sp -s 323 < data.txt
stk-files interval -o out.int < data.txt
```

Input: whitespace-delimited rows (first column = ISO-YMD timestamp, rest = numeric data). Use `-d ","` for CSV.

Common options: `-o FILE`, `-a/--axes AXES`, `-b/--central-body BODY`, `-t/--time-format FMT`, `-e/--scenario-epoch EPOCH`, `-s/--sequence SEQ`, `-d/--delimiter DELIM`.
