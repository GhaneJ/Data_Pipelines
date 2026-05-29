-- Indexes for the most likely Part 3 API filters and lookups.
-- PostgreSQL automatically indexes primary keys, so diarienummer is already indexed.

CREATE INDEX IF NOT EXISTS idx_applications_source_year
    ON applications (source_year);

CREATE INDEX IF NOT EXISTS idx_applications_decision_code
    ON applications (decision_code);

CREATE INDEX IF NOT EXISTS idx_applications_location_id
    ON applications (location_id);

CREATE INDEX IF NOT EXISTS idx_applications_provider_id
    ON applications (provider_id);

CREATE INDEX IF NOT EXISTS idx_applications_education_area_id
    ON applications (education_area_id);

CREATE INDEX IF NOT EXISTS idx_applications_study_form_id
    ON applications (study_form_id);

CREATE INDEX IF NOT EXISTS idx_applications_principal_type_id
    ON applications (principal_type_id);

CREATE INDEX IF NOT EXISTS idx_applications_year_decision
    ON applications (source_year, decision_code);

CREATE INDEX IF NOT EXISTS idx_applications_distance_based
    ON applications (is_distance_based);

CREATE INDEX IF NOT EXISTS idx_locations_lan_kommun
    ON locations (lan, kommun);

CREATE INDEX IF NOT EXISTS idx_providers_name
    ON providers (utbildningsanordnare);

CREATE INDEX IF NOT EXISTS idx_education_areas_name
    ON education_areas (utbildningsomrade);

CREATE INDEX IF NOT EXISTS idx_study_forms_name
    ON study_forms (studieform);


CREATE INDEX IF NOT EXISTS idx_application_notes_diarienummer
    ON application_notes (diarienummer);

CREATE INDEX IF NOT EXISTS idx_auth_users_username
    ON auth_users (username);

CREATE INDEX IF NOT EXISTS idx_auth_users_role
    ON auth_users (role);

CREATE INDEX IF NOT EXISTS idx_auth_users_provider_id
    ON auth_users (provider_id);

CREATE INDEX IF NOT EXISTS idx_auth_access_tokens_token_hash
    ON auth_access_tokens (token_hash);

CREATE INDEX IF NOT EXISTS idx_auth_access_tokens_user_id
    ON auth_access_tokens (user_id);

CREATE INDEX IF NOT EXISTS idx_auth_access_tokens_expires_at
    ON auth_access_tokens (expires_at);
