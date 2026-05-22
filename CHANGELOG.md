# Changelog

## [0.1.0] - Unreleased

### Added
- Initial repo scaffold
- Plugin architecture via Python entry points (`s3peek.readers`, `s3peek.themes`, `s3peek.commands`)
- Built-in format readers: FITS, ASDF, Parquet, JSON (stubbed, implementations in next iteration)
- CLI commands: `browse`, `peek`, `share`, `ls`, `du`, `firefly`, `version`
- Firefly integration (`src/s3peek/firefly.py`) — stream S3 objects to a transient local file and display them with Firefly `show_data`
- GitHub Actions CI matrix (ubuntu + macos, Python 3.11/3.12)
- ASDF deep-inspect mode: `peek --deep` uses `asdf.open(_force_raw_types=True)` to extract full ASDF tree including nested `roman`, `wcs`, and schema metadata nodes previously lost to `TaggedDict` serialization
- `peek` command accepts local file paths in addition to `s3://` URIs
- `quicklook()` and all readers accept `deep: bool = False` kwarg; FITS/Parquet/JSON readers ignore it via `**_kwargs`

### Fixed
- ASDF deep-inspect output now preserves nested YAML/tree structures and `asdf_*`/schema metadata that were previously lost during serialization; the fast-path reader remains a deliberately shallow 8 KB header preview
- `TaggedDict` (asdf `UserDict` subclass) serialized as `{}` under `json.dumps` — fixed via recursive `_to_plain()` converter
