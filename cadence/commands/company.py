"""cadence company — manage companies."""

import click
from rich.console import Console

from cadence.config import load_config
from cadence.models import Company
from cadence.storage import Store
from cadence.utils.cli import resolve_or_pick, print_kv, short_id

console = Console()


@click.group()
def company() -> None:
    """Manage companies."""
    pass


@company.command("add")
@click.option("--name", prompt="Company name")
@click.option("--domain", default=None, help="e.g. acme.com")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--notes", default="")
def company_add(name: str, domain: str, tags: str, notes: str) -> None:
    """Add a new company."""
    store = Store(load_config())
    c = Company(
        display_name=name,
        domain=domain or None,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        notes=notes,
    )
    store.save_company(c)
    console.print(f"[green]Added[/green] {name} [{short_id(c.id)}]")


@company.command("show")
@click.argument("query")
def company_show(query: str) -> None:
    """Show a company by name prefix or ID."""
    store = Store(load_config())
    c = resolve_or_pick(query, store.find_company,
                        lambda x: x.display_name, "company")
    if not c:
        return
    print_kv([
        ("ID", c.id),
        ("Name", c.display_name),
        ("Domain", c.domain),
        ("Tags", ", ".join(c.tags) if c.tags else None),
        ("Notes", c.notes),
        ("Created", c.created_at),
    ], title=c.display_name)


@company.command("list")
@click.option("--tag", default=None, help="Filter by tag")
def company_list(tag: str) -> None:
    """List all companies."""
    store = Store(load_config())
    companies = list(store.all_companies())
    if tag:
        companies = [c for c in companies if tag in c.tags]
    if not companies:
        console.print("[dim]No companies found.[/dim]")
        return
    for c in sorted(companies, key=lambda x: x.display_name.lower()):
        tags = f" [dim]{', '.join(c.tags)}[/dim]" if c.tags else ""
        console.print(f"  [{short_id(c.id)}]  {c.display_name}{tags}")
