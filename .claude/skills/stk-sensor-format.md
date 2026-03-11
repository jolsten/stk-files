# STK Sensor Pointing File Format (*.sp)

Reference for STK 13 external sensor pointing files. Source: AGI/Ansys STK Help `importfiles-07.htm`.

## File Structure

```
stk.v.11.0
[keywords outside block]
BEGIN Attitude
  <FormatKeyword>
  <time> <data...>
  ...
END Attitude
```

**Note:** Sensor pointing files use `BEGIN Attitude` / `END Attitude` (same block name as attitude files), despite having `.sp` extension.

## Keywords

| Keyword | Required | Description |
|---------|----------|-------------|
| `stk.v.X.X` | Yes | Version stamp, must be first line |
| `BEGIN Attitude` / `END Attitude` | Yes | Brackets data section |
| `MessageLevel` | No | `Errors`, `Warnings`, or `Verbose` |
| `CentralBody` | No | Default: parent vehicle's central body |
| `CoordinateAxes` | No | Reference frame. When unspecified: parent body axes (rotated 180 deg about X for ground objects) |
| `ScenarioEpoch` | No | Reference epoch: `dd mmm yyyy hh:mm:ss.s` |
| `TimeFormat` | No | Date format abbreviation |
| `NumberOfAttitudePoints` | No | Max points to read (recommended) |
| `Sequence` | Conditional | Rotation order for Euler/YPR/AzEl formats |
| `RepeatPattern` | No | Cycles data; first/last points should match |
| `AttitudeDeviations` | No | `Rapid` (default) or `Mild` |
| `InterpolationMethod` | No | `Lagrange` (default) or `Hermite` |
| `InterpolationOrder` | No | Default: 1 |

## Coordinate Axes

Same as attitude files: Fixed, J2000, ICRF, Inertial, TrueOfDate, MeanOfDate, plus epoch-dependent and custom AWB.

**Default behavior when unspecified:**
- **Vehicle parent:** parent's body axes
- **Facility/Target/Place parent:** parent's body axes rotated 180 degrees about X-axis

## Data Formats

### Quaternion Formats

| Format Keyword | Columns | Notes |
|----------------|---------|-------|
| `AttitudeTimeQuaternions` | `time q1 q2 q3 q4` | q4 is scalar (scalar-last) |
| `AttitudeTimeQuatScalarFirst` | `time q1 q2 q3 q4` | q1 is scalar |

### Angle Formats

| Format Keyword | Columns | Notes |
|----------------|---------|-------|
| `AttitudeTimeEulerAngles` | `time rotA rotB rotC` | Degrees. Requires `Sequence`. |
| `AttitudeTimeYPRAngles` | `time Y P R` | Degrees. Data always in Y-P-R order. |
| `AttitudeTimeAzElAngles` | `time azimuth elevation` | Degrees. Sensor-specific format. |

### AzElAngles Details

- **Azimuth:** positive counter-clockwise about +Z axis (vehicles) or -Z axis (ground locations)
- **Elevation:** degrees above XY plane, positive toward +Z axis
- Third rotation is always 0.0 (not provided in data)

## Rotation Sequences

**Euler sequences:** 121, 123, 131, 132, 212, 213, 231, 232, 312, 313, 321, 323 (default: 313)

**YPR sequences:** 123, 132, 213, 231, 312 (default: **312**, differs from attitude file default of 321)

**AzEl sequences:** 323 (default, "Rotate About Boresight"), 213 ("Hold About Boresight")

## Data Conventions

- One data point per line, values separated by at least one space
- Ascending time order, no duplicate timestamps
- For dynamic attitudes: 3-4 points per revolution minimum
- Sensor boresight is the Z-axis of the sensor body frame

## Example (AzEl)

```
stk.v.11.0
ScenarioEpoch 1 Jan 2003 00:00:00.0
Sequence 323
BEGIN Attitude
AttitudeTimeAzElAngles
0.0    45.0  30.0
3600.0 90.0  45.0
7200.0 135.0 60.0
END Attitude
```

## Example (Quaternions)

```
stk.v.11.0
CoordinateAxes J2000
BEGIN Attitude
AttitudeTimeQuaternions
0.0     0.0  0.0  0.0  1.0
3600.0  0.1  0.2  0.3  0.9274
END Attitude
```
