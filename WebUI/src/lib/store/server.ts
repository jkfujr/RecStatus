import { defineStore } from 'pinia'
import { fetchServers } from '@/lib/utils/api'
import type { RecServer, RoomData } from '@/lib/types/api'
import { useRoomStore } from './room'
import { useRoomUtils } from '@/lib/utils/useRoomUtils'

interface ServerState {
  servers: RecServer[]
  loading: boolean
  error: string | null
  lastUpdated: Date | null
}

export const useServerStore = defineStore('server', {
  state: (): ServerState => ({
    servers: [],
    loading: false,
    error: null,
    lastUpdated: null
  }),

  getters: {
    lastUpdatedText: (state) => {
      if (!state.lastUpdated) return '从未更新';
      
      const now = new Date();
      const diff = now.getTime() - state.lastUpdated.getTime();
      
      // 转换为秒
      const seconds = Math.floor(diff / 1000);
      
      if (seconds < 60) {
        return `${seconds}秒前`;
      } else if (seconds < 3600) {
        return `${Math.floor(seconds / 60)}分钟前`;
      } else if (seconds < 86400) {
        return `${Math.floor(seconds / 3600)}小时前`;
      } else {
        return `${Math.floor(seconds / 86400)}天前`;
      }
    },

    filteredServers: (state) => (type: 'all' | 'recheme' | 'blrec') => {
      if (type === 'all') return state.servers
      return state.servers.filter((server: RecServer) => server.recType === type)
    },

    serverStats: (state) => {
      const roomStore = useRoomStore()
      const { isStreaming, isRecording } = useRoomUtils()
      return state.servers.map((server: RecServer) => {
        const rooms = roomStore.rooms.filter((room: RoomData) => 
          room.recServer.recHost === server.recHost
        )
        const stats = {
          totalRooms: rooms.length,
          streamingRooms: rooms.filter((room: RoomData) => isStreaming(room)).length,
          recordingRooms: rooms.filter((room: RoomData) => isRecording(room)).length
        }

        return {
          ...server,
          ...stats
        }
      })
    }
  },

  actions: {
    async fetchServers() {
      if (this.loading) return

      this.loading = true
      this.error = null

      try {
        const servers = await fetchServers()
        this.servers = servers
        this.lastUpdated = new Date()
      } catch (error) {
        console.error('Failed to fetch servers:', error)
        this.error = (error as Error).message
      } finally {
        this.loading = false
      }
    }
  }
}) 