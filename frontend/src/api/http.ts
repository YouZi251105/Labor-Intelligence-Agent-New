const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const TOKEN_KEY = 'lia_token'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>(path, init)
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, ...requestInit } = init
  const headers = new Headers(requestInit.headers)
  headers.set('Accept', 'application/json')

  if (auth) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestInit,
    headers,
  })

  if (!response.ok) {
    let message = `请求失败：${response.status}`
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') {
        message = payload.detail
      } else if (Array.isArray(payload.detail) && payload.detail.length > 0) {
        // FastAPI/Pydantic 422 校验错误：detail 是数组，提取首个字段和提示
        const first = payload.detail[0] as { loc?: string[]; msg?: string }
        const field = first?.loc?.slice(-1)[0]
        message = first?.msg ?? message
        if (field) message = `${field}: ${message}`
      }
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new ApiError(message, response.status)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export { API_BASE_URL, TOKEN_KEY }
