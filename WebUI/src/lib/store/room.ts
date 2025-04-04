import { defineStore } from 'pinia'
import { fetchRoomList } from '@/lib/utils/api'
import type { RoomData } from '@/lib/types/api'
import { useRoomUtils } from '@/lib/utils/useRoomUtils'

export const useRoomStore = defineStore('room', {
  state: () => ({
    rooms: [] as RoomData[],
    loading: false,
    error: null as string | null,
    searchQuery: '',
    filterType: 'all' as 'all' | 'recheme' | 'blrec',
    filterStatus: 'all' as 'all' | 'streaming' | 'recording',
    refreshInterval: null as number | null,
    lastUpdated: null as Date | null,
    lastFetchTime: 0,
    autoRefreshEnabled: true,
  }),

  getters: {
    totalUsers: (state) => state.rooms?.length || 0,
    streamingUsers: (state) => {
      if (!state.rooms) return 0;
      const { isRechemeRoom } = useRoomUtils();
      return state.rooms.filter((room: RoomData) => {
        if (isRechemeRoom(room)) {
          return room.streaming;
        } else {
          return room.room_info.live_status === 1;
        }
      }).length;
    },
    recordingUsers: (state) => {
      if (!state.rooms) return 0;
      const { isRechemeRoom } = useRoomUtils();
      return state.rooms.filter((room: RoomData) => {
        if (isRechemeRoom(room)) {
          return room.recording;
        } else {
          return room.task_status.running_status === 'recording';
        }
      }).length;
    },
    rechemeServers: (state) => [
      ...new Set(
        state.rooms
          .filter((room: RoomData) => room.recServer.recType === 'recheme')
          .map((room: RoomData) => room.recServer.recHost)
      )
    ],
    blrecServers: (state) => [
      ...new Set(
        state.rooms
          .filter((room: RoomData) => room.recServer.recType === 'blrec')
          .map((room: RoomData) => room.recServer.recHost)
      )
    ],
    filteredRooms: (state) => {
      let result = state.rooms;

      if (state.filterType !== 'all') {
        result = result.filter((room: RoomData) => {
          return room.recServer.recType === state.filterType;
        });
      }
      
      if (state.filterStatus !== 'all') {
        const { isRechemeRoom } = useRoomUtils();
        result = result.filter((room: RoomData) => {
          if (isRechemeRoom(room)) {
            return state.filterStatus === 'streaming' ? room.streaming : room.recording;
          } else {
            return state.filterStatus === 'streaming' 
              ? room.room_info.live_status === 1 
              : room.task_status.running_status === 'recording';
          }
        });
      }
      
      if (state.searchQuery) {
        const query = state.searchQuery.toLowerCase();
        const { isRechemeRoom } = useRoomUtils();
        result = result.filter((room: RoomData) => {
          if (isRechemeRoom(room)) {
            return room.roomId.toString().includes(query) || 
                   room.name.toLowerCase().includes(query) ||
                   room.title.toLowerCase().includes(query);
          } else {
            return room.room_info.room_id.toString().includes(query) || 
                   room.user_info.name.toLowerCase().includes(query) ||
                   room.room_info.title.toLowerCase().includes(query);
          }
        });
      }
      
      return result;
    },
    lastUpdatedText: (state) => {
      if (!state.lastUpdated) return '从未'
      const now = new Date()
      const diff = now.getTime() - state.lastUpdated.getTime()

      const seconds = Math.floor(diff / 1000)
      
      if (seconds < 60) {
        return `${seconds}秒前`
      }
      
      const minutes = Math.floor(seconds / 60)
      if (minutes < 60) {
        return `${minutes}分钟前`
      }
      
      const hours = Math.floor(minutes / 60)
      if (hours < 24) {
        return `${hours}小时前`
      }
      
      return state.lastUpdated.toLocaleString()
    }
  },

  actions: {
    async init() {
      await this.fetchRooms()
      if (this.autoRefreshEnabled) {
        this.startAutoRefresh()
      }
    },
    
    async fetchRooms() {
      const now = Date.now()
      if (this.loading || now - this.lastFetchTime < 5000) return
      
      this.loading = true
      this.error = null
      try {
        const { data } = await fetchRoomList()
        this.rooms = data || []
        this.lastUpdated = new Date()
        this.lastFetchTime = now
      } catch (error) {
        this.error = (error as Error).message
        console.error('Error fetching rooms:', error)
      } finally {
        this.loading = false
      }
    },

    startAutoRefresh(interval = 30000) {
      this.stopAutoRefresh()
      this.refreshInterval = window.setInterval(() => {
        if (!document.hidden) {
          this.fetchRooms()
        }
      }, interval)

      document.addEventListener('visibilitychange', this.handleVisibilityChange)
    },

    stopAutoRefresh() {
      if (this.refreshInterval) {
        window.clearInterval(this.refreshInterval)
        this.refreshInterval = null
      }
      document.removeEventListener('visibilitychange', this.handleVisibilityChange)
    },

    handleVisibilityChange() {
      if (!document.hidden && this.refreshInterval) {
        this.fetchRooms()
      }
    },

    setSearchQuery(query: string) {
      this.searchQuery = query
    },
    setFilterType(type: 'all' | 'recheme' | 'blrec') {
      this.filterType = type
    },
    setFilterStatus(status: 'all' | 'streaming' | 'recording') {
      this.filterStatus = status
    },
  }
}) 