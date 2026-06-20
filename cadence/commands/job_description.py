"""cadence jd — manage job descriptions."""

import click
from rich.console import Console

from cadence.config import load_config
from cadence.models import JobDescription
from cadence.storage import Store
from cadence.utils.cli import resolve_or_pick, open_in_editor, short_id, print_kv

console = Console()


@click.group()
def jd() -> None:
    """Manage job descriptions."""
    pass


@jd.command("add")
@click.option("--company", "company_query", default=None)
@click.option("--title", default=None)
@click.option("--url", default=None)
@click.option("--source", default=None, help="e.g. linkedin, hacker_news, referral")
@click.option("--closes", default=None, help="Closing date YYYY-MM-DD")
def jd_add(company_query, title, url, source, closes) -> None:
    """Add a job description (paste body in $EDITOR)."""
    store = Store(load_config())

    if not company_query:
        company_query = click.prompt("Company name or ID")
    c = resolve_or_pick(company_query, store.find_company,
                        lambda x: x.display_name, "company")
    if not c:
        return

    title = title or click.prompt("Job title")
    body = open_in_editor("# Paste job description here\n")

    j = JobDescription(
        company_id=c.id,
        title=title,
        url=url,
        body=body,
        source=source,
        closes_at=closes,
    )
    store.save_job_description(j)
    console.print(f"[green]Added[/green] {title} [{short_id(j.id)}]")


@jd.command("show")
@click.argument("jd_query")
def jd_show(jd_query: str) -> None:
    """Show a job description. Accepts ID or unique ID prefix."""
    store = Store(load_config())
    j = resolve_or_pick(
        jd_query, store.find_job_description,
        lambda x: f"{x.title}  [{short_id(x.id)}]", "job description"
    )
    if not j:
        return
    companies = {c.id: c for c in store.all_companies()}
    company = companies.get(j.company_id)
    print_kv([
        ("ID", j.id),
        ("Company", company.display_name if company else j.company_id),
        ("Title", j.title),
        ("URL", j.url),
        ("Source", j.source),
        ("Captured", j.captured_at[:10]),
        ("Closes", j.closes_at),
    ])
    if j.body:
        console.print("\n[bold]Description[/bold]")
        console.print(j.body[:2000] + ("…" if len(j.body) > 2000 else ""))


@jd.command("list")
@click.option("--company", "company_query", default=None)
@click.option("--open", "open_only", is_flag=True, default=False,
              help="Only show JDs with no application yet")
def jd_list(company_query, open_only) -> None:
    """List job descriptions."""
    store = Store(load_config())
    companies = {c.id: c for c in store.all_companies()}
    applied_jd_ids = {
        a.job_description_id for a in store.all_applications()
        if a.job_description_id
    }

    jds = list(store.all_job_descriptions())
    if company_query:
        matches = store.find_company(company_query)
        ids = {c.id for c in matches}
        jds = [j for j in jds if j.company_id in ids]
    if open_only:
        jds = [j for j in jds if j.id not in applied_jd_ids]

    if not jds:
        console.print("[dim]No job descriptions found.[/dim]")
        return

    for j in sorted(jds, key=lambda x: x.captured_at, reverse=True):
        company = companies.get(j.company_id)
        applied = " [dim](applied)[/dim]" if j.id in applied_jd_ids else ""
        console.print(
            f"  [{short_id(j.id)}]  "
            f"{company.display_name if company else '?'}  —  "
            f"{j.title}{applied}"
        )
