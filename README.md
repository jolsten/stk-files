# stk-files

Python library and CLI for generating and reading
[STK](https://www.ansys.com/products/missions/ansys-stk) external data files.

Supports attitude (`.a`), ephemeris (`.e`), sensor pointing (`.sp`), and
interval list (`.int`) file formats.

## Installation

```bash
pip install stk-files
```

Optional DataFrame support:

```bash
pip install stk-files[pandas]
pip install stk-files[polars]
```

## Quick start

### Write an ephemeris file

```python
import numpy as np
from stk_files import EphemerisConfig, write_ephemeris

times = np.array(["2024-01-01T00:00:00", "2024-01-01T00:01:00"], dtype="datetime64[ms]")
data = np.array([
    [7000.0, 0.0, 0.0, 0.0, 7.5, 0.0],
    [6999.0, 100.0, 0.0, -0.1, 7.5, 0.0],
])

config = EphemerisConfig(format="TimePosVel", coordinate_system="ICRF")

with open("satellite.e", "w") as f:
    write_ephemeris(f, config, times, data)
```

### Write an attitude file

```python
import numpy as np
from stk_files import AttitudeConfig, write_attitude

times = np.array(["2024-01-01T00:00:00", "2024-01-01T00:01:00"], dtype="datetime64[ms]")
quats = np.array([
    [0.0, 0.0, 0.0, 1.0],
    [0.0, 0.0, 0.1, 0.995],
])

config = AttitudeConfig(format="Quaternions")

with open("satellite.a", "w") as f:
    write_attitude(f, config, times, quats)
```

### Read a file back

```python
from stk_files import read_ephemeris

with open("satellite.e") as f:
    config, times, data = read_ephemeris(f)
```

`read_attitude`, `read_sensor`, and `read_interval` work the same way.

### Streaming writes

For large datasets that don't fit in memory, use the chunked writer context
managers:

```python
from stk_files import EphemerisConfig, ephemeris_writer

config = EphemerisConfig(format="TimePosVel")

with open("satellite.e", "w") as f, ephemeris_writer(f, config) as writer:
    for times_chunk, data_chunk in data_source:
        writer.write_chunk(times_chunk, data_chunk)
```

### Interval lists

```python
import numpy as np
from stk_files import Interval, write_interval

intervals = [
    Interval(
        start=np.datetime64("2024-01-01T00:00:00", "ms"),
        end=np.datetime64("2024-01-01T01:00:00", "ms"),
    ),
]

with open("access.int", "w") as f:
    write_interval(f, intervals)
```

### Availability detection

Detect contiguous data spans and write them as an interval file:

```python
import numpy as np
from stk_files import detect_availability, write_availability

spans = detect_availability(times, max_gap=np.timedelta64(60, "s"))

with open("availability.int", "w") as f:
    write_availability(f, times, max_gap=np.timedelta64(60, "s"))
```

### Pandas and Polars

Pass DataFrame columns directly -- they are coerced to numpy automatically:

```python
import pandas as pd
from stk_files import EphemerisConfig, write_ephemeris

df = pd.read_csv("orbit.csv", parse_dates=["time"])
config = EphemerisConfig(format="TimePosVel")

with open("satellite.e", "w") as f:
    write_ephemeris(f, config, df["time"], df[["x", "y", "z", "vx", "vy", "vz"]])
```

### Validation

Data is validated before writing. Use `strict=True` to raise on invalid rows,
or leave the default (`strict=False`) to silently filter them:

```python
# Raises ValueError on non-unit quaternions
write_attitude(f, config, times, quats, strict=True)

# Filters out non-unit quaternions and continues
write_attitude(f, config, times, quats, strict=False)
```

Set `max_rate` to flag excessive angular/position rates:

```python
write_attitude(f, config, times, quats, max_rate=10.0)
```

## CLI

The `stk-files` CLI reads whitespace-delimited data from stdin.

```bash
# Ephemeris
cat orbit.txt | stk-files ephemeris TimePosVel -o satellite.e

# Attitude quaternions
cat attitude.txt | stk-files attitude Quaternions -o satellite.a --axes ICRF

# Sensor pointing
cat pointing.txt | stk-files sensor AzElAngles -o sensor.sp -s 323

# Interval list
cat intervals.txt | stk-files interval -o access.int
```

Use `stk-files --help` or `stk-files <command> --help` for full option details.

## Documentation

- [Attitude files](docs/attitude.md) -- config options, formats, sequences, validation
- [Ephemeris files](docs/ephemeris.md) -- config options, formats, coordinate systems
- [Sensor pointing files](docs/sensor.md) -- config options, formats, AzElAngles
- [Interval list files](docs/interval.md) -- intervals, metadata, availability detection
- [CLI reference](docs/cli.md) -- all subcommands, options, and input formats

## Supported formats

**Attitude** (`AttitudeFormat`): `Quaternions`, `QuatScalarFirst`, `EulerAngles`,
`YPRAngles`, `DCM`, `ECFVector`, `ECIVector`

**Ephemeris** (`EphemerisFormat`): `TimePos`, `TimePosVel`, `TimePosVelAcc`,
`LLATimePos`, `LLATimePosVel`

**Sensor** (`SensorFormat`): All attitude formats plus `AzElAngles`

## License

MIT
