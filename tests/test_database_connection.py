import sqlite3
from contextlib import closing

import pytest

from app.database.connection import open_connection


def test_open_connection_creates_directory_and_file(tmp_path):
    database_path = tmp_path / "data" / "test.db"

    with closing(open_connection(database_path)):
        assert database_path.parent.is_dir()
        assert database_path.is_file()


def test_new_database_directory_is_private(tmp_path):
    database_path = tmp_path / "data" / "test.db"

    with closing(open_connection(database_path)):
        assert database_path.parent.stat().st_mode & 0o777 == 0o700


def test_new_database_file_is_private(tmp_path):
    database_path = tmp_path / "data" / "test.db"

    with closing(open_connection(database_path)):
        assert database_path.stat().st_mode & 0o777 == 0o600


def test_existing_directory_permissions_are_not_changed(tmp_path):
    shared_directory = tmp_path / "shared"
    shared_directory.mkdir(mode=0o755)
    shared_directory.chmod(0o755)

    with closing(open_connection(shared_directory / "test.db")):
        assert shared_directory.stat().st_mode & 0o777 == 0o755


def test_foreign_keys_are_enforced(tmp_path):
    with closing(open_connection(tmp_path / "test.db")) as connection:
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE child ("
            "id INTEGER PRIMARY KEY, "
            "parent_id INTEGER NOT NULL REFERENCES parent(id))"
        )

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            connection.execute("INSERT INTO child (parent_id) VALUES (999)")


def test_rows_can_be_read_by_column_name(tmp_path):
    with closing(open_connection(tmp_path / "test.db")) as connection:
        row = connection.execute("SELECT 42 AS answer").fetchone()

        assert row["answer"] == 42


def test_busy_timeout_is_configured(tmp_path):
    with closing(open_connection(tmp_path / "test.db")) as connection:
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]

        assert busy_timeout == 5000


def test_open_connection_rejects_file_that_is_not_a_database(tmp_path):
    not_a_database = tmp_path / "notes.db"
    not_a_database.write_text("This is not a database. " * 100, encoding="utf-8")

    with pytest.raises(sqlite3.DatabaseError, match="not a database"):
        open_connection(not_a_database)
