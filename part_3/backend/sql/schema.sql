-- Safe PostgreSQL schema for the curated MYH applications database.
--
-- This file is the single source of truth for project-managed table
-- definitions. It is safe to run during FastAPI startup because it only uses
-- CREATE TABLE IF NOT EXISTS and never resets existing data.

CREATE TABLE IF NOT EXISTS decisions (
    decision_code TEXT PRIMARY KEY,
    decision_label TEXT NOT NULL UNIQUE,
    CONSTRAINT decisions_code_check CHECK (decision_code IN ('approved', 'rejected', 'withdrawn'))
);

CREATE TABLE IF NOT EXISTS providers (
    provider_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    utbildningsanordnare TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS education_areas (
    education_area_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    utbildningsomrade TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lan TEXT NOT NULL,
    kommun TEXT NOT NULL,
    CONSTRAINT locations_lan_kommun_unique UNIQUE (lan, kommun)
);

CREATE TABLE IF NOT EXISTS principal_types (
    principal_type_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    huvudmannatyp TEXT NOT NULL UNIQUE,
    huvudmannatyp_normalized TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS study_forms (
    study_form_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    studieform TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS applications (
    -- Natural application identifier from the curated MYH dataset.
    diarienummer TEXT PRIMARY KEY,

    -- Traceability back to the curated Part 2 export and original source file.
    source_year SMALLINT NOT NULL,
    source_file TEXT NOT NULL,
    source_sheet TEXT NOT NULL,
    source_row INTEGER NOT NULL,

    -- Core application description.
    utbildningsnamn TEXT NOT NULL,
    education_area_id INTEGER NOT NULL REFERENCES education_areas (education_area_id),
    decision_code TEXT NOT NULL REFERENCES decisions (decision_code),
    beslut TEXT NOT NULL,
    is_approved BOOLEAN NOT NULL,
    location_id INTEGER NOT NULL REFERENCES locations (location_id),
    provider_id INTEGER NOT NULL REFERENCES providers (provider_id),
    principal_type_id INTEGER NOT NULL REFERENCES principal_types (principal_type_id),
    study_form_id INTEGER NOT NULL REFERENCES study_forms (study_form_id),

    -- Useful fields for filtering, statistics, and future API responses.
    flera_kommuner TEXT NOT NULL,
    has_multiple_municipalities BOOLEAN NOT NULL,
    antal_kommuner INTEGER NOT NULL,
    yh_poang INTEGER NOT NULL,
    is_distance_based BOOLEAN NOT NULL,
    studietakt_procent INTEGER NOT NULL,
    examenstyp TEXT,
    sokta_utbildningsomgangar INTEGER NOT NULL,
    beviljade_utbildningsomgangar INTEGER NOT NULL,

    -- Newer-year optional fields. These are nullable because older years do not
    -- contain all of them in the curated dataset.
    sun5_inriktning TEXT,
    sun5_inriktning_namn TEXT,
    seqf_niva NUMERIC(4, 1),
    smalt_yrkesomrade TEXT,
    sokta_platser_per_utbildningsomgang NUMERIC(10, 1),
    sokta_platser_totalt NUMERIC(10, 1),
    beviljade_platser_totalt NUMERIC(10, 1),

    CONSTRAINT applications_source_year_check CHECK (source_year BETWEEN 2020 AND 2025),
    CONSTRAINT applications_source_row_check CHECK (source_row > 0),
    CONSTRAINT applications_antal_kommuner_check CHECK (antal_kommuner >= 1),
    CONSTRAINT applications_yh_poang_check CHECK (yh_poang > 0),
    CONSTRAINT applications_studietakt_check CHECK (studietakt_procent > 0 AND studietakt_procent <= 100),
    CONSTRAINT applications_sokta_omgangar_check CHECK (sokta_utbildningsomgangar >= 0),
    CONSTRAINT applications_beviljade_omgangar_check CHECK (beviljade_utbildningsomgangar >= 0),
    CONSTRAINT applications_flera_kommuner_check CHECK (flera_kommuner IN ('Ja', 'Nej'))
);

-- Local admin metadata is deliberately separate from curated MYH source data.
-- The service validates diarienummer against applications before writing notes.
-- No foreign key is used here so a full curated-data refresh does not
-- automatically remove local admin notes.
CREATE TABLE IF NOT EXISTS application_notes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    diarienummer TEXT NOT NULL,
    note_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT application_notes_diarienummer_not_blank CHECK (btrim(diarienummer) <> ''),
    CONSTRAINT application_notes_note_text_not_blank CHECK (btrim(note_text) <> '')
);

-- Database-backed authentication users. Passwords are stored only as salted
-- PBKDF2 hashes. Provider users must be tied to one provider_id; admin users
-- are not tied to a provider.
CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'provider')),
    provider_id TEXT NULL,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    password_algorithm TEXT NOT NULL,
    password_iterations INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ NULL,
    last_login_at TIMESTAMPTZ NULL,
    password_changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (btrim(username) <> ''),
    CHECK (btrim(display_name) <> ''),
    CHECK (password_iterations > 0),
    CHECK (failed_login_count >= 0),
    CHECK (
        (role = 'admin' AND provider_id IS NULL)
        OR
        (role = 'provider' AND provider_id IS NOT NULL AND btrim(provider_id) <> '')
    )
);

-- Opaque bearer access-token sessions. Only token hashes are stored; raw bearer
-- tokens are returned once at login and never persisted.
CREATE TABLE IF NOT EXISTS auth_access_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    last_used_at TIMESTAMPTZ NULL,
    CHECK (btrim(token_hash) <> ''),
    CHECK (expires_at > created_at)
);
