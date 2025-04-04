<template>
  <div class="room-list">
    <div class="filters">
      <div class="search">
        <n-input
          :value="roomStore.searchQuery"
          @update:value="roomStore.setSearchQuery"
          placeholder="搜索房间号或主播名..."
        >
          <template #prefix>
            <n-icon><SearchOutline /></n-icon>
          </template>
        </n-input>
      </div>
      <div class="filter-buttons">
        <n-radio-group 
          :value="roomStore.filterType"
          @update:value="roomStore.setFilterType"
          size="small"
          buttonStyle="solid"
        >
          <n-radio-button value="all">全部</n-radio-button>
          <n-radio-button value="recheme">录播姬</n-radio-button>
          <n-radio-button value="blrec">BLREC</n-radio-button>
        </n-radio-group>
        
        <n-radio-group 
          :value="roomStore.filterStatus"
          @update:value="roomStore.setFilterStatus"
          size="small"
          buttonStyle="solid"
        >
          <n-radio-button value="all">全部</n-radio-button>
          <n-radio-button value="streaming">直播中</n-radio-button>
          <n-radio-button value="recording">录制中</n-radio-button>
        </n-radio-group>
        
        <n-button 
          type="primary" 
          @click="roomStore.fetchRooms"
          :loading="isLoading"
        >
          <template #icon>
            <n-icon><RefreshOutline /></n-icon>
          </template>
        </n-button>
      </div>
    </div>

    <div class="room-list-content">
      <n-spin :show="isLoading">
        <n-empty 
          v-if="!isLoading && filteredRooms.length === 0" 
          description="没有找到符合条件的房间" 
        />
        <div v-else ref="containerRef" class="room-container" :style="{ height: `${totalHeight}px` }">
          <div class="virtual-list" :style="{ transform: `translateY(${offsetY}px)` }">
            <n-card
              v-for="room in visibleItems"
              :key="getUniqueKey(room)"
              :class="getRoomCardClass(room)"
              @click="showRoomDetail(room)"
              hoverable
              size="small"
              class="room-item"
            >
              <template #header>
                <div class="room-header">
                  <div class="server-info">
                    <n-tag :type="getRoomType(room) === 'recheme' ? 'success' : 'warning'" size="small">
                      {{ getRoomType(room) === 'recheme' ? '录播姬' : 'BLREC' }}
                    </n-tag>
                    <span class="server-name">{{ room.recServer.recName }}</span>
                  </div>
                </div>
              </template>
              <div class="room-content">
                <div class="room-name-container">
                  <span class="room-name">{{ getRoomName(room) }}</span>
                  <span class="room-id">{{ getRoomId(room) }}</span>
                </div>
                <div class="room-title">{{ getRoomTitle(room) }}</div>
                <div class="room-area">
                  <n-tag size="small">{{ getParentAreaName(room) }}</n-tag>
                  <n-tag size="small" type="info">{{ getAreaName(room) }}</n-tag>
                </div>
                <div class="room-status">
                  <n-tag
                    :type="isStreaming(room) ? 'error' : 'info'"
                    size="small"
                  >
                    {{ isStreaming(room) ? '直播中' : '未开播' }}
                  </n-tag>
                  <n-tag
                    :type="isRecording(room) ? 'success' : 'info'"
                    size="small"
                  >
                    {{ isRecording(room) ? '录制中' : '未录制' }}
                  </n-tag>
                </div>
              </div>
            </n-card>
          </div>
        </div>
      </n-spin>
    </div>

    <room-detail
      v-model:show="showDetail"
      :room="selectedRoom"
      @update:room="handleRoomUpdate"
      @room:deleted="handleRoomDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { SearchOutline, RefreshOutline } from '@vicons/ionicons5'
import { useRoomStore } from '@/lib/store/room'
import RoomDetail from './RoomDetail.vue'
import type { RoomData, RoomInfo } from '@/lib/types/api'
import { useGlobalService } from '@/lib/utils/useGlobalService'
import { useVirtualList } from '@/lib/utils/useVirtualList'

const roomStore = useRoomStore()
const route = useRoute()
const { message } = useGlobalService()

// 房间详情
const showDetail = ref(false)
const selectedRoom = ref<RoomData | null>(null)

// 计算属性
const isLoading = computed(() => roomStore.loading)
const filteredRooms = computed(() => roomStore.filteredRooms)
const { containerRef, visibleItems, totalHeight, offsetY } = useVirtualList(
  computed(() => filteredRooms.value),
  {
    itemHeight: 180,
    bufferSize: 5,
    pageSize: 20
  }
)

// 检查是录播姬房间
function isRechemeRoom(room: RoomData): room is RoomInfo {
  return room && 'recServer' in room && room.recServer.recType === 'recheme';
}

// 房间类型
function getRoomType(room: RoomData): 'recheme' | 'blrec' {
  return isRechemeRoom(room) ? 'recheme' : 'blrec';
}

// 唯一标识符作为key
function getUniqueKey(room: RoomData): string {
  if (isRechemeRoom(room)) {
    return `recheme-${room.roomId}`;
  } else {
    return `blrec-${room.room_info.room_id}`;
  }
}

// 房间名称
function getRoomName(room: RoomData): string {
  return isRechemeRoom(room) ? room.name : room.user_info.name;
}

// 房间ID
function getRoomId(room: RoomData): number {
  return isRechemeRoom(room) ? room.roomId : room.room_info.room_id;
}

// 房间标题
function getRoomTitle(room: RoomData): string {
  return isRechemeRoom(room) ? room.title : room.room_info.title;
}

// 父分区
function getParentAreaName(room: RoomData): string {
  return isRechemeRoom(room) ? room.areaNameParent : room.room_info.parent_area_name;
}

// 子分区
function getAreaName(room: RoomData): string {
  return isRechemeRoom(room) ? room.areaNameChild : room.room_info.area_name;
}

// 直播中
function isStreaming(room: RoomData): boolean {
  return isRechemeRoom(room) ? room.streaming : room.room_info.live_status === 1;
}

// 录制中
function isRecording(room: RoomData): boolean {
  return isRechemeRoom(room) ? room.recording : room.task_status.running_status === 'recording';
}

// 房间卡片类名
const getRoomCardClass = (room: RoomData) => ({
  'room-card': true,
  'is-streaming': isStreaming(room),
  'is-recording': isRecording(room)
})

// 显示房间详情
const showRoomDetail = (room: RoomData) => {
  selectedRoom.value = room
  showDetail.value = true
}

// 房间更新
const handleRoomUpdate = (room: RoomData) => {
  if (room) {
    message?.success('房间信息已更新')
    roomStore.fetchRooms()
  }
}

// 房间删除
const handleRoomDeleted = (roomId: number) => {
  message?.success(`房间 ${roomId} 已删除`)
  roomStore.fetchRooms()
}

// 路由变化时重置筛选
watch(() => route, () => {
  roomStore.setSearchQuery('')
  roomStore.setFilterType('all')
  roomStore.setFilterStatus('all')
})

onMounted(() => {
  roomStore.init()
})

onUnmounted(() => {
  roomStore.stopAutoRefresh()
})
</script>

<style scoped lang="scss">
.room-list {
  height: 100%;
  display: flex;
  flex-direction: column;
  
  .filters {
    margin-bottom: 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    
    .search {
      flex: 1;
      min-width: 200px;
    }
    
    .filter-buttons {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
  }
  
  .room-list-content {
    position: relative;
    overflow-y: auto;
  }

  .room-container {
    position: relative;
    overflow-y: auto;
  }

  .room-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
    padding: 16px;
  }
  
  .room-card {
    cursor: pointer;
    transition: all 0.3s;
    
    &:hover {
      transform: translateY(-5px);
      box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    }
    
    &.is-streaming {
      border-color: var(--n-color-error);
      
      :deep(.n-card__header) {
        background-color: rgba(var(--n-error-color-rgb), 0.1);
      }
    }
    
    &.is-recording {
      border-color: var(--n-color-success);
      
      :deep(.n-card__header) {
        background-color: rgba(var(--n-success-color-rgb), 0.1);
      }
    }

    .room-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .server-info {
        display: flex;
        align-items: center;
        gap: 8px;

        .server-name {
          font-size: 12px;
          color: var(--text-color-secondary);
        }
      }
    }

    .room-content {
      .room-name-container {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;

        .room-name {
          font-size: 16px;
          font-weight: bold;
          color: var(--text-color);
        }

        .room-id {
          font-size: 12px;
          color: var(--text-color-secondary);
        }
      }

      .room-title {
        font-size: 14px;
        color: var(--el-text-color-secondary);
        margin-bottom: 8px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .room-area {
        margin-bottom: 8px;
        display: flex;
        gap: 8px;
      }

      .room-status {
        display: flex;
        gap: 8px;
      }
    }
  }
}
</style> 