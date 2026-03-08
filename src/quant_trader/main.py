"""Application entry point for QuantTrader phase 1 foundation."""

from __future__ import annotations

from quant_trader.config.settings import load_settings
from quant_trader.core.logging import configure_logging, get_logger


def main() -> None:
    """Bootstrap settings and logging for the application."""

    settings = load_settings()
    configure_logging(settings.logging)
    logger = get_logger(__name__)
    logger.info("%s starting in %s mode", settings.app_name, settings.environment)


if __name__ == "__main__":
    main()
