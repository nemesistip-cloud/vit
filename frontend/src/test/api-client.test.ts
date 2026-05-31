import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const mockToast = vi.fn();
vi.mock("sonner", () => ({ toast: { error: mockToast, warning: vi.fn() } }));

vi.mock("wouter", () => ({
  useLocation: () => ["/", vi.fn()],
}));

describe("apiClient refreshToken failure handling", () => {
  let originalFetch: typeof fetch;
  let originalDispatch: typeof window.dispatchEvent;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    originalDispatch = window.dispatchEvent;
    window.dispatchEvent = vi.fn();
    localStorage.setItem("vit_token", "expired-token");
    localStorage.setItem("vit_refresh_token", "bad-refresh");
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    window.dispatchEvent = originalDispatch;
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("clears tokens when main request gets 401 and refresh endpoint returns non-ok", async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Unauthorized" }),
        headers: { get: () => null },
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Invalid refresh token" }),
        headers: { get: () => null },
      });

    const { apiGet } = await import("@/lib/apiClient");

    try {
      await apiGet("/test");
    } catch {
    }

    expect(localStorage.getItem("vit_token")).toBeNull();
    expect(localStorage.getItem("vit_refresh_token")).toBeNull();
  });

  it("does NOT clear tokens when the primary request fails with a network error (no 401)", async () => {
    globalThis.fetch = vi.fn().mockRejectedValueOnce(new Error("Failed to fetch"));

    const { apiGet } = await import("@/lib/apiClient");

    try {
      await apiGet("/test");
    } catch {
    }

    expect(localStorage.getItem("vit_token")).toBe("expired-token");
    expect(localStorage.getItem("vit_refresh_token")).toBe("bad-refresh");
  });

  it("deduplicates concurrent refresh calls (_pendingRefresh race guard)", async () => {
    let refreshCallCount = 0;

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/auth/refresh")) {
        refreshCallCount++;
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ access_token: "new-token", refresh_token: "new-refresh" }),
          headers: { get: () => null },
        });
      }
      return Promise.resolve({
        ok: false,
        status: 401,
        json: async () => ({}),
        headers: { get: () => null },
      });
    });

    const { apiGet } = await import("@/lib/apiClient");

    await Promise.allSettled([apiGet("/a"), apiGet("/b"), apiGet("/c")]);

    expect(refreshCallCount).toBeLessThanOrEqual(1);
  });
});
