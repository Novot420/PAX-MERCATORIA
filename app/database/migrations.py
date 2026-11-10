import sqlite3
from pathlib import Path


MIGRATIONS_DIRECTORY = Path(__file__).resolve().parent / "migrations"


class MigrationError(Exception):
    pass


def apply_migrations(connection, migrations_directory=MIGRATIONS_DIRECTORY):
    if connection.in_transaction:
        raise MigrationError("Migrations must not run inside an open transaction")

    migrations = find_migrations(migrations_directory)
    current_version = get_schema_version(connection)
    latest_version = len(migrations)

    if current_version > latest_version:
        raise MigrationError(
            f"Database schema version {current_version} is newer than "
            f"this application supports ({latest_version})"
        )

    for version, migration_path in migrations:
        if version > current_version:
            apply_migration(connection, version, migration_path)

    return get_schema_version(connection)


def find_migrations(migrations_directory):
    if not migrations_directory.is_dir():
        raise MigrationError(
            f"Migrations directory not found: {migrations_directory}"
        )

    migrations = []
    for migration_path in sorted(migrations_directory.glob("*.sql")):
        prefix, separator, _ = migration_path.name.partition("_")
        if len(prefix) != 3 or not prefix.isdigit() or not separator:
            raise MigrationError(
                f"Invalid migration file name: {migration_path.name}"
            )
        migrations.append((int(prefix), migration_path))

    for expected_version, (version, migration_path) in enumerate(migrations, start=1):
        if version != expected_version:
            raise MigrationError(
                f"Expected migration {expected_version:03d}, "
                f"found {migration_path.name}"
            )

    return migrations


def get_schema_version(connection):
    return connection.execute("PRAGMA user_version").fetchone()[0]


def apply_migration(connection, version, migration_path):
    sql = migration_path.read_text(encoding="utf-8")
    script = f"BEGIN;\n{sql}\nPRAGMA user_version = {int(version)};\nCOMMIT;"

    try:
        connection.executescript(script)
    except sqlite3.Error as error:
        if connection.in_transaction:
            connection.rollback()
        raise MigrationError(
            f"Migration {migration_path.name} failed: {error}"
        ) from error
