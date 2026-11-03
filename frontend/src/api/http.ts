import { createSseParser } from '../utils/sse'

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

export async function apiFile(
  path: string,
  init: RequestInit & { auth?: boolean; accept?: string } = {},
): Promise<Blob> {
  const {
    auth = true,
    accept = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ...requestInit
  } = init
  const headers = new Headers(requestInit.headers)
  headers.set('Accept', accept)
  if (auth) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestInit,
    headers,
  })
  if (!response.ok) {
    throw new ApiError(
      await responseErrorMessage(response),
      response.status,
    )
  }
  return response.blob()
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
    throw new ApiError(
      await responseErrorMessage(response),
      response.status,
    )
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function apiStream(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
  onEvent: (event: string, data: unknown) => void,
): Promise<void> {
  const { auth = true, ...requestInit } = init
  const headers = new Headers(requestInit.headers)
  headers.set('Accept', 'text/event-stream')
  if (auth) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestInit,
    headers,
  })
  if (!response.ok) {
    throw new ApiError(
      await responseErrorMessage(response),
      response.status,
    )
  }
  if (!response.body) {
    throw new ApiError('服务端未返回流式响应', response.status)
  }

  const parser = createSseParser(onEvent)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      parser.push(decoder.decode(value, { stream: true }))
    }
    parser.push(decoder.decode())
    parser.finish()
  } catch (error) {
    await reader.cancel().catch(() => undefined)
    throw error
  } finally {
    reader.releaseLock()
  }
}

async function responseErrorMessage(response: Response): Promise<string> {
  let message = `请求失败：${response.status}`
  try {
    const payload = (await response.json()) as { detail?: unknown }
    const detail = payload.detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { loc?: string[]; msg?: string }
      const field = first?.loc?.slice(-1)[0]
      message = first?.msg ?? message
      if (field) message = `${field}: ${message}`
      return message
    }
    if (
      detail &&
      typeof detail === 'object' &&
      'errors' in detail &&
      Array.isArray(detail.errors) &&
      detail.errors.length > 0
    ) {
      return detail.errors.map(String).join('\n')
    }
  } catch {
    // Keep the status-based message when the response is not JSON.
  }
  return message
}

export { API_BASE_URL, TOKEN_KEY }
