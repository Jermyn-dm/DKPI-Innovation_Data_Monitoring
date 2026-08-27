from __future__ import annotations

from dkpi_monitoring.logging_config import configure_logging


def main() -> None:
    """Initialize the application runtime for future monitoring features."""
    configure_logging()


if __name__ == "__main__":
    main()
