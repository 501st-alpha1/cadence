"""Shared utilities for CLI commands."""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Callable, Optional, TypeVar

import click
from rich.console import Console
from rich.table import Table

console = Console()
T = TypeVar("T")


def resolve_or_pick(query: str, find_fn: Callable[[str], list[T]],
                    label_fn: Callable[[T], str], noun: str) -> Optional[T]:
    """
    Resolve a query string to a single record.
    - If exactly one match: return it.
    - If multiple matches: present a numbered list and ask the user to pick.
    - If no matches: print error and return None.
    """
    results = find_fn(query)
    if not results:
        console.print(f"[red]No {noun} found matching '{query}'[/red]")
        return None
    if len(results) == 1:
        return results[0]

    console.print(f"[yellow]Multiple {noun}s match '{query}':[/yellow]")
    for i, item in enumerate(results, 1):
        console.print(f"  {i}. {label_fn(item)}")
    choice = click.prompt("Pick one", type=click.IntRange(1, len(results)))
    return results[choice - 1]


def open_in_editor(initial_text: str = "") -> str:
    """Open $EDITOR with initial_text, return edited content."""
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(initial_text)
        tmppath = f.name
    subprocess.call([editor, tmppath])
    with open(tmppath, encoding="utf-8") as f:
        return f.read()


def short_id(id: str) -> str:
    """Return first 8 chars of a UUID for display."""
    return id[:8]


def print_kv(pairs: list[tuple[str, str]], title: Optional[str] = None) -> None:
    """Print key-value pairs in a simple two-column layout."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    if title:
        console.print(f"\n[bold]{title}[/bold]")
    for key, value in pairs:
        table.add_row(key, str(value) if value else "[dim]—[/dim]")
    console.print(table)
