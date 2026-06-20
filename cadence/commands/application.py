"""cadence app — manage job applications."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from cadence.config import load_config
from cadence.models import Application, ApplicationStatus
from cadence.models.application import TERMINAL_STATUSES
from cadence.storage import Store
from cadence.utils.cli import resolve_or_pick, open_in_editor, short_id, print_kv

console = Console()

VALID_STATUSES = [s.value for s in ApplicationStatus]


@click.group()
def app() -> None:
    """Manage job applications."""
    pass


@app.command("add")
@click.option("--company", "company_query", default=None,
              help="Company name prefix or ID")
@click.option("--jd", "jd_id", default=None, help="Job description ID")
@click.option("--role", default=None, help="Role title (if no JD)")
@click.option("--source", default=None,
              help="e.g. linkedin, referral, hacker_news")
@click.option("--resume", default=None, help="Resume version label")
@click.option("--status", default="started",
              type=click.Choice(VALID_STATUSES), show_default=True)
def app_add(company_query, jd_id, role, source, resume, status) -> None:
    """Add a new application."""
    config = load_config()
    store = Store(config)

    # Resolve company
    if not company_query and not jd_id:
        company_query = click.prompt("Company name or ID")

    company_id = None
    if jd_id:
        jd = store.get_job_description(jd_id)
        if not jd:
            console.print(f"[red]Job description {jd_id} not found[/red]")
            return
        company_id = jd.company_id
        role = role or jd.title
    else:
        c = resolve_or_pick(company_query, store.find_company,
                            lambda x: x.display_name, "company")
        if not c:
            return
        company_id = c.id

    if not role:
        role = click.prompt("Role title")

    resume_version = resume or config.get("resume", "default_version")

    application = Application(
        company_id=company_id,
        job_description_id=jd_id,
        role_title=role,
        source=source,
        resume_version=resume_version,
    )
    application.transition(status)
    if status == "applied":
        application.applied_at = application.status_history[-1].at

    store.save_application(application)
    console.print(
        f"[green]Added application[/green] {role} [{short_id(application.id)}]"
    )


@app.command("show")
@click.argument("app_id")
def app_show(app_id: str) -> None:
    """Show an application."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        # Try prefix match
        matches = [
            a for a in store.all_applications()
            if a.id.startswith(app_id)
        ]
        if len(matches) == 1:
            application = matches[0]
        elif len(matches) > 1:
            console.print("[yellow]Multiple matches — be more specific[/yellow]")
            return
        else:
            console.print(f"[red]Application {app_id} not found[/red]")
            return

    companies = {c.id: c for c in store.all_companies()}
    jds = {j.id: j for j in store.all_job_descriptions()}

    company = companies.get(application.company_id)
    jd = jds.get(application.job_description_id or "")

    print_kv([
        ("ID", application.id),
        ("Company", company.display_name if company else application.company_id),
        ("Role", application.role_title or (jd.title if jd else "—")),
        ("Status", application.status),
        ("Applied", application.applied_at),
        ("Source", application.source),
        ("Resume", application.resume_version),
        ("Cover letter", application.cover_letter_version or ("yes" if application.cover_letter else None)),
        ("Notes", application.notes),
    ], title="Application")

    if application.status_history:
        console.print("\n[bold]Status history[/bold]")
        for transition in application.status_history:
            note = f"  [dim]{transition.notes}[/dim]" if transition.notes else ""
            console.print(f"  {transition.at[:10]}  {transition.status}{note}")

    if application.interviews:
        console.print("\n[bold]Interviews[/bold]")
        for iv in application.interviews:
            done = "✓" if iv.completed_at else " "
            ty = "✓" if iv.thank_you_sent else " "
            console.print(
                f"  [{done}] {iv.round_type}  {iv.scheduled_at[:10]}"
                f"  [thank-you:{ty}]  [{short_id(iv.id)}]"
            )


@app.command("list")
@click.option("--status", default=None, type=click.Choice(VALID_STATUSES))
@click.option("--company", "company_query", default=None)
@click.option("--active", is_flag=True, default=False,
              help="Exclude terminal statuses")
def app_list(status, company_query, active) -> None:
    """List applications."""
    store = Store(load_config())
    companies = {c.id: c for c in store.all_companies()}
    jds = {j.id: j for j in store.all_job_descriptions()}

    applications = list(store.all_applications())

    if active:
        applications = [a for a in applications if a.status not in TERMINAL_STATUSES]
    if status:
        applications = [a for a in applications if a.status == status]
    if company_query:
        matches = store.find_company(company_query)
        ids = {c.id for c in matches}
        applications = [a for a in applications if a.company_id in ids]

    if not applications:
        console.print("[dim]No applications found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("ID", style="dim", width=9)
    table.add_column("Company")
    table.add_column("Role")
    table.add_column("Status")
    table.add_column("Applied", style="dim")

    for a in sorted(applications, key=lambda x: x.applied_at or x.created_at, reverse=True):
        company = companies.get(a.company_id)
        jd = jds.get(a.job_description_id or "")
        role = a.role_title or (jd.title if jd else "—")
        table.add_row(
            short_id(a.id),
            company.display_name if company else "—",
            role,
            a.status or "—",
            (a.applied_at or "")[:10],
        )

    console.print(table)


@app.command("status")
@click.argument("app_id")
@click.argument("new_status", type=click.Choice(VALID_STATUSES))
@click.option("--notes", default="", help="Reason or context for this change")
def app_status(app_id: str, new_status: str, notes: str) -> None:
    """Update the status of an application."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
        return
    application.transition(new_status, notes=notes)
    if new_status == "applied" and not application.applied_at:
        application.applied_at = application.status_history[-1].at
    store.save_application(application)
    console.print(f"[green]Status updated[/green] → {new_status}")


@app.command("submit")
@click.argument("app_id")
@click.option("--notes", default="")
def app_submit(app_id: str, notes: str) -> None:
    """Mark an application as submitted (started → applied)."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
        return
    application.transition("applied", notes=notes)
    application.applied_at = application.status_history[-1].at
    store.save_application(application)
    console.print(f"[green]Submitted.[/green] Status → applied")


@app.command("cancel")
@click.argument("app_id")
@click.option("--notes", default="", help="Why you're abandoning this application")
def app_cancel(app_id: str, notes: str) -> None:
    """Abandon an application before submitting it (started → canceled)."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
        return
    application.transition("canceled", notes=notes)
    store.save_application(application)
    console.print("[yellow]Application canceled.[/yellow]")


@app.command("note")
@click.argument("app_id")
def app_note(app_id: str) -> None:
    """Edit notes on an application in $EDITOR."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
        return
    application.notes = open_in_editor(application.notes)
    store.save_application(application)
    console.print("[green]Notes saved.[/green]")


@app.command("cover")
@click.argument("app_id")
@click.option("--version", default=None, help="Version label for this cover letter")
def app_cover(app_id: str, version: str) -> None:
    """Compose or edit the cover letter for an application in $EDITOR."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
        return
    application.cover_letter = open_in_editor(application.cover_letter)
    if version:
        application.cover_letter_version = version
    store.save_application(application)
    console.print("[green]Cover letter saved.[/green]")
