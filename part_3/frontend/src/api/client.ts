export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
export const SESSION_TOKEN_KEY = "part3.sessionToken";
export const AUTH_EXPIRED_EVENT = "part3:auth-expired";

export class ApiError extends Error {
  status: number | null;
  requestId: string | null;

  constructor(message: string, status: number | null = null, requestId: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
  }
}

export function getSessionToken(): string | null {
  try {
    return sessionStorage.getItem(SESSION_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setSessionToken(token: string): void {
  sessionStorage.setItem(SESSION_TOKEN_KEY, token);
}

export function clearSessionToken(): void {
  sessionStorage.removeItem(SESSION_TOKEN_KEY);
}

export function buildApiUrl(path: string, params: Record<string, string | number | boolean | undefined | null> = {}): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
  auth?: boolean;
}

async function readError(response: Response): Promise<ApiError> {
  const requestId = response.headers.get("X-Request-ID");
  try {
    const payload = (await response.json()) as {
      detail?: unknown;
      error?: { message?: string; request_id?: string };
    };
    const message =
      payload.error?.message ??
      (typeof payload.detail === "string" ? payload.detail : undefined) ??
      (payload.detail ? JSON.stringify(payload.detail) : undefined) ??
      `API request failed with status ${response.status}`;
    return new ApiError(message, response.status, payload.error?.request_id ?? requestId);
  } catch {
    return new ApiError(`API request failed with status ${response.status}`, response.status, requestId);
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = getSessionToken();

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (options.auth !== false && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(buildApiUrl(path, options.params), {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (response.status === 401) {
    clearSessionToken();
    window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
  }

  if (!response.ok) {
    throw await readError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
