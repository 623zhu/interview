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
    const response = await fetch(`/api${path}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    })
    if (response.status === 204) {
        return undefined as T
    }
    const body = await response.json().catch(() => null)
    if (!response.ok) {
        const detail = body?.detail
        throw new ApiError(response.status, errorMessage(detail))
    }
    return body as T
}
