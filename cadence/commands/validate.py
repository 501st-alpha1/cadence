"""cadence validate — cross-repo integrity check."""

import click
from rich.console import Console

from cadence.config import load_config
from cadence.storage import Store

console = Console()


@click.command()
def validate() -> None:
    """Check referential integrity across both repos."""
    store = Store(load_config())
    errors: list[str] = []
    warnings: list[str] = []

    company_ids = {c.id for c in store.all_companies()}
    jd_ids = {j.id for j in store.all_job_descriptions()}
    person_ids = {p.id for p in store.all_people()}
    ref_ids = {r.id for r in store.all_reference_contacts()}

    # Job descriptions → companies
    for jd in store.all_job_descriptions():
        if jd.company_id not in company_ids:
            errors.append(
                f"job_description {jd.id[:8]}: company_id {jd.company_id[:8]} not found"
            )

    # Applications
    for app in store.all_applications():
        if app.company_id not in company_ids:
            errors.append(
                f"application {app.id[:8]}: company_id {app.company_id[:8]} not found"
            )
        if app.job_description_id and app.job_description_id not in jd_ids:
            errors.append(
                f"application {app.id[:8]}: job_description_id "
                f"{app.job_description_id[:8]} not found"
            )
        for iv in app.interviews:
            for session in iv.sessions:
                if session.interviewer_id not in person_ids:
                    warnings.append(
                        f"application {app.id[:8]} interview {iv.id[:8]}: "
                        f"interviewer {session.interviewer_id[:8]} not in people"
                    )
        for ar in app.application_references:
            if ar.reference_contact_id not in ref_ids:
                errors.append(
                    f"application {app.id[:8]}: reference_contact_id "
                    f"{ar.reference_contact_id[:8]} not found"
                )

    # People → companies (warning only — company_id is optional)
    for person in store.all_people():
        if person.company_id and person.company_id not in company_ids:
            warnings.append(
                f"person {person.id[:8]} ({person.name}): "
                f"company_id {person.company_id[:8]} not found"
            )

    # Reference contacts → people
    for rc in store.all_reference_contacts():
        if rc.person_id not in person_ids:
            errors.append(
                f"reference_contact {rc.id[:8]}: person_id "
                f"{rc.person_id[:8]} not found"
            )

    # Messages
    app_ids = {a.id for a in store.all_applications()}
    for msg in store.all_messages():
        if msg.application_id and msg.application_id not in app_ids:
            errors.append(
                f"message {msg.id[:8]}: application_id "
                f"{msg.application_id[:8]} not found"
            )
        if msg.person_id and msg.person_id not in person_ids:
            warnings.append(
                f"message {msg.id[:8]}: person_id "
                f"{msg.person_id[:8]} not found"
            )

    # Offers and take-homes → applications
    for offer in store.all_offers():
        if offer.application_id not in app_ids:
            errors.append(
                f"offer {offer.id[:8]}: application_id "
                f"{offer.application_id[:8]} not found"
            )
    for th in store.all_take_homes():
        if th.application_id not in app_ids:
            errors.append(
                f"take_home {th.id[:8]}: application_id "
                f"{th.application_id[:8]} not found"
            )

    # Output
    if not errors and not warnings:
        console.print("[green]✓ All good — no integrity issues found.[/green]")
        return

    if errors:
        console.print(f"\n[bold red]Errors ({len(errors)})[/bold red]")
        for e in errors:
            console.print(f"  [red]✗[/red] {e}")

    if warnings:
        console.print(f"\n[bold yellow]Warnings ({len(warnings)})[/bold yellow]")
        for w in warnings:
            console.print(f"  [yellow]![/yellow] {w}")
