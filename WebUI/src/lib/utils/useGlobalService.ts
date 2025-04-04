import type { GlobalService } from '@/lib/types/api'

export const GLOBAL_SERVICE_KEY = Symbol('global-service')

export function useGlobalService(): GlobalService {
  const globalService = inject<GlobalService>(GLOBAL_SERVICE_KEY)
  
  if (!globalService) {
    throw new Error('useGlobalService() 必须在 GlobalProvider 内部使用')
  }
  
  return globalService
} 