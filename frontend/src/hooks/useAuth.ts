// useAuth.ts — simple localStorage-backed auth state

export interface AuthUser {
  id: number
  username: string
  role: string
}

export function getAuthToken(): string | null {
  return localStorage.getItem('vit_token')
}

export function setAuthToken(token: string) {
  localStorage.setItem('vit_token', token)
}

export function clearAuth() {
  localStorage.removeItem('vit_token')
  localStorage.removeItem('vit_user')
}

export function getStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem('vit_user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function storeUser(user: AuthUser) {
  localStorage.setItem('vit_user', JSON.stringify(user))
}

/** Returns auth header object ready for fetch, or {} if not logged in. */
export function authHeaders(): Record<string, string> {
  const t = getAuthToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

/**
 * H4 fix: Drop-in fetch replacement that automatically:
 *  - Injects the Bearer token from localStorage.
 *  - On a 401 response, clears stored auth and redirects to /login so the
 *    user is never stuck in a loop of authenticated-looking calls that fail.
 *
 * Use instead of bare `fetch()` for any authenticated API call.
 */
export async function fetchWithAuth(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = getAuthToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(input, { ...init, headers })

  if (res.status === 401) {
    clearAuth()
    // Use replaceState so the browser back-button does not loop back here.
    if (typeof window !== 'undefined') {
      window.location.replace('/login')
    }
  }

  return res
}
