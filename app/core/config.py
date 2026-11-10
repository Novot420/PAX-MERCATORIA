import tomllib
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config.toml"

ALLOWED_ENVIRONMENTS = ("development", "production")


def load_config(config_path=CONFIG_PATH):
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    try:
        with open(config_path, "rb") as config_file:
            config = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(
            f"Invalid configuration file: {error}"
        ) from error

    validate_config(config)
    return config


def validate_config(config):
    app = require_setting(config, "app", dict, "[app]")
    require_setting(app, "name", str, "app.name")
    require_setting(app, "version", str, "app.version")
    environment = require_setting(app, "environment", str, "app.environment")
    require_setting(app, "debug", bool, "app.debug")

    identity = require_setting(app, "identity", dict, "[app.identity]")
    require_setting(identity, "tagline", str, "app.identity.tagline")

    if environment not in ALLOWED_ENVIRONMENTS:
        raise ValueError(
            f"Setting app.environment must be one of: "
            f"{', '.join(ALLOWED_ENVIRONMENTS)}"
        )

    database = require_setting(config, "database", dict, "[database]")
    database_path = require_setting(database, "path", str, "database.path")

    if not database_path.strip():
        raise ValueError("Setting database.path must not be empty")


def get_database_path(config):
    database_path = Path(config["database"]["path"])

    if database_path.is_absolute():
        return database_path

    return BASE_DIR / database_path


def require_setting(section, key, expected_type, location):
    if key not in section:
        raise ValueError(f"Missing required setting: {location}")

    value = section[key]
    if not isinstance(value, expected_type):
        raise ValueError(
            f"Setting {location} must be of type {expected_type.__name__}"
        )

    return value
