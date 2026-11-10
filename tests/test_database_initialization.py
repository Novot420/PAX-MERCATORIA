import sqlite3
from contextlib import closing

import pytest

from app.database.connection import open_connection
from app.database.initialization import initialize_database
from app.database.migrations import MigrationError


def write_migration(migrations_directory, name, sql):
    migrations_directory.mkdir(exist_ok=True)
    (migrations_directory / name).write_text(sql, encoding="utf-8")


def test_initialize_database_creates_private_database(tmp_path):
    database_path = tmp_path / "data" / "test.db"
    migrations_directory = tmp_path / "migrations"
    migrations_directory.mkdir()

    assert initialize_database(database_path, migrations_directory) == 0
    assert database_path.parent.stat().st_mode & 0o777 == 0o700
    assert database_path.stat().st_mode & 0o777 == 0o600


def test_initialize_database_applies_migrations(tmp_path):
    database_path = tmp_path / "test.db"
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")
    write_migration(migrations_directory, "002_second.sql", "CREATE TABLE second (id INTEGER);")

    assert initialize_database(database_path, migrations_directory) == 2

    with closing(open_connection(database_path)) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name"
        ).fetchall()
        assert [row["name"] for row in rows] == ["first", "second"]


def test_initialize_database_is_safe_on_repeated_startup(tmp_path):
    database_path = tmp_path / "test.db"
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")

    assert initialize_database(database_path, migrations_directory) == 1
    assert initialize_database(database_path, migrations_directory) == 1


def test_initialize_database_works_with_project_migrations(tmp_path):
    assert initialize_database(tmp_path / "test.db") == 0


def test_initialize_database_reports_file_that_is_not_a_database(tmp_path):
    not_a_database = tmp_path / "notes.db"
    not_a_database.write_text("This is not a database. " * 100, encoding="utf-8")

    with pytest.raises(sqlite3.DatabaseError, match="not a database"):
        initialize_database(not_a_database)


def test_initialize_database_reports_failed_migration(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_broken.sql", "THIS IS NOT SQL;")

    with pytest.raises(MigrationError, match="Migration 001_broken.sql failed"):
        initialize_database(tmp_path / "test.db", migrations_directory)
