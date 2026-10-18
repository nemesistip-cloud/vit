const VITPREDICT_API = '/api/apps/vitpredict'

const API_PREFIXES: Array<[string, string]> = [
  ['/api/analytics/leaderboard/users', `${VITPREDICT_API}/analytics/leaderboard/users`],
  ['/api/analytics-studio', `${VITPREDICT_API}/analytics`],
  ['/api/dashboard', `${VITPREDICT_API}/dashboard`],
  ['/api/predictions', `${VITPREDICT_API}/attestations`],
  ['/api/matches', `${VITPREDICT_API}/matches`],
  ['/api/predict', `${VITPREDICT_API}/predict`],
  ['/api/odds', `${VITPREDICT_API}/odds`],
]

export function vitpredictApiPath(path: string): string {
  const queryStart = path.indexOf('?')
  const pathname = queryStart >= 0 ? path.slice(0, queryStart) : path
  const query = queryStart >= 0 ? path.slice(queryStart) : ''
  const [legacyPrefix, appPrefix] = API_PREFIXES.find(([prefix]) =>
    pathname === prefix || pathname.startsWith(`${prefix}/`),
  ) ?? ['', '']

  if (!legacyPrefix) return path
  const appPath = `${appPrefix}${pathname.slice(legacyPrefix.length)}`
  return `${appPath}${query}`
}