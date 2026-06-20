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


def _application_label(store: Store, a: Application) -> str:
    companies = {c.id: c for c in store.all_companies()}
    jds = {j.id: j for j in store.all_job_descriptions()}
    company = companies.get(a.company_id)
    jd = jds.get(a.job_description_id or "")
    role = a.role_title or (jd.title if jd else "—")
    co = company.display_name if company else "?"
    return f"{co} — {role}  [{a.status}]  [{short_id(a.id)}]"


def resolve_application(store: Store, query: str) -> Application | None:
    """Resolve an application by ID prefix, prompting if ambiguous."""
    return resolve_or_pick(
        query, store.find_application,
        lambda a: _application_label(store, a), "application"
    )


@click.group()
def app() -> None:
    """Manage job applications."""
    pass


@app.command("add")
@click.option("--company", "company_query", default=None,
              help="Company name prefix or ID")
@click.option("--jd", "jd_query", default=None, help="Job description ID prefix")
@click.option("--role", default=None, help="Role title (if no JD)")
@click.option("--source", default=None,
              help="e.g. linkedin, referral, hacker_news")
@click.option("--resume", default=None, help="Resume version label")
@click.option("--status", default="started",
              type=click.Choice(VALID_STATUSES), show_default=True)
def app_add(company_query, jd_query, role, source, resume, status) -> None:
    """Add a new application."""
    config = load_config()
    store = Store(config)

    # Resolve company
    if not company_query and not jd_query:
        company_query = click.prompt("Company name or ID")

    jd_id = None
    company_id = None
    if jd_query:
        jd = resolve_or_pick(
            jd_query, store.find_job_description,
            lambda j: f"{j.title}  [{short_id(j.id)}]", "job description"
        )
        if not jd:
            return
        jd_id = jd.id
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
@click.argument("app_query")
def app_show(app_query: str) -> None:
    """Show an application. Accepts ID or unique ID prefix."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
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
@click.argument("app_query")
@click.argument("new_status", type=click.Choice(VALID_STATUSES))
@click.option("--notes", default="", help="Reason or context for this change")
def app_status(app_query: str, new_status: str, notes: str) -> None:
    """Update the status of an application."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return
    application.transition(new_status, notes=notes)
    if new_status == "applied" and not application.applied_at:
        application.applied_at = application.status_history[-1].at
    store.save_application(application)
    console.print(f"[green]Status updated[/green] → {new_status}")


@app.command("submit")
@click.argument("app_query")
@click.option("--notes", default="")
def app_submit(app_query: str, notes: str) -> None:
    """Mark an application as submitted (started → applied)."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return
    application.transition("applied", notes=notes)
    application.applied_at = application.status_history[-1].at
    store.save_application(application)
    console.print(f"[green]Submitted.[/green] Status → applied")


@app.command("cancel")
@click.argument("app_query")
@click.option("--notes", default="", help="Why you're abandoning this application")
def app_cancel(app_query: str, notes: str) -> None:
    """Abandon an application before submitting it (started → canceled)."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return
    application.transition("canceled", notes=notes)
    store.save_application(application)
    console.print("[yellow]Application canceled.[/yellow]")


@app.command("note")
@click.argument("app_query")
def app_note(app_query: str) -> None:
    """Edit notes on an application in $EDITOR."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return
    application.notes = open_in_editor(application.notes)
    store.save_application(application)
    console.print("[green]Notes saved.[/green]")


@app.command("cover")
@click.argument("app_query")
@click.option("--version", default=None, help="Version label for this cover letter")
def app_cover(app_query: str, version: str) -> None:
    """Compose or edit the cover letter for an application in $EDITOR."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return
    application.cover_letter = open_in_editor(application.cover_letter)
    if version:
        application.cover_letter_version = version
    store.save_application(application)
    console.print("[green]Cover letter saved.[/green]")
