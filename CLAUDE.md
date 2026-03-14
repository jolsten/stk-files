# CLAUDE.md — stk-files

## What this is

Python package for generating STK (Systems Tool Kit) external data files. Provides a programmatic API and CLI to write attitude, ephemeris, sensor pointing, and interval list data in STK-compatible formats.

## Quick reference

```bash
uv sync                    # Install dependencies
pytest                     # Run tests
ruff check src/ tests/     # Lint
ruff format src/ tests/    # Format
mypy src/                  # Type check (strict mode)
```

## Project layout

- `src/stk_files/` — package source
  - `attitude.py`, `ephemeris.py`, `interval.py`, `sensor.py` — file type modules (each has a frozen Config dataclass + `write_*` function)
  - `_types.py` — type literals, column count dicts, format constants
  - `_validation.py` — shape/quaternion/angle/sequence validation + filtering
  - `_formatting.py` — row formatting (ISO-YMD timestamps, EpSec, quaternions, generic)
  - `_coerce.py` — runtime coercion of pandas/polars Series/DataFrames to numpy arrays
  - `_writer.py` — `stk_writer()` context manager, `RowWriter`
  - `cli.py` — Click CLI with subcommands (attitude, ephemeris, interval, sensor)
  - `__init__.py` — public API exports
- `tests/` — pytest + hypothesis tests
  - `strategies.py` — custom hypothesis strategies (quaternions, angles, sorted datetimes)

## Conventions

- **Python >=3.9**, strict mypy, ruff (line-length 99)
- Private modules prefixed with `_`, config classes suffixed with `Config`
- `from __future__ import annotations` in all modules
- Timestamps are `np.datetime64[ms]`; data arrays are numpy ndarrays (pandas/polars inputs are coerced automatically via `_coerce.py`)
- pandas and polars are optional dependencies (`pip install stk-files[pandas]` / `stk-files[polars]`)
- Validation has strict mode (raise on invalid) and non-strict (filter invalid rows)
- Frozen dataclasses for configs; each config has `header()` and `footer()` methods
- Tests use hypothesis property-based testing with custom strategies in `strategies.py`

## Adding a new file format

1. Add type literals and column counts to `_types.py`
2. Add validation rules to `_validation.py` if needed
3. Add formatter to `_formatting.py` if special formatting needed
4. Create module with Config dataclass and `write_*` function
5. Export in `__init__.py`
6. Add CLI subcommand in `cli.py`
7. Add tests with hypothesis strategies
