# Welcome to MkDocs

For full documentation visit [mkdocs.org](https://www.mkdocs.org).

## Commands

* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs -h` - Print help message and exit.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.

## Usage

```python
from stkfiles import attitude_file

filename = "file.a"
time = np.array([
    "2020-01-01T00:00:00",
    "2020-01-01T00:01:00",
    "2020-01-01T00:02:00"
], dtype="datetime64")
data = np.array([
    [1.0, 0.0, 0.0, 0.0],
    [1.0, 10., 0.0, 0.0], # RSS of this row is not ~= 1.0, so it will be thrown away 
    [0.5, 0.5, 0.5, 0.5]
], dtype="f4")
attitude_file(filename, format="quaternion", time=time, data=data)
```
