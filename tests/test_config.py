import pytest

from app.core.config import (
    BASE_DIR,
    get_database_path,
    load_config,
    validate_config,
)


VALID_CONFIG_TOML = """
[app]
name = "Test App"
version = "1.0.0"
environment = "development"
debug = false

[app.identity]
tagline = "Test tagline"

[database]
path = "data/test.db"
"""


def make_valid_config():
    return {
        "app": {
            "name": "Test App",
            "version": "1.0.0",
            "environment": "development",
            "debug": False,
            "identity": {"tagline": "Test tagline"},
        },
        "database": {"path": "data/test.db"},
    }


def test_load_config_reads_valid_file(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(VALID_CONFIG_TOML, encoding="utf-8")

    config = load_config(config_file)

    assert config["app"]["name"] == "Test App"


def test_project_config_file_is_valid():
    config = load_config()

    assert config["app"]["name"] == "PAX MERCATORIA"


def test_load_config_raises_error_for_missing_file(tmp_path):
    missing_file = tmp_path / "missing.toml"

    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        load_config(missing_file)


def test_load_config_raises_error_for_invalid_toml(tmp_path):
    invalid_file = tmp_path / "invalid.toml"
    invalid_file.write_text('name = “PAX MERCATORIA”', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid configuration file"):
        load_config(invalid_file)


def test_load_config_rejects_incomplete_file(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[app]\nname = "Test App"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required setting: app.version"):
        load_config(config_file)


def test_validate_config_accepts_valid_config():
    validate_config(make_valid_config())


def test_validate_config_rejects_missing_setting():
    config = make_valid_config()
    del config["app"]["version"]

    with pytest.raises(ValueError, match="Missing required setting: app.version"):
        validate_config(config)


def test_validate_config_rejects_wrong_type():
    config = make_valid_config()
    config["app"]["debug"] = "yes"

    with pytest.raises(ValueError, match="app.debug must be of type bool"):
        validate_config(config)


def test_validate_config_rejects_unknown_environment():
    config = make_valid_config()
    config["app"]["environment"] = "prodution"

    with pytest.raises(ValueError, match="app.environment must be one of"):
        validate_config(config)


def test_validate_config_rejects_missing_database_section():
    config = make_valid_config()
    del config["database"]

    with pytest.raises(ValueError, match=r"Missing required setting: \[database\]"):
        validate_config(config)


def test_validate_config_rejects_non_text_database_path():
    config = make_valid_config()
    config["database"]["path"] = 123

    with pytest.raises(ValueError, match="database.path must be of type str"):
        validate_config(config)


def test_validate_config_rejects_empty_database_path():
    config = make_valid_config()
    config["database"]["path"] = "   "

    with pytest.raises(ValueError, match="database.path must not be empty"):
        validate_config(config)


def test_get_database_path_resolves_relative_path_from_project_root():
    config = make_valid_config()

    assert get_database_path(config) == BASE_DIR / "data" / "test.db"


def test_get_database_path_keeps_absolute_path(tmp_path):
    config = make_valid_config()
    config["database"]["path"] = str(tmp_path / "custom.db")

    assert get_database_path(config) == tmp_path / "custom.db"


def test_project_database_path_is_inside_data_directory():
    config = load_config()

    assert get_database_path(config) == BASE_DIR / "data" / "pax_mercatoria.db"
