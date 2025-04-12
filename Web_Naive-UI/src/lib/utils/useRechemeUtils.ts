import type { RoomInfo } from '@/lib/types/api'

export function useRechemeUtils() {
  // 名称
  function getRoomName(room: RoomInfo): string {
    return room.name
  }

  // 房间ID
  function getRoomId(room: RoomInfo): number {
    return room.roomId
  }

  // 短ID
  function getShortId(room: RoomInfo): number {
    return room.shortId
  }

  // UID
  function getUid(room: RoomInfo): number {
    return room.uid
  }

  // 标题
  function getRoomTitle(room: RoomInfo): string {
    return room.title
  }

  // 父分区
  function getParentAreaName(room: RoomInfo): string {
    return room.areaNameParent
  }

  // 子分区
  function getAreaName(room: RoomInfo): string {
    return room.areaNameChild
  }

  // 是否直播中
  function isStreaming(room: RoomInfo): boolean {
    return room.streaming
  }

  // 是否录制中
  function isRecording(room: RoomInfo): boolean {
    return room.recording
  }

  // 录播机信息
  function getRecServer(room: RoomInfo) {
    return {
      name: room.recServer.recName,
      type: room.recServer.recType,
      host: room.recServer.recHost
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
    getRecServer
  }
} 