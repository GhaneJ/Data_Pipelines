import { apiRequest } from "@/api/client";
import type { ManagedUser, ManagedUserCreateInput, ManagedUserUpdateInput, Paginated, Role, SessionInfo } from "@/api/types";

export function listUsers(params: { role?: Role; is_active?: boolean; search?: string; limit?: number; offset?: number } = {}) {
  return apiRequest<Paginated<ManagedUser>>("/admin/users", { params });
}

export function getUser(userId: string) {
  return apiRequest<ManagedUser>(`/admin/users/${userId}`);
}

export function createUser(payload: ManagedUserCreateInput) {
  return apiRequest<ManagedUser>("/admin/users", { method: "POST", body: payload });
}

export function updateUser(userId: string, payload: ManagedUserUpdateInput) {
  return apiRequest<ManagedUser>(`/admin/users/${userId}`, { method: "PATCH", body: payload });
}

export function resetPassword(userId: string, newPassword: string) {
  return apiRequest<ManagedUser>(`/admin/users/${userId}/reset-password`, {
    method: "POST",
    body: { new_password: newPassword, revoke_existing_sessions: true },
  });
}

export function deactivateUser(userId: string) {
  return apiRequest<{ id: string; changed: boolean }>(`/admin/users/${userId}/deactivate`, { method: "POST" });
}

export function reactivateUser(userId: string) {
  return apiRequest<{ id: string; changed: boolean }>(`/admin/users/${userId}/reactivate`, { method: "POST" });
}

export function listUserSessions(userId: string) {
  return apiRequest<{ items: SessionInfo[] }>(`/admin/users/${userId}/sessions`);
}

export function revokeUserSession(userId: string, sessionId: string) {
  return apiRequest<{ id: string; revoked: boolean }>(`/admin/users/${userId}/sessions/${sessionId}/revoke`, { method: "POST" });
}
