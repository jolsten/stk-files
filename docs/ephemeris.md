# Ephemeris Files (.e)

Write and read STK ephemeris data files using `write_ephemeris`,
`read_ephemeris`, and the streaming `ephemeris_writer`.

## EphemerisConfig

```python
from stk_files import EphemerisConfig

config = EphemerisConfig(
    format="TimePosVel",            # required — see Formats below
    coordinate_system="ICRF",       # default: "ICRF"
    time_format="ISO-YMD",          # "ISO-YMD" (default) or "EpSec"
    scenario_epoch=None,            # required when time_format="EpSec"
    central_body=None,              # "Earth" or "Moon"
    coordinate_system_epoch=None,   # required for epoch-dependent coordinate systems
    interpolation_method=None,      # "Lagrange" or "Hermite"
    interpolation_order=None,       # integer
    message_level=None,             # "Errors", "Warnings", or "Verbose"
)
```

The config is frozen (immutable) after creation.

### Coordinate system

Any string is accepted. Epoch-dependent systems (`MeanOfEpoch`, `TrueOfEpoch`,
`TEMEOfEpoch`, `AlignmentAtEpoch`) require `coordinate_system_epoch`.

## Formats

| Format | Data columns | Description |
|--------|-------------|-------------|
| `TimePos` | 3 | Position only (x, y, z) in km |
| `TimePosVel` | 6 | Position + velocity (x, y, z, vx, vy, vz) in km and km/s |
| `TimePosVelAcc` | 9 | Position + velocity + acceleration in km, km/s, km/s^2 |
| `LLATimePos` | 3 | Lat (deg), lon (deg), alt (km) |
| `LLATimePosVel` | 6 | Lat, lon, alt + velocity components |

## Writing

### One-shot

```python
import numpy as np
from stk_files import EphemerisConfig, write_ephemeris

times = np.array([
    "2024-01-01T00:00:00",
    "2024-01-01T00:01:00",
], dtype="datetime64[ms]")

data = np.array([
    [7000.0, 0.0, 0.0, 0.0, 7.5, 0.0],
    [6999.0, 100.0, 0.0, -0.1, 7.5, 0.0],
])

config = EphemerisConfig(format="TimePosVel", coordinate_system="ICRF")

with open("satellite.e", "w") as f:
    write_ephemeris(f, config, times, data)
```

### Parameters

```python
write_ephemeris(
    stream,              # any text IO (file, StringIO, stdout)
    config,              # EphemerisConfig
    times,               # NDArray[datetime64[ms]]
    data,                # NDArray[floating] — shape (N, cols)
    strict=False,        # True: raise on invalid data; False: filter silently
    max_rate=None,       # max position change rate (km/s) between rows
    presorted=False,     # True: skip sorting (data must already be time-sorted)
    chunk_size=None,     # rows per write chunk (None = all at once)
)
```

### Position only

```python
config = EphemerisConfig(format="TimePos")

pos = np.array([
    [7000.0, 0.0, 0.0],
    [6999.0, 100.0, 0.0],
])

with open("satellite.e", "w") as f:
    write_ephemeris(f, config, times, pos)
```

### LLA coordinates

```python
config = EphemerisConfig(format="LLATimePos", central_body="Earth")

lla = np.array([
    [40.0, -75.0, 400.0],   # lat, lon, alt
    [41.0, -74.0, 401.0],
])

with open("satellite.e", "w") as f:
    write_ephemeris(f, config, times, lla)
```

### EpSec time format

```python
epoch = np.datetime64("2024-01-01T00:00:00", "ms")
config = EphemerisConfig(
    format="TimePosVel",
    time_format="EpSec",
    scenario_epoch=epoch,
)

with open("epsec.e", "w") as f:
    write_ephemeris(f, config, times, data)
```

### Streaming (chunked writes)

For large datasets, use `ephemeris_writer` to write data in chunks.
`NumberOfEphemerisPoints` is omitted from the header in chunked mode because
the total count is unknown upfront. STK treats this field as optional.

```python
from stk_files import EphemerisConfig, ephemeris_writer

config = EphemerisConfig(format="TimePosVel")

with open("satellite.e", "w") as f, ephemeris_writer(f, config) as writer:
    for times_chunk, data_chunk in data_source:
        writer.write_chunk(times_chunk, data_chunk)
```

## Reading

```python
from stk_files import read_ephemeris

with open("satellite.e") as f:
    config, times, data = read_ephemeris(f)
```

Returns `(EphemerisConfig, times, data)`. The config is reconstructed from the
file header.

## Validation

By default, invalid rows are silently filtered out. Set `strict=True` to raise.

**Checks performed:**

- All values must be finite (no NaN or Inf)
- If `max_rate` is set, position change rate (km/s) between consecutive rows
  is checked
- Timestamps must not contain NaT or duplicates

```python
# Strict: raises ValueError on first invalid row
write_ephemeris(f, config, times, data, strict=True)

# Rate limiting: flag rows where position changes faster than 100 km/s
write_ephemeris(f, config, times, data, max_rate=100.0)
```

## Pandas / Polars

Timestamps and data columns from DataFrames are automatically coerced to numpy:

```python
import pandas as pd
from stk_files import EphemerisConfig, write_ephemeris

df = pd.read_csv("orbit.csv", parse_dates=["time"])
config = EphemerisConfig(format="TimePosVel")

with open("satellite.e", "w") as f:
    write_ephemeris(f, config, df["time"], df[["x", "y", "z", "vx", "vy", "vz"]])
```

Polars DataFrames and Series work the same way.
