/* ============================================================
   VIT API Client — INT1
   Token refresh · Rate limit handling · Loading states
   ============================================================ */

import { toast } from "sonner";

const API_BASE = import.meta.env.VITE_API_URL || "";

let _pendingRefresh: Promise<string | null> | null = null;

function getToken(): string {
  return localStorage.getItem("vit_token") ?? "";
}

function setToken(token: string) {
  localStorage.setItem("vit_token", token);
}

function getRefreshToken(): string {
  return localStorage.getItem("vit_refresh_token") ?? "";
}

async function refreshToken(): Promise<string | null> {
  if (_pendingRefresh) return _pendingRefresh;

  _pendingRefresh = (async () => {
    try {
      const storedRefresh = getRefreshToken();
      if (!storedRefresh) return null;
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: storedRefresh }),
      });
      if (!res.ok) return null;
      const data = await res.json().catch(() => null);
      if (data?.access_token) {
        setToken(data.access_token);
        if (data.refresh_token) {
          localStorage.setItem("vit_refresh_token", data.refresh_token);
        }
        return data.access_token;
      }
      return null;
    } catch {
      return null;
    } finally {
      _pendingRefresh = null;
    }
  })();

  return _pendingRefresh;
}

function parseError(err: unknown, fallback: string): Error {
  if (typeof err === "object" && err !== null) {
    const e = err as Record<string, unknown>;
    let msg: unknown = e.detail ?? e.message ?? e.error;
    if (Array.isArray(msg)) {
      const first = msg[0] as any;
      msg = first?.msg ?? first?.message ?? JSON.stringify(first);
    }
    if (msg === undefined || msg === null || msg === "") {
      return new Error(fallback);
    }
    if (typeof msg === "string") return new Error(msg);
    const stringified = JSON.stringify(msg);
    if (stringified === "{}" || stringified === "[]") return new Error(fallback);
    return new Error(stringified);
  }
  return new Error(fallback);
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> ?? {}),
  };

  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(init.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (res.status === 401 && retry) {
    const newToken = await refreshToken();
    if (newToken) {
      return request<T>(path, init, false);
    }
    localStorage.removeItem("vit_token");
    window.dispatchEvent(new Event("vit:logout"));
    throw new Error("Session expired. Please sign in again.");
  }

  if (res.status === 429) {
    const retryAfter = res.headers.get("Retry-After");
    const secs = retryAfter ? parseInt(retryAfter, 10) : 30;
    toast.warning(`Rate limited. Retry in ${secs}s.`);
    throw new Error(`Rate limited. Retry after ${secs} seconds.`);
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw parseError(err, res.statusText || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export async function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

export async function apiFormPost<T>(path: string, form: FormData): Promise<T> {
  return request<T>(path, { method: "POST", body: form });
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}
