type MatchPickRecord = {
  sport?: unknown
  prediction_status?: unknown
  home_prob?: unknown
  draw_prob?: unknown
  away_prob?: unknown
  bet_side?: unknown
  evidence?: {
    missing_elements?: unknown
  } | null
}

export type PickPresentation = {
  state: 'sealed' | 'unavailable' | 'processing' | 'stale' | 'not-sealed'
  stateLabel: string
  pickLabel: string
  probabilityLabel: string
  message: string | null
}

const TWO_WAY_SPORTS = new Set([
  'basketball',
  'tennis',
  'rugby',
  'rugby_union',
  'american_football',
  'baseball',
  'ice_hockey',
  'mma',
  'boxing',
  'cricket',
])

function readProbability(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1
    ? value
    : null
}

function unavailable(
  state: PickPresentation['state'],
  stateLabel: string,
  message: string,
): PickPresentation {
  return {
    state,
    stateLabel,
    pickLabel: 'No sealed pick',
    probabilityLabel: '—',
    message,
  }
}

export function presentStoredPick(match: MatchPickRecord): PickPresentation {
  const status = typeof match.prediction_status === 'string'
    ? match.prediction_status.toLowerCase()
    : ''
  if (status !== 'ready') {
    if (status === 'failed') {
      const missing = Array.isArray(match.evidence?.missing_elements)
        ? match.evidence.missing_elements.filter((item): item is string => typeof item === 'string')
        : []
      const detail = missing.length > 0 ? `Missing evidence: ${missing.join(', ')}.` : null
      return unavailable(
        'unavailable',
        'Unavailable',
        detail ?? 'No verified prediction was recorded for this match.',
      )
    }
    if (status === 'initializing') {
      return unavailable('processing', 'Processing', 'Prediction generation is still in progress.')
    }
    if (status === 'stale') {
      return unavailable('stale', 'Stale', 'The stored prediction is stale and is not shown as a current pick.')
    }
    return unavailable('not-sealed', 'Not sealed', 'No verified prediction has been sealed for this match.')
  }

  const home = readProbability(match.home_prob)
  const away = readProbability(match.away_prob)
  const sport = typeof match.sport === 'string' ? match.sport.toLowerCase().replace(/\s+/g, '_') : ''
  const twoWay = TWO_WAY_SPORTS.has(sport)
  const draw = twoWay ? null : readProbability(match.draw_prob)
  const values = twoWay ? [home, away] : [home, draw, away]

  if (
    values.some((value) => value == null)
    || Math.abs(values.reduce<number>((sum, value) => sum + (value ?? 0), 0) - 1) > 0.01
  ) {
    return unavailable(
      'unavailable',
      'Unavailable',
      'The prediction record is incomplete; no pick was sealed.',
    )
  }

  const sides = [
    { side: 'home', label: 'Home win', probability: home },
    ...(!twoWay ? [{ side: 'draw', label: 'Draw', probability: draw }] : []),
    { side: 'away', label: 'Away win', probability: away },
  ]
  const savedSide = typeof match.bet_side === 'string' ? match.bet_side.toLowerCase() : ''
  const selected = sides.find((entry) => entry.side === savedSide)
    ?? sides.reduce((best, entry) => (entry.probability ?? 0) > (best.probability ?? 0) ? entry : best)

  return {
    state: 'sealed',
    stateLabel: 'Sealed',
    pickLabel: selected.label,
    probabilityLabel: `${Math.round((selected.probability ?? 0) * 100)}%`,
    message: null,
  }
}
