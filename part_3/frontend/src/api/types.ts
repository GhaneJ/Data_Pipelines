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

export interface Paginated<T> {
  items: T[];
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
