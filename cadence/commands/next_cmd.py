"""cadence next — surface everything that needs attention today."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

import click
from rich.console import Console
from rich.rule import Rule

from cadence.config import load_config
from cadence.storage import Store
from cadence.models.application import TERMINAL_STATUSES
from cadence.utils.cli import short_id

console = Console()

_TERMINAL_STATUSES = TERMINAL_STATUSES


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(dt: Optional[datetime]) -> Optional[float]:
    if dt is None:
        return None
    return (_now() - dt).total_seconds() / 86400


@click.command()
def next_cmd() -> None:
    """Show everything that needs attention today."""
    config = load_config()
    store = Store(config)
    t = config.thresholds

    msg_days = t.get("message_followup_days", 5)
    app_days = t.get("application_followup_days", 14)
    ghosted_days = t.get("ghosted_days", 30)
    thankyou_hours = t.get("interview_thankyou_hours", 48)
    prep_days = t.get("interview_prep_days", 2)

    urgent = []
    respond = []
    followup = []
    interview_items = []

    # Build company + JD lookup maps for display
    companies = {c.id: c for c in store.all_companies()}
    jds = {j.id: j for j in store.all_job_descriptions()}

    def company_name(app) -> str:
        c = companies.get(app.company_id)
        return c.display_name if c else app.company_id[:8]

    def role_label(app) -> str:
        if app.job_description_id and app.job_description_id in jds:
            return jds[app.job_description_id].title
        return app.role_title or "unknown role"

    # ---- Applications ------------------------------------------------ #
    for app in store.all_applications():
        if app.status in _TERMINAL_STATUSES:
            continue

        label = f"{company_name(app)} — {role_label(app)} [{short_id(app.id)}]"

        # JD closing date
        jd = jds.get(app.job_description_id or "")
        if jd and jd.closes_at:
            closes = _parse_dt(jd.closes_at)
            if closes:
                days_left = (closes - _now()).days
                if days_left <= 3:
                    urgent.append(
                        f"[red]JD closes in {days_left}d[/red]  {label}"
                    )

        # Take-home deadline
        th = store.take_home_for_application(app.id)
        if th and not th.is_submitted and th.due_at:
            due = _parse_dt(th.due_at)
            if due:
                days_left = (due - _now()).days
                if days_left <= 3:
                    urgent.append(
                        f"[red]Take-home due in {days_left}d[/red]  {label}"
                    )

        # Offer expiry
        offer = store.offer_for_application(app.id)
        if offer and offer.status == "pending" and offer.expires_at:
            exp = _parse_dt(offer.expires_at)
            if exp:
                days_left = (exp - _now()).days
                if days_left <= 3:
                    urgent.append(
                        f"[red]Offer expires in {days_left}d[/red]  {label}"
                    )

        # Application-level follow-up (no status change in N days)
        threshold = app.follow_up_after_days or app_days
        if app.status_history:
            last_transition = _parse_dt(app.status_history[-1].at)
            age = _days_ago(last_transition)
            if age and age > ghosted_days:
                followup.append(
                    f"[dim]Possibly ghosted ({int(age)}d)[/dim]  {label}"
                )
            elif age and age > threshold:
                followup.append(
                    f"[yellow]No update in {int(age)}d[/yellow]  {label}"
                )

        # Interview: prep reminder and thank-you
        for iv in app.interviews:
            scheduled = _parse_dt(iv.scheduled_at)
            completed = _parse_dt(iv.completed_at)

            if scheduled and not completed:
                days_until = (scheduled - _now()).total_seconds() / 86400
                if 0 < days_until <= prep_days:
                    interview_items.append(
                        f"[cyan]Prep reminder[/cyan]  {label} — "
                        f"{iv.round_type} in {int(days_until * 24)}h"
                    )

            if completed and not iv.thank_you_sent:
                hours_since = (_now() - completed).total_seconds() / 3600
                if hours_since <= thankyou_hours:
                    interview_items.append(
                        f"[cyan]Send thank-you[/cyan]  {label} — "
                        f"{iv.round_type} completed {int(hours_since)}h ago"
                    )

    # ---- Messages ---------------------------------------------------- #
    # Group messages: prefer surfacing under application, else under person
    people = {p.id: p for p in store.all_people()}

    for msg in store.all_messages():
        sent = _parse_dt(msg.sent_at)
        age = _days_ago(sent)
        if age is None:
            continue

        # Inbound with no reply yet — surfaces immediately
        if msg.direction == "inbound":
            # Check if there's a later outbound message in the same thread
            if msg.application_id:
                thread = store.messages_for_application(msg.application_id)
            elif msg.person_id:
                thread = store.messages_for_person(msg.person_id)
            else:
                thread = []

            has_reply = any(
                m.direction == "outbound" and
                _parse_dt(m.sent_at) and
                _parse_dt(m.sent_at) > sent  # type: ignore[operator]
                for m in thread
            )
            if not has_reply:
                who = ""
                if msg.person_id and msg.person_id in people:
                    who = f" from {people[msg.person_id].name}"
                context = ""
                if msg.application_id:
                    app = store.get_application(msg.application_id)
                    if app:
                        context = f" ({company_name(app)})"
                respond.append(
                    f"[green]Reply needed[/green]{context}{who} — "
                    f"{int(age)}d ago [{short_id(msg.id)}]"
                )

        # Outbound with no response after threshold
        elif msg.direction == "outbound" and age > msg_days:
            if msg.application_id:
                thread = store.messages_for_application(msg.application_id)
            elif msg.person_id:
                thread = store.messages_for_person(msg.person_id)
            else:
                thread = []

            has_response = any(
                m.direction == "inbound" and
                _parse_dt(m.sent_at) and
                _parse_dt(m.sent_at) > sent  # type: ignore[operator]
                for m in thread
            )
            if not has_response:
                context = ""
                if msg.application_id:
                    app = store.get_application(msg.application_id)
                    if app:
                        context = f" ({company_name(app)})"
                elif msg.person_id and msg.person_id in people:
                    context = f" ({people[msg.person_id].name})"
                followup.append(
                    f"[yellow]No reply to outbound{context}[/yellow] — "
                    f"{int(age)}d ago [{short_id(msg.id)}]"
                )

        # Unfulfilled document requests
        for doc in msg.requested_documents:
            if not doc.sent_at:
                context = ""
                if msg.application_id:
                    app = store.get_application(msg.application_id)
                    if app:
                        context = f"{company_name(app)} — "
                respond.append(
                    f"[green]Send {doc.type}[/green]  {context}"
                    f"requested {int(age)}d ago [{short_id(msg.id)}]"
                )

    # ---- Output ------------------------------------------------------ #
    nothing = not any([urgent, respond, followup, interview_items])
    if nothing:
        console.print("[green]All clear — nothing needs attention right now.[/green]")
        return

    if urgent:
        console.print(Rule("[bold red]URGENT[/bold red]"))
        for item in urgent:
            console.print(f"  {item}")

    if interview_items:
        console.print(Rule("[bold cyan]INTERVIEWS[/bold cyan]"))
        for item in interview_items:
            console.print(f"  {item}")

    if respond:
        console.print(Rule("[bold green]RESPOND[/bold green]"))
        for item in respond:
            console.print(f"  {item}")

    if followup:
        console.print(Rule("[bold yellow]FOLLOW UP[/bold yellow]"))
        for item in followup:
            console.print(f"  {item}")
