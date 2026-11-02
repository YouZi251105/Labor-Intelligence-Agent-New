import { defineStore } from 'pinia'

import { apiRequest, TOKEN_KEY } from '../api/http'
import type { AuthResponse, User } from '../types/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) as string | null,
    user: null as User | null,
    initialized: false,
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
      localStorage.setItem(TOKEN_KEY, response.access_token)
    },
    markProfileCompleted() {
      if (this.user) this.user.profile_completed = true
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
