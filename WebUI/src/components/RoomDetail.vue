<template>
  <n-drawer
    :show="show"
    @update:show="emit('update:show', $event)"
    :width="600"
    placement="right"
  >
    <n-drawer-content v-if="currentRoom && show" :title="currentRoom ? getRoomName(currentRoom) : ''">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%">
          <span>{{ currentRoom ? getRoomName(currentRoom) : '' }}</span>
          <n-button 
            v-if="canManageRoom"
            type="error" 
            secondary 
            size="small" 
            @click="confirmDelete"
          >
            <template #icon><n-icon><trash-outline /></n-icon></template>
            删除房间
          </n-button>
        </div>
      </template>
      <!-- 基本信息 -->
      <n-descriptions bordered size="small" :column="2" class="basic-info">
        <n-descriptions-item label="房间号">
          {{ getRoomId(currentRoom) }}
          <template v-if="getShortId(currentRoom) !== 0">({{ getShortId(currentRoom) }})</template>
        </n-descriptions-item>
        <n-descriptions-item label="UID">{{ getUid(currentRoom) }}</n-descriptions-item>
        <n-descriptions-item label="标题" :span="2">{{ getRoomTitle(currentRoom) }}</n-descriptions-item>
        <n-descriptions-item label="分区">
          {{ getParentAreaName(currentRoom) }} > {{ getAreaName(currentRoom) }}
        </n-descriptions-item>
        <n-descriptions-item label="服务器">
          <n-tag :type="currentRoom.recServer.recType === 'recheme' ? 'success' : 'warning'" size="small">
            {{ currentRoom.recServer.recType === 'recheme' ? '录播姬' : 'BLREC' }}
          </n-tag>
          {{ currentRoom.recServer.recName }}
        </n-descriptions-item>
        <n-descriptions-item label="状态">
          <div class="status-tags">
            <n-tag :type="isStreaming(currentRoom) ? 'success' : 'default'" size="small">
              {{ isStreaming(currentRoom) ? '直播中' : '未开播' }}
            </n-tag>
            <n-tag :type="isRecording(currentRoom) ? 'error' : 'default'" size="small">
              {{ isRecording(currentRoom) ? '录制中' : '未录制' }}
            </n-tag>
          </div>
        </n-descriptions-item>
      </n-descriptions>

      <!-- 录播姬信息 -->
      <div v-if="isRechemeRoom(currentRoom)" class="detail-section">
        <n-card title="录制状态" size="small" class="mt-3">
          <n-grid :cols="3" :x-gap="12">
            <n-grid-item>
              <n-statistic label="自动录制">
                <n-tag :type="currentRoom.autoRecord ? 'success' : 'default'" size="small">
                  {{ currentRoom.autoRecord ? '开启' : '关闭' }}
                </n-tag>
              </n-statistic>
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="弹幕连接">
                <n-tag :type="currentRoom.danmakuConnected ? 'success' : 'default'" size="small">
                  {{ currentRoom.danmakuConnected ? '已连接' : '未连接' }}
                </n-tag>
              </n-statistic>
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="本次启动录制">
                <n-tag :type="currentRoom.autoRecordForThisSession ? 'success' : 'default'" size="small">
                  {{ currentRoom.autoRecordForThisSession ? '开启' : '关闭' }}
                </n-tag>
              </n-statistic>
            </n-grid-item>
          </n-grid>
        </n-card>

        <!-- 录制统计 -->
        <n-card title="录制统计" size="small" class="mt-3">
          <template v-if="currentRoom.recording">
            <div class="stat-section">
              <h4>基本统计</h4>
              <n-grid :cols="2" :x-gap="12">
                <n-grid-item>
                  <n-statistic label="会话时长">
                    {{ msToHuman(currentRoom.recordingStats?.sessionDuration || 0) }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="总接收字节">
                    {{ formatBytes(currentRoom.recordingStats?.totalInputBytes || 0) }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="总写入字节">
                    {{ formatBytes(currentRoom.recordingStats?.totalOutputBytes || 0) }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="当前文件大小">
                    {{ formatBytes(currentRoom.recordingStats?.currentFileSize || 0) }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="当前文件最大时间戳">
                    {{ msToHuman(currentRoom.recordingStats?.fileMaxTimestamp || 0) }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="录制速度比例">
                    {{ typeof currentRoom.recordingStats?.durationRatio === 'number' 
                       ? (currentRoom.recordingStats.durationRatio * 100).toFixed(2) 
                       : '0.00' }} %
                  </n-statistic>
                </n-grid-item>
              </n-grid>
            </div>
            
            <div class="stat-section">
              <h4>统计区间数据</h4>
              <n-grid :cols="2" :x-gap="12">
                <n-grid-item>
                  <n-statistic label="统计区间直播数据时长">
                    {{ currentRoom.recordingStats?.addedDuration || 0 }} 毫秒
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="统计区间经过时长">
                    {{ currentRoom.recordingStats?.passedTime || 0 }} 毫秒
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="区间收到视频数据">
                    {{ formatBytes(currentRoom.recordingStats?.inputVideoBytes || 0) }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="区间收到音频数据">
                    {{ formatBytes(currentRoom.recordingStats?.inputAudioBytes || 0) }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="区间新写入视频帧">
                    {{ currentRoom.recordingStats?.outputVideoFrames || 0 }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="区间新写入音频帧">
                    {{ currentRoom.recordingStats?.outputAudioFrames || 0 }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="区间新写入视频">
                    {{ formatBytes(currentRoom.recordingStats?.outputVideoBytes || 0) }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="区间新写入音频">
                    {{ formatBytes(currentRoom.recordingStats?.outputAudioBytes || 0) }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="总计写入视频帧数">
                    {{ currentRoom.recordingStats?.totalOutputVideoFrames || 0 }}
                  </n-statistic>
                </n-grid-item>
                <n-grid-item>
                  <n-statistic label="总计写入音频帧数">
                    {{ currentRoom.recordingStats?.totalOutputAudioFrames || 0 }}
                  </n-statistic>
                </n-grid-item>
              </n-grid>
            </div>

          </template>
          <n-empty v-else description="未在录制中" />
        </n-card>

        <!-- IO 统计 -->
        <n-card title="IO 统计" size="small" class="mt-3">
          <template v-if="currentRoom.recording">
            <n-grid :cols="2" :x-gap="12">
              <n-grid-item>
                <n-statistic label="直播服务器域名">
                  {{ currentRoom.ioStats?.streamHost || '未知' }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="统计区间开始时间">
                  {{ formatIoTime(currentRoom.ioStats?.startTime) }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="统计区间结束时间">
                  {{ formatIoTime(currentRoom.ioStats?.endTime) }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="统计区间时长">
                  {{ currentRoom.ioStats?.duration || 0 }} 毫秒
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="统计区间下载数据">
                  {{ formatBytes(currentRoom.ioStats?.networkBytesDownloaded || 0) }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="平均下载速度">
                  {{ typeof currentRoom.ioStats?.networkMbps === 'number' 
                     ? currentRoom.ioStats.networkMbps.toFixed(2) 
                     : '0.00' }} Mbps
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="统计区间磁盘写入耗时">
                  {{ currentRoom.ioStats?.diskWriteDuration || 0 }} 毫秒
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="统计区间磁盘写入数据">
                  {{ formatBytes(currentRoom.ioStats?.diskBytesWritten || 0) }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="平均写入速度">
                  {{ typeof currentRoom.ioStats?.diskMBps === 'number' 
                     ? currentRoom.ioStats.diskMBps.toFixed(2) 
                     : '0.00' }} MB/s
                </n-statistic>
              </n-grid-item>
            </n-grid>
          </template>
          <n-empty v-else description="未在录制中" />
        </n-card>
      </div>

      <!-- BLREC特有信息 -->
      <div v-if="isBlrecRoom(currentRoom)" class="detail-section">
        <!-- 房间信息 -->
        <n-card title="房间信息" size="small" class="mt-3">
          <n-descriptions bordered size="small" :column="2">
            <n-descriptions-item label="在线人数">
              {{ currentRoom.room_info.online.toLocaleString() }}
            </n-descriptions-item>
            <n-descriptions-item label="开播时间">
              {{ formatTimestamp(currentRoom.room_info.live_start_time) }}
            </n-descriptions-item>
            <n-descriptions-item label="标签" :span="2">
              {{ currentRoom.room_info.tags || '无' }}
            </n-descriptions-item>
            <n-descriptions-item label="分区ID">
              {{ currentRoom.room_info.parent_area_id }}/{{ currentRoom.room_info.area_id }}
            </n-descriptions-item>
            <n-descriptions-item label="简介">
              {{ currentRoom.room_info.description || '无' }}
            </n-descriptions-item>
          </n-descriptions>
        </n-card>

        <!-- 录制状态 -->
        <n-card title="录制状态" size="small" class="mt-3">
          <template v-if="currentRoom.task_status.running_status === 'recording'">
            <n-descriptions bordered size="small" :column="2">
              <n-descriptions-item label="监控状态">
                <n-tag :type="currentRoom.task_status.monitor_enabled ? 'success' : 'default'" size="small">
                  {{ currentRoom.task_status.monitor_enabled ? '已启用' : '未启用' }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="录制状态">
                <n-tag :type="currentRoom.task_status.recorder_enabled ? 'success' : 'default'" size="small">
                  {{ currentRoom.task_status.recorder_enabled ? '已启用' : '未启用' }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="运行状态">
                <n-tag type="error" size="small">录制中</n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="录制画质">
                {{ currentRoom.task_status.real_quality_number === 10000 ? '原画' : currentRoom.task_status.real_quality_number }}
              </n-descriptions-item>
              <n-descriptions-item label="流格式">
                {{ currentRoom.task_status.real_stream_format?.toUpperCase() || '未知' }}
              </n-descriptions-item>
              <n-descriptions-item label="直播服务器">
                {{ currentRoom.task_status.stream_host || '未知' }}
              </n-descriptions-item>
              <n-descriptions-item label="录制路径" :span="2">
                <n-ellipsis>
                  {{ currentRoom.task_status.recording_path || '未开始录制' }}
                </n-ellipsis>
              </n-descriptions-item>
            </n-descriptions>
          </template>
          <n-empty v-else description="未在录制中" />
        </n-card>

        <!-- 统计数据 -->
        <n-card title="IO统计" size="small" class="mt-3">
          <template v-if="currentRoom.task_status.running_status === 'recording'">
            <n-grid :cols="2" :x-gap="12">
              <n-grid-item>
                <n-statistic label="录制时长">
                  {{ formatDuration(currentRoom.task_status.rec_elapsed) }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="下载总量">
                  {{ formatBytes(currentRoom.task_status.dl_total) }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="下载速率">
                  {{ formatDataRate(currentRoom.task_status.dl_rate) }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="录制总量">
                  {{ formatBytes(currentRoom.task_status.rec_total) }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="录制速率">
                  {{ formatDataRate(currentRoom.task_status.rec_rate) }}
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="弹幕总数">
                  {{ currentRoom.task_status.danmu_total }} 条
                </n-statistic>
              </n-grid-item>
              <n-grid-item>
                <n-statistic label="弹幕速率">
                  {{ currentRoom.task_status.danmu_rate.toFixed(2) }} 条/秒
                </n-statistic>
              </n-grid-item>
            </n-grid>
          </template>
          <n-empty v-else description="未在录制中" />
        </n-card>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { 
  NDrawer, NDrawerContent, NDescriptions, 
  NDescriptionsItem, NTag, NGrid, NGridItem, 
  NStatistic, NIcon, NCard, NEllipsis, NEmpty,
  NButton
} from 'naive-ui'
import { TrashOutline } from '@vicons/ionicons5'
import type { RoomData } from '@/lib/types/api'
import { useRoomUtils } from '@/lib/utils/useRoomUtils'
import { formatDuration, formatDataRate } from '@/lib/utils/useFormatUtils'
import { deleteRoom } from '@/lib/utils/api'
import { useRoomStore } from '@/lib/store/room'
import { useDialog, useMessage } from 'naive-ui'
import { useAuthStore } from '@/lib/store/auth'

const props = defineProps<{
  show: boolean
  room: RoomData | null
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
  (e: 'room:deleted', roomId: number): void
}>()

const roomStore = useRoomStore()
const currentRoom = ref<RoomData | null>(null)
const deleteLoading = ref(false)
const dialog = useDialog()
const message = useMessage()
const authStore = useAuthStore()

// 是否可以管理房间
const canManageRoom = computed(() => {
  return !authStore.authRequired || authStore.isAuthenticated
})

// 仅在抽屉打开时更新当前房间数据
watch(() => roomStore.rooms, (newRooms: RoomData[]) => {
  if (props.show && currentRoom.value) {
    const updatedRoom = newRooms.find((r: RoomData) => {
      const serverTypeMatch = r.recServer.recType === currentRoom.value?.recServer.recType;
      
      if (!serverTypeMatch || !currentRoom.value) return false;
      
      if (r.recServer.recType === 'recheme') {
        return isRechemeRoom(r) && isRechemeRoom(currentRoom.value) && 
               r.roomId === currentRoom.value.roomId;
      } else {
        return isBlrecRoom(r) && isBlrecRoom(currentRoom.value) && 
               r.room_info.room_id === currentRoom.value.room_info.room_id;
      }
    });
    
    if (updatedRoom) {
      currentRoom.value = updatedRoom;
    }
  }
})

// 监听show属性变化，更新当前房间数据
watch(() => props.show, (newShow: boolean) => {
  if (newShow && props.room) {
    currentRoom.value = props.room
  } else {
    currentRoom.value = null
  }
})

// 监听room属性变化，更新当前房间数据
watch(() => props.room, (newRoom: RoomData | null) => {
  if (props.show && newRoom) {
    currentRoom.value = newRoom
  }
})

const {
  getRoomName,
  getRoomId,
  getShortId,
  getUid,
  getRoomTitle,
  getParentAreaName,
  getAreaName,
  isStreaming,
  isRecording,
  isRechemeRoom,
  isBlrecRoom
} = useRoomUtils()

// 格式化字节
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 毫秒 to 秒
function msToHuman(ms: number): string {
  if (!ms || ms <= 0) return '0秒'
  
  const seconds = ms / 1000
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = Math.floor(seconds % 60)

  const parts = []
  if (hours > 0) parts.push(`${hours}小时`)
  if (minutes > 0) parts.push(`${minutes}分钟`)
  if (remainingSeconds > 0) parts.push(`${remainingSeconds}秒`)

  return parts.join('')
}

// 格式化时间戳
function formatTimestamp(timestamp: number): string {
  if (!timestamp) return '未知'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化ISO时间
function formatIoTime(timeString: string | undefined): string {
  if (!timeString) return '未知'
  try {
    const date = new Date(timeString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }) + '.' + date.getMilliseconds().toString().padStart(3, '0')
  } catch (e) {
    return '日期格式错误'
  }
}

// 确认删除房间
function confirmDelete() {
  if (!currentRoom.value) return
  
  const roomId = isRechemeRoom(currentRoom.value) 
    ? currentRoom.value.roomId 
    : currentRoom.value.room_info.room_id

  const roomName = getRoomName(currentRoom.value)
  const recType = currentRoom.value.recServer.recType
  const recName = currentRoom.value.recServer.recName
  
  dialog.warning({
    title: '删除房间',
    content: `确定要从${recType === 'recheme' ? '录播姬' : 'BLREC'}(${recName})中删除房间 "${roomName}"(${roomId}) 吗？`,
    positiveText: '确定删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        deleteLoading.value = true
        await handleDeleteRoom(roomId, { recType })
        message.success(`成功从${recType === 'recheme' ? '录播姬' : 'BLREC'}中删除房间`)
        
        emit('update:show', false)
        emit('room:deleted', roomId)
        
        // 刷新数据
        roomStore.fetchRooms()
      } catch (error) {
        message.error(`删除房间失败: ${(error as Error).message}`)
      } finally {
        deleteLoading.value = false
      }
    }
  })
}

// 处理删除房间
async function handleDeleteRoom(
  roomId: number, 
  options?: { recType?: 'recheme' | 'blrec', recName?: string }
) {
  return await deleteRoom(roomId, options)
}
</script>

<style scoped lang="scss">
.basic-info {
  margin-bottom: 12px;
  
  :deep(.n-descriptions-table-wrapper) {
    .n-descriptions-table-header {
      min-width: 80px;
    }
  }
}

.status-tags {
  display: flex;
  gap: 6px;
}

.n-statistic {
  margin-bottom: 10px;
  
  :deep(.n-statistic__label) {
    font-size: 12px;
    color: var(--n-text-color-3);
  }
  
  :deep(.n-statistic__value) {
    font-size: 13px;
    margin-top: 3px;
  }
}

.n-grid {
  margin: 6px 0;
}

.stat-section {
  margin-bottom: 16px;
  
  h4 {
    margin: 14px 0 6px;
    font-size: 14px;
    color: var(--n-text-color-1);
  }
  
  &:last-child {
    margin-bottom: 0;
  }
}

.mb-3 {
  margin-bottom: 12px;
}

.mt-3 {
  margin-top: 12px;
}
</style> 