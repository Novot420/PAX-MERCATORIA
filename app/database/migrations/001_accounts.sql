-- Identity Engine: pseudonymous accounts and their credentials.
-- Owned by the Identity Engine; other modules must not query these tables directly.

CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_id TEXT NOT NULL UNIQUE
        CONSTRAINT public_id_format
            CHECK (length(public_id) = 32 AND public_id NOT GLOB '*[^0-9a-f]*'),
    display_name TEXT NOT NULL UNIQUE COLLATE NOCASE
        CONSTRAINT display_name_length
            CHECK (length(display_name) BETWEEN 3 AND 32)
        CONSTRAINT display_name_characters
            CHECK (display_name NOT GLOB '*[^A-Za-z0-9_-]*'),
    status TEXT NOT NULL DEFAULT 'active'
        CONSTRAINT account_status
            CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        CONSTRAINT created_at_utc_format
            CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT;

CREATE TABLE credentials (
    account_id INTEGER PRIMARY KEY
        REFERENCES accounts (id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL
        CONSTRAINT password_hash_not_empty
            CHECK (length(password_hash) > 0),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        CONSTRAINT updated_at_utc_format
            CHECK (updated_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')
) STRICT, WITHOUT ROWID;
