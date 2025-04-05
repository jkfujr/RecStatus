<template>
  <div class="rooms">
    <n-scrollbar 
      class="room-scrollbar"
      style="height: calc(100vh - 64px)"
    >
      <div class="room-container">
        <div class="filter-section">
          <div class="left">
            <n-popover trigger="click" placement="bottom-start" :width="500">
              <template #trigger>
                <n-button size="small" class="mr-2">
                  <template #icon>
                    <n-icon><FilterOutline /></n-icon>
                  </template>
                  <div style="display: flex; align-items: center; gap: 4px;">
                    录播机筛选
                    <n-badge :value="selectedServers.length" :show="selectedServers.length > 0" />
                  </div>
                </n-button>
              </template>
              
              <n-transfer
                v-model:value="selectedServers"
                :options="serverOptions"
                :render-source-list="renderServerSourceList"
                source-filterable
                size="small"
                style="width: 100%"
                select-all-text="全选"
                clear-text="清空"
                source-filter-placeholder="请输入关键词搜索"
                no-data-text="暂无数据"
              />
            </n-popover>
            
            <n-radio-group v-model:value="filterStatus" size="small" buttonStyle="solid" class="mr-2">
              <n-radio-button value="all">全部</n-radio-button>
              <n-radio-button value="live">直播中</n-radio-button>
              <n-radio-button value="recording">录制中</n-radio-button>
            </n-radio-group>
            
            <n-button 
              v-if="canAddRoom && serverStore.servers.length > 0"
              type="primary" 
              size="small" 
              @click="showAddRoomModal = true"
            >
              <template #icon>
                <n-icon><AddOutline /></n-icon>
              </template>
              添加房间
            </n-button>
          </div>
          
          <div class="right">
            <n-input 
              v-model:value="searchQuery" 
              placeholder="搜索房间号或主播名" 
              class="search-input mr-2"
            >
              <template #prefix>
                <n-icon><SearchOutline /></n-icon>
              </template>
            </n-input>
            
            <n-tag 
              size="small" 
              :type="roomStore.loading ? 'warning' : 'success'"
            >
              {{ roomStore.loading ? '更新中' : '最后更新：' + roomStore.lastUpdatedText }}
            </n-tag>
            
            <n-button
              type="primary"
              circle
              size="small"
              @click="roomStore.fetchRooms()"
              :loading="roomStore.loading"
            >
              <template #icon>
                <n-icon><RefreshOutline /></n-icon>
              </template>
            </n-button>
          </div>
        </div>

        <n-spin :show="roomStore.loading">
          <n-empty 
            v-if="!roomStore.loading && filteredRooms.length === 0" 
            description="没有找到符合条件的房间" 
          />
          <div v-else class="room-grid">
            <n-card
              v-for="room in filteredRooms"
              :key="getUniqueKey(room)"
              :class="getRoomCardClass(room)"
              @click="showRoomDetail(room)"
              @contextmenu="handleContextMenu($event, room)"
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
                  <n-tag :type="isStreaming(room) ? 'error' : 'info'" size="small">
                    {{ isStreaming(room) ? '直播中' : '未开播' }}
                  </n-tag>
                  <n-tag :type="isRecording(room) ? 'success' : 'info'" size="small">
                    {{ isRecording(room) ? '录制中' : '未录制' }}
                  </n-tag>
                </div>
              </div>
            </n-card>
          </div>
        </n-spin>
      </div>
    </n-scrollbar>
    
    <!-- 右键菜单 -->
    <n-dropdown
      placement="bottom-start"
      trigger="manual"
      :x="dropdownX"
      :y="dropdownY"
      :options="dropdownOptions"
      :show="showDropdown"
      :on-clickoutside="() => showDropdown = false"
      @select="handleDropdownSelect"
    />
    
    <room-detail
      v-model:show="showDetail"
      :room="selectedRoom"
      @room:deleted="handleRoomDeleted"
    />

    <n-modal v-model:show="showAddRoomModal" preset="card" title="添加房间" style="width: 600px">
      <n-form
        ref="formRef"
        :model="formModel"
        :rules="rules"
        label-placement="left"
        label-width="auto"
        require-mark-placement="right-hanging"
        size="medium"
      >
        <n-form-item label="房间号" path="roomIds">
          <n-input
            v-model:value="formModel.roomIds"
            type="textarea"
            placeholder="请输入房间号，每行一个"
            :autosize="{ minRows: 3, maxRows: 10 }"
          />
          <template #help>
            <n-text depth="3">
              支持批量添加，每行输入一个房间号
            </n-text>
          </template>
        </n-form-item>
        
        <n-form-item label="录播机类型" path="recType">
          <n-radio-group v-model:value="formModel.recType" name="recType" buttonStyle="solid">
            <n-radio-button value="all">全部</n-radio-button>
            <n-radio-button value="recheme">录播姬</n-radio-button>
            <n-radio-button value="blrec">BLREC</n-radio-button>
          </n-radio-group>
        </n-form-item>
        
        <n-form-item label="录播机实例" path="recName">
          <n-select
            v-model:value="formModel.recName"
            :options="recServerOptions"
            placeholder="请选择录播机实例"
            multiple
            clearable
          />
          <template #help>
            <n-text depth="3">
              <ul style="margin: 0; padding-left: 16px;">
                <li>不选择：添加到所有符合类型的在线录播机</li>
                <li>选择一个或多个：仅添加到指定的录播机实例</li>
                <li>离线或错误状态的录播机无法选择</li>
                <li>只显示启用了管理功能的录播机实例</li>
              </ul>
            </n-text>
          </template>
        </n-form-item>
        
        <n-form-item label="自动录制" path="autoRecord">
          <n-switch v-model:value="formModel.autoRecord" />
          <template #help>
            <n-text depth="3" v-if="formModel.recType === 'blrec'">
              BLREC始终自动开始录制，此选项对BLREC无效
            </n-text>
            <n-text depth="3" v-else>
              开启后，房间开播时将自动开始录制（仅对录播姬有效）
            </n-text>
          </template>
        </n-form-item>
      </n-form>
      
      <n-alert type="info" style="margin-top: 16px;">
        <template #icon>
          <n-icon><InformationCircleOutline /></n-icon>
        </template>
        <p>说明:</p>
        <ul style="margin: 0; padding-left: 16px;">
          <li>必须添加到启用了管理功能的录播机实例</li>
          <li>当房间已存在时, 将覆盖原有设置</li>
          <li>BLREC默认自动开始录制, 不受自动录制选项影响</li>
        </ul>
      </n-alert>
      
      <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
        <n-button type="primary" @click="handleAddRoom" :loading="submitting">
          确定
        </n-button>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
// @ts-ignore
import { SearchOutline, RefreshOutline, AddOutline, InformationCircleOutline, TrashOutline, FilterOutline } from '@vicons/ionicons5'
import { useRoomStore } from '@/lib/store/room'
import { useServerStore } from '@/lib/store/server'
import { useAuthStore } from '@/lib/store/auth'
import RoomDetail from '@/components/RoomDetail.vue'
import type { RoomData, RecServer } from '@/lib/types/api'
import { useRoomUtils } from '@/lib/utils/useRoomUtils'
// @ts-ignore
import type { FormInst } from 'naive-ui'
import { addRoom, addRoomsBatch, deleteRoom } from '@/lib/utils/api'
import { NTree } from 'naive-ui'
import type { TransferRenderSourceList, TreeOption } from 'naive-ui'

const roomStore = useRoomStore()
const serverStore = useServerStore()
const authStore = useAuthStore()
const message = useMessage()
const dialog = useDialog()
const loadingBar = useLoadingBar()
const searchQuery = ref('')
const filterType = ref('all')
const filterStatus = ref('all')
const showDetail = ref(false)
const selectedRoom = ref<RoomData | null>(null)
const showAddRoomModal = ref(false)
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

// 右键菜单
const showDropdown = ref(false)
const dropdownX = ref(0)
const dropdownY = ref(0)

// 获取房间
const {
  getRoomType,
  getUniqueKey,
  getRoomName,
  getRoomId,
  getRoomTitle,
  getParentAreaName,
  getAreaName,
  isStreaming,
  isRecording
} = useRoomUtils()

const formModel = ref({
  roomIds: '',
  recType: 'all',
  recName: [] as string[],
  autoRecord: true
})

const rules = {
  roomIds: {
    required: true,
    message: '请输入房间号',
    trigger: 'blur'
  },
}

const selectedServers = ref<Array<string>>([])

const serverTreeData = computed(() => {
  const treeData: any[] = [
    {
      label: '录播姬',
      value: 'recheme-all',
      key: 'recheme-all',
      type: 'recheme',
      children: []
    },
    {
      label: 'BLREC',
      value: 'blrec-all',
      key: 'blrec-all',
      type: 'blrec',
      children: []
    }
  ]
  
  serverStore.servers.forEach((server: RecServer) => {
    const parentNode = treeData.find(node => node.type === server.recType)
    if (parentNode) {
      parentNode.children.push({
        label: server.recName,
        value: `${server.recType}-${server.recName}`,
        key: `${server.recType}-${server.recName}`,
        type: server.recType,
        isLeaf: true
      })
    }
  })
  
  return treeData
})

const serverOptions = computed(() => {
  const result: any[] = []
  
  function flatten(list: any[] = []) {
    list.forEach(item => {
      result.push({
        label: item.label,
        value: item.value,
        disabled: false
      })
      
      if (item.children && item.children.length) {
        flatten(item.children)
      }
    })
  }
  
  flatten(serverTreeData.value)
  return result
})

const recServerOptions = computed(() => {
  return serverStore.servers
    .filter(server => {
      if (server.recStatus !== 'online' || !server.recManage) {
        return false;
      }
      
      if (formModel.value.recType === 'all') {
        return true;
      }
      
      return server.recType === formModel.value.recType;
    })
    .map(server => ({
      label: `${server.recName} (${server.recType === 'recheme' ? '录播姬' : 'BLREC'})`,
      value: server.recName
    }));
});

const renderServerSourceList: TransferRenderSourceList = function ({ onCheck, pattern }) {
  return h(NTree, {
    style: 'margin: 0 4px;',
    keyField: 'value',
    checkable: true,
    selectable: false,
    blockLine: true,
    checkOnClick: true,
    data: serverTreeData.value as unknown as TreeOption[],
    pattern,
    checkedKeys: selectedServers.value,
    onUpdateCheckedKeys: (checkedKeys: Array<string>) => {
      onCheck(checkedKeys)
    }
  })
}

onMounted(async () => {
  if (serverStore.servers.length === 0) {
    await serverStore.fetchServers()
  }
  
  // 初始化房间数据
  if (roomStore.rooms.length === 0) {
    await roomStore.fetchRooms()
  }
  
  // 启动自动刷新
  roomStore.startAutoRefresh()
})

onUnmounted(() => {
  // 停止自动刷新
  roomStore.stopAutoRefresh()
})

watch(() => formModel.value.recType, () => {
  formModel.value.recName = []
})

// 筛选逻辑
const filteredRooms = computed(() => {
  return roomStore.rooms.filter((room: RoomData) => {
    let serverMatch = true
    
    if (selectedServers.value.length > 0) {
      const roomType = getRoomType(room)
      const roomServerName = room.recServer?.recName || ''
      const typeSelected = selectedServers.value.includes(`${roomType}-all`)
      const serverSelected = selectedServers.value.includes(`${roomType}-${roomServerName}`)
      
      serverMatch = typeSelected || serverSelected
    }

    let statusMatch = true
    if (filterStatus.value === 'live') {
      statusMatch = isStreaming(room)
    } else if (filterStatus.value === 'recording') {
      statusMatch = isRecording(room)
    }

    const searchText = searchQuery.value.toLowerCase()
    const searchMatch = searchText === '' || 
      getRoomName(room).toLowerCase().includes(searchText) || 
      getRoomId(room).toString().includes(searchText) ||
      getRoomTitle(room).toLowerCase().includes(searchText)

    return serverMatch && statusMatch && searchMatch
  })
})

const getRoomCardClass = (room: RoomData) => ({
  'room-card': true,
  'is-streaming': isStreaming(room),
  'is-recording': isRecording(room)
})

const showRoomDetail = (room: RoomData) => {
  selectedRoom.value = room
  showDetail.value = true
}

async function handleAddRoom() {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitting.value = true
    
    const roomIds = formModel.value.roomIds
      .split('\n')
      .map((id: string) => id.trim())
      .filter((id: string) => id && !isNaN(Number(id)))
      .map(Number)
    
    if (roomIds.length === 0) {
      throw new Error('没有有效的房间号')
    }
    
    console.log('[DEBUG] 处理房间号列表:', roomIds)
    
    const recType = formModel.value.recType === 'all' ? undefined : formModel.value.recType as 'recheme' | 'blrec' | undefined
    const recNames: string[] = formModel.value.recName
    const autoRecord = formModel.value.autoRecord
    
    console.log('[DEBUG] 选择的录播机类型:', recType)
    console.log('[DEBUG] 选择的录播机实例:', recNames)
    console.log('[DEBUG] 自动录制设置:', autoRecord)
    
    let results;
    
    if (roomIds.length === 1) {
      const roomId = roomIds[0];
      
      if (recNames.length === 0) {
        console.log('[DEBUG] 添加单个房间到所有录播机:', roomId)
        try {
          await addRoom(roomId, {
            autoRecord,
            recType
          });
          results = [{ status: 'fulfilled' }];
        } catch (err) {
          console.error('[DEBUG] 添加房间错误:', err)
          results = [{ status: 'rejected', reason: err }];
        }
      } else {
        console.log('[DEBUG] 添加单个房间到指定录播机:', recNames)
        results = await Promise.allSettled(
          recNames.map(recName => 
            addRoom(roomId, {
              autoRecord,
              recName
            })
          )
        );
      }
    } else {
      const roomObjects = roomIds.map((roomId: number) => ({ 
        roomId, 
        autoRecord 
      }));
      
      if (recNames.length === 0) {
        console.log('[DEBUG] 批量添加房间到所有录播机:', roomIds.length)
        try {
          await addRoomsBatch(roomObjects, { recType });
          results = [{ status: 'fulfilled' }];
        } catch (err) {
          console.error('[DEBUG] 批量添加房间错误:', err)
          results = [{ status: 'rejected', reason: err }];
        }
      } else if (recNames.length === 1) {
        console.log('[DEBUG] 批量添加房间到单个录播机:', recNames[0])
        try {
          await addRoomsBatch(roomObjects, { 
            recName: recNames[0] 
          });
          results = [{ status: 'fulfilled' }];
        } catch (err) {
          console.error('[DEBUG] 批量添加到单个录播机错误:', err)
          results = [{ status: 'rejected', reason: err }];
        }
      } else {
        console.log('[DEBUG] 批量添加房间到多个录播机实例')
        results = await Promise.allSettled(
          recNames.map(recName => 
            addRoomsBatch(roomObjects, { recName })
          )
        );
      }
    }
    
    console.log('[DEBUG] 添加结果:', results)
    
    const succeeded = results.filter(
      (r): r is PromiseFulfilledResult<any> => r.status === 'fulfilled'
    ).length;
    const total = results.length;
    const failed = total - succeeded;
    
    if (failed > 0) {
      const firstError = results.find(r => r.status === 'rejected') as PromiseRejectedResult;
      if (firstError) {
        const errorMessage = firstError.reason?.message || '未知错误';
        message.warning(`添加完成: ${succeeded}个成功，${failed}个失败。错误: ${errorMessage}`);
      } else {
        message.warning(`添加完成: ${succeeded}个成功，${failed}个失败`);
      }
    } else {
      if (roomIds.length === 1) {
        message.success(`成功添加房间: ${roomIds[0]}`);
      } else {
        message.success(`成功添加${roomIds.length}个房间`);
      }
    }
    
    if (succeeded > 0) {
      showAddRoomModal.value = false;
      roomStore.fetchRooms();
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : '添加房间失败';
    console.error('[DEBUG] 处理添加房间过程错误:', errorMessage);
    message.error(errorMessage);
  } finally {
    submitting.value = false;
  }
}

const dropdownOptions = computed(() => {
  if (!selectedRoom.value) return []
  
  const room = selectedRoom.value
  const options = []

  if (authStore.isAuthenticated && room.recServer?.recManage) {
    options.push({
      label: '删除房间',
      key: 'delete',
      icon: () => h(TrashOutline, { 
        style: { 
          width: '20px', 
          height: '20px' 
        }
      }),
      props: {
        class: 'dropdown-danger-item'
      } as any
    })
  }
  
  return options
})

// 右键菜单
function handleContextMenu(event: MouseEvent, room: RoomData) {
  event.preventDefault()
  
  console.log('[DEBUG] 右键菜单 - 房间信息:', room);
  selectedRoom.value = room
  
  dropdownX.value = event.clientX
  dropdownY.value = event.clientY
  
  showDropdown.value = true
  
  console.log('[DEBUG] 显示房间右键菜单:', getRoomId(room))
}

// 下拉菜单选择
async function handleDropdownSelect(key: string) {
  if (!selectedRoom.value) return
  
  const room = selectedRoom.value
  const roomId = getRoomId(room)
  const recType = getRoomType(room)
  const recName = room.recServer?.recName
  
  showDropdown.value = false
  
  console.log(`[DEBUG] 选择菜单项: ${key}, 房间: ${roomId}`)
  
  if (key === 'delete') {
    dialog.warning({
      title: '确认删除',
      content: `确定要从录播机中删除房间 ${roomId} 吗？`,
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: async () => {
        try {
          loadingBar.start()
          
          console.log(`[DEBUG] 确认删除房间 ${roomId}`)
          await deleteRoom(roomId, {
            recType: recType as 'recheme' | 'blrec',
            recName
          })
          
          message.success(`已成功删除房间 ${roomId}`)
          await roomStore.fetchRooms()
        } catch (error) {
          console.error(`[DEBUG] 删除房间失败:`, error)
          message.error(`删除房间失败: ${error instanceof Error ? error.message : String(error)}`)
        } finally {
          loadingBar.finish()
        }
      }
    })
  }
}

function handleRoomDeleted(roomId: number) {
  message.success(`房间 ${roomId} 已删除`)
  roomStore.fetchRooms()
}

const canAddRoom = computed(() => {
  return authStore.isAuthenticated && !authStore.loading
})

watch(() => showAddRoomModal.value, (show) => {
  if (show) {
    serverStore.fetchServers();
    formModel.value = {
      roomIds: '',
      recType: 'all',
      recName: [],
      autoRecord: true
    };
  }
});
</script>

<style scoped lang="scss">
.rooms {
  height: 100%;
  
  .room-scrollbar {
    .room-container {
      padding: 24px;
      
      .filter-section {
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
        
        .left {
          display: flex;
          align-items: center;
          
          .title {
            font-size: 16px;
            font-weight: bold;
          }
        }
        
        .right {
          display: flex;
          gap: 12px;
          align-items: center;
          flex-wrap: wrap;
          
          .search-input {
            width: 200px;
          }
        }
      }
    }
  }

  .room-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }
  
  .room-item {
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      transform: translateY(-4px);
    }

    &.streaming {
      border: 1px solid rgba(var(--n-error-color-rgb), 0.3);
    }

    &.recording {
      border: 1px solid rgba(var(--n-success-color-rgb), 0.3);
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
        font-size: 13px;
        color: var(--text-color-secondary);
        margin-bottom: 8px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .room-area {
        margin-bottom: 8px;
        display: flex;
        gap: 4px;
      }

      .room-status {
        display: flex;
        gap: 8px;
      }
    }
  }
}

.dropdown-icon {
  display: flex;
  align-items: center;
  margin-right: 6px;
}

:deep(.dropdown-danger-item) {
  color: var(--n-error-color) !important;
  
  html.dark & {
    color: var(--n-error-color) !important;
  }
}
</style> 