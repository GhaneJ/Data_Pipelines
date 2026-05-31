export type Role = "admin" | "provider";
export type RegistrationStatus = "pending" | "approved" | "rejected";
export type SubmissionStatus = "draft" | "submitted" | "under_review" | "needs_changes" | "approved" | "rejected";

export interface Principal {
  subject: string;
  username: string;
  display_name: string;
  role: Role;
  provider_id: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
}

export interface RegistrationRequestInput {
  requested_username: string;
  display_name: string;
  password: string;
  provider_id: string;
  email?: string;
  organization_name?: string;
  message?: string;
}

export interface RegistrationRequest {
  id: string;
  requested_username: string;
  display_name: string;
  email: string | null;
  provider_id: string;
  requested_role: "provider";
  organization_name: string | null;
  message: string | null;
  status: RegistrationStatus;
  created_at: string;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_user_id: string | null;
}


export interface ProviderSummary {
  provider_id: string | number;
  utbildningsanordnare: string;
  total_applications: number;
  approved_applications: number;
  first_year: number | null;
  last_year: number | null;
}

export interface Paginated<T> {
  items: T[];
  total?: number;
  limit: number;
  offset: number;
}

export interface ManagedUser {
  id: string;
  username: string;
  display_name: string;
  role: Role;
  provider_id: string | null;
  is_active: boolean;
  failed_login_count: number;
  locked_until: string | null;
  last_login_at: string | null;
  password_changed_at: string;
  created_at: string;
  updated_at: string;
}

export interface ManagedUserCreateInput {
  username: string;
  display_name: string;
  role: Role;
  password: string;
  provider_id?: string | null;
  is_active?: boolean;
}

export interface ManagedUserUpdateInput {
  display_name?: string;
  role?: Role;
  provider_id?: string | null;
  is_active?: boolean;
}

export interface SessionInfo {
  id: string;
  user_id: string;
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
  last_used_at: string | null;
  is_active: boolean;
}

export interface ProviderSubmissionInput {
  target_year?: number | null;
  education_name: string;
  education_area?: string | null;
  municipality?: string | null;
  region?: string | null;
  yh_points?: number | null;
  study_form?: string | null;
  study_pace_percent?: number | null;
  head_provider_type?: string | null;
  description?: string | null;
  notes?: string | null;
}

export type ProviderSubmissionUpdateInput = Partial<ProviderSubmissionInput>;

export interface ProviderSubmission extends ProviderSubmissionInput {
  id: string;
  provider_id: string;
  provider_name: string | null;
  created_by_user_id: string;
  status: SubmissionStatus;
  target_year: number | null;
  education_name: string;
  submitted_at: string | null;
  review_started_at: string | null;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewEvent {
  id: string;
  submission_id: string;
  actor_user_id: string | null;
  actor_role: "admin" | "provider" | "system";
  action: string;
  from_status: SubmissionStatus | null;
  to_status: SubmissionStatus;
  notes: string | null;
  created_at: string;
}

export interface ApiKeyMetadata {
  id: string;
  name: string;
  description: string | null;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreateResponse extends ApiKeyMetadata {
  api_key: string;
}


export interface SourceMonitorStatus {
  monitor_enabled: boolean;
  run_on_startup: boolean;
  auto_import_enabled: boolean;
  interval_minutes: number;
  source_url: string;
  last_check: Record<string, unknown> | null;
  known_source_files: number;
  unread_notifications: number;
  latest_refresh_run: Record<string, unknown> | null;
}

export interface SourceCheckResponse {
  check_run_id: string;
  status: string;
  source_url: string;
  started_at: string;
  finished_at: string | null;
  http_status: number | null;
  discovered_count: number;
  new_count: number;
  changed_count: number;
  known_count: number;
  message: string;
  error_message: string | null;
  files: SourceFile[];
}

export interface SourceFile {
  id: string;
  file_name: string;
  file_url: string;
  file_type: string;
  source_year: number | null;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
  last_checked_at: string | null;
  last_downloaded_at: string | null;
  last_sha256: string | null;
  downloaded_path: string | null;
  last_error: string | null;
}

export type SourceFileList = Paginated<SourceFile>;

export interface SourceFileDownloadResponse {
  source_file_id: string;
  file_name: string;
  downloaded_path: string;
  sha256: string;
  size_bytes: number;
  changed: boolean;
  message: string;
}

export interface RefreshRun {
  id: string;
  source_file_id: string | null;
  status: string;
  mode: string;
  started_at: string;
  finished_at: string | null;
  rows_imported: number | null;
  affected_years: string | null;
  source_sha256: string | null;
  downloaded_path: string | null;
  processed_path: string | null;
  validation_summary: string | null;
  error_message: string | null;
  triggered_by_user_id: string | null;
}

export type RefreshRunList = Paginated<RefreshRun>;

export interface AdminNotification {
  id: string;
  notification_type: string;
  severity: "info" | "success" | "warning" | "error";
  title: string;
  message: string;
  status: "unread" | "read" | "resolved";
  source_file_id: string | null;
  refresh_run_id: string | null;
  created_at: string;
  read_at: string | null;
  resolved_at: string | null;
  actor_user_id: string | null;
}

export type AdminNotificationList = Paginated<AdminNotification>;
