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

    CONSTRAINT applications_source_year_check CHECK (source_year BETWEEN 2020 AND 2100),
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


-- Database-backed API keys for machine/client access. Raw API keys are
-- returned once at creation and never stored; only key_hash is persisted.
-- Scopes use a simple comma-separated TEXT representation to stay explainable
-- with the project's raw-SQL style.
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

-- Provider-created application submissions are a separate write-side workflow
-- table. They do not mutate or replace the historical curated applications
-- table. Admin approval is a workflow decision only and does not insert rows
-- into the historical curated applications table.
CREATE TABLE IF NOT EXISTS provider_application_submissions (
    id UUID PRIMARY KEY,
    provider_id TEXT NOT NULL,
    provider_name TEXT NULL,
    created_by_user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'draft',
    target_year SMALLINT NULL,
    education_name TEXT NOT NULL,
    education_area TEXT NULL,
    municipality TEXT NULL,
    region TEXT NULL,
    yh_points INTEGER NULL,
    study_form TEXT NULL,
    study_pace_percent INTEGER NULL,
    head_provider_type TEXT NULL,
    description TEXT NULL,
    notes TEXT NULL,
    submitted_at TIMESTAMPTZ NULL,
    review_started_at TIMESTAMPTZ NULL,
    reviewed_by_user_id UUID NULL,
    reviewed_at TIMESTAMPTZ NULL,
    review_notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT provider_submission_reviewed_by_user_id_fkey
        FOREIGN KEY (reviewed_by_user_id) REFERENCES auth_users(id) ON DELETE SET NULL,
    CHECK (btrim(provider_id) <> ''),
    CONSTRAINT provider_submission_status_check
        CHECK (status IN ('draft', 'submitted', 'under_review', 'needs_changes', 'approved', 'rejected')),
    CHECK (target_year IS NULL OR target_year BETWEEN 2020 AND 2100),
    CHECK (btrim(education_name) <> ''),
    CHECK (yh_points IS NULL OR yh_points > 0),
    CHECK (study_pace_percent IS NULL OR (study_pace_percent >= 1 AND study_pace_percent <= 100)),
    CHECK (submitted_at IS NULL OR submitted_at >= created_at),
    CONSTRAINT provider_submission_submitted_at_status_check
        CHECK ((status = 'draft' AND submitted_at IS NULL) OR (status <> 'draft' AND submitted_at IS NOT NULL)),
    CHECK (review_started_at IS NULL OR review_started_at >= created_at),
    CHECK (reviewed_at IS NULL OR reviewed_at >= created_at)
);

CREATE TABLE IF NOT EXISTS provider_submission_review_events (
    id UUID PRIMARY KEY,
    submission_id UUID NOT NULL REFERENCES provider_application_submissions(id) ON DELETE CASCADE,
    actor_user_id UUID NULL REFERENCES auth_users(id) ON DELETE SET NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    from_status TEXT NULL,
    to_status TEXT NOT NULL,
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (actor_role IN ('admin', 'provider', 'system')),
    CHECK (action IN ('submitted', 'review_started', 'changes_requested', 'approved', 'rejected', 'resubmitted')),
    CHECK (from_status IS NULL OR from_status IN ('draft', 'submitted', 'under_review', 'needs_changes', 'approved', 'rejected')),
    CHECK (to_status IN ('draft', 'submitted', 'under_review', 'needs_changes', 'approved', 'rejected'))
);


-- Controlled provider access requests. Public signup inserts pending rows here;
-- only an admin approval creates a real provider user in auth_users.
CREATE TABLE IF NOT EXISTS user_registration_requests (
    id UUID PRIMARY KEY,
    requested_username TEXT NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT NULL,
    provider_id TEXT NOT NULL,
    requested_role TEXT NOT NULL DEFAULT 'provider',
    organization_name TEXT NULL,
    message TEXT NULL,
    pending_password_hash TEXT NOT NULL,
    pending_password_salt TEXT NOT NULL,
    pending_password_algorithm TEXT NOT NULL,
    pending_password_iterations INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by_user_id UUID NULL REFERENCES auth_users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ NULL,
    review_notes TEXT NULL,
    created_user_id UUID NULL REFERENCES auth_users(id) ON DELETE SET NULL,
    CHECK (btrim(requested_username) <> ''),
    CHECK (btrim(display_name) <> ''),
    CHECK (btrim(provider_id) <> ''),
    CHECK (requested_role = 'provider'),
    CHECK (pending_password_iterations > 0),
    CHECK (status IN ('pending', 'approved', 'rejected')),
    CHECK ((status = 'pending' AND reviewed_at IS NULL) OR (status <> 'pending' AND reviewed_at IS NOT NULL)),
    CHECK ((status = 'approved' AND created_user_id IS NOT NULL) OR status <> 'approved')
);

-- Small admin/auth audit trail for explainability. It deliberately stores only
-- safe metadata and notes, never passwords, bearer tokens, or API keys.
CREATE TABLE IF NOT EXISTS auth_admin_events (
    id UUID PRIMARY KEY,
    actor_user_id UUID NULL REFERENCES auth_users(id) ON DELETE SET NULL,
    target_user_id UUID NULL REFERENCES auth_users(id) ON DELETE SET NULL,
    registration_request_id UUID NULL REFERENCES user_registration_requests(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (btrim(action) <> ''),
    CHECK (action IN (
        'registration_request_created',
        'registration_request_approved',
        'registration_request_rejected',
        'user_created',
        'user_updated',
        'password_reset',
        'user_deactivated',
        'user_reactivated',
        'session_revoked'
    ))
);

-- Database-backed MYH source monitoring and refresh operations. These tables
-- track official MYH source files, check runs, refresh/import runs, and admin
-- notifications without mixing provider submissions into official data.
CREATE TABLE IF NOT EXISTS myh_source_check_runs (
    id UUID PRIMARY KEY,
    source_url TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ NULL,
    http_status INTEGER NULL,
    discovered_count INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    changed_count INTEGER NOT NULL DEFAULT 0,
    known_count INTEGER NOT NULL DEFAULT 0,
    message TEXT NULL,
    error_message TEXT NULL,
    CHECK (btrim(source_url) <> ''),
    CHECK (status IN ('running', 'success', 'failed')),
    CHECK (discovered_count >= 0),
    CHECK (new_count >= 0),
    CHECK (changed_count >= 0),
    CHECK (known_count >= 0)
);

CREATE TABLE IF NOT EXISTS myh_source_files (
    id UUID PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL UNIQUE,
    file_type TEXT NOT NULL,
    source_year SMALLINT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_checked_at TIMESTAMPTZ NULL,
    last_downloaded_at TIMESTAMPTZ NULL,
    last_download_size_bytes BIGINT NULL,
    last_sha256 TEXT NULL,
    downloaded_path TEXT NULL,
    first_check_run_id UUID NULL REFERENCES myh_source_check_runs(id) ON DELETE SET NULL,
    last_check_run_id UUID NULL REFERENCES myh_source_check_runs(id) ON DELETE SET NULL,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (btrim(file_name) <> ''),
    CHECK (btrim(file_url) <> ''),
    CHECK (file_type IN ('xlsx', 'xlsm', 'xls', 'csv')),
    CHECK (source_year IS NULL OR source_year BETWEEN 2020 AND 2100),
    CHECK (status IN ('new', 'known', 'changed', 'ignored', 'imported', 'failed')),
    CHECK (last_download_size_bytes IS NULL OR last_download_size_bytes >= 0),
    CHECK (last_sha256 IS NULL OR length(last_sha256) = 64)
);

CREATE TABLE IF NOT EXISTS myh_refresh_runs (
    id UUID PRIMARY KEY,
    source_file_id UUID NULL REFERENCES myh_source_files(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    mode TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ NULL,
    rows_imported INTEGER NULL,
    affected_years TEXT NULL,
    source_sha256 TEXT NULL,
    downloaded_path TEXT NULL,
    processed_path TEXT NULL,
    validation_summary TEXT NULL,
    error_message TEXT NULL,
    triggered_by_user_id UUID NULL REFERENCES auth_users(id) ON DELETE SET NULL,
    CHECK (status IN ('running', 'success', 'failed')),
    CHECK (mode IN ('official_source_file', 'curated_csv_compatibility', 'scheduled_official_source_file')),
    CHECK (rows_imported IS NULL OR rows_imported >= 0),
    CHECK (source_sha256 IS NULL OR length(source_sha256) = 64)
);

CREATE TABLE IF NOT EXISTS admin_notifications (
    id UUID PRIMARY KEY,
    notification_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread',
    source_file_id UUID NULL REFERENCES myh_source_files(id) ON DELETE SET NULL,
    refresh_run_id UUID NULL REFERENCES myh_refresh_runs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at TIMESTAMPTZ NULL,
    resolved_at TIMESTAMPTZ NULL,
    actor_user_id UUID NULL REFERENCES auth_users(id) ON DELETE SET NULL,
    CHECK (btrim(notification_type) <> ''),
    CHECK (severity IN ('info', 'success', 'warning', 'error')),
    CHECK (btrim(title) <> ''),
    CHECK (btrim(message) <> ''),
    CHECK (status IN ('unread', 'read', 'resolved'))
);
