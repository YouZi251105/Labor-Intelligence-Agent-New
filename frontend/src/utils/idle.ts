export const IDLE_TIMEOUT_MS = 20 * 60 * 1000
export const IDLE_ACTIVITY_KEY = 'lia_last_activity'

export function isIdleExpired(
  lastActivity: number | null,
  now = Date.now(),
  timeout = IDLE_TIMEOUT_MS,
) {
  return lastActivity !== null && now - lastActivity >= timeout
}

export function readLastActivity() {
  const value = localStorage.getItem(IDLE_ACTIVITY_KEY)
  if (!value) return null
  const timestamp = Number(value)
  return Number.isFinite(timestamp) ? timestamp : null
}

export function markActivity(now = Date.now()) {
  localStorage.setItem(IDLE_ACTIVITY_KEY, String(now))
}

export function clearActivity() {
  localStorage.removeItem(IDLE_ACTIVITY_KEY)
}

export function remainingIdleTime(
  lastActivity: number | null,
  now = Date.now(),
  timeout = IDLE_TIMEOUT_MS,
) {
  if (lastActivity === null) return timeout
  return Math.max(0, timeout - (now - lastActivity))
}
