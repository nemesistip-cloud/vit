import { useState, useEffect, useCallback } from "react";

function getToken(): string | null {
  return localStorage.getItem("vit_token");
}

async function apiFetch(endpoint: string, params?: Record<string, any>): Promise<any> {
  const token = getToken();
  let url = endpoint;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    const qsStr = qs.toString();
    if (qsStr) url = `${endpoint}?${qsStr}`;
  }
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export interface UseAdminDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useAdminData<T>(
  endpoint: string,
  params?: Record<string, any>,
): UseAdminDataResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiFetch(endpoint, params)
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch((e) => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, [endpoint, JSON.stringify(params), tick]);

  return { data, loading, error, refetch };
}

export { apiFetch };
