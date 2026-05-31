import { apiRequest } from "@/api/client";
import type { Paginated, ProviderSubmission, ProviderSubmissionInput, ProviderSubmissionUpdateInput, SubmissionStatus } from "@/api/types";

export function listProviderSubmissions(params: { status?: SubmissionStatus; target_year?: number; limit?: number; offset?: number } = {}) {
  return apiRequest<Paginated<ProviderSubmission>>("/provider/submissions", { params });
}

export function getProviderSubmission(submissionId: string) {
  return apiRequest<ProviderSubmission>(`/provider/submissions/${submissionId}`);
}

export function createProviderSubmission(payload: ProviderSubmissionInput) {
  return apiRequest<ProviderSubmission>("/provider/submissions", { method: "POST", body: payload });
}

export function updateProviderSubmission(submissionId: string, payload: ProviderSubmissionUpdateInput) {
  return apiRequest<ProviderSubmission>(`/provider/submissions/${submissionId}`, { method: "PATCH", body: payload });
}

export function submitProviderSubmission(submissionId: string) {
  return apiRequest<ProviderSubmission>(`/provider/submissions/${submissionId}/submit`, { method: "POST" });
}
