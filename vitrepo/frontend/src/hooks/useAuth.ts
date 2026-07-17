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
