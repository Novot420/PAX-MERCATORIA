from contextlib import closing

from app.database.connection import open_connection
from app.database.migrations import MIGRATIONS_DIRECTORY, apply_migrations


def initialize_database(database_path, migrations_directory=MIGRATIONS_DIRECTORY):
    with closing(open_connection(database_path)) as connection:
        return apply_migrations(connection, migrations_directory)
