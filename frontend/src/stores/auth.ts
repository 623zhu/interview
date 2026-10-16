import {ref} from 'vue'
import {defineStore} from 'pinia'
import { login as LoginRequest,type LoginResponse } from '@/api/user'

export const useAuthStore = defineStore('auth',()=>{
    const accessToken = ref('')
    const refreshToken = ref('')

    async function login(email: string, password: string) {
        const result = await LoginRequest(email,password)
        accessToken.value = result.access_token
        refreshToken.value = result.refresh_token
        return result
    }

    return {accessToken,refreshToken,login}
})