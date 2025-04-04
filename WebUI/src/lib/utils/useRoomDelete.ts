import { globalService } from '@/lib/utils/globalService'
import { useRoomStore } from '@/lib/store/room'
import { deleteRoom } from '@/lib/utils/api'
import type { RoomData } from '@/lib/types/api'
import { useRoomUtils } from '@/lib/utils/useRoomUtils'

export function useRoomDelete() {
  const { message, loadingBar, dialog } = globalService
  const roomStore = useRoomStore()
  const { getRoomId, getRoomType, getRoomName } = useRoomUtils()
  const confirmDeleteRoom = (room: RoomData, callback?: (roomId: number) => void) => {
    if (!room) return
    
    const roomId = getRoomId(room)
    const recType = getRoomType(room)
    const recName = room.recServer?.recName
    const roomName = getRoomName(room)
    
    dialog.warning({
      title: '确认删除',
      content: `确定要从${recType === 'recheme' ? '录播姬' : 'BLREC'}(${recName})中删除房间 "${roomName}"(${roomId}) 吗？`,
      positiveText: '确定删除',
      negativeText: '取消',
      onPositiveClick: async () => {
        try {
          loadingBar.start()
          
          await deleteRoom(roomId, {
            recType: recType as 'recheme' | 'blrec',
            recName
          })
          
          message.success(`已成功删除房间 ${roomId}`)
          
          await roomStore.fetchRooms()
          
          if (callback) callback(roomId)
        } catch (error) {
          message.error(`删除房间失败: ${error instanceof Error ? error.message : String(error)}`)
          console.error('[DEBUG] 删除房间失败:', error)
        } finally {
          loadingBar.finish()
        }
      }
    })
  }

  return {
    confirmDeleteRoom
  }
} 