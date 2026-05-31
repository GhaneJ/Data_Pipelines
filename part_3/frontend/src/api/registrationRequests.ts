import { apiRequest } from "@/api/client";
import type { Paginated, RegistrationRequest, RegistrationStatus } from "@/api/types";

export function listRegistrationRequests(params: { status?: RegistrationStatus; limit?: number; offset?: number } = {}) {
  return apiRequest<Paginated<RegistrationRequest>>("/admin/registration-requests", { params });
}

export function getRegistrationRequest(requestId: string) {
  return apiRequest<RegistrationRequest>(`/admin/registration-requests/${requestId}`);
}

export function approveRegistrationRequest(requestId: string, reviewNotes?: string) {
  return apiRequest<RegistrationRequest>(`/admin/registration-requests/${requestId}/approve`, {
    method: "POST",
    body: { review_notes: reviewNotes || null },
  });
}

export function rejectRegistrationRequest(requestId: string, reviewNotes?: string) {
  return apiRequest<RegistrationRequest>(`/admin/registration-requests/${requestId}/reject`, {
    method: "POST",
    body: { review_notes: reviewNotes || null },
  });
}
