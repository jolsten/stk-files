# CLI

The `stk-files` command reads whitespace-delimited data from stdin and writes
STK files. Each file type has its own subcommand.

```
stk-files <command> [options]
```

## Common conventions

- Data is read from **stdin**, one row per line
- The first column is always a timestamp (ISO-8601 format)
- Remaining columns are numeric data values
- Lines starting with `#` and blank lines are skipped
- Output goes to **stdout** by default; use `-o` to write to a file
- Use `-d` to set a custom column delimiter (default: whitespace)

## attitude

Generate an STK attitude file (`.a`).

```
stk-files attitude FORMAT [options] < data.txt
```

**FORMAT** is one of: `DCM`, `ECFVector`, `ECIVector`, `EulerAngles`,
`QuatScalarFirst`, `Quaternions`, `YPRAngles`

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o`, `--output FILE` | Output file | stdout |
| `-a`, `--axes AXES` | Coordinate axes | `ICRF` |
| `--axes-epoch DATETIME` | Coordinate axes epoch | |
| `-b`, `--central-body BODY` | Central body (`Earth`, `Moon`) | |
| `-t`, `--time-format FMT` | `ISO-YMD` or `EpSec` | `ISO-YMD` |
| `-e`, `--scenario-epoch DT` | Scenario epoch (required for EpSec) | |
| `--interpolation-method M` | `Lagrange` or `Hermite` | |
| `--interpolation-order N` | Interpolation order | |
| `-s`, `--sequence SEQ` | Rotation sequence (required for angle formats) | |
| `-d`, `--delimiter DELIM` | Column delimiter | whitespace |

### Examples

```bash
# Quaternion attitude from a space-delimited file
cat attitude.txt | stk-files attitude Quaternions -o satellite.a

# Euler angles with sequence 321
cat euler.txt | stk-files attitude EulerAngles -s 321 -o satellite.a

# Custom axes and central body
cat attitude.txt | stk-files attitude Quaternions -a J2000 -b Earth -o satellite.a

# EpSec time format
cat attitude.txt | stk-files attitude Quaternions -t EpSec -e "2024-01-01T00:00:00" -o satellite.a
```

### Input format

```
2024-01-01T00:00:00.000 0.0 0.0 0.0 1.0
2024-01-01T00:01:00.000 0.0 0.0 0.1 0.995
```

## ephemeris

Generate an STK ephemeris file (`.e`).

```
stk-files ephemeris FORMAT [options] < data.txt
```

**FORMAT** is one of: `LLATimePos`, `LLATimePosVel`, `TimePos`, `TimePosVel`,
`TimePosVelAcc`

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o`, `--output FILE` | Output file | stdout |
| `-a`, `--axes AXES` | Coordinate system | `ICRF` |
| `--axes-epoch DATETIME` | Coordinate system epoch | |
| `-b`, `--central-body BODY` | Central body (`Earth`, `Moon`) | |
| `-t`, `--time-format FMT` | `ISO-YMD` or `EpSec` | `ISO-YMD` |
| `-e`, `--scenario-epoch DT` | Scenario epoch (required for EpSec) | |
| `--interpolation-method M` | `Lagrange` or `Hermite` | |
| `--interpolation-order N` | Interpolation order | |
| `-d`, `--delimiter DELIM` | Column delimiter | whitespace |

### Examples

```bash
# Position + velocity
cat orbit.txt | stk-files ephemeris TimePosVel -o satellite.e

# Position only with Lagrange interpolation
cat orbit.txt | stk-files ephemeris TimePos --interpolation-method Lagrange -o satellite.e

# LLA coordinates
cat lla.txt | stk-files ephemeris LLATimePos -b Earth -o satellite.e

# CSV input with comma delimiter
cat orbit.csv | stk-files ephemeris TimePosVel -d "," -o satellite.e
```

### Input format

```
2024-01-01T00:00:00.000 7000.0 0.0 0.0 0.0 7.5 0.0
2024-01-01T00:01:00.000 6999.0 100.0 0.0 -0.1 7.5 0.0
```

## sensor

Generate an STK sensor pointing file (`.sp`).

```
stk-files sensor FORMAT [options] < data.txt
```

**FORMAT** is one of: `AzElAngles`, `DCM`, `ECFVector`, `ECIVector`,
`EulerAngles`, `QuatScalarFirst`, `Quaternions`, `YPRAngles`

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o`, `--output FILE` | Output file | stdout |
| `-a`, `--axes AXES` | Coordinate axes | |
| `-b`, `--central-body BODY` | Central body (`Earth`, `Moon`) | |
| `-t`, `--time-format FMT` | `ISO-YMD` or `EpSec` | `ISO-YMD` |
| `-e`, `--scenario-epoch DT` | Scenario epoch (required for EpSec) | |
| `-s`, `--sequence SEQ` | Rotation sequence (required for angle formats) | |
| `-d`, `--delimiter DELIM` | Column delimiter | whitespace |

### Examples

```bash
# Azimuth/elevation with sequence 323
cat pointing.txt | stk-files sensor AzElAngles -s 323 -o sensor.sp

# Quaternion sensor pointing
cat pointing.txt | stk-files sensor Quaternions -o sensor.sp
```

### Input format

```
2024-01-01T00:00:00.000 45.0 30.0
2024-01-01T00:01:00.000 46.0 31.0
```

## interval

Generate an STK interval list file (`.int`).

```
stk-files interval [options] < data.txt
```

No format argument is needed.

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o`, `--output FILE` | Output file | stdout |
| `-d`, `--delimiter DELIM` | Column delimiter | whitespace |

### Examples

```bash
# Basic interval list
cat intervals.txt | stk-files interval -o access.int
```

### Input format

Each line has a start time, end time, and optional metadata:

```
2024-01-01T00:00:00.000 2024-01-01T01:00:00.000
2024-01-01T02:00:00.000 2024-01-01T03:00:00.000 Ground Station Alpha
```
