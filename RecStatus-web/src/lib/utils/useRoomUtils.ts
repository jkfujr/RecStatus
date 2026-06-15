import type { RoomInfo, BlrecRoomInfo, RoomData } from '@/lib/types/api'
import { useRechemeUtils } from './useRechemeUtils'
import { useBlrecUtils } from './useBlrecUtils'
import { formatDuration, formatDataRate } from './useFormatUtils'

/**
 * 房间数据相关工具函数
 */
export function useRoomUtils() {
  const rechemeUtils = useRechemeUtils()
  const blrecUtils = useBlrecUtils()

  // 检查是否是录播姬
  function isRechemeRoom(room: RoomData): room is RoomInfo {
    return room && 'objectId' in room && !('user_info' in room);
  }

  // 检查是否是BLREC
  function isBlrecRoom(room: RoomData): room is BlrecRoomInfo {
    return room && 'user_info' in room && 'room_info' in room;
  }

  // 类型
  function getRoomType(room: RoomData): 'recheme' | 'blrec' | 'unknown' {
    if (!room) return 'unknown';
    return room.recServer.recType;
  }

  // key
  function getUniqueKey(room: RoomData): string {
    if (isRechemeRoom(room)) {
      return room.objectId;
    } else if (isBlrecRoom(room)) {
      return `blrec-${room.room_info.room_id}`;
    }
    return Math.random().toString();
  }

  // 代理到工具函数
  function proxyToUtils<R>(
    rechemeFunc: (room: RoomInfo) => R,
    blrecFunc: (room: BlrecRoomInfo) => R
  ): (room: RoomData) => R {
    return (room: RoomData) => {
      if (isRechemeRoom(room)) {
        return rechemeFunc(room);
      } else if (isBlrecRoom(room)) {
        return blrecFunc(room);
      }
      throw new Error('Unknown room type');
    };
  }

  // 录播机信息
  function proxyToRecServer(
    rechemeFunc: (room: RoomInfo) => { name: string; type: 'recheme'; host: string },
    blrecFunc: (room: BlrecRoomInfo) => { name: string; type: 'blrec'; host: string }
  ): (room: RoomData) => { name: string; type: 'recheme' | 'blrec'; host: string } {
    return (room: RoomData) => {
      if (isRechemeRoom(room)) {
        return rechemeFunc(room);
      } else if (isBlrecRoom(room)) {
        return blrecFunc(room);
      }
      throw new Error('Unknown room type');
    };
  }

  return {
    isRechemeRoom,
    isBlrecRoom,
    getRoomType,
    getUniqueKey,
    getRoomName: proxyToUtils(rechemeUtils.getRoomName, blrecUtils.getRoomName),
    getRoomId: proxyToUtils(rechemeUtils.getRoomId, blrecUtils.getRoomId),
    getShortId: proxyToUtils(rechemeUtils.getShortId, blrecUtils.getShortId),
    getUid: proxyToUtils(rechemeUtils.getUid, blrecUtils.getUid),
    getRoomTitle: proxyToUtils(rechemeUtils.getRoomTitle, blrecUtils.getRoomTitle),
    getParentAreaName: proxyToUtils(rechemeUtils.getParentAreaName, blrecUtils.getParentAreaName),
    getAreaName: proxyToUtils(rechemeUtils.getAreaName, blrecUtils.getAreaName),
    isStreaming: proxyToUtils(rechemeUtils.isStreaming, blrecUtils.isStreaming),
    isRecording: proxyToUtils(rechemeUtils.isRecording, blrecUtils.isRecording),
    getRecServer: proxyToRecServer(rechemeUtils.getRecServer, blrecUtils.getRecServer),
    formatDuration,
    formatDataRate
  }
} 