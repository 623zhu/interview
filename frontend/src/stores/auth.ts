import { ref } from 'vue'
import { defineStore } from 'pinia'
import { login as loginRequest, logout as logoutRequest, type LoginResponse } from '@/api/user'

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

function read(key: string) {
  return localStorage.getItem(key) ?? ''
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(read(ACCESS_KEY))
  const refreshToken = ref(read(REFRESH_KEY))

  function persist() {
    if (accessToken.value) {
      localStorage.setItem(ACCESS_KEY, accessToken.value)
    } else {
      localStorage.removeItem(ACCESS_KEY)
    }
    if (refreshToken.value) {
      localStorage.setItem(REFRESH_KEY, refreshToken.value)
    } else {
      localStorage.removeItem(REFRESH_KEY)
    }
  }

  function clear() {
    accessToken.value = ''
    refreshToken.value = ''
    persist()
  }

  async function login(email: string, password: string): Promise<LoginResponse> {
    const result = await loginRequest(email, password)
    accessToken.value = result.access_token
    refreshToken.value = result.refresh_token
    persist()
    return result
  }

  async function logout() {
    const token = refreshToken.value
    try {
      if (token) {
        await logoutRequest(token)
      }
    } catch {
      // 本地仍退出
    } finally {
      clear()
    }
  }

  return { accessToken, refreshToken, login, logout, clear }
})
