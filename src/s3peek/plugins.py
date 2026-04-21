from __future__ import annotations

from importlib.metadata import entry_points
from typing import TYPE_CHECKING

import typer

from s3peek.readers import BaseReader
from s3peek.themes import ThemeBase

if TYPE_CHECKING:
    pass


def load_readers() -> list[BaseReader]:
    eps = entry_points(group="s3peek.readers")
    readers: list[BaseReader] = [ep.load()() for ep in eps]
    return sorted(readers, key=lambda r: r.priority, reverse=True)


def load_themes() -> dict[str, ThemeBase]:
    eps = entry_points(group="s3peek.themes")
    return {ep.name: ep.load()() for ep in eps}


def load_commands() -> list[typer.Typer]:
    eps = entry_points(group="s3peek.commands")
    return [ep.load() for ep in eps]
