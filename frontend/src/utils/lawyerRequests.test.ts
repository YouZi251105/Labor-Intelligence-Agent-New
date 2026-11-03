import { describe, expect, it } from 'vitest'

import type { LawyerRequestItem } from '../types/api'
import { splitLawyerRequests } from './lawyerRequests'

function request(overrides: Partial<LawyerRequestItem>): LawyerRequestItem {
  return {
    id: 1,
    case_id: 1,
    user_id: 1,
    lawyer_id: null,
    reason: '需要律师协助',
    preferred_time: '',
    preferred_date: null,
    preferred_slot: null,
    priority: 'normal',
    status: 'pending',
    reject_reason: '',
    created_at: '2026-11-03T10:00:00Z',
    updated_at: '2026-11-03T10:00:00Z',
    accepted_at: null,
    completed_at: null,
    ...overrides,
  }
}

describe('splitLawyerRequests', () => {
  it('keeps a rejected request available for the user to read', () => {
    const result = splitLawyerRequests([
      request({
        id: 7,
        status: 'rejected',
        reject_reason: '近期时段已排满，请改约',
      }),
    ])

    expect(result.active).toBeNull()
    expect(result.terminal?.id).toBe(7)
    expect(result.terminal?.reject_reason).toBe('近期时段已排满，请改约')
  })

  it('prefers the newest active request while retaining the newest terminal request', () => {
    const result = splitLawyerRequests([
      request({ id: 1, status: 'rejected', created_at: '2026-11-03T09:00:00Z' }),
      request({ id: 2, status: 'pending', created_at: '2026-11-03T10:00:00Z' }),
      request({ id: 3, status: 'completed', created_at: '2026-11-03T08:00:00Z' }),
    ])

    expect(result.active?.id).toBe(2)
    expect(result.terminal?.id).toBe(1)
  })
})
