# Changelog

## [0.1.0] - Unreleased

### Added
- Initial repo scaffold
- Plugin architecture via Python entry points (`s3peek.readers`, `s3peek.themes`, `s3peek.commands`)
- Built-in format readers: FITS, ASDF, Parquet, JSON (stubbed, implementations in next iteration)
- CLI commands: `browse`, `peek`, `share`, `ls`, `du`, `firefly`, `version`
- Firefly integration (`src/s3peek/firefly.py`) — stream S3 objects to a transient local file and display them with Firefly `show_data`
- GitHub Actions CI matrix (ubuntu + macos, Python 3.11/3.12)
