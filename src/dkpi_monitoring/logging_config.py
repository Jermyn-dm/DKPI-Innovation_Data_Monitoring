from __future__ import annotations

import logging.config
from pathlib import Path


DEFAULT_LOGGING_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "logging.ini"


def configure_logging(config_path: Path | None = None) -> None:
    """Configure application logging from the repository logging configuration."""
    logging.config.fileConfig(
        config_path or DEFAULT_LOGGING_CONFIG,
        disable_existing_loggers=False,
    )
