import type { LawyerRequestItem } from '../types/api'

const ACTIVE_STATUSES = new Set(['pending', 'accepted', 'in_session'])

export function splitLawyerRequests(items: LawyerRequestItem[]) {
  const sorted = [...items].sort(
    (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
  )
  return {
    active: sorted.find((item) => ACTIVE_STATUSES.has(item.status)) ?? null,
    terminal: sorted.find((item) => !ACTIVE_STATUSES.has(item.status)) ?? null,
  }
}
