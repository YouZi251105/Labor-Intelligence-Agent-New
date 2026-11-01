import { defineStore } from 'pinia'

import { apiGet } from '../api/http'

export interface HealthResponse {
  status: string
  service: string
  version: string
  environment: string
}

type ConnectionState = 'checking' | 'online' | 'offline'

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    connection: 'checking' as ConnectionState,
    health: null as HealthResponse | null,
    lastCheckedAt: null as Date | null,
  }),
  actions: {
    async checkHealth() {
      this.connection = 'checking'
      try {
        this.health = await apiGet<HealthResponse>('/health')
        this.connection = 'online'
      } catch {
        this.connection = 'offline'
        this.health = null
      } finally {
        this.lastCheckedAt = new Date()
      }
    },
  },
})
