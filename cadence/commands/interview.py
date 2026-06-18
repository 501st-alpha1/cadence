"""cadence interview — manage interview rounds."""

import click
from rich.console import Console

from cadence.config import load_config
from cadence.models.application import Interview, InterviewSession
from cadence.models.base import now_utc
from cadence.storage import Store
from cadence.utils.cli import resolve_or_pick, short_id

console = Console()

ROUND_TYPES = ["phone_screen", "technical", "system_design", "behavioural", "onsite", "final", "other"]


@click.group()
def interview() -> None:
    """Manage interview rounds."""
    pass


@interview.command("add")
@click.argument("app_id")
@click.option("--round", "round_type", type=click.Choice(ROUND_TYPES), prompt=True)
@click.option("--scheduled", prompt="Scheduled date/time (YYYY-MM-DD or ISO)")
@click.option("--notes", default="")
def interview_add(app_id: str, round_type: str, scheduled: str, notes: str) -> None:
    """Add an interview round to an application."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
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
@click.argument("app_id")
@click.argument("interview_id")
@click.option("--interviewer", "person_query", prompt="Interviewer name or ID")
@click.option("--format", "fmt", default=None,
              help="e.g. technical, behavioural, system_design")
@click.option("--notes", default="")
def interview_session(app_id: str, interview_id: str, person_query: str,
                      fmt: str, notes: str) -> None:
    """Add a session (interviewer + notes) to an interview round."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
        return

    iv = next((i for i in application.interviews if i.id.startswith(interview_id)), None)
    if not iv:
        console.print(f"[red]Interview {interview_id} not found on this application[/red]")
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
@click.argument("app_id")
@click.argument("interview_id")
@click.option("--notes", default="", help="Post-interview notes")
def interview_complete(app_id: str, interview_id: str, notes: str) -> None:
    """Mark an interview round as completed."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
        return

    iv = next((i for i in application.interviews if i.id.startswith(interview_id)), None)
    if not iv:
        console.print(f"[red]Interview {interview_id} not found[/red]")
        return

    iv.completed_at = now_utc()
    if notes:
        iv.notes = (iv.notes + "\n" + notes).strip()
    store.save_application(application)
    console.print(f"[green]Interview marked complete.[/green] Remember to send a thank-you!")


@interview.command("thankyou")
@click.argument("app_id")
@click.argument("interview_id")
def interview_thankyou(app_id: str, interview_id: str) -> None:
    """Mark thank-you sent for an interview round."""
    store = Store(load_config())
    application = store.get_application(app_id)
    if not application:
        console.print(f"[red]Application {app_id} not found[/red]")
        return

    iv = next((i for i in application.interviews if i.id.startswith(interview_id)), None)
    if not iv:
        console.print(f"[red]Interview {interview_id} not found[/red]")
        return

    iv.thank_you_sent = True
    store.save_application(application)
    console.print("[green]Thank-you marked as sent.[/green]")
