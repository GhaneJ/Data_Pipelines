import { apiRequest } from "@/api/client";
import type { Paginated, ProviderSummary } from "@/api/types";

export function searchProviders(params: { q?: string; limit?: number; offset?: number } = {}) {
  return apiRequest<Paginated<ProviderSummary>>("/providers", {
    auth: false,
    params: {
      q: params.q,
      limit: params.limit ?? 12,
      offset: params.offset ?? 0,
    },
  });
}
