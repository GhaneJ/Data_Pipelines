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

CREATE INDEX IF NOT EXISTS idx_provider_submissions_provider_id
    ON provider_application_submissions (provider_id);

CREATE INDEX IF NOT EXISTS idx_provider_submissions_created_by_user_id
    ON provider_application_submissions (created_by_user_id);

CREATE INDEX IF NOT EXISTS idx_provider_submissions_status
    ON provider_application_submissions (status);

CREATE INDEX IF NOT EXISTS idx_provider_submissions_target_year
    ON provider_application_submissions (target_year);

CREATE INDEX IF NOT EXISTS idx_provider_submissions_created_at
    ON provider_application_submissions (created_at DESC);


CREATE INDEX IF NOT EXISTS idx_provider_submissions_reviewed_by_user_id
    ON provider_application_submissions (reviewed_by_user_id);

CREATE INDEX IF NOT EXISTS idx_provider_submissions_review_started_at
    ON provider_application_submissions (review_started_at DESC);

CREATE INDEX IF NOT EXISTS idx_provider_submissions_reviewed_at
    ON provider_application_submissions (reviewed_at DESC);

CREATE INDEX IF NOT EXISTS idx_provider_submissions_provider_status
    ON provider_application_submissions (provider_id, status);

CREATE INDEX IF NOT EXISTS idx_provider_submission_review_events_submission_id
    ON provider_submission_review_events (submission_id);

CREATE INDEX IF NOT EXISTS idx_provider_submission_review_events_actor_user_id
    ON provider_submission_review_events (actor_user_id);

CREATE INDEX IF NOT EXISTS idx_provider_submission_review_events_action
    ON provider_submission_review_events (action);

CREATE INDEX IF NOT EXISTS idx_provider_submission_review_events_created_at
    ON provider_submission_review_events (created_at ASC);

CREATE INDEX IF NOT EXISTS idx_user_registration_requests_username
    ON user_registration_requests (requested_username);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_registration_requests_pending_username_unique
    ON user_registration_requests (requested_username)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_user_registration_requests_status
    ON user_registration_requests (status);

CREATE INDEX IF NOT EXISTS idx_user_registration_requests_provider_id
    ON user_registration_requests (provider_id);

CREATE INDEX IF NOT EXISTS idx_user_registration_requests_created_at
    ON user_registration_requests (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_admin_events_actor_user_id
    ON auth_admin_events (actor_user_id);

CREATE INDEX IF NOT EXISTS idx_auth_admin_events_target_user_id
    ON auth_admin_events (target_user_id);

CREATE INDEX IF NOT EXISTS idx_auth_admin_events_registration_request_id
    ON auth_admin_events (registration_request_id);

CREATE INDEX IF NOT EXISTS idx_auth_admin_events_action
    ON auth_admin_events (action);

CREATE INDEX IF NOT EXISTS idx_auth_admin_events_created_at
    ON auth_admin_events (created_at DESC);


CREATE INDEX IF NOT EXISTS idx_myh_source_check_runs_started_at
    ON myh_source_check_runs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_myh_source_files_source_year
    ON myh_source_files (source_year DESC);

CREATE INDEX IF NOT EXISTS idx_myh_source_files_status
    ON myh_source_files (status);

CREATE INDEX IF NOT EXISTS idx_myh_source_files_last_seen_at
    ON myh_source_files (last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_myh_refresh_runs_source_file_id
    ON myh_refresh_runs (source_file_id);

CREATE INDEX IF NOT EXISTS idx_myh_refresh_runs_started_at
    ON myh_refresh_runs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_myh_refresh_runs_status
    ON myh_refresh_runs (status);

CREATE INDEX IF NOT EXISTS idx_admin_notifications_status
    ON admin_notifications (status);

CREATE INDEX IF NOT EXISTS idx_admin_notifications_created_at
    ON admin_notifications (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_notifications_source_file_id
    ON admin_notifications (source_file_id);

CREATE INDEX IF NOT EXISTS idx_admin_notifications_refresh_run_id
    ON admin_notifications (refresh_run_id);
