"""cadence person — manage people."""

import click
from rich.console import Console

from cadence.config import load_config
from cadence.models import Person, Message
from cadence.storage import Store
from cadence.utils.cli import resolve_or_pick, short_id, print_kv

console = Console()


@click.group()
def person() -> None:
    """Manage people."""
    pass


@person.command("add")
@click.option("--name", prompt="Name")
@click.option("--company", "company_query", default=None)
@click.option("--role", default=None)
@click.option("--email", default=None)
@click.option("--linkedin", default=None)
@click.option("--notes", default="")
def person_add(name, company_query, role, email, linkedin, notes) -> None:
    """Add a person. Optionally log an inbound message from them."""
    config = load_config()
    store = Store(config)

    company_id = None
    if company_query:
        c = resolve_or_pick(company_query, store.find_company,
                            lambda x: x.display_name, "company")
        if c:
            company_id = c.id

    p = Person(
        name=name,
        company_id=company_id,
        role=role,
        email=email,
        linkedin_url=linkedin,
        notes=notes,
    )
    store.save_person(p)
    console.print(f"[green]Added[/green] {name} [{short_id(p.id)}]")

    # Offer to log an initial inbound message immediately
    if click.confirm("Log an inbound message from this person now?", default=False):
        channel = click.prompt("Channel", type=click.Choice(
            ["email", "linkedin", "phone", "other"]), default="linkedin")
        body = click.prompt("Message body (or summary)")
        msg = Message(
            direction="inbound",
            channel=channel,
            body=body,
            person_id=p.id,
        )
        store.save_message(msg)
        console.print(f"[green]Message logged[/green] [{short_id(msg.id)}]")


@person.command("show")
@click.argument("query")
def person_show(query: str) -> None:
    """Show a person by name prefix or ID."""
    store = Store(load_config())
    p = resolve_or_pick(query, store.find_person, lambda x: x.name, "person")
    if not p:
        return
    companies = {c.id: c for c in store.all_companies()}
    company = companies.get(p.company_id or "")
    print_kv([
        ("ID", p.id),
        ("Name", p.name),
        ("Company", company.display_name if company else None),
        ("Role", p.role),
        ("Email", p.email),
        ("LinkedIn", p.linkedin_url),
        ("Notes", p.notes),
    ], title=p.name)


@person.command("list")
@click.option("--company", "company_query", default=None)
def person_list(company_query) -> None:
    """List people."""
    store = Store(load_config())
    companies = {c.id: c for c in store.all_companies()}
    people = list(store.all_people())

    if company_query:
        matches = store.find_company(company_query)
        ids = {c.id for c in matches}
        people = [p for p in people if p.company_id in ids]

    if not people:
        console.print("[dim]No people found.[/dim]")
        return

    for p in sorted(people, key=lambda x: x.name.lower()):
        company = companies.get(p.company_id or "")
        co = f"  [dim]{company.display_name}[/dim]" if company else ""
        role = f", {p.role}" if p.role else ""
        console.print(f"  [{short_id(p.id)}]  {p.name}{role}{co}")
