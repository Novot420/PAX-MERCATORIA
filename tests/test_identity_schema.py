import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from app.database.connection import open_connection
from app.database.migrations import MigrationError, apply_migrations, get_schema_version


UTC_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def open_migrated_database(tmp_path):
    connection = open_connection(tmp_path / "test.db")
    apply_migrations(connection)
    return connection


def insert_account(connection, display_name, public_id=None):
    if public_id is None:
        public_id = secrets.token_hex(16)

    cursor = connection.execute(
        "INSERT INTO accounts (public_id, display_name) VALUES (?, ?)",
        (public_id, display_name),
    )
    return cursor.lastrowid


def insert_credentials(connection, account_id, password_hash="placeholder-hash"):
    connection.execute(
        "INSERT INTO credentials (account_id, password_hash) VALUES (?, ?)",
        (account_id, password_hash),
    )


def parse_utc_timestamp(value):
    return datetime.strptime(value, UTC_TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)


# Migration


def test_migration_creates_schema_version_one(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        assert get_schema_version(connection) == 1


def test_migration_is_safe_to_run_again(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        assert apply_migrations(connection) == 1


def test_failed_migration_leaves_no_identity_tables(tmp_path):
    with closing(open_connection(tmp_path / "test.db")) as connection:
        connection.execute("CREATE TABLE credentials (unrelated INTEGER)")

        with pytest.raises(MigrationError, match="001_accounts.sql failed"):
            apply_migrations(connection)

        tables = connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table' AND name = 'accounts'"
        ).fetchall()
        assert tables == []
        assert get_schema_version(connection) == 0


# Table structure


def test_accounts_table_structure(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        columns = [
            (row["name"], row["type"], row["notnull"], row["pk"])
            for row in connection.execute("PRAGMA table_info(accounts)")
        ]

    assert columns == [
        ("id", "INTEGER", 0, 1),
        ("public_id", "TEXT", 1, 0),
        ("display_name", "TEXT", 1, 0),
        ("status", "TEXT", 1, 0),
        ("created_at", "TEXT", 1, 0),
    ]


def test_credentials_table_structure(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        columns = [
            (row["name"], row["type"], row["notnull"], row["pk"])
            for row in connection.execute("PRAGMA table_info(credentials)")
        ]

    assert columns == [
        ("account_id", "INTEGER", 1, 1),
        ("password_hash", "TEXT", 1, 0),
        ("updated_at", "TEXT", 1, 0),
    ]


def test_identity_tables_are_strict(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        rows = connection.execute(
            "SELECT name, strict, wr FROM pragma_table_list "
            "WHERE name IN ('accounts', 'credentials') ORDER BY name"
        ).fetchall()

    assert [tuple(row) for row in rows] == [
        ("accounts", 1, 0),
        ("credentials", 1, 1),
    ]


def test_credentials_reference_accounts_with_cascade(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(credentials)"
        ).fetchall()

    assert len(foreign_keys) == 1
    assert foreign_keys[0]["table"] == "accounts"
    assert foreign_keys[0]["from"] == "account_id"
    assert foreign_keys[0]["to"] == "id"
    assert foreign_keys[0]["on_delete"] == "CASCADE"


def test_strict_table_rejects_wrong_value_type(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="cannot store BLOB value in TEXT column"):
            connection.execute(
                "INSERT INTO accounts (public_id, display_name) VALUES (?, ?)",
                (secrets.token_hex(16), b"alice"),
            )


# Defaults


def test_new_account_defaults(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        account_id = insert_account(connection, "alice")
        row = connection.execute(
            "SELECT status, created_at FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()

    assert row["status"] == "active"
    created_at = parse_utc_timestamp(row["created_at"])
    assert abs(datetime.now(timezone.utc) - created_at) < timedelta(minutes=1)


def test_new_credentials_get_utc_updated_at(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        account_id = insert_account(connection, "alice")
        insert_credentials(connection, account_id)
        row = connection.execute(
            "SELECT updated_at FROM credentials WHERE account_id = ?", (account_id,)
        ).fetchone()

    updated_at = parse_utc_timestamp(row["updated_at"])
    assert abs(datetime.now(timezone.utc) - updated_at) < timedelta(minutes=1)


# Public identifier


def test_public_id_must_be_unique(tmp_path):
    public_id = secrets.token_hex(16)

    with closing(open_migrated_database(tmp_path)) as connection:
        insert_account(connection, "alice", public_id=public_id)

        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed: accounts.public_id"):
            insert_account(connection, "bob", public_id=public_id)


@pytest.mark.parametrize(
    "public_id",
    [
        "0123456789ABCDEF0123456789ABCDEF",
        "0123456789abcdef",
        "0123456789abcdef0123456789abcdef00",
        "0123456789abcdef0123456789abcdeg",
        "0123456789abcdef-123456789abcdef",
        "",
    ],
)
def test_public_id_format_is_enforced(tmp_path, public_id):
    with closing(open_migrated_database(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="public_id_format"):
            insert_account(connection, "alice", public_id=public_id)


# Display name


@pytest.mark.parametrize("second_name", ["alice", "ALICE", "Alice", "aLiCe"])
def test_display_name_is_unique_regardless_of_case(tmp_path, second_name):
    with closing(open_migrated_database(tmp_path)) as connection:
        insert_account(connection, "Alice")

        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed: accounts.display_name"):
            insert_account(connection, second_name)


def test_display_name_lookup_ignores_case(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        account_id = insert_account(connection, "Alice")
        row = connection.execute(
            "SELECT id FROM accounts WHERE display_name = ?", ("aLICE",)
        ).fetchone()

    assert row["id"] == account_id


@pytest.mark.parametrize("display_name", ["abc", "a" * 32, "alice_01", "bob-smith", "UPPER_lower-9"])
def test_valid_display_names_are_accepted(tmp_path, display_name):
    with closing(open_migrated_database(tmp_path)) as connection:
        insert_account(connection, display_name)


@pytest.mark.parametrize("display_name", ["", "ab", "a" * 33])
def test_display_name_length_is_enforced(tmp_path, display_name):
    with closing(open_migrated_database(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="display_name_length"):
            insert_account(connection, display_name)


@pytest.mark.parametrize(
    "display_name",
    [
        "has space",
        " alice",
        "alice ",
        "Älice",
        "Sаtoshi",
        "alice;",
        "al.ice",
        "alice\n",
        "ali​ce",
    ],
)
def test_display_name_characters_are_enforced(tmp_path, display_name):
    with closing(open_migrated_database(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="display_name_characters"):
            insert_account(connection, display_name)


# Account status


@pytest.mark.parametrize("status", ["active", "suspended", "deleted"])
def test_valid_account_statuses_are_accepted(tmp_path, status):
    with closing(open_migrated_database(tmp_path)) as connection:
        connection.execute(
            "INSERT INTO accounts (public_id, display_name, status) VALUES (?, ?, ?)",
            (secrets.token_hex(16), "alice", status),
        )


@pytest.mark.parametrize("status", ["banned", "ACTIVE", "Active", "", "active "])
def test_invalid_account_statuses_are_rejected(tmp_path, status):
    with closing(open_migrated_database(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="account_status"):
            connection.execute(
                "INSERT INTO accounts (public_id, display_name, status) VALUES (?, ?, ?)",
                (secrets.token_hex(16), "alice", status),
            )


# Required fields and timestamps


@pytest.mark.parametrize("column", ["public_id", "display_name", "status", "created_at"])
def test_account_fields_are_required(tmp_path, column):
    values = {
        "public_id": secrets.token_hex(16),
        "display_name": "alice",
        "status": "active",
        "created_at": "2026-01-01T00:00:00Z",
    }
    values[column] = None

    with closing(open_migrated_database(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError, match=f"NOT NULL constraint failed: accounts.{column}"):
            connection.execute(
                "INSERT INTO accounts (public_id, display_name, status, created_at) "
                "VALUES (:public_id, :display_name, :status, :created_at)",
                values,
            )


@pytest.mark.parametrize("column", ["account_id", "password_hash", "updated_at"])
def test_credentials_fields_are_required(tmp_path, column):
    with closing(open_migrated_database(tmp_path)) as connection:
        values = {
            "account_id": insert_account(connection, "alice"),
            "password_hash": "placeholder-hash",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        values[column] = None

        with pytest.raises(sqlite3.IntegrityError, match=f"NOT NULL constraint failed: credentials.{column}"):
            connection.execute(
                "INSERT INTO credentials (account_id, password_hash, updated_at) "
                "VALUES (:account_id, :password_hash, :updated_at)",
                values,
            )


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-11-10 17:00:00",
        "2026-11-10T17:00:00",
        "2026-11-10T17:00:00+01:00",
        "2026-11-10T17:00:00.123Z",
        "10.11.2026",
    ],
)
def test_account_created_at_must_be_utc_format(tmp_path, timestamp):
    with closing(open_migrated_database(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="created_at_utc_format"):
            connection.execute(
                "INSERT INTO accounts (public_id, display_name, created_at) VALUES (?, ?, ?)",
                (secrets.token_hex(16), "alice", timestamp),
            )


def test_credentials_updated_at_must_be_utc_format(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        account_id = insert_account(connection, "alice")

        with pytest.raises(sqlite3.IntegrityError, match="updated_at_utc_format"):
            connection.execute(
                "INSERT INTO credentials (account_id, password_hash, updated_at) VALUES (?, ?, ?)",
                (account_id, "placeholder-hash", "2026-11-10 17:00:00"),
            )


# Credentials


def test_credentials_require_existing_account(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            insert_credentials(connection, account_id=999)


def test_null_account_id_is_never_assigned_automatically(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        insert_account(connection, "alice")

        with pytest.raises(sqlite3.IntegrityError, match="NOT NULL constraint failed: credentials.account_id"):
            insert_credentials(connection, account_id=None)

        assert connection.execute("SELECT count(*) FROM credentials").fetchone()[0] == 0


def test_account_has_at_most_one_credentials_row(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        account_id = insert_account(connection, "alice")
        insert_credentials(connection, account_id)

        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed: credentials.account_id"):
            insert_credentials(connection, account_id, password_hash="another-hash")


def test_empty_password_hash_is_rejected(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        account_id = insert_account(connection, "alice")

        with pytest.raises(sqlite3.IntegrityError, match="password_hash_not_empty"):
            insert_credentials(connection, account_id, password_hash="")


# Deletion behaviour and internal IDs


def test_deleting_account_deletes_its_credentials(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        alice_id = insert_account(connection, "alice")
        bob_id = insert_account(connection, "bob")
        insert_credentials(connection, alice_id)
        insert_credentials(connection, bob_id)

        connection.execute("DELETE FROM accounts WHERE id = ?", (alice_id,))

        remaining = connection.execute("SELECT account_id FROM credentials").fetchall()
        assert [row["account_id"] for row in remaining] == [bob_id]


def test_deleting_credentials_keeps_account(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        account_id = insert_account(connection, "alice")
        insert_credentials(connection, account_id)

        connection.execute("DELETE FROM credentials WHERE account_id = ?", (account_id,))

        assert connection.execute("SELECT count(*) FROM accounts").fetchone()[0] == 1


def test_internal_account_ids_are_never_reused(tmp_path):
    with closing(open_migrated_database(tmp_path)) as connection:
        insert_account(connection, "alice")
        bob_id = insert_account(connection, "bob")
        connection.execute("DELETE FROM accounts WHERE id = ?", (bob_id,))

        carol_id = insert_account(connection, "carol")

    assert carol_id > bob_id
