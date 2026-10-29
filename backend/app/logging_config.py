import logging

from .config import settings


def setup_logging() -> None:
    """Configure root logging once. Never log API keys or full request URLs."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
