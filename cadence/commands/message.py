"""cadence msg — log and view messages."""

import click
from rich.console import Console

from cadence.config import load_config
from cadence.commands.application import resolve_application
from cadence.models import Message
from cadence.storage import Store
from cadence.utils.cli import resolve_or_pick, short_id

console = Console()


@click.group()
def msg() -> None:
    """Log and view messages."""
    pass


@msg.command("add")
@click.option("--app", "app_query", default=None, help="Application ID prefix")
@click.option("--person", "person_query", default=None, help="Person name or ID")
@click.option("--direction", type=click.Choice(["inbound", "outbound"]),
              prompt=True)
@click.option("--channel", type=click.Choice(["email", "linkedin", "phone", "other"]),
              prompt=True)
@click.option("--subject", default=None)
@click.option("--body", prompt="Body (or summary)")
@click.option("--request-doc", multiple=True,
              help="Document type requested (e.g. resume). Repeatable.")
def msg_add(app_query, person_query, direction, channel, subject, body, request_doc) -> None:
    """Log a message."""
    store = Store(load_config())

    app_id = None
    if app_query:
        application = resolve_application(store, app_query)
        if not application:
            return
        app_id = application.id

    person_id = None
    if person_query:
        p = resolve_or_pick(person_query, store.find_person,
                            lambda x: x.name, "person")
        if p:
            person_id = p.id

    if not app_id and not person_id:
        console.print("[red]Provide --app or --person[/red]")
        return

    from cadence.models.message import RequestedDocument
    from cadence.models.base import now_utc

    docs = [RequestedDocument(type=d) for d in request_doc]

    m = Message(
        direction=direction,
        channel=channel,
        body=body,
        subject=subject,
        application_id=app_id,
        person_id=person_id,
        requested_documents=docs,
    )
    store.save_message(m)
    console.print(f"[green]Message logged[/green] [{short_id(m.id)}]")


@msg.command("list")
@click.option("--app", "app_query", default=None, help="Application ID prefix")
@click.option("--person", "person_query", default=None)
@click.option("--unanswered", is_flag=True, default=False)
def msg_list(app_query, person_query, unanswered) -> None:
    """List messages."""
    store = Store(load_config())

    if person_query:
        p = resolve_or_pick(person_query, store.find_person,
                            lambda x: x.name, "person")
        messages = store.messages_for_person(p.id) if p else []
    elif app_query:
        application = resolve_application(store, app_query)
        messages = store.messages_for_application(application.id) if application else []
    else:
        messages = list(store.all_messages())

    if not messages:
        console.print("[dim]No messages found.[/dim]")
        return

    people = {p.id: p for p in store.all_people()}

    for m in sorted(messages, key=lambda x: x.sent_at, reverse=True):
        who = people.get(m.person_id or "")
        who_str = f"  {who.name}" if who else ""
        docs = ""
        if m.requested_documents:
            pending = [d.type for d in m.requested_documents if not d.sent_at]
            if pending:
                docs = f"  [yellow]docs: {', '.join(pending)}[/yellow]"
        console.print(
            f"  [{short_id(m.id)}]  {m.sent_at[:10]}  "
            f"{'→' if m.direction == 'outbound' else '←'}  "
            f"{m.channel}{who_str}{docs}"
        )
