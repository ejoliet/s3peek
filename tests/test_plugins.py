from __future__ import annotations

from s3peek.plugins import load_readers, load_themes


def test_load_readers_returns_four_builtins() -> None:
    readers = load_readers()
    names = {r.__class__.__name__ for r in readers}
    assert names == {"FITSReader", "ASDFReader", "ParquetReader", "JSONReader"}


def test_reader_priorities_are_ints() -> None:
    for reader in load_readers():
        assert isinstance(reader.priority, int)


def test_readers_sorted_by_priority_descending() -> None:
    readers = load_readers()
    priorities = [r.priority for r in readers]
    assert priorities == sorted(priorities, reverse=True)


def test_load_themes_returns_dark_and_light() -> None:
    themes = load_themes()
    assert "dark" in themes
    assert "light" in themes
