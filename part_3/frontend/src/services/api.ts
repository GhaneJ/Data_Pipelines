const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, "");

export type ApiStatus = "idle" | "loading" | "success" | "error";

export interface HealthStatus {
  status: string;
}

export interface RequiredTablesHealth {
  ok: boolean;
  checked: string[];
  missing: string[];
}

export interface TableRowHealth {
  table: string;
  ok: boolean;
  row_count: number;
}

export interface DatabaseHealth {
  status: string;
  database_connected: boolean;
  required_tables: RequiredTablesHealth;
  applications: TableRowHealth | null;
  lookup_tables: TableRowHealth[];
}

export class ApiError extends Error {
  status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function buildApiUrl(path: string, params: Record<string, string | number | undefined | null> = {}): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`);

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

export async function requestJson<T>(path: string, params?: Record<string, string | number | undefined | null>): Promise<T> {
  const response = await fetch(buildApiUrl(path, params), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (payload.detail) {
      return JSON.stringify(payload.detail);
    }
  } catch {
    // Fall through to the status-based message below.
  }

  return `API request failed with status ${response.status}`;
}

export function getHealth(): Promise<HealthStatus> {
  return requestJson<HealthStatus>("/health");
}

export function getDatabaseHealth(): Promise<DatabaseHealth> {
  return requestJson<DatabaseHealth>("/health/db");
}
