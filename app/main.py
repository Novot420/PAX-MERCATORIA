import sqlite3
import sys

from app.core.config import get_database_path, load_config
from app.core.logger import set_log_level, setup_logging
from app.database.initialization import initialize_database
from app.database.migrations import MigrationError


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

    try:
        schema_version = initialize_database(get_database_path(config))
    except (OSError, sqlite3.Error, MigrationError) as error:
        logger.error(f"Startup failed: database error: {error}")
        sys.exit(1)

    logger.info(f"Database ready (schema version {schema_version}).")


if __name__ == "__main__":
    main()