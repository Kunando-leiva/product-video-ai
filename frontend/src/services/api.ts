export const API_BASE = "http://127.0.0.1:8000/api";

export interface ApiError {
  error: string;
  message: string;
  cause?: string | null;
  solution?: string | null;
  detail?: unknown;
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (res.status === 204) return undefined as T;

  const body = await res.json().catch(() => null);

  if (!res.ok) {
    const err = (body ?? {}) as Partial<ApiError>;
    throw new Error(
      err.message || err.error || `Error ${res.status} en ${path}`
    );
  }
  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(data) }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(data) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
};

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return api.get<HealthResponse>("/health");
}