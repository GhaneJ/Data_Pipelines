import { apiRequest, clearSessionToken, setSessionToken } from "@/api/client";
import type { LoginResponse, Principal, RegistrationRequest, RegistrationRequestInput } from "@/api/types";

export async function login(username: string, password: string): Promise<Principal> {
  const result = await apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    auth: false,
    body: { username, password },
  });
  setSessionToken(result.access_token);
  return whoami();
}

export function whoami(): Promise<Principal> {
  return apiRequest<Principal>("/auth/whoami");
}

export async function logout(): Promise<void> {
  try {
    await apiRequest<{ revoked: boolean }>("/auth/logout", { method: "POST" });
  } finally {
    clearSessionToken();
  }
}

export function submitRegistrationRequest(payload: RegistrationRequestInput): Promise<RegistrationRequest> {
  return apiRequest<RegistrationRequest>("/auth/registration-requests", {
    method: "POST",
    auth: false,
    body: payload,
  });
}
