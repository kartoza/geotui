"""CLI interface for GeoTUI.

Provides subcommands for bulk publish, export, and import-config
that can be run headlessly or from CI pipelines.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from geotui import __version__
from geotui.config import ConfigManager
from geotui.publisher import NamingStrategy, PublishConfig


def _unlock_config(cm: ConfigManager):
    """Prompt for the master password and unlock the vault.

    If the vault is not set up, prompts the user to create one.
    Exits on failure.

    Args:
        cm: ConfigManager instance.

    Returns:
        Fernet instance for decrypting credentials, or None if no vault.
    """
    if not cm.has_vault:
        if not cm.config.connections:
            return None  # No connections, nothing to protect
        # Existing connections without vault - prompt to set up
        click.echo("Your connections are not encrypted yet.")
        pw = click.prompt("Create a master password", hide_input=True)
        pw_confirm = click.prompt("Confirm master password", hide_input=True)
        if pw != pw_confirm:
            click.echo("Error: Passwords do not match.", err=True)
            sys.exit(1)
        if len(pw) < 8:
            click.echo("Error: Password must be at least 8 characters.", err=True)
            sys.exit(1)
        cm.init_vault(pw)
        click.echo("Vault created. Credentials are now encrypted.")
        return cm.unlock(pw)

    for attempt in range(3):
        pw = click.prompt("Master password", hide_input=True)
        fernet = cm.unlock(pw)
        if fernet:
            return fernet
        remaining = 2 - attempt
        if remaining:
            click.echo(f"Wrong password. {remaining} attempt(s) remaining.", err=True)
    click.echo("Error: Too many failed attempts.", err=True)
    sys.exit(1)


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """GeoTUI - GeoServer Manager."""


@cli.command()
@click.option("--connection", "-c", required=True, help="Saved connection name")
@click.option("--workspace", "-w", required=True, help="Target workspace")
@click.option("--datastore", "-d", required=True, help="Target datastore")
@click.option(
    "--source",
    "-s",
    required=True,
    type=click.Path(exists=True),
    help="Source directory",
)
@click.option(
    "--naming",
    default="basename",
    type=click.Choice(["basename", "prefixed_basename", "path_slug"]),
)
@click.option("--prefix", default="", help="Prefix for prefixed_basename strategy")
@click.option("--concurrency", default=4, type=int, help="Max concurrent uploads")
@click.option("--dry-run", is_flag=True, help="Validate without uploading")
@click.option("--fail-fast", is_flag=True, help="Abort on first failure")
@click.option("--output", "-o", type=click.Path(), help="Report output directory")
@click.option("--config-path", type=click.Path(), help="Override config file path")
def publish(
    connection: str,
    workspace: str,
    datastore: str,
    source: str,
    naming: str,
    prefix: str,
    concurrency: int,
    dry_run: bool,
    fail_fast: bool,
    output: str | None,
    config_path: str | None,
) -> None:
    """Bulk publish shapefiles to GeoServer."""
    from geotui.publisher import run_publish
    from geotui.report import generate_json_report, generate_pdf_report

    cfg_path = Path(config_path) if config_path else None
    cm = ConfigManager(config_path=cfg_path)
    fernet = _unlock_config(cm)
    conn = cm.get_connection_by_name(connection)
    if not conn:
        click.echo(f"Error: Connection '{connection}' not found.", err=True)
        sys.exit(1)
    # Decrypt the connection password
    if fernet:
        conn = cm.decrypt_connection(conn, fernet)

    config = PublishConfig(
        workspace=workspace,
        datastore=datastore,
        source_directory=Path(source),
        naming=NamingStrategy(naming),
        prefix=prefix,
        concurrency=concurrency,
        dry_run=dry_run,
        fail_fast=fail_fast,
    )

    def progress(current: int, total: int, name: str) -> None:
        click.echo(f"[{current}/{total}] {name}")

    report = asyncio.run(run_publish(conn, config, progress_callback=progress))

    out_dir = Path(output) if output else Path.cwd() / ".geotui" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
    pdf_path = out_dir / f"publish-{ts}.pdf"
    json_path = out_dir / f"publish-{ts}.json"

    generate_pdf_report(report, pdf_path)
    generate_json_report(report, json_path)

    click.echo(
        f"\nCreated: {report.created} | Updated: {report.updated} | "
        f"Failed: {report.failed} | Skipped: {report.skipped}"
    )
    click.echo(f"Total time: {report.wall_clock_seconds:.1f}s")
    click.echo(f"PDF report: {pdf_path}")
    click.echo(f"JSON report: {json_path}")

    if report.failed > 0:
        sys.exit(1)


@cli.command()
@click.option("--connection", "-c", required=True, help="Saved connection name")
@click.option("--workspace", "-w", required=True, help="Workspace to export")
@click.option(
    "--output", "-o", required=True, type=click.Path(), help="Output directory"
)
@click.option("--config-path", type=click.Path(), help="Override config file path")
def export(
    connection: str,
    workspace: str,
    output: str,
    config_path: str | None,
) -> None:
    """Export GeoServer workspace configuration."""
    click.echo(f"Exporting workspace '{workspace}' to {output}")


@cli.command("import-config")
@click.option("--connection", "-c", required=True, help="Target connection name")
@click.option(
    "--input",
    "-i",
    "input_dir",
    required=True,
    type=click.Path(exists=True),
    help="Config directory",
)
@click.option("--config-path", type=click.Path(), help="Override config file path")
def import_config(
    connection: str,
    input_dir: str,
    config_path: str | None,
) -> None:
    """Import GeoServer workspace configuration."""
    click.echo(f"Importing config from {input_dir}")
