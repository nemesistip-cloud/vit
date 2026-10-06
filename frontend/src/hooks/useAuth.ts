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
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('vit-auth-change'))
  }
}

export function clearAuth() {
  localStorage.removeItem('vit_token')
  localStorage.removeItem('vit_user')
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('vit-auth-change'))
  }
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
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('vit-auth-change'))
  }
}

export function getDeviceId(): string {
  if (typeof window === 'undefined') return 'dev_server'
  let devId = localStorage.getItem('vit_device_id')
  if (!devId) {
    devId = 'dev_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36)
    localStorage.setItem('vit_device_id', devId)
  }
  return devId
}

/** Returns auth header object ready for fetch, or {} if not logged in. */
export function authHeaders(): Record<string, string> {
  const t = getAuthToken()
  const devId = getDeviceId()
  const headers: Record<string, string> = { 'X-Device-Id': devId }
  if (t) headers.Authorization = `Bearer ${t}`
  return headers
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
  const devId = getDeviceId()
  if (devId) headers.set('X-Device-Id', devId)

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
