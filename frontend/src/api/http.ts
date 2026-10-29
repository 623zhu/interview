import { useAuthStore } from '@/stores/auth'

const ACCESS_REFRESH_SKEW_SECONDS = 60

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export type RequestOptions = RequestInit & {
  skipAuth?: boolean
  skipRefresh?: boolean
}

export function errorMessage(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item: { msg?: string }) => item.msg ?? '')
      .join(';')
  }
  return '请求失败'
}

let refreshPromise: Promise<boolean> | null = null

function accessTokenExp(token: string): number | null {
  const parts = token.split('.')
  if (parts.length < 2) return null
  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const pad = base64.length % 4
    const padded = pad ? `${base64}${'='.repeat(4 - pad)}` : base64
    const payload = JSON.parse(atob(padded)) as { exp?: number }
    return typeof payload.exp === 'number' ? payload.exp : null
  } catch {
    return null
  }
}

function accessTokenNeedsRefresh(token: string): boolean {
  const exp = accessTokenExp(token)
  if (exp == null) return false
  return exp <= Date.now() / 1000 + ACCESS_REFRESH_SKEW_SECONDS
}

export async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    const auth = useAuthStore()
    if (!auth.refreshToken) return false
    try {
      const { refreshToken } = await import('./user')
      const result = await refreshToken(auth.refreshToken)
      auth.setTokens(result.access_token, result.refresh_token)
      return true
    } catch {
      return false
    }
  })().finally(() => {
    refreshPromise = null
  })
  return refreshPromise
}

export function forceLogin() {
  useAuthStore().clear()
  if (!window.location.pathname.startsWith('/login')) {
    window.location.replace('/login')
  }
}

export async function ensureFreshAccessToken(options: { force?: boolean } = {}): Promise<boolean> {
  const auth = useAuthStore()
  if (!options.force && auth.accessToken && !accessTokenNeedsRefresh(auth.accessToken)) {
    return true
  }
  if (!auth.refreshToken) return false
  return refreshAccessToken()
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuth, skipRefresh, headers: initHeaders, ...fetchInit } = options
  const accessToken = skipAuth ? '' : useAuthStore().accessToken
  const headers = new Headers(initHeaders)
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  const isFormData = fetchInit.body instanceof FormData
  if (!isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`/api${path}`, {
    ...fetchInit,
    headers,
  })
  if (response.status === 204) {
    return undefined as T
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const canRefresh =
      response.status === 401 &&
      !skipRefresh &&
      Boolean(accessToken) &&
      !path.includes('/users/session')
    if (canRefresh) {
      const ok = await refreshAccessToken()
      if (ok) {
        return request<T>(path, { ...options, skipRefresh: true })
      }
      forceLogin()
    } else if (response.status === 401 && accessToken) {
      forceLogin()
    }
    throw new ApiError(response.status, errorMessage(body?.detail))
  }
  return body as T
}
