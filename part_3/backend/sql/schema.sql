-- PostgreSQL schema for the curated MYH applications dataset.
--
-- This schema is intentionally normalized, but still small enough to explain.
-- The curated CSV remains the source of truth; this SQL only defines how the
-- finished Part 2 dataset is stored for Part 3.

DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS providers CASCADE;
DROP TABLE IF EXISTS education_areas CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS decisions CASCADE;
DROP TABLE IF EXISTS principal_types CASCADE;
DROP TABLE IF EXISTS study_forms CASCADE;

CREATE TABLE decisions (
    decision_code TEXT PRIMARY KEY,
    decision_label TEXT NOT NULL UNIQUE,
    CONSTRAINT decisions_code_check CHECK (decision_code IN ('approved', 'rejected', 'withdrawn'))
);

CREATE TABLE providers (
    provider_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    utbildningsanordnare TEXT NOT NULL UNIQUE
);

CREATE TABLE education_areas (
    education_area_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    utbildningsomrade TEXT NOT NULL UNIQUE
);

CREATE TABLE locations (
    location_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lan TEXT NOT NULL,
    kommun TEXT NOT NULL,
    CONSTRAINT locations_lan_kommun_unique UNIQUE (lan, kommun)
);

CREATE TABLE principal_types (
    principal_type_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    huvudmannatyp TEXT NOT NULL UNIQUE,
    huvudmannatyp_normalized TEXT NOT NULL
);

CREATE TABLE study_forms (
    study_form_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    studieform TEXT NOT NULL UNIQUE
);

CREATE TABLE applications (
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
