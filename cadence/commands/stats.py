"""cadence stats — job search statistics."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.table import Table

from cadence.config import load_config
from cadence.storage import Store

console = Console()


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        return None


@click.command()
@click.option("--by-source", is_flag=True, default=False)
@click.option("--by-month", is_flag=True, default=False)
def stats(by_source: bool, by_month: bool) -> None:
    """Show job search statistics."""
    store = Store(load_config())
    applications = list(store.all_applications())

    if not applications:
        console.print("[dim]No applications yet.[/dim]")
        return

    total = len(applications)
    by_status: Counter = Counter()
    sources: Counter = Counter()
    months: Counter = Counter()
    interview_count = 0
    offer_count = 0
    accepted_count = 0

    for a in applications:
        status = a.status or "unknown"
        by_status[status] += 1

        src = a.source or "unknown"
        sources[src] += 1

        if a.applied_at:
            month = (a.applied_at or "")[:7]  # YYYY-MM
            if month:
                months[month] += 1

        if a.interviews:
            interview_count += 1

        offer = store.offer_for_application(a.id)
        if offer:
            offer_count += 1
            if offer.status == "accepted":
                accepted_count += 1

    applied = sum(v for k, v in by_status.items()
                  if k not in ("saved",))
    responded = sum(v for k, v in by_status.items()
                    if k not in ("saved", "applied", "ghosted"))

    console.print("\n[bold]Overview[/bold]")
    console.print(f"  Total tracked:     {total}")
    console.print(f"  Applied:           {applied}")
    console.print(f"  Got a response:    {responded}"
                  f"  [dim]({responded * 100 // applied if applied else 0}% response rate)[/dim]")
    console.print(f"  Reached interview: {interview_count}"
                  f"  [dim]({interview_count * 100 // applied if applied else 0}% interview rate)[/dim]")
    console.print(f"  Offers received:   {offer_count}"
                  f"  [dim]({offer_count * 100 // applied if applied else 0}% offer rate)[/dim]")
    if accepted_count:
        console.print(f"  Accepted:          {accepted_count}")

    console.print("\n[bold]By status[/bold]")
    for status, count in by_status.most_common():
        bar = "█" * count
        console.print(f"  {status:<20} {count:>3}  [dim]{bar}[/dim]")

    if by_source:
        console.print("\n[bold]By source[/bold]")
        for source, count in sources.most_common():
            console.print(f"  {source:<20} {count:>3}")

    if by_month:
        console.print("\n[bold]By month[/bold]")
        for month in sorted(months):
            count = months[month]
            bar = "█" * count
            console.print(f"  {month}  {count:>3}  [dim]{bar}[/dim]")
