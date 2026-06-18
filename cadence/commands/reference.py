"""cadence ref — manage reference contacts."""

import click
from rich.console import Console

from cadence.config import load_config
from cadence.models import ReferenceContact
from cadence.models.application import ApplicationReference
from cadence.models.base import now_utc
from cadence.storage import Store
from cadence.utils.cli import resolve_or_pick, short_id, print_kv

console = Console()


@click.group()
def ref() -> None:
    """Manage reference contacts."""
    pass


@ref.command("add")
@click.argument("person_query")
@click.option("--relationship", default=None, help="e.g. 'former manager'")
@click.option("--known-for", default=None, help="e.g. '3 years'")
@click.option("--notes", default="")
def ref_add(person_query: str, relationship: str, known_for: str, notes: str) -> None:
    """Mark a person as an agreed reference."""
    store = Store(load_config())
    p = resolve_or_pick(person_query, store.find_person, lambda x: x.name, "person")
    if not p:
        return

    # Check for duplicate
    existing = [r for r in store.all_reference_contacts() if r.person_id == p.id]
    if existing:
        console.print(f"[yellow]{p.name} is already a reference contact.[/yellow]")
        return

    r = ReferenceContact(
        person_id=p.id,
        relationship=relationship,
        how_long_known=known_for,
        notes=notes,
    )
    store.save_reference_contact(r)
    console.print(f"[green]Added reference contact[/green] {p.name} [{short_id(r.id)}]")


@ref.command("list")
def ref_list() -> None:
    """List all reference contacts with usage count."""
    store = Store(load_config())
    refs = list(store.all_reference_contacts())
    if not refs:
        console.print("[dim]No reference contacts.[/dim]")
        return

    people = {p.id: p for p in store.all_people()}

    # Count usage across all applications
    usage: dict[str, int] = {r.id: 0 for r in refs}
    ref_by_person: dict[str, str] = {r.person_id: r.id for r in refs}
    for app in store.all_applications():
        for ar in app.application_references:
            # Look up ref id via person
            rc = store.get_reference_contact(ar.reference_contact_id)
            if rc and rc.id in usage:
                usage[rc.id] += 1

    for r in sorted(refs, key=lambda x: people.get(x.person_id, None) and
                    people[x.person_id].name or ""):
        p = people.get(r.person_id)
        name = p.name if p else r.person_id
        rel = f"  [dim]{r.relationship}[/dim]" if r.relationship else ""
        used = usage.get(r.id, 0)
        used_str = f"  [dim]used {used}x[/dim]" if used else ""
        console.print(f"  [{short_id(r.id)}]  {name}{rel}{used_str}")


@ref.command("use")
@click.argument("app_id")
@click.argument("ref_id")
@click.option("--notes", default="")
def ref_use(app_id: str, ref_id: str, notes: str) -> None:
    """Record that a reference was listed on an application."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
        return

    rc = store.get_reference_contact(ref_id)
    if not rc:
        console.print(f"[red]Reference contact {ref_id} not found[/red]")
        return

    # Avoid duplicates
    already = any(ar.reference_contact_id == rc.id
                  for ar in application.application_references)
    if already:
        console.print("[yellow]This reference is already listed on this application.[/yellow]")
        return

    application.application_references.append(
        ApplicationReference(reference_contact_id=rc.id, notes=notes)
    )
    store.save_application(application)

    people = {p.id: p for p in store.all_people()}
    p = people.get(rc.person_id)
    console.print(f"[green]Reference added[/green] {p.name if p else rc.id}")
