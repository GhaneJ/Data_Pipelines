import { apiRequest } from "@/api/client";
import type { Paginated, ProviderSubmission, ReviewEvent, SubmissionStatus } from "@/api/types";

export function listAdminProviderSubmissions(params: { status?: SubmissionStatus; provider_id?: string; target_year?: number; limit?: number; offset?: number } = {}) {
  return apiRequest<Paginated<ProviderSubmission>>("/admin/provider-submissions", { params });
}

export function getAdminProviderSubmission(submissionId: string) {
  return apiRequest<ProviderSubmission>(`/admin/provider-submissions/${submissionId}`);
}

export function listReviewEvents(submissionId: string) {
  return apiRequest<ReviewEvent[]>(`/admin/provider-submissions/${submissionId}/events`);
}

function transition(submissionId: string, action: "start-review" | "request-changes" | "approve" | "reject", reviewNotes?: string) {
  return apiRequest<ProviderSubmission>(`/admin/provider-submissions/${submissionId}/${action}`, {
    method: "POST",
    body: { review_notes: reviewNotes || null },
  });
}

export const startReview = (submissionId: string, reviewNotes?: string) => transition(submissionId, "start-review", reviewNotes);
export const requestChanges = (submissionId: string, reviewNotes?: string) => transition(submissionId, "request-changes", reviewNotes);
export const approveSubmission = (submissionId: string, reviewNotes?: string) => transition(submissionId, "approve", reviewNotes);
export const rejectSubmission = (submissionId: string, reviewNotes?: string) => transition(submissionId, "reject", reviewNotes);
