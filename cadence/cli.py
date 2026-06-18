"""
cadence — a plain-text, git-native job search tracker

Usage:
    cadence next
    cadence company [add|show|list]
    cadence jd      [add|show|list]
    cadence app     [add|show|list|status|note|cover]
    cadence person  [add|show|list]
    cadence msg     [add|list]
    cadence interview [add|complete|thankyou]
    cadence takehome  [add|submit]
    cadence offer     [add|update|accept|decline]
    cadence ref       [add|list|use]
    cadence stats
    cadence validate
    cadence init
"""

import click
from rich.console import Console

from cadence.config import load_config, ensure_user_config
from cadence.storage import Store

console = Console()


def get_store() -> Store:
    config = load_config()
    return Store(config)


@click.group()
@click.version_option(version="0.1.0", prog_name="cadence")
def cli() -> None:
    """Cadence — job search tracker."""
    pass


# ------------------------------------------------------------------ #
# Init
# ------------------------------------------------------------------ #

@cli.command()
def init() -> None:
    """Create default config file and initialise data directories."""
    path = ensure_user_config()
    console.print(f"[green]Config written to[/green] {path}")
    console.print("Edit it to set your repo paths, then run [bold]cadence next[/bold].")


# ------------------------------------------------------------------ #
# Register command groups
# ------------------------------------------------------------------ #

from cadence.commands.next_cmd import next_cmd          # noqa: E402
from cadence.commands.company import company             # noqa: E402
from cadence.commands.job_description import jd         # noqa: E402
from cadence.commands.application import app            # noqa: E402
from cadence.commands.person import person              # noqa: E402
from cadence.commands.message import msg                # noqa: E402
from cadence.commands.interview import interview        # noqa: E402
from cadence.commands.offer import offer                # noqa: E402
from cadence.commands.reference import ref              # noqa: E402
from cadence.commands.stats import stats                # noqa: E402
from cadence.commands.validate import validate          # noqa: E402

cli.add_command(next_cmd, name="next")
cli.add_command(company)
cli.add_command(jd)
cli.add_command(app)
cli.add_command(person)
cli.add_command(msg)
cli.add_command(interview)
cli.add_command(offer)
cli.add_command(ref)
cli.add_command(stats)
cli.add_command(validate)
