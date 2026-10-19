import test from 'node:test'
import assert from 'node:assert/strict'

import { presentStoredPick } from './pickPresentation.ts'

test('presentStoredPick accepts numeric strings and canonicalizes home/away sides', () => {
  const result = presentStoredPick({
    sport: 'basketball',
    prediction_status: 'ready',
    home_prob: '0.62',
    away_prob: '0.38',
    bet_side: 'HOME',
  })

  assert.equal(result.state, 'sealed')
  assert.equal(result.stateLabel, 'Sealed')
  assert.equal(result.pickLabel, 'Home win')
  assert.equal(result.probabilityLabel, '62%')
  assert.equal(result.message, null)
})

test('presentStoredPick keeps three-way picks with normalized draw side names', () => {
  const result = presentStoredPick({
    sport: 'football',
    prediction_status: 'ready',
    home_prob: 0.41,
    draw_prob: '0.29',
    away_prob: 0.3,
    bet_side: 'Draw',
  })

  assert.equal(result.state, 'sealed')
  assert.equal(result.pickLabel, 'Draw')
  assert.equal(result.probabilityLabel, '29%')
})
