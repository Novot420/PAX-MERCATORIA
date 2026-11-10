import pytest

from app.core.config import load_config


def test_load_config_reads_valid_file(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[app]\nname = "Test App"\n', encoding="utf-8")

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
