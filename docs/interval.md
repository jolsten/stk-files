## Interval File

### interval_file()

::: stk_files.funcs.interval_file

#### Examples

The two intervals below...
```python
import datetime
from stk_files import interval_file
intervals = [
    (datetime.datetime(2020,1,1,0,0,0), datetime.datetime(2020,1,1,0,10,0)),
    (datetime.datetime(2020,1,2,0,0,0), datetime.datetime(2020,1,2,0,20,0))
]
interval_file("example.int", intervals)
```

Will create an interval file that looks like:

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
