import { request } from "./http"

export interface LoginResponse {
    access_token: string
    refresh_token: string
    token_type: string
    expires_in: number
}

export function login(email: string, password: string) {
    return request<LoginResponse>('/api/v1/users/session', {
        method:'POST',
        body:JSON.stringify({email,password}),
        skipAuth: true,
        skipRefresh: true,
    })
}

export function logout(refreshToken: string) {
    return request<void>('/api/v1/users/session', {
        method: 'DELETE',
        body: JSON.stringify({ refresh_token: refreshToken }),
        skipAuth: true,
        skipRefresh: true,
    })
}

export function sendRegisterCode(email:string) {
    return request<Record<string,never>>('/api/v1/users/verification-codes',{
         method:'POST',
         body:JSON.stringify({email}),
    })
}

export function register(email: string, password: string, verificationCode: string) {
    return request('/api/v1/users', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        verification_code: verificationCode,
      }),
    })
  }

  export function refreshToken(refreshToken: string) {
    return request<LoginResponse>('/api/v1/users/session/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
      skipAuth: true,
      skipRefresh: true,
    })
  }

  export function sendResetCode(email: string) {
    return request<Record<string, never>>('/api/v1/users/password-reset/verification-codes', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }

  export function resetPassword(email: string, newPassword: string, verificationCode: string) {
    return request<{ message: string }>('/api/v1/users/password-reset', {
      method: 'POST',
      body: JSON.stringify({
        email,
        new_password: newPassword,
        verification_code: verificationCode,
      }),
    })
  }