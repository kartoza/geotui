"""Entry point for GeoTUI application."""

import sys


def main() -> None:
    """Launch GeoTUI.

    Routes to CLI if subcommand arguments are provided,
    otherwise launches the TUI.
    """
    cli_commands = {"publish", "export", "import-config", "--version", "--help"}
    if len(sys.argv) > 1 and sys.argv[1] in cli_commands:
        from geotui.cli import cli

        cli()
    else:
        from geotui.app import GeoTUIApp

        app = GeoTUIApp()
        app.run()


if __name__ == "__main__":
    main()
