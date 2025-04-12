import type { RoomData, ApiResponse, RecServer, ServerQueryParams } from '@/lib/types/api'
import { useAuthStore } from '@/lib/store/auth'

// Vite 代理处理
const API_BASE_URL = ''

// 请求头
export function createHeaders() {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache'
  }
  
  const token = localStorage.getItem('auth_token')
  
  if (token && token !== 'undefined' && token !== 'null') {
    headers['Authorization'] = `Bearer ${token}`
  } else if (token) {
    console.warn('Found invalid token in localStorage')
    localStorage.removeItem('auth_token')
  }
  
  return headers
}

// 通用请求
async function apiRequest<T = any>(
  url: string, 
  options: {
    method?: string,
    body?: any,
    timeout?: number,
    errorMessage?: string
  } = {}
): Promise<T> {
  const { 
    method = 'GET', 
    body = undefined, 
    timeout = 10000,
    errorMessage = '请求失败'
  } = options;

  try {
    const requestOptions: RequestInit = {
      method,
      headers: createHeaders(),
      signal: timeout ? AbortSignal.timeout(timeout) : undefined
    }

    if (body) {
      requestOptions.body = JSON.stringify(body)
    }

    const response = await fetch(`${API_BASE_URL}${url}`, requestOptions)
    
    if (response.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      throw new Error('认证已过期，请重新登录')
    }
    
    if (response.status === 429) {
      throw new Error('请求过于频繁，请稍后再试')
    }
    
    const responseText = await response.text()
    
    if (!response.ok) {
      try {
        if (responseText) {
          const errorData = JSON.parse(responseText)
          if (errorData.detail) {
            if (typeof errorData.detail === 'string') {
              throw new Error(errorData.detail)
            } else if (Array.isArray(errorData.detail)) {
              const errorMessages = errorData.detail.map((err: any) => {
                if (err.loc && err.msg) {
                  return `${err.loc.join('.')}: ${err.msg}`
                }
                return err.msg || JSON.stringify(err)
              }).join('; ')
              
              throw new Error(`验证错误: ${errorMessages}`)
            }
          }
          throw new Error(errorData.message || `${errorMessage}: ${response.status}`)
        }
      } catch (e) {
        if (e instanceof Error) {
          throw e
        }
        throw new Error(`${errorMessage}: ${response.status}`)
      }
    }
    
    if (responseText && responseText.trim()) {
      try {
        return JSON.parse(responseText) as T
      } catch (e) {
        console.warn('Response is not valid JSON:', responseText.substring(0, 100))
        return { success: true } as unknown as T
      }
    }
    
    return { success: true } as unknown as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('请求超时，请检查网络连接')
    }
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error('无法连接到服务器，请检查网络连接或服务器状态')
    }
    
    throw error
  }
}

// 房间列表
export async function fetchRoomList(): Promise<ApiResponse> {
  try {
    const data = await apiRequest<RoomData[]>('/api/room', {
      errorMessage: '获取房间列表失败'
    })
    return { data }
  } catch (error) {
    console.error('Failed to fetch room list:', error)
    throw error
  }
}

/**
 * 删除房间
 * @param roomId 房间ID
 * @param options 可选参数，指定删除的录播机类型或名称
 */
export async function deleteRoom(
  roomId: number,
  options?: {
    recType?: 'recheme' | 'blrec',
    recName?: string
  }
): Promise<any> {
  try {
    let url = `/api/room/${roomId}`
    const queryParams = new URLSearchParams()
    
    if (options?.recType) {
      queryParams.append('recType', options.recType)
    }
    if (options?.recName) {
      queryParams.append('recName', options.recName)
    }
    
    if (queryParams.toString()) {
      url += `?${queryParams.toString()}`
    }
    
    return await apiRequest(url, {
      method: 'DELETE',
      errorMessage: '删除房间失败'
    })
  } catch (error) {
    console.error('Failed to delete room:', error)
    throw error
  }
}

/**
 * 查询录播机信息
 * @param params 查询参数
 */
export async function fetchServers(params?: ServerQueryParams): Promise<RecServer[]> {
  try {
    let url = '/api/server'
    
    if (params) {
      const queryParams = new URLSearchParams()
      if (params.recName) queryParams.append('recName', params.recName)
      if (params.recType) queryParams.append('recType', params.recType)
      if (params.recStatus) queryParams.append('recStatus', params.recStatus)
      
      const queryString = queryParams.toString()
      if (queryString) {
        url = `${url}?${queryString}`
      }
    }
    
    return await apiRequest<RecServer[]>(url, {
      errorMessage: '获取录播机信息失败'
    })
  } catch (error) {
    console.error('Failed to fetch servers:', error)
    throw error
  }
}

// 添加房间
export async function addRoom(
  roomId: number,
  options?: {
    autoRecord?: boolean,
    recType?: 'recheme' | 'blrec',
    recName?: string
  }
): Promise<any> {
  try {
    if (!roomId || isNaN(Number(roomId)) || Number(roomId) <= 0) {
      throw new Error('无效的房间ID')
    }
    
    const payload: any = {
      roomId: Number(roomId),
    }
    
    if (options) {
      if (options.autoRecord !== undefined) {
        payload.autoRecord = Boolean(options.autoRecord)
      }
      
      if (options.recType) {
        if (options.recType !== 'recheme' && options.recType !== 'blrec') {
          throw new Error(`不支持的录播机类型: ${options.recType}`)
        }
        payload.recType = options.recType
      }
      
      if (options.recName) {
        if (options.recName.startsWith('http://') || options.recName.startsWith('https://')) {
          console.warn('检测到recName是URL格式，这可能不是服务器期望的格式')
        }
        payload.recName = options.recName
      }
    }
    
    return await apiRequest('/api/room', {
      method: 'POST',
      body: payload,
      errorMessage: '添加房间失败'
    })
  } catch (error) {
    console.error('Failed to add room:', error)
    throw error
  }
}

// 批量添加房间
export async function addRoomsBatch(
  rooms: Array<{ roomId: number; autoRecord?: boolean }>,
  options?: {
    recType?: 'recheme' | 'blrec',
    recName?: string
  }
): Promise<any> {
  try {
    const normalizedRooms = rooms.map(room => ({
      roomId: Number(room.roomId),
      autoRecord: room.autoRecord !== undefined ? Boolean(room.autoRecord) : true
    }))
    
    const payload: any = {
      rooms: normalizedRooms
    }
    
    if (options) {
      if (options.recType) {
        payload.recType = options.recType
      }
      if (options.recName) {
        payload.recName = options.recName
      }
    }
    
    return await apiRequest('/api/room/batch', {
      method: 'POST',
      body: payload,
      errorMessage: '批量添加房间失败'
    })
  } catch (error) {
    console.error('Failed to add rooms in batch:', error)
    throw error
  }
}

// 添加录播机
export async function addServer(server: {
  recType: string
  recName: string
  url: string
  manage?: boolean
  basic?: boolean
  basicUser?: string
  basicPass?: string
  basicKey?: string
}) {
  try {
    if (!server.recType || !server.recName || !server.url) {
      throw new Error('录播机类型、名称和URL不能为空')
    }
    
    if (server.recType !== 'recheme' && server.recType !== 'blrec') {
      throw new Error('录播机类型必须是 recheme 或 blrec')
    }
    
    if (!server.url.startsWith('http://') && !server.url.startsWith('https://')) {
      throw new Error('URL必须以 http:// 或 https:// 开头')
    }
    
    const payload: Record<string, any> = {
      recType: server.recType,
      recName: server.recName,
      url: server.url,
      manage: server.manage !== undefined ? server.manage : true
    }
    
    if (server.basic !== undefined) {
      payload.basic = server.basic
      
      if (server.basic) {
        if (server.recType === 'recheme' && server.basicUser && server.basicPass) {
          payload.basicUser = server.basicUser
          payload.basicPass = server.basicPass
        } else if (server.recType === 'blrec' && server.basicKey) {
          payload.basicKey = server.basicKey
        }
      }
    }
    
    return await apiRequest('/api/server', {
      method: 'POST',
      body: payload,
      errorMessage: '添加录播机失败'
    })
  } catch (error) {
    console.error('Failed to add server:', error)
    throw error
  }
}

// 批量添加录播机
export async function addServersBatch(servers: Array<{
  recType: string
  recName: string
  url: string
  manage?: boolean
  basic?: boolean
  basicUser?: string
  basicPass?: string
  basicKey?: string
}>) {
  try {
    for (const server of servers) {
      if (!server.recType || !server.recName || !server.url) {
        throw new Error('每个录播机的类型、名称和URL不能为空')
      }
      
      if (server.recType !== 'recheme' && server.recType !== 'blrec') {
        throw new Error(`录播机 ${server.recName} 的类型必须是 recheme 或 blrec`)
      }
      
      if (!server.url.startsWith('http://') && !server.url.startsWith('https://')) {
        throw new Error(`录播机 ${server.recName} 的URL必须以 http:// 或 https:// 开头`)
      }
    }
    
    const processedServers = servers.map(server => ({
      ...server,
      manage: server.manage !== undefined ? server.manage : true,
      basic: server.basic !== undefined ? server.basic : 
             !!(server.basicUser || server.basicPass || server.basicKey)
    }))
    
    return await apiRequest('/api/server/batch', {
      method: 'POST',
      body: processedServers,
      errorMessage: '批量添加录播机失败'
    })
  } catch (error) {
    console.error('Failed to add servers in batch:', error)
    throw error
  }
}

// 删除单个录播机
export async function deleteServer(recName: string, recType: string) {
  try {
    if (!recName || !recType) {
      throw new Error('录播机名称和类型不能为空')
    }
    
    if (recType !== 'recheme' && recType !== 'blrec') {
      throw new Error('录播机类型必须是 recheme 或 blrec')
    }
    
    return await apiRequest('/api/server', {
      method: 'DELETE',
      body: { recName, recType },
      errorMessage: '删除录播机失败'
    })
  } catch (error) {
    console.error('Failed to delete server:', error)
    throw error
  }
}

// 批量删除录播机
export async function deleteServers(servers: Array<{recName: string, recType: string}>) {
  try {
    for (const server of servers) {
      if (!server.recName || !server.recType) {
        throw new Error('录播机名称和类型不能为空')
      }
      
      if (server.recType !== 'recheme' && server.recType !== 'blrec') {
        throw new Error(`录播机 ${server.recName} 的类型必须是 recheme 或 blrec`)
      }
    }
    
    return await apiRequest('/api/server/batch', {
      method: 'DELETE',
      body: { servers },
      errorMessage: '批量删除录播机失败'
    })
  } catch (error) {
    console.error('Failed to delete servers in batch:', error)
    throw error
  }
}

// 开始/停止录制
export async function toggleRecording(
  roomId: number,
  enabled: boolean,
  options?: {
    recType?: 'recheme' | 'blrec',
    recName?: string
  }
) {
  try {
    let url = `/api/room/${roomId}/record`
    
    const params = new URLSearchParams()
    if (options?.recType) {
      params.append('recType', options.recType)
    }
    if (options?.recName) {
      params.append('recName', options.recName)
    }
    
    if (params.toString()) {
      url += `?${params.toString()}`
    }
    
    return await apiRequest(url, {
      method: 'POST',
      body: { enabled },
      errorMessage: `${enabled ? '开始' : '停止'}录制失败`
    })
  } catch (error) {
    console.error(`Failed to ${enabled ? 'start' : 'stop'} recording:`, error)
    throw error
  }
} 