import type { BlrecRoomInfo } from '@/lib/types/api'

export function useBlrecUtils() {
  // 名称
  function getRoomName(room: BlrecRoomInfo): string {
    return room.user_info.name
  }

  // 房间ID
  function getRoomId(room: BlrecRoomInfo): number {
    return room.room_info.room_id
  }

  // 短ID
  function getShortId(room: BlrecRoomInfo): number {
    return room.room_info.short_room_id
  }

  // UID
  function getUid(room: BlrecRoomInfo): number {
    return room.user_info.uid
  }

  // 标题
  function getRoomTitle(room: BlrecRoomInfo): string {
    return room.room_info.title
  }

  // 父分区
  function getParentAreaName(room: BlrecRoomInfo): string {
    return room.room_info.parent_area_name
  }

  // 子分区
  function getAreaName(room: BlrecRoomInfo): string {
    return room.room_info.area_name
  }

  // 是否直播中
  function isStreaming(room: BlrecRoomInfo): boolean {
    return room.room_info.live_status === 1
  }

  // 是否录制中
  function isRecording(room: BlrecRoomInfo): boolean {
    return room.task_status.running_status === 'recording'
  }

  // 录播机信息
  function getRecServer(room: BlrecRoomInfo) {
    return {
      name: room.recServer.recName,
      type: room.recServer.recType,
      host: room.recServer.recHost
    }
  }

  // 录制详情
  function getRecordingDetails(room: BlrecRoomInfo) {
    return {
      elapsed: room.task_status.rec_elapsed,
      dlRate: room.task_status.dl_rate,
      recRate: room.task_status.rec_rate
    }
  }

  return {
    getRoomName,
    getRoomId,
    getShortId,
    getUid,
    getRoomTitle,
    getParentAreaName,
    getAreaName,
    isStreaming,
    isRecording,
    getRecServer,
    getRecordingDetails
  }
} 