/**
 * API client for communicating with the Rosetta backend.
 * Handles JWT attachment, error normalization, and typed responses.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export class ApiClientError extends Error {
  public code: string;
  public status: number;
  public details: Record<string, unknown>;

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.name = "ApiClientError";
    this.code = error.code;
    this.status = status;
    this.details = error.details || {};
  }
}

async function getAuthToken(): Promise<string | null> {
  // Dynamically import to avoid circular dependencies
  const { supabase } = await import("./supabase");
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token || null;
}

async function request<T>(
  method: string,
  path: string,
  options: {
    body?: unknown;
    params?: Record<string, string | number>;
    requireAuth?: boolean;
  } = {}
): Promise<T> {
  const { body, params, requireAuth = true } = options;

  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, String(value));
    });
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (requireAuth) {
    const token = await getAuthToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const response = await fetch(url.toString(), {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let errorData: ApiError;
    try {
      const parsed = await response.json();
      errorData = parsed.detail || parsed.error || { code: "UNKNOWN", message: "An error occurred." };
    } catch {
      errorData = { code: "UNKNOWN", message: response.statusText };
    }
    throw new ApiClientError(response.status, errorData);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  get: <T>(path: string, params?: Record<string, string | number>) =>
    request<T>("GET", path, { params }),

  post: <T>(path: string, body?: unknown) =>
    request<T>("POST", path, { body }),

  patch: <T>(path: string, body?: unknown) =>
    request<T>("PATCH", path, { body }),

  delete: <T>(path: string) =>
    request<T>("DELETE", path),

  // Unauthenticated requests (for auth endpoints)
  publicPost: <T>(path: string, body?: unknown) =>
    request<T>("POST", path, { body, requireAuth: false }),
};
