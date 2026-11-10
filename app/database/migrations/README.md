# Database migrations

Each file in this folder changes the database structure by one step.
The migration runner (`app/database/migrations.py`) applies pending files
in order at startup and records the result in SQLite's `user_version`.

## Rules

- Name files `NNN_short_description.sql`, for example `001_accounts.sql`.
- Number them from `001` upwards, with no gaps and no duplicates.
- Never edit a migration that has already been applied. Write a new one instead.
- Do not use `BEGIN`, `COMMIT` or `ROLLBACK` in a file. The runner wraps
  every migration in its own transaction, so it is applied completely or not at all.
- Migrations contain schema only. Never put personal data in them.
