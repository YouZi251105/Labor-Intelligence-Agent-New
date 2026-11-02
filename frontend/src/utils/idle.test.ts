import { describe, expect, it } from 'vitest'

import {
  IDLE_TIMEOUT_MS,
  isIdleExpired,
  remainingIdleTime,
} from './idle'

describe('idle timeout', () => {
  it('expires only after twenty minutes without activity', () => {
    const start = 1_000_000
    expect(isIdleExpired(null, start)).toBe(false)
    expect(isIdleExpired(start, start + IDLE_TIMEOUT_MS - 1)).toBe(false)
    expect(isIdleExpired(start, start + IDLE_TIMEOUT_MS)).toBe(true)
  })

  it('returns the remaining idle time', () => {
    const start = 1_000_000
    expect(remainingIdleTime(start, start + 30_000)).toBe(IDLE_TIMEOUT_MS - 30_000)
    expect(remainingIdleTime(start, start + IDLE_TIMEOUT_MS + 1)).toBe(0)
  })
})
