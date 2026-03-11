# STK Attitude File Format (*.a)

Reference for STK 13 external attitude data files. Source: AGI/Ansys STK Help `importfiles-01.htm`.

## File Structure

```
stk.v.11.0
BEGIN Attitude
  [keywords]
  <FormatKeyword>
  <time> <data...>
  ...
END Attitude
```

## Keywords

| Keyword | Required | Description |
|---------|----------|-------------|
| `stk.v.X.X` | Yes | Version stamp, must be first line |
| `BEGIN Attitude` / `END Attitude` | Yes | Brackets all data |
| `MessageLevel` | No | `Errors`, `Warnings`, or `Verbose` |
| `ScenarioEpoch` | No | Reference epoch: `dd mmm yyyy hh:mm:ss.s` |
| `CentralBody` | No | Default: Earth |
| `CoordinateAxes` | No | Reference coordinate system (see below) |
| `CoordinateAxesEpoch` | Conditional | Required for epoch-dependent axes |
| `InterpolationMethod` | No | `Lagrange` (default) or `Hermite` |
| `InterpolationOrder` | No | Default: 1 |
| `NumberOfAttitudePoints` | No | Max points to read |
| `AttitudeDeviations` | No | `Rapid` (default) or `Mild` |
| `BlockingFactor` | No | Memory allocation for large files |
| `Sequence` | Conditional | Rotation order for Euler/YPR formats |
| `InitialQuaternion` | Conditional | `<q1> <q2> <q3> <q4>` (q4=scalar), for AngVels format |
| `InitialEulerAngle` | Conditional | `<Sequence> <RotA> <RotB> <RotC>`, for EulerAngleRates |
| `InitialYPRAngle` | Conditional | `<Sequence> <Y> <P> <R>`, for YPRAngleRates |
| `TimeFormat` | No | Date format abbreviation (default: EpSec) |
| `RepeatPattern` | No | Cycles data; first/last points should match |

## Coordinate Axes

**Standard:** Fixed, J2000, ICRF, Inertial, TrueOfDate, MeanOfDate

**Epoch-dependent (require CoordinateAxesEpoch):** MeanOfEpoch, TrueOfEpoch, TEMEOfEpoch, AlignmentAtEpoch

**Custom (VGT):** `CoordinateAxes AWB <AxisName> <ObjectPath>`

## Data Formats (16 total)

### Quaternion Formats

| Format Keyword | Columns | Notes |
|----------------|---------|-------|
| `AttitudeTimeQuaternions` | `time q1 q2 q3 q4` | q4 is scalar (scalar-last). Auto-normalized to unit magnitude. |
| `AttitudeTimeQuatScalarFirst` | `time q1 q2 q3 q4` | q1 is scalar (scalar-first) |
| `AttitudeTimeQuatAngVels` | `time q1 q2 q3 q4 wx wy wz` | + angular velocity (deg/s, body frame) |
| `AttitudeTimeAngVels` | `time rA rB rC` | Rates only (deg/s). Requires `InitialQuaternion`. |

### Euler Angle Formats

| Format Keyword | Columns | Notes |
|----------------|---------|-------|
| `AttitudeTimeEulerAngles` | `time rotA rotB rotC` | Degrees. Requires `Sequence`. |
| `AttitudeTimeEulerAngleRates` | `time rateA rateB rateC` | deg/s. Requires `InitialEulerAngle`. |
| `AttitudeTimeEulerAnglesAndRates` | `time rotA rotB rotC rateA rateB rateC` | Requires `InitialEulerAngle`. |

**Valid Euler sequences:** 121, 123, 131, 132, 212, 213, 231, 232, 312, 313, 321, 323 (default: 313)

Euler rotations are relative to the rotated frame.

### YPR Angle Formats

| Format Keyword | Columns | Notes |
|----------------|---------|-------|
| `AttitudeTimeYPRAngles` | `time Y P R` | Degrees. Data always in Y-P-R order. Requires `Sequence`. |
| `AttitudeTimeYPRAngleRates` | `time rateA rateB rateC` | deg/s. Requires `InitialYPRAngle`. |
| `AttitudeTimeYPRAnglesAndRates` | `time Y P R rateA rateB rateC` | Requires `InitialYPRAngle`. |

**Valid YPR sequences:** 123, 132, 213, 231, 312, 321 (default: 321)

YPR rotations are relative to the original reference frame. Sequence controls rotation order, not data column order.

### DCM Formats

| Format Keyword | Columns | Notes |
|----------------|---------|-------|
| `AttitudeTimeDCM` | `time m11 m12 m13 m21 m22 m23 m31 m32 m33` | Row-major, ref-to-body |
| `AttitudeTimeDCMAngVels` | `time m11..m33 wx wy wz` | + angular velocity (deg/s, body frame) |

### Vector Formats

| Format Keyword | Columns | Notes |
|----------------|---------|-------|
| `AttitudeTimeECIVector` | `time V1 V2 V3` | Body X-axis in ECI, Z toward nadir. Ignores CoordinateAxes. |
| `AttitudeTimeECFVector` | `time V1 V2 V3` | Body X-axis in ECF, Z toward nadir. Ignores CoordinateAxes. |

## Data Conventions

- One data point per line, values separated by at least one space
- Ascending time order, no duplicate timestamps
- Angular velocities always in degrees/second, body-frame components
- Quaternions are auto-normalized to unit magnitude by STK
- For spinning objects: 3-4 points per revolution minimum
- Neighboring points should span less than half a revolution, or include angular velocity data
- All attitudes represent rotation from reference frame to body frame

## Example

```
stk.v.11.0
BEGIN Attitude
NumberOfAttitudePoints 3
ScenarioEpoch 1 Jan 2003 00:00:00.0
CoordinateAxes J2000
InterpolationMethod Lagrange
InterpolationOrder 1
AttitudeTimeQuaternions
0.0     0.0  0.0  0.0  1.0
3600.0  0.1  0.2  0.3  0.9274
7200.0  0.0  0.0  0.7071  0.7071
END Attitude
```
