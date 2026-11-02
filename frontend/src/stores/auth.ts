import { defineStore } from 'pinia'

import { apiRequest, TOKEN_KEY } from '../api/http'
import type { AuthResponse, User } from '../types/api'
import {
  clearActivity,
  isIdleExpired,
  markActivity,
  readLastActivity,
} from '../utils/idle'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) as string | null,
    user: null as User | null,
    initialized: false,
    logoutReason: null as 'idle' | null,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
    isAdmin: (state) => state.user?.role === 'admin',
    isLawyer: (state) => state.user?.role === 'lawyer',
  },
  actions: {
    async login(username: string, password: string) {
      const response = await apiRequest<AuthResponse>('/auth/login', {
        method: 'POST',
        auth: false,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      this.setSession(response)
      return response.user
    },
    async register(username: string, password: string, displayName: string) {
      const response = await apiRequest<AuthResponse>('/auth/register', {
        method: 'POST',
        auth: false,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          password,
          display_name: displayName,
        }),
      })
      this.setSession(response)
      return response.user
    },
    async restore() {
      if (!this.token) {
        this.initialized = true
        return
      }
      if (isIdleExpired(readLastActivity())) {
        this.logout('idle')
        this.initialized = true
        return
      }
      try {
        this.user = await apiRequest<User>('/auth/me')
      } catch {
        this.logout()
      } finally {
        this.initialized = true
      }
    },
    setSession(response: AuthResponse) {
      this.token = response.access_token
      this.user = response.user
      this.logoutReason = null
      localStorage.setItem(TOKEN_KEY, response.access_token)
      markActivity()
    },
    markProfileCompleted() {
      if (this.user) this.user.profile_completed = true
    },
    logout(reason: 'idle' | null = null) {
      this.token = null
      this.user = null
      this.logoutReason = reason
      localStorage.removeItem(TOKEN_KEY)
      clearActivity()
    },
  },
})
