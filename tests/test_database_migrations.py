from contextlib import closing

import pytest

from app.database.connection import open_connection
from app.database.migrations import (
    MIGRATIONS_DIRECTORY,
    MigrationError,
    apply_migrations,
    find_migrations,
    get_schema_version,
)


def write_migration(migrations_directory, name, sql):
    migrations_directory.mkdir(exist_ok=True)
    (migrations_directory / name).write_text(sql, encoding="utf-8")


def table_names(connection):
    rows = connection.execute(
        "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def test_new_database_without_migrations_stays_at_version_zero(tmp_path):
    migrations_directory = tmp_path / "migrations"
    migrations_directory.mkdir()

    with closing(open_connection(tmp_path / "test.db")) as connection:
        assert apply_migrations(connection, migrations_directory) == 0


def test_migrations_are_applied_in_order(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")
    write_migration(migrations_directory, "002_second.sql", "CREATE TABLE second (id INTEGER);")

    with closing(open_connection(tmp_path / "test.db")) as connection:
        assert apply_migrations(connection, migrations_directory) == 2
        assert table_names(connection) == ["first", "second"]


def test_running_migrations_twice_is_safe(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")

    with closing(open_connection(tmp_path / "test.db")) as connection:
        apply_migrations(connection, migrations_directory)

        assert apply_migrations(connection, migrations_directory) == 1
        assert table_names(connection) == ["first"]


def test_only_pending_migrations_are_applied(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")

    with closing(open_connection(tmp_path / "test.db")) as connection:
        apply_migrations(connection, migrations_directory)

        write_migration(migrations_directory, "002_second.sql", "CREATE TABLE second (id INTEGER);")

        assert apply_migrations(connection, migrations_directory) == 2
        assert table_names(connection) == ["first", "second"]


def test_failed_migration_is_rolled_back_completely(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")
    write_migration(
        migrations_directory,
        "002_broken.sql",
        "CREATE TABLE second (id INTEGER);\nTHIS IS NOT SQL;",
    )

    with closing(open_connection(tmp_path / "test.db")) as connection:
        with pytest.raises(MigrationError, match="Migration 002_broken.sql failed"):
            apply_migrations(connection, migrations_directory)

        assert get_schema_version(connection) == 1
        assert table_names(connection) == ["first"]
        assert not connection.in_transaction


def test_gap_in_migration_numbers_is_rejected(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")
    write_migration(migrations_directory, "003_third.sql", "CREATE TABLE third (id INTEGER);")

    with closing(open_connection(tmp_path / "test.db")) as connection:
        with pytest.raises(MigrationError, match="Expected migration 002, found 003_third.sql"):
            apply_migrations(connection, migrations_directory)

        assert get_schema_version(connection) == 0
        assert table_names(connection) == []


def test_duplicate_migration_number_is_rejected(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")
    write_migration(migrations_directory, "001_other.sql", "CREATE TABLE other (id INTEGER);")

    with pytest.raises(MigrationError, match="Expected migration 002, found 001_other.sql"):
        find_migrations(migrations_directory)


def test_invalid_migration_file_name_is_rejected(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "accounts.sql", "CREATE TABLE accounts (id INTEGER);")

    with pytest.raises(MigrationError, match="Invalid migration file name: accounts.sql"):
        find_migrations(migrations_directory)


def test_missing_migrations_directory_is_rejected(tmp_path):
    with pytest.raises(MigrationError, match="Migrations directory not found"):
        find_migrations(tmp_path / "does_not_exist")


def test_database_newer_than_application_is_rejected(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")

    with closing(open_connection(tmp_path / "test.db")) as connection:
        connection.execute("PRAGMA user_version = 5")

        with pytest.raises(MigrationError, match="schema version 5 is newer"):
            apply_migrations(connection, migrations_directory)

        assert table_names(connection) == []


def test_migrations_refuse_to_run_inside_open_transaction(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")
    database_path = tmp_path / "test.db"

    with closing(open_connection(database_path)) as connection:
        connection.execute("CREATE TABLE pending (id INTEGER)")
        connection.commit()
        connection.execute("INSERT INTO pending (id) VALUES (1)")

        with pytest.raises(MigrationError, match="inside an open transaction"):
            apply_migrations(connection, migrations_directory)

        connection.rollback()

    with closing(open_connection(database_path)) as connection:
        assert connection.execute("SELECT count(*) FROM pending").fetchone()[0] == 0
        assert get_schema_version(connection) == 0


def test_non_sql_files_are_ignored(tmp_path):
    migrations_directory = tmp_path / "migrations"
    write_migration(migrations_directory, "001_first.sql", "CREATE TABLE first (id INTEGER);")
    write_migration(migrations_directory, "README.md", "Notes about migrations.")

    assert [version for version, _ in find_migrations(migrations_directory)] == [1]


def test_project_migrations_directory_is_valid():
    assert find_migrations(MIGRATIONS_DIRECTORY) == []
