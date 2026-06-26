/**
 * admin.ts — Typed API client for all admin endpoints.
 * All functions attach the JWT from localStorage automatically.
 */

function getToken(): string | null {
  return localStorage.getItem("vit_token");
}

async function req<T = any>(
  method: string,
  path: string,
  body?: any,
  params?: Record<string, any>,
): Promise<T> {
  const token = getToken();
  let url = path;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    const s = qs.toString();
    if (s) url = `${path}?${s}`;
  }
  const res = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(e?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Users ─────────────────────────────────────────────────────────────────────
export interface AdminUser {
  id: number; username: string; email: string; role: string;
  admin_role: string | null; subscription_tier: string; is_active: boolean;
  is_flagged: boolean; withdrawals_frozen: boolean; wallet_balance: number;
  prediction_count: number; created_at: string;
}

export interface UserDetail extends AdminUser {
  kyc_status: string; validator_status: string | null; referral_count: number;
  clv_score: number | null;
}

export interface UsersListParams {
  page?: number; limit?: number; search?: string;
  role?: string; subscription_tier?: string; is_active?: boolean;
}

export const adminApi = {
  // Users
  getUsers: (p?: UsersListParams) => req("GET", "/api/admin/users", undefined, p as any),
  getUser: (id: number) => req("GET", `/api/admin/users/${id}`),
  updateUser: (id: number, body: Partial<{
    role: string; subscription_tier: string; is_active: boolean;
    withdrawals_frozen: boolean; is_flagged: boolean;
  }>) => req("PATCH", `/api/admin/users/${id}`, body),
  resetUserPassword: (id: number) => req("POST", `/api/admin/users/${id}/reset-password`),
  deleteUser: (id: number) => req("DELETE", `/api/admin/users/${id}`),
  exportUsers: (p?: UsersListParams) =>
    fetch(`/api/admin/users/export?${new URLSearchParams(p as any)}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then((r) => r.blob()),

  // Matches
  getMatches: (p?: { page?: number; limit?: number; status?: string; league?: string; sport?: string; date_from?: string; date_to?: string }) =>
    req("GET", "/api/admin/matches", undefined, p as any),
  setMatchResult: (matchId: string, body: { actual_outcome: string; home_goals?: number; away_goals?: number }) =>
    req("PATCH", `/api/admin/matches/${matchId}/result`, body),
  deleteMatch: (matchId: string) => req("DELETE", `/api/admin/matches/${matchId}`),

  // Predictions
  getPredictions: (p?: { page?: number; limit?: number; user_id?: number; match_id?: string; was_correct?: boolean; date_from?: string; date_to?: string }) =>
    req("GET", "/api/admin/predictions", undefined, p as any),
  recalculateCLV: () => req("POST", "/api/admin/predictions/recalculate-clv"),

  // Config
  getConfig: () => req("GET", "/api/admin/config"),
  updateConfig: (key: string, value: any) => req("PUT", `/api/admin/config/${key}`, { value }),
  createConfig: (body: { key: string; value: any; description?: string }) =>
    req("POST", "/api/admin/config", body),
  deleteConfig: (key: string) => req("DELETE", `/api/admin/config/${key}`),

  // Models
  getModels: () => req("GET", "/api/admin/models"),
  retrainModel: (modelKey: string) => req("POST", `/api/admin/models/${modelKey}/retrain`),
  retrainAll: () => req("POST", "/api/admin/models/retrain-all"),
  getTrainingJobs: (p?: { page?: number; limit?: number; status?: string }) =>
    req("GET", "/api/admin/training-jobs", undefined, p as any),
  getTrainingJob: (jobId: string) => req("GET", `/api/admin/training-jobs/${jobId}`),

  // Audit
  getAuditLog: (p?: { page?: number; limit?: number; admin_id?: number; action?: string; target_type?: string; date_from?: string; date_to?: string }) =>
    req("GET", "/api/admin/audit-log", undefined, p as any),

  // System
  getSystemHealth: () => req("GET", "/api/admin/system/health"),
  getSystemMetrics: () => req("GET", "/api/admin/system/metrics"),
  flushCache: () => req("POST", "/api/admin/system/cache/flush"),

  // Wallet
  getWalletTransactions: (p?: { page?: number; limit?: number; user_id?: number; type?: string; status?: string; currency?: string; date_from?: string; date_to?: string }) =>
    req("GET", "/api/admin/wallet/transactions", undefined, p as any),
  manualCredit: (body: { user_id: number; amount: number; currency: string; reason: string }) =>
    req("POST", "/api/admin/wallet/manual-credit", body),
  manualDebit: (body: { user_id: number; amount: number; currency: string; reason: string }) =>
    req("POST", "/api/admin/wallet/manual-debit", body),
  getVITCoinPrice: () => req("GET", "/api/admin/wallet/vitcoin-price"),
  overrideVITCoinPrice: (price: number) => req("POST", "/api/admin/wallet/vitcoin-price/override", { price_usd: price }),
  getPlatformRevenue: () => req("GET", "/api/admin/wallet/platform-revenue"),
  getWithdrawalQueue: () => req("GET", "/api/admin/wallet/withdrawal-queue"),
  approveWithdrawal: (txId: string) => req("POST", `/api/admin/wallet/withdrawal/${txId}/approve`),
  rejectWithdrawal: (txId: string, reason: string) =>
    req("POST", `/api/admin/wallet/withdrawal/${txId}/reject`, { reason }),

  // Validators
  getValidators: () => req("GET", "/api/admin/validators"),
  slashValidator: (id: number, body: { amount: number; reason: string }) =>
    req("POST", `/api/admin/validators/${id}/slash`, body),
  reinstateValidator: (id: number) => req("POST", `/api/admin/validators/${id}/reinstate`),
  getValidatorAppeals: () => req("GET", "/api/admin/validators/appeals"),
  updateAppeal: (appealId: string, body: { decision: "approved" | "rejected"; admin_note?: string }) =>
    req("PATCH", `/api/admin/validators/appeals/${appealId}`, body),

  // Marketplace
  getMarketplaceListings: (p?: { status?: string }) =>
    req("GET", "/api/admin/marketplace/listings", undefined, p as any),
  approveMarketplaceListing: (id: string) =>
    req("POST", `/api/admin/marketplace/listings/${id}/approve`),
  rejectMarketplaceListing: (id: string, note: string) =>
    req("POST", `/api/admin/marketplace/listings/${id}/reject`, { approval_note: note }),
  deleteMarketplaceListing: (id: string) =>
    req("DELETE", `/api/admin/marketplace/listings/${id}`),
};
