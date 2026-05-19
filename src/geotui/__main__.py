"""Entry point for GeoTUI application."""

from geotui.app import GeoTUIApp


def main() -> None:
    """Launch the GeoTUI application."""
    app = GeoTUIApp()
    app.run()


if __name__ == "__main__":
    main()
