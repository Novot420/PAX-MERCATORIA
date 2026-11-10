import sqlite3


BUSY_TIMEOUT_SECONDS = 5
DIRECTORY_PERMISSIONS = 0o700
FILE_PERMISSIONS = 0o600


def open_connection(database_path):
    database_path.parent.mkdir(
        mode=DIRECTORY_PERMISSIONS,
        parents=True,
        exist_ok=True,
    )
    database_path.touch(mode=FILE_PERMISSIONS, exist_ok=True)

    connection = sqlite3.connect(database_path, timeout=BUSY_TIMEOUT_SECONDS)

    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("SELECT count(*) FROM sqlite_schema").fetchone()
    except sqlite3.Error:
        connection.close()
        raise

    return connection
