from app.core.config import load_config
from app.core.logger import setup_logging


def main():
    logger = setup_logging()

    logger.info("PAX MERCATORIA is starting.")

    config = load_config()

    logger.info(f"Application: {config['app']['name']}")
    logger.info(f"Version: {config['app']['version']}")
    logger.info("Configuration loaded successfully.")

    logger.info(f"Application: {config['app']['name']}")
    logger.info(f"Version: {config['app']['version']}")
    logger.info(f"Tagline: {config['app']['identity']['tagline']}")


if __name__ == "__main__":
    main()