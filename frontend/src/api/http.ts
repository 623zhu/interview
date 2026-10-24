import { useAuthStore } from '@/stores/auth'

export class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
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

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const accessToken = useAuthStore().accessToken
    const headers = new Headers(options.headers)
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`)
    }
    const isFormData = options.body instanceof FormData
    if (!isFormData && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }
    const response = await fetch(`/api${path}`, {
        ...options,
        headers,
    })
    if (response.status === 204) {
        return undefined as T
    }
    const body = await response.json().catch(() => null)
    if (!response.ok) {
        if (response.status === 401 && accessToken) {
          useAuthStore().clear()
          if (!window.location.pathname.startsWith('/login')) {
            window.location.replace('/login')
          }
        }
        const detail = body?.detail
        throw new ApiError(response.status, errorMessage(detail))
    }
    return body as T
}
