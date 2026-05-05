# s3peek Backlog

## Missing reader formats (peek)
- **VOTable** (.vot, .xml w/ VOTABLE root) — common in astronomy catalogs
- **HDF5** (.h5, .hdf5) — large datasets
- **CSV** (.csv) — show column names + row count from first chunk
- **ECSV** (.ecsv) — Astropy enhanced CSV

## Technical debt / revisit
- **Lazy loading / hydration efficiency**: readers currently load full `data` bytes
  passed from `range_get`. For large files, ensure partial-read is actually used
  (FITS header is at start ✅, ASDF header at start ✅, Parquet footer at end ⚠️).
  Revisit Parquet: do a tail range-get for footer bytes instead of returning note.
- **Reader import cost**: all reader deps (astropy, asdf, pyarrow) imported at call
  time inside `read()` — good. Verify `load_readers()` in plugins.py does not eagerly
  import all reader modules at startup.
- **Streaming**: `range_get` always fetches `max_range_get_bytes` even for tiny files.
  Could stat first and fetch min(size, max_range_get_bytes).

## Confirmed working (user-tested)
- FITS ✅
- Parquet ✅
- ASDF ✅
- JSON ✅ (test suite)
