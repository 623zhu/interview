import { useAuthStore } from '@/stores/auth'

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

function errorMessage(detail: unknown): string {
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

async function refreshAccessToken(): Promise<boolean> {
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
}

function forceLogin() {
  useAuthStore().clear()
  if (!window.location.pathname.startsWith('/login')) {
    window.location.replace('/login')
  }
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
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null
        })
      }
      const ok = await refreshPromise
      if (ok) {
        return request<T>(path, { ...options, skipRefresh: true })
      }
      forceLogin()
    } else if (response.status === 401 && accessToken) {
      forceLogin()
    }
    const detail = body?.detail
    throw new ApiError(response.status, errorMessage(detail))
  }
  return body as T
}
