-- Optional non-destructive upgrade for existing 3.15.1 development databases.
-- FastAPI startup also runs these definitions through schema.sql and indexes.sql,
-- so this file is only for users who want to upgrade manually with psql.

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    scopes TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ NULL,
    revoked_at TIMESTAMPTZ NULL,
    revoked_by_user_id UUID NULL REFERENCES auth_users(id) ON DELETE SET NULL,
    created_by_user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NULL,
    CHECK (btrim(name) <> ''),
    CHECK (btrim(key_prefix) <> ''),
    CHECK (btrim(key_hash) <> ''),
    CHECK (btrim(scopes) <> ''),
    CHECK (expires_at IS NULL OR expires_at > created_at),
    CHECK (revoked_at IS NULL OR revoked_at >= created_at)
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash
    ON api_keys (key_hash);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_prefix
    ON api_keys (key_prefix);

CREATE INDEX IF NOT EXISTS idx_api_keys_is_active
    ON api_keys (is_active);

CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at
    ON api_keys (expires_at);

CREATE INDEX IF NOT EXISTS idx_api_keys_created_by_user_id
    ON api_keys (created_by_user_id);
