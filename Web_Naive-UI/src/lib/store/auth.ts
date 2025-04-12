import { defineStore } from 'pinia'
import { globalService } from '@/lib/utils/globalService'

interface LoginResponse {
  token?: string
  auth_required?: boolean
  message?: string
  detail?: string | object
}

interface AuthState {
  token: string | null
  authRequired: boolean
  loading: boolean
  error: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: null,
    authRequired: false,
    loading: false,
    error: null
  }),

  getters: {
    isAuthenticated: (state) => {
      return !state.authRequired || !!state.token
    }
  },

  actions: {
    async checkAuthStatus() {
      this.loading = true
      this.error = null
      
      try {
        const response = await fetch('/api/login')
        const data = await response.json() as LoginResponse
        this.authRequired = !!data.auth_required
        
        if (!data.auth_required) {
          return true
        }
        
        // 检查 token
        const storedToken = localStorage.getItem('auth_token')
        if (storedToken) {
          this.token = storedToken
          return true
        }
        
        return false
      } catch (error) {
        console.error('Failed to check auth status:', error)
        this.error = (error as Error).message
        return false
      } finally {
        this.loading = false
      }
    },

    async login(username: string, password: string) {
      this.loading = true
      this.error = null

      const { message } = globalService
      
      try {
        const response = await fetch('/api/login', {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ username, password })
        })
        
        let data: LoginResponse = {}
        try {
          data = await response.json()
        } catch (e) {
          console.error('解析登录响应失败:', e)
        }
        
        if (response.ok) {
          if (data.token) {
            this.token = data.token
            localStorage.setItem('auth_token', data.token)
            message?.success('登录成功')
            return true
          } else {
            return !data.auth_required
          }
        } else {
          const errorMsg = this.extractErrorMessage(data)
          throw new Error(errorMsg)
        }
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
        message?.error(`登录失败: ${this.error}`)
        return false
      } finally {
        this.loading = false
      }
    },
    
    // 提取错误信息
    extractErrorMessage(data: LoginResponse): string {
      if (!data) return '登录失败'
      
      if (data.detail) {
        return typeof data.detail === 'string' 
          ? data.detail 
          : JSON.stringify(data.detail)
      }
      
      if (data.message) {
        return data.message
      }
      
      return '登录失败'
    },

    logout() {
      this.token = null
      localStorage.removeItem('auth_token')
      globalService.message?.success('已退出登录')
    }
  }
}) 