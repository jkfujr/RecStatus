import { globalService } from '@/lib/utils/globalService'
import { useAuthStore } from '@/lib/store/auth'

export function useErrorHandler() {
  const { message } = globalService
  const authStore = useAuthStore()

  const handleApiError = (error: unknown, defaultMessage = '操作失败') => {
    console.error('[API Error]', error)
    
    if (error instanceof Response && error.status === 401) {
      authStore.logout()
      message.error('认证已过期，请重新登录')
      return
    }
    
    if (error instanceof DOMException && error.name === 'AbortError') {
      message.error('请求超时，请检查网络连接')
      return
    }
    
    const errorMessage = error instanceof Error ? error.message : String(error)
    message.error(`${defaultMessage}: ${errorMessage}`)
  }

  return {
    handleApiError
  }
} 