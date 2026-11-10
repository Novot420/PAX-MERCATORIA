import tomllib
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config.toml"


def load_config(config_path=CONFIG_PATH):
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    try:
        with open(config_path, "rb") as config_file:
            return tomllib.load(config_file)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(
            f"Invalid configuration file: {error}"
        ) from error
