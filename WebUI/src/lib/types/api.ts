import type { DialogApi, MessageApi, NotificationApi, LoadingBarApi } from 'naive-ui'

export interface RecordingStats {
  sessionDuration: number
  totalInputBytes: number
  totalOutputBytes: number
  currentFileSize: number
  sessionMaxTimestamp: number
  fileMaxTimestamp: number
  addedDuration: number
  passedTime: number
  durationRatio: string
  inputVideoBytes: number
  inputAudioBytes: number
  outputVideoFrames: number
  outputAudioFrames: number
  outputVideoBytes: number
  outputAudioBytes: number
  totalInputVideoBytes: number
  totalInputAudioBytes: number
  totalOutputVideoFrames: number
  totalOutputAudioFrames: number
  totalOutputVideoBytes: number
  totalOutputAudioBytes: number
}

export interface IoStats {
  streamHost: string | null
  startTime: string
  endTime: string
  duration: number
  networkBytesDownloaded: number
  networkMbps: number
  diskWriteDuration: number
  diskBytesWritten: number
  diskMBps: number
}

export interface RoomInfo {
  objectId: string
  roomId: number
  shortId: number
  name: string
  uid: number
  title: string
  areaNameParent: string
  areaNameChild: string
  streaming: boolean
  recording: boolean
  danmakuConnected: boolean
  autoRecord: boolean
  autoRecordForThisSession: boolean
  recordingStats: RecordingStats
  ioStats: IoStats
  recServer: {
    recName: string
    recType: 'recheme'
    recHost: string
    recManage: boolean
  }
}

export interface BlrecRoomInfo {
  user_info: {
    name: string
    gender: string
    face: string
    uid: number
  }
  room_info: {
    uid: number
    room_id: number
    short_room_id: number
    area_id: number
    area_name: string
    parent_area_id: number
    parent_area_name: string
    live_status: number
    live_start_time: number
    online: number
    title: string
    cover: string
    tags: string
    description: string
  }
  task_status: {
    monitor_enabled: boolean
    recorder_enabled: boolean
    running_status: string
    stream_url: string
    stream_host: string
    dl_total: number
    dl_rate: number
    rec_elapsed: number
    rec_total: number
    rec_rate: number
    danmu_total: number
    danmu_rate: number
    real_stream_format: string | null
    real_quality_number: number | null
    recording_path: string
    postprocessor_status: string
    postprocessing_path: string | null
    postprocessing_progress: number | null
  }
  recServer: {
    recName: string
    recType: 'blrec'
    recHost: string
    recManage: boolean
  }
}

export type RoomData = RoomInfo | BlrecRoomInfo

export interface ServerInfo {
  type: 'recheme' | 'blrec'
  url: string
  totalRooms: number
  streamingRooms: number
  recordingRooms: number
}

export interface ApiResponse {
  data: RoomData[]
}

export interface GlobalService {
  dialog: DialogApi
  message: MessageApi
  notification: NotificationApi
  loadingBar: LoadingBarApi
}

export interface RecServer {
  recName: string
  recType: 'recheme' | 'blrec'
  recHost: string
  recStatus: 'online' | 'offline' | 'error'
  recManage: boolean
}

export interface ServerQueryParams {
  recName?: string
  recType?: 'recheme' | 'blrec'
  recStatus?: 'online' | 'offline' | 'error'
} 