"""cadence interview — manage interview rounds."""

from __future__ import annotations

import click
from rich.console import Console

from cadence.config import load_config
from cadence.commands.application import resolve_application
from cadence.models.application import Application, Interview, InterviewSession
from cadence.models.base import now_utc
from cadence.storage import Store
from cadence.utils.cli import resolve_or_pick, short_id

console = Console()

ROUND_TYPES = ["phone_screen", "technical", "system_design", "behavioural", "onsite", "final", "other"]


def resolve_interview(application: Application, query: str) -> Interview | None:
    """Resolve an interview round on an application by ID prefix, prompting if ambiguous."""
    q = query.lower()
    matches = [i for i in application.interviews if i.id.lower().startswith(q)]
    if not matches:
        console.print(f"[red]No interview found matching '{query}' on this application[/red]")
        return None
    if len(matches) == 1:
        return matches[0]
    console.print(f"[yellow]Multiple interviews match '{query}':[/yellow]")
    for i, iv in enumerate(matches, 1):
        console.print(f"  {i}. {iv.round_type}  {iv.scheduled_at[:10]}  [{short_id(iv.id)}]")
    choice = click.prompt("Pick one", type=click.IntRange(1, len(matches)))
    return matches[choice - 1]


@click.group()
def interview() -> None:
    """Manage interview rounds."""
    pass


@interview.command("add")
@click.argument("app_query")
@click.option("--round", "round_type", type=click.Choice(ROUND_TYPES), prompt=True)
@click.option("--scheduled", prompt="Scheduled date/time (YYYY-MM-DD or ISO)")
@click.option("--notes", default="")
def interview_add(app_query: str, round_type: str, scheduled: str, notes: str) -> None:
    """Add an interview round to an application."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return

    iv = Interview(
        round_type=round_type,
        scheduled_at=scheduled,
        notes=notes,
    )
    application.interviews.append(iv)
    # Move status to interview if not already further along
    current = application.status or ""
    if current in ("applied", "phone_screen", "saved"):
        application.transition("interview")
    store.save_application(application)
    console.print(f"[green]Interview added[/green] {round_type} on {scheduled} [{short_id(iv.id)}]")


@interview.command("session")
@click.argument("app_query")
@click.argument("interview_query")
@click.option("--interviewer", "person_query", prompt="Interviewer name or ID")
@click.option("--format", "fmt", default=None,
              help="e.g. technical, behavioural, system_design")
@click.option("--notes", default="")
def interview_session(app_query: str, interview_query: str, person_query: str,
                      fmt: str, notes: str) -> None:
    """Add a session (interviewer + notes) to an interview round."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return

    iv = resolve_interview(application, interview_query)
    if not iv:
        return

    p = resolve_or_pick(person_query, store.find_person, lambda x: x.name, "person")
    if not p:
        return

    session = InterviewSession(
        interviewer_id=p.id,
        format=fmt,
        notes=notes,
    )
    iv.sessions.append(session)
    store.save_application(application)
    console.print(f"[green]Session added[/green] with {p.name}")


@interview.command("complete")
@click.argument("app_query")
@click.argument("interview_query")
@click.option("--notes", default="", help="Post-interview notes")
def interview_complete(app_query: str, interview_query: str, notes: str) -> None:
    """Mark an interview round as completed."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return

    iv = resolve_interview(application, interview_query)
    if not iv:
        return

    iv.completed_at = now_utc()
    if notes:
        iv.notes = (iv.notes + "\n" + notes).strip()
    store.save_application(application)
    console.print(f"[green]Interview marked complete.[/green] Remember to send a thank-you!")


@interview.command("thankyou")
@click.argument("app_query")
@click.argument("interview_query")
def interview_thankyou(app_query: str, interview_query: str) -> None:
    """Mark thank-you sent for an interview round."""
    store = Store(load_config())
    application = resolve_application(store, app_query)
    if not application:
        return

    iv = resolve_interview(application, interview_query)
    if not iv:
        return

    iv.thank_you_sent = True
    store.save_application(application)
    console.print("[green]Thank-you marked as sent.[/green]")
