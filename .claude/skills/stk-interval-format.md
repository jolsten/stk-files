# STK Interval List File Format (*.int)

Reference for STK 13 external interval list files. Source: AGI/Ansys STK Help `importfiles-04.htm`.

## File Structure

```
stk.v.12.0
BEGIN IntervalList
    ScenarioEpoch <epoch>         (option A: numeric seconds)
    DateUnitAbrv <abbreviation>   (option B: formatted dates)
BEGIN Intervals
    <start> <stop> [optional_data]
    ...
END Intervals
END IntervalList
```

## Keywords

| Keyword | Required | Description |
|---------|----------|-------------|
| `stk.v.X.X` | Yes | Version stamp, must be first line |
| `BEGIN IntervalList` / `END IntervalList` | Yes | Brackets entire keyword group |
| `BEGIN Intervals` / `END Intervals` | Yes | Brackets data entries |
| `ScenarioEpoch` | Option A | `dd mmm yyyy hh:mm:ss.s` (Gregorian UTC). Times as seconds past epoch. |
| `DateUnitAbrv` | Option B | STK date format abbreviation. Non-numeric times must be quoted. |

All keywords are case-insensitive.

## Time Format Options

### Option A: ScenarioEpoch (numeric seconds)
```
ScenarioEpoch 1 Jul 2000 00:00:00.00
BEGIN Intervals
    0.000000  3600.000000
    7200.000000  10800.000000
END Intervals
```

### Option B: DateUnitAbrv (formatted dates, quoted)
```
DateUnitAbrv UTCG
BEGIN Intervals
    "1 Jul 2000 00:00:00.00" "1 Jul 2000 01:30:00.00"
    "1 Jul 2000 02:00:00.00" "1 Jul 2000 03:00:00.00"
END Intervals
```

**Supported abbreviations:** EpSec, UTCG, GPSG, GPSZ, TAIG, TDTG, JDate, ModJDate, YYDDD, YYYYDDD, ISO-YMD, ISO-YD, and others.

**Not supported:** LCLG (local Gregorian), LCLJ (local Julian), Mission Elapsed.

## Data Line Format

Each line: `<start_time> <stop_time> [optional_data_string]`

Non-numerical times must be enclosed in quotes.

## Optional Data Strings

| Field | Examples |
|-------|----------|
| Target/Object | `Facility/Philadelphia`, `Satellite/Sat315` |
| Color | `Color red`, `Color #0000ff` |
| Pointing target | `Sun`, `Viewer` |
| 2D Graphics | `Show On`, `Color`, `LineStyle dotted`, `LineWidth 3`, `MarkerStyle Plus` |
| 3D Graphics | `Show On`, `Color`, `LineWidth 3`, `Translucency 50` |

Invalid optional data is silently ignored.

## Example (ISO-YMD)

```
stk.v.12.0
BEGIN IntervalList
    DateUnitAbrv ISO-YMD
BEGIN Intervals
    "2020-01-01T00:00:00.000" "2020-01-01T00:10:00.000"
    "2020-01-02T00:00:00.000" "2020-01-02T00:20:00.000"
END Intervals
END IntervalList
```
