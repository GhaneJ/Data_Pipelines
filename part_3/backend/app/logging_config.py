"""Small logging setup for local development and portfolio demos."""

from __future__ import annotations

import logging
import os


def configure_logging() -> None:
    """Configure readable application logging once."""
    if logging.getLogger().handlers:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
