import { onBeforeUnmount, onMounted } from 'vue'

import { TOKEN_KEY } from '../api/http'
import {
  IDLE_ACTIVITY_KEY,
  isIdleExpired,
  markActivity,
  readLastActivity,
  remainingIdleTime,
} from '../utils/idle'

const activityEvents = ['pointerdown', 'keydown', 'touchstart', 'scroll'] as const

export function useIdleLogout(onLogout: () => void) {
  let timer: ReturnType<typeof setTimeout> | null = null
  let lastBroadcast = 0
  let mounted = true

  function clearTimer() {
    if (timer) clearTimeout(timer)
    timer = null
  }

  function schedule() {
    if (!mounted) return
    clearTimer()
    const lastActivity = readLastActivity()
    if (isIdleExpired(lastActivity)) {
      onLogout()
      return
    }
    timer = setTimeout(
      () => schedule(),
      remainingIdleTime(lastActivity),
    )
  }

  function recordActivity() {
    const now = Date.now()
    if (now - lastBroadcast < 750) return
    lastBroadcast = now
    markActivity(now)
    schedule()
  }

  function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
      schedule()
    }
  }

  function handleStorage(event: StorageEvent) {
    if (event.key === IDLE_ACTIVITY_KEY) {
      schedule()
    }
    if (event.key === TOKEN_KEY && event.newValue === null) {
      onLogout()
    }
  }

  onMounted(() => {
    if (readLastActivity() === null) markActivity()
    activityEvents.forEach((event) =>
      window.addEventListener(event, recordActivity, { passive: true }),
    )
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('storage', handleStorage)
    schedule()
  })

  onBeforeUnmount(() => {
    mounted = false
    clearTimer()
    activityEvents.forEach((event) =>
      window.removeEventListener(event, recordActivity),
    )
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    window.removeEventListener('storage', handleStorage)
  })
}
