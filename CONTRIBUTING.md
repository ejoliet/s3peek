# Contributing to s3peek

s3peek is extensible via Python entry points. No fork required — third-party packages
register themselves and s3peek discovers them at runtime.

## Writing a format reader plugin

Implement the `BaseReader` protocol and register it under the `s3peek.readers` entry-point group.

### 1. Implement `BaseReader`

```python
# my_package/reader.py
from s3peek.readers import BaseReader, HeaderResult

class MyFormatReader:
    extensions = (".myext",)
    priority = 10  # higher = tried first; use >10 to override built-ins

    def can_read(self, key: str, first_bytes: bytes) -> bool:
        return key.endswith(self.extensions) or first_bytes[:4] == b"MYFM"

    def read(self, data: bytes, *, max_headers: int = 1) -> HeaderResult:
        headers = [{"field1": "...", "field2": "..."}]
        return HeaderResult(format="myformat", headers=headers[:max_headers])
```

### 2. Register via entry points

```toml
# my_package/pyproject.toml
[project.entry-points."s3peek.readers"]
myformat = "my_package.reader:MyFormatReader"
```

After `pip install my-package`, run `s3peek peek s3://bucket/file.myext` — your reader
is used automatically. No changes to s3peek are required.

### 3. Test your reader

```python
from s3peek.readers import HeaderResult
from my_package.reader import MyFormatReader

def test_can_read():
    r = MyFormatReader()
    assert r.can_read("file.myext", b"MYFM\x00")

def test_read():
    r = MyFormatReader()
    data = b"..."  # minimal valid bytes for your format
    result = r.read(data)
    assert isinstance(result, HeaderResult)
    assert result.format == "myformat"
    assert "field1" in result.headers[0]
```

---

## Writing a theme plugin

Subclass `ThemeBase` and register under `s3peek.themes`.

```python
# my_theme/theme.py
from s3peek.themes import ThemeBase

class NordTheme(ThemeBase):
    name = "nord"
    CSS = """
    Screen { background: #2e3440; color: #d8dee9; }
    """
```

```toml
[project.entry-points."s3peek.themes"]
nord = "my_theme.theme:NordTheme"
```

Set in `~/.config/s3peek/config.toml`:
```toml
theme = "nord"
```

---

## Writing a command plugin

Expose a `typer.Typer` instance and register under `s3peek.commands`.

```python
# my_plugin/cli.py
import typer

app = typer.Typer(name="myplugin", help="Extra commands from my-plugin.")

@app.command()
def greet(uri: str) -> None:
    typer.echo(f"Hello from my plugin: {uri}")
```

```toml
[project.entry-points."s3peek.commands"]
myplugin = "my_plugin.cli:app"
```

After install, `s3peek greet s3://bucket/key` works immediately.

---

## Built-in readers reference

| Reader | Extensions | Magic bytes | Deps |
|--------|------------|-------------|------|
| `FITSReader` | `.fits` `.fit` `.fz` `.fits.gz` | `SIMPLE  =` | `astropy` |
| `ASDFReader` | `.asdf` | `#ASDF` | `asdf`; optional `roman_datamodels` |
| `ParquetReader` | `.parquet` `.pq` | `PAR1` | `pyarrow` |
| `JSONReader` | `.json` | _(extension only)_ | stdlib |
