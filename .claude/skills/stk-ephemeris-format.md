# STK Ephemeris File Format (*.e)

Reference for STK 13 external ephemeris data files. Source: AGI/Ansys STK Help `importfiles-02.htm`.

## File Structure

```
stk.v.12.0
BEGIN Ephemeris
  [keywords]
  <FormatKeyword>
  <time> <data...>
  ...
END Ephemeris
```

## Keywords

| Keyword | Required | Description |
|---------|----------|-------------|
| `stk.v.X.X` | Yes | Version stamp, must be first line |
| `BEGIN Ephemeris` / `END Ephemeris` | Yes | Brackets all data |
| `ScenarioEpoch` | No | Reference epoch: `dd mmm yyyy hh:mm:ss.s` (UTC) |
| `CentralBody` | No | Default: Earth |
| `CoordinateSystem` | No | Default: Fixed. **Note: uses `CoordinateSystem`, not `CoordinateAxes`** |
| `CoordinateSystemEpoch` | Conditional | Required for epoch-dependent frames |
| `DistanceUnit` | No | Default: meters |
| `TimeFormat` | No | Default: EpSec |
| `TimeScale` | No | Default: TAI. Alternative: TDB |
| `MessageLevel` | No | `Errors`, `Warnings`, or `Verbose` |
| `NumberOfEphemerisPoints` | No | Max points to read (optional since STK 11.5) |
| `InterpolationMethod` | No | `Lagrange` (default), `Hermite`, `LagrangeVOP`, `GreatArc`, `GreatArcTerrain`, `GreatArcMSL` |
| `InterpolationSamplesM1` | No | Default: 5. One less than interpolation point count. Replaces deprecated `InterpolationOrder`. |
| `ComputeVelocity` | No | `DerivativeOfInterpolatingPolynomial` (default), `ForwardDifference`, `BackwardDifference`, `CentralDifference` |
| `SmoothData` | No | `Yes`/`No`, `True`/`False`, `On`/`Off` |
| `BlockingFactor` | No | Memory allocation hint |

## Coordinate Systems

**Standard:** Fixed (default), J2000, ICRF, Inertial, TrueOfDate, MeanOfDate

**Epoch-dependent (require CoordinateSystemEpoch):** MeanOfEpoch, TrueOfEpoch, TEMEOfEpoch, AlignmentAtEpoch

**Custom (VGT):** `CoordinateSystem AWB <name> <object>`

## Data Formats (14 ephemeris + 3 covariance)

### Cartesian Formats

| Format Keyword | Columns | Units |
|----------------|---------|-------|
| `EphemerisTimePos` | `time X Y Z` | sec, m |
| `EphemerisTimePosVel` | `time X Y Z Xdot Ydot Zdot` | sec, m, m/s |
| `EphemerisTimePosVelAcc` | `time X Y Z Xdot Ydot Zdot Xddot Yddot Zddot` | sec, m, m/s, m/s^2 |

### Geodetic LLA Formats

| Format Keyword | Columns | Units |
|----------------|---------|-------|
| `EphemerisLLATimePos` | `time Lat Lon Alt` | sec, deg, deg, m |
| `EphemerisLLATimePosVel` | `time Lat Lon Alt LatDot LonDot AltDot` | sec, deg, deg, m, deg/s, deg/s, m/s |
| `EphemerisMSLLLATimePos` | `time Lat Lon Alt(MSL)` | sec, deg, deg, m |
| `EphemerisMSLLLATimePosVel` | `time Lat Lon Alt(MSL) LatDot LonDot AltDot` | same |
| `EphemerisTerrainLLATimePos` | `time Lat Lon Alt(terrain)` | sec, deg, deg, m |

### Geocentric LLR Formats

| Format Keyword | Columns | Units |
|----------------|---------|-------|
| `EphemerisLLRTimePos` | `time Lat(geocentric) Lon Radius` | sec, deg, deg, m |
| `EphemerisLLRTimePosVel` | `time Lat Lon Radius LatDot LonDot RadDot` | sec, deg, deg, m, deg/s, deg/s, m/s |

### Mixed Geodetic/Geocentric Formats

| Format Keyword | Columns |
|----------------|---------|
| `EphemerisGeocentricLLATimePos` | `time Lat(geocentric) Lon Alt` |
| `EphemerisGeocentricLLATimePosVel` | `time Lat Lon Alt LatDot LonDot AltDot` |
| `EphemerisGeodeticLLRTimePos` | `time Lat(geodetic) Lon Radius` |
| `EphemerisGeodeticLLRTimePosVel` | `time Lat Lon Radius LatDot LonDot RadDot` |

### Covariance Formats

| Format Keyword | Values | Notes |
|----------------|--------|-------|
| `CovarianceTimePos` | 6 unique | 3x3 position covariance (m^2) |
| `CovarianceTimePosVel` | 21 unique | 6x6 pos+vel covariance |
| `StateErrorTransition` | 36 values | 6x6 state transition matrix |

Covariance keywords: `CovarianceFormat` (LowerTriangular/UpperTriangular), `CovarianceInterpolationMethod`, `CovarianceCoordinateSystem`.

## Interpolation Methods

| Method | Notes |
|--------|-------|
| `Lagrange` | Default polynomial interpolation |
| `Hermite` | Uses velocity for smoother results; requires velocity data |
| `LagrangeVOP` | Requires mu: `InterpolationMethod LagrangeVOP 3.986e+14` |
| `GreatArc` | Fixed frame, WGS84 great circle |
| `GreatArcTerrain` | Terrain-following great arc |
| `GreatArcMSL` | MSL-following great arc |

## Optional Sections

**SegmentBoundaryTimes:** List of times where interpolation should not cross. Allows duplicate times at boundaries.

**TrendingControl (STK 11.6+):** `TrendingControlTimes` block or `TrendingControlStep <seconds>`.

## Data Conventions

- One data point per line, values separated by at least one space
- Ascending time order (not necessarily evenly spaced)
- No duplicate times except at SegmentBoundaryTimes
- Minimum 90 points per orbital revolution recommended
- Scientific notation permitted
- Position-only formats auto-generate velocity via `ComputeVelocity` method

## Example

```
stk.v.12.0
BEGIN Ephemeris
ScenarioEpoch  1 Jan 2003 00:00:00.0
CentralBody    Earth
CoordinateSystem J2000
InterpolationMethod Lagrange
InterpolationSamplesM1 5
NumberOfEphemerisPoints 3

EphemerisTimePosVel
0.0    7000000.0  0.0    0.0    0.0   7500.0   0.0
60.0   6999500.0  450200.0  10500.0  -100.0   7400.0   50.0
120.0  6998000.0  897800.0  40200.0  -300.0   7300.0   150.0

END Ephemeris
```
