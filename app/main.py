import sys

from app.core.config import load_config
from app.core.logger import set_log_level, setup_logging


def main():
    logger = setup_logging()

    logger.info("PAX MERCATORIA is starting.")

    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as error:
        logger.error(f"Startup failed: {error}")
        sys.exit(1)

    logger.info("Configuration loaded successfully.")

    set_log_level(config["app"]["debug"])
    logger.debug("Debug logging is enabled.")

    logger.info(f"Application: {config['app']['name']}")
    logger.info(f"Version: {config['app']['version']}")
    logger.info(f"Tagline: {config['app']['identity']['tagline']}")


if __name__ == "__main__":
    main()