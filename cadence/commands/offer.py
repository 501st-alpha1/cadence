"""cadence offer — manage offers."""

import click
from rich.console import Console

from cadence.config import load_config
from cadence.commands.application import resolve_application
from cadence.models import Offer
from cadence.models.offer import OfferVersion, OfferStatus
from cadence.models.application import TERMINAL_STATUSES
from cadence.models.base import now_utc
from cadence.storage import Store
from cadence.utils.cli import short_id, print_kv

console = Console()


@click.group()
def offer() -> None:
    """Manage offers."""
    pass


@offer.command("add")
@click.argument("app_query")
@click.option("--compensation", prompt="Compensation (freeform)")
@click.option("--expires", default=None, help="Expiry date YYYY-MM-DD")
@click.option("--notes", default="")
def offer_add(app_query: str, compensation: str, expires: str, notes: str) -> None:
    """Record an offer for an application."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return

    existing = store.offer_for_application(application.id)
    if existing:
        console.print("[yellow]An offer already exists for this application. "
                      "Use 'cadence offer revise' to add a new version.[/yellow]")
        return

    o = Offer(
        application_id=application.id,
        versions=[OfferVersion(compensation=compensation, notes=notes)],
        expires_at=expires,
        notes=notes,
    )
    store.save_offer(o)
    application.transition("offer")
    store.save_application(application)
    console.print(f"[green]Offer recorded[/green] [{short_id(o.id)}]")


@offer.command("revise")
@click.argument("app_query")
@click.option("--compensation", prompt="New compensation terms")
@click.option("--notes", default="")
def offer_revise(app_query: str, compensation: str, notes: str) -> None:
    """Add a revised offer version (after negotiation)."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return
    o = store.offer_for_application(application.id)
    if not o:
        console.print(f"[red]No offer found for this application[/red]")
        return
    o.versions.append(OfferVersion(compensation=compensation, notes=notes))
    store.save_offer(o)
    console.print(f"[green]Offer revision added[/green] (version {len(o.versions)})")


@offer.command("show")
@click.argument("app_query")
def offer_show(app_query: str) -> None:
    """Show offer details for an application."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return
    o = store.offer_for_application(application.id)
    if not o:
        console.print(f"[red]No offer found for this application[/red]")
        return
    print_kv([
        ("ID", o.id),
        ("Status", o.status),
        ("Expires", o.expires_at),
        ("Received", o.received_at[:10]),
        ("Notes", o.notes),
    ], title="Offer")
    console.print("\n[bold]Versions[/bold]")
    for i, v in enumerate(o.versions, 1):
        console.print(f"  {i}. {v.at[:10]}  {v.compensation}")
        if v.notes:
            console.print(f"     [dim]{v.notes}[/dim]")


@offer.command("accept")
@click.argument("app_query")
def offer_accept(app_query: str) -> None:
    """Accept an offer and optionally withdraw other active applications."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return
    o = store.offer_for_application(application.id)
    if not o:
        console.print(f"[red]No offer found for this application[/red]")
        return

    o.status = OfferStatus.ACCEPTED
    store.save_offer(o)

    application.transition("accepted")
    store.save_application(application)

    # Offer to withdraw other active applications
    others = [
        a for a in store.all_applications()
        if a.id != application.id and a.status not in TERMINAL_STATUSES
    ]
    if others:
        console.print(
            f"\n[yellow]You have {len(others)} other active application(s).[/yellow]"
        )
        if click.confirm("Withdraw all of them?", default=False):
            for a in others:
                a.transition("withdrawn", notes="Accepted another offer")
                store.save_application(a)
            console.print(f"[green]Withdrew {len(others)} application(s).[/green]")

    console.print("[green]Offer accepted. Congratulations![/green]")


@offer.command("decline")
@click.argument("app_query")
@click.option("--notes", default="")
def offer_decline(app_query: str, notes: str) -> None:
    """Decline an offer."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return
    o = store.offer_for_application(application.id)
    if not o:
        console.print(f"[red]No offer found for this application[/red]")
        return
    o.status = OfferStatus.DECLINED
    if notes:
        o.notes = (o.notes + "\n" + notes).strip()
    store.save_offer(o)

    application.transition("declined_offer", notes=notes)
    store.save_application(application)

    console.print("[green]Offer declined.[/green]")
