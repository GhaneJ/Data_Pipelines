import { apiRequest } from "@/api/client";
import type { ApiKeyCreateResponse, ApiKeyMetadata } from "@/api/types";

export function listApiKeys() {
  return apiRequest<ApiKeyMetadata[]>("/admin/api-keys");
}

export function createApiKey(payload: { name: string; description?: string; scopes: string[]; expires_in_days?: number | null }) {
  return apiRequest<ApiKeyCreateResponse>("/admin/api-keys", { method: "POST", body: payload });
}

export function revokeApiKey(keyId: string) {
  return apiRequest<{ id: string; revoked: boolean }>(`/admin/api-keys/${keyId}/revoke`, { method: "POST" });
}
