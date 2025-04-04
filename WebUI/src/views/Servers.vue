<template>
  <div class="servers">
    <n-scrollbar 
      class="server-scrollbar"
      style="height: calc(100vh - 64px)"
    >
      <div class="server-container">
        <div class="filter-section">
          <div class="left">
            <n-radio-group v-model:value="serverFilter" size="small" buttonStyle="solid" class="mr-2">
              <n-radio-button value="all">全部</n-radio-button>
              <n-radio-button value="recheme">录播姬</n-radio-button>
              <n-radio-button value="blrec">BLREC</n-radio-button>
            </n-radio-group>
            
            <n-button 
              v-if="canAddServer"
              type="primary" 
              size="small" 
              @click="showAddServerModal = true"
            >
              <template #icon>
                <n-icon><AddOutline /></n-icon>
              </template>
              添加录播机
            </n-button>
          </div>
          
          <div class="right">
            <n-tag 
              size="small" 
              :type="loading ? 'warning' : 'success'"
              class="mr-2"
            >
              {{ loading ? '更新中' : '最后更新：' + lastUpdatedText }}
            </n-tag>
            
            <n-button
              type="primary"
              circle
              size="small"
              @click="handleRefresh"
              :loading="loading"
            >
              <template #icon>
                <n-icon><RefreshOutline /></n-icon>
              </template>
            </n-button>
          </div>
        </div>

        <n-data-table
          :loading="loading"
          :data="filteredServerData" 
          :bordered="false"
          :row-class-name="getRowClassName"
          :columns="columns"
          :single-line="false"
          size="medium"
          :max-height="tableMaxHeight"
          :scroll-x="tableWidth"
          class="server-table"
        />
      </div>
    </n-scrollbar>
    
    <n-modal v-model:show="showAddServerModal" preset="card" title="添加录播机" style="width: 600px">
      <n-tabs type="line" animated>
        <n-tab-pane name="single" tab="单个添加">
          <n-form
            ref="singleFormRef"
            :model="singleFormModel"
            :rules="serverRules"
            label-placement="left"
            label-width="120"
            require-mark-placement="right-hanging"
          >
            <n-form-item label="录播机类型" path="recType">
              <n-radio-group v-model:value="singleFormModel.recType" name="recType">
                <n-radio-button value="recheme">录播姬</n-radio-button>
                <n-radio-button value="blrec">BLREC</n-radio-button>
              </n-radio-group>
              <template #help>
                <n-text depth="3">
                  录播姬和BLREC为不同的录播软件，请根据你的实际使用选择
                </n-text>
              </template>
            </n-form-item>
            <n-form-item label="录播机名称" path="recName">
              <n-input v-model:value="singleFormModel.recName" placeholder="请输入唯一的录播机名称" />
              <template #help>
                <n-text depth="3">
                  必须是全局唯一的名称，用于标识此录播机
                </n-text>
              </template>
            </n-form-item>
            <n-form-item label="录播机地址" path="url">
              <n-input v-model:value="singleFormModel.url" placeholder="例如：http://192.168.1.100:2356" />
              <template #help>
                <n-text depth="3">
                  录播姬默认端口为2356，BLREC默认端口为2233，必须以http://或https://开头
                </n-text>
              </template>
            </n-form-item>
            <n-form-item v-if="singleFormModel.recType === 'recheme'" label="启用管理" path="manage">
              <n-switch v-model:value="singleFormModel.manage" />
              <template #help>
                <n-text depth="3">
                  启用后可以在此平台添加房间、修改设置等；关闭则仅支持查看状态
                </n-text>
              </template>
            </n-form-item>
            <n-form-item v-if="singleFormModel.recType === 'blrec'" label="启用管理" path="manage">
              <n-switch v-model:value="singleFormModel.manage" />
              <template #help>
                <n-text depth="3">
                  启用后可以在此平台添加房间、修改设置等；关闭则仅支持查看状态
                </n-text>
              </template>
            </n-form-item>
            <n-form-item label="认证设置" path="authType">
              <n-radio-group v-model:value="singleFormModel.authType">
                <n-radio value="global">全局设置</n-radio>
                <n-radio value="enable">启用认证</n-radio>
                <n-radio v-if="singleFormModel.recType === 'recheme'" value="disable">禁用认证</n-radio>
              </n-radio-group>
            </n-form-item>
            <template v-if="singleFormModel.recType === 'recheme' && singleFormModel.authType === 'enable'">
              <n-form-item label="用户名" path="basicUser">
                <n-input v-model:value="singleFormModel.basicUser" placeholder="请输入录播姬HTTP Basic认证用户名" />
              </n-form-item>
              <n-form-item label="密码" path="basicPass">
                <n-input v-model:value="singleFormModel.basicPass" type="password" placeholder="请输入录播姬HTTP Basic认证密码" />
              </n-form-item>
            </template>
            <template v-if="singleFormModel.recType === 'blrec' && singleFormModel.authType === 'enable'">
              <n-form-item label="API密钥" path="basicKey">
                <n-input v-model:value="singleFormModel.basicKey" placeholder="请输入BLREC的API密钥" />
              </n-form-item>
            </template>
          </n-form>
          <div class="action-btns">
            <n-button type="primary" @click="handleAddSingleServer" :loading="submitting">
              添加
            </n-button>
          </div>
        </n-tab-pane>
        
        <n-tab-pane name="batch" tab="批量添加">
          <n-alert title="批量添加说明" type="info" style="margin-bottom: 16px">
            <template #icon>
              <n-icon><InformationCircleOutline /></n-icon>
            </template>
            请按照以下JSON格式输入录播机信息，可以同时添加多个录播机。
          </n-alert>
          <n-space vertical>
            <n-button @click="fillBatchExampleData" size="small">填充示例数据</n-button>
            <n-input
              v-model:value="batchFormModel.servers"
              type="textarea"
              :autosize="{ minRows: 10, maxRows: 20 }"
              placeholder='[
  {
    "recType": "recheme",
    "recName": "Recorder1",
    "url": "http://192.168.1.100:2356",
    "manage": true,
    "basic": true,
    "basicUser": "admin",
    "basicPass": "password"
  },
  {
    "recType": "blrec",
    "recName": "BLRecorder1",
    "url": "http://192.168.1.101:2233",
    "basicKey": "custom_key"
  }
]'
            />
          </n-space>
          <div class="action-btns">
            <n-button type="primary" @click="handleAddBatchServers" :loading="submitting">
              批量添加
            </n-button>
          </div>
        </n-tab-pane>
      </n-tabs>
    </n-modal>

    <room-detail
      :show="showDetail"
      @update:show="handleServerDetailVisibility"
      :room="selectedRoom"
      @room:deleted="handleRoomDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { RefreshOutline, AddOutline, InformationCircleOutline, EllipsisHorizontalOutline, TrashOutline } from '@vicons/ionicons5'
import { useRoomStore } from '@/lib/store/room'
import { NTag, NDropdown, NButton, NIcon } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import type { RecServer, RoomData } from '@/lib/types/api'
import { useMessage, useNotification, useDialog } from 'naive-ui'
import type { FormInst } from 'naive-ui'
import { useServerStore } from '@/lib/store/server'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/lib/store/auth'
import { addServer, deleteServers } from '@/lib/utils/api'
import RoomDetail from '@/components/RoomDetail.vue'

const roomStore = useRoomStore()
const serverStore = useServerStore()
const authStore = useAuthStore()
const message = useMessage()
const notification = useNotification()
const dialog = useDialog()
const serverFilter = ref('all')
const tableMaxHeight = ref(0)
const tableWidth = ref(0)
const showAddServerModal = ref(false)
const submitting = ref(false)
const singleFormRef = ref<FormInst | null>(null)
const showDetail = ref(false)
const selectedRoom = ref<RoomData | null>(null)
let updateTimer: number | null = null

const { loading: serverLoading } = storeToRefs(serverStore)
const { loading: roomLoading } = storeToRefs(roomStore)

const loading = computed(() => serverLoading.value || roomLoading.value)

const canAddServer = computed(() => {
  return authStore.isAuthenticated && !authStore.loading
})

// 添加排序相关的状态变量
const sortConfig = ref({
  key: '', // 默认无排序
  order: 'asc'    // 默认升序
})

// 添加一个函数来解析主机地址，提取域名/IP和端口
const parseHostPort = (url: string) => {
  // 移除 http:// 或 https://
  let hostPart = url.replace(/^https?:\/\//, '');
  
  // 分割域名/IP和端口
  const parts = hostPart.split(':');
  const host = parts[0];
  const port = parts.length > 1 ? parseInt(parts[1], 10) : NaN;
  
  return { host, port };
}

// 修改 filteredServerData 计算属性中的排序逻辑
const filteredServerData = computed(() => {
  const filteredData = serverStore.serverStats
    .filter((server: RecServer & { totalRooms?: number; streamingRooms?: number; recordingRooms?: number }) => 
      serverFilter.value === 'all' || server.recType === serverFilter.value
    )
  
  // 如果没有设置排序字段，则返回原始数据
  if (!sortConfig.value.key) {
    return filteredData;
  }
  
  // 根据排序配置进行排序
  return filteredData.sort((a: any, b: any) => {
    // 值可能不存在，做好空值处理
    const valueA = a[sortConfig.value.key] ?? '';
    const valueB = b[sortConfig.value.key] ?? '';
    
    // 对 recHost 进行特殊处理，分离主机名和端口号
    if (sortConfig.value.key === 'recHost') {
      const hostA = parseHostPort(valueA);
      const hostB = parseHostPort(valueB);
      
      // 先比较主机名
      const hostCompare = hostA.host.localeCompare(hostB.host);
      if (hostCompare !== 0) {
        return sortConfig.value.order === 'asc' ? hostCompare : -hostCompare;
      }
      
      // 如果主机名相同，按端口号数值比较
      if (!isNaN(hostA.port) && !isNaN(hostB.port)) {
        return sortConfig.value.order === 'asc' 
          ? hostA.port - hostB.port 
          : hostB.port - hostA.port;
      }
    }
    
    // 不同类型的值需要不同的比较方式
    if (typeof valueA === 'string' && typeof valueB === 'string') {
      // 字符串比较
      return sortConfig.value.order === 'asc' 
        ? valueA.localeCompare(valueB) 
        : valueB.localeCompare(valueA);
    } else {
      // 数值比较
      const numA = Number(valueA) || 0;
      const numB = Number(valueB) || 0;
      return sortConfig.value.order === 'asc' ? numA - numB : numB - numA;
    }
  })
})

onMounted(() => {
  tableMaxHeight.value = window.innerHeight - 64 - 48 - 56 - 16
  
  window.addEventListener('resize', () => {
    tableMaxHeight.value = window.innerHeight - 64 - 48 - 56 - 16
  })
  const calculateTableWidth = () => {
    const baseWidth = 48
    const urlColumnWidth = Math.max(...serverStore.serverStats.map((server: RecServer) => 
      getHostname(server.recHost).length * 10 + 100
    ))
    const numberColumnWidth = 100
    
    tableWidth.value = baseWidth + urlColumnWidth + numberColumnWidth * 3
  }

  watch(() => serverStore.serverStats, calculateTableWidth, { immediate: true })

  handleRefresh()

  const updateTimer = setInterval(() => {
    tableMaxHeight.value = tableMaxHeight.value;
  }, 1000);
})

onUnmounted(() => {
  if (updateTimer) clearInterval(updateTimer);
})

const getHostname = (url: string) => {
  try {
    const urlObj = new URL(url)
    return urlObj.port ? `${urlObj.hostname}:${urlObj.port}` : urlObj.hostname
  } catch (error) {
    console.warn('Invalid URL:', url)
    return url
  }
}

const getRowClassName = (row: RecServer & { recordingRooms?: number; streamingRooms?: number }): string => {
  if (!row) return ''
  
  // 将对象转换为字符串类名
  const classObj = {
    'is-recording': row.recordingRooms && row.recordingRooms > 0,
    'is-streaming': row.streamingRooms && row.streamingRooms > 0,
    'is-offline': row.recStatus === 'offline',
    'is-error': row.recStatus === 'error'
  }
  
  // 将活跃的类名合并为空格分隔的字符串
  return Object.entries(classObj)
    .filter(([_, value]) => value)
    .map(([key]) => key)
    .join(' ')
}

// 修改排序处理函数，改成三态切换
const handleSortChange = (key: string) => {
  if (sortConfig.value.key === key) {
    // 同一字段，切换排序顺序：升序 -> 降序 -> 无排序
    if (sortConfig.value.order === 'asc') {
      sortConfig.value.order = 'desc';
    } else if (sortConfig.value.order === 'desc') {
      // 清除排序
      sortConfig.value.key = '';
    } else {
      // 从无排序切换到升序
      sortConfig.value.order = 'asc';
    }
  } else {
    // 不同字段，设置为升序
    sortConfig.value.key = key;
    sortConfig.value.order = 'asc';
  }
}

// 修改辅助函数：获取排序图标
const getSortIcon = (key: string) => {
  if (sortConfig.value.key !== key) {
    return '○'; // 未排序
  }
  return sortConfig.value.order === 'asc' ? '▲' : '▼'; // 升序/降序
}

// 修改 columns 定义，添加排序功能
const columns: DataTableColumns<RecServer & { totalRooms?: number; streamingRooms?: number; recordingRooms?: number }> = [
  {
    title: () => h('div', { 
      class: 'sortable-header', 
      onClick: () => handleSortChange('recType') 
    }, [
      '类型',
      h('span', { 
        class: 'sort-icon',
        style: {
          color: sortConfig.value.key === 'recType' ? 'var(--n-primary-color)' : 'transparent',
          marginLeft: '4px',
          fontSize: '12px'
        }
      }, getSortIcon('recType'))
    ]),
    key: 'recType',
    width: 100,
    align: 'center',
    render(row) {
      return h(
        NTag,
        {
          type: row.recType === 'recheme' ? 'success' : 'warning',
          size: 'small'
        },
        { default: () => row.recType === 'recheme' ? '录播姬' : 'BLREC' }
      )
    }
  },
  {
    title: () => h('div', { 
      class: 'sortable-header', 
      onClick: () => handleSortChange('recName') 
    }, [
      '名称',
      h('span', { 
        class: 'sort-icon',
        style: {
          color: sortConfig.value.key === 'recName' ? 'var(--n-primary-color)' : 'transparent',
          marginLeft: '4px',
          fontSize: '12px'
        }
      }, getSortIcon('recName'))
    ]),
    key: 'recName',
    width: 180,
    align: 'center'
  },
  {
    title: () => h('div', { 
      class: 'sortable-header', 
      onClick: () => handleSortChange('recHost') 
    }, [
      '地址',
      h('span', { 
        class: 'sort-icon',
        style: {
          color: sortConfig.value.key === 'recHost' ? 'var(--n-primary-color)' : 'transparent',
          marginLeft: '4px',
          fontSize: '12px'
        }
      }, getSortIcon('recHost'))
    ]),
    key: 'recHost',
    width: 280,
    align: 'center',
    render(row) {
      return h('span', { class: 'url-text' }, getHostname(row.recHost))
    }
  },
  {
    title: () => h('div', { 
      class: 'sortable-header', 
      onClick: () => handleSortChange('recStatus') 
    }, [
      '状态',
      h('span', { 
        class: 'sort-icon',
        style: {
          color: sortConfig.value.key === 'recStatus' ? 'var(--n-primary-color)' : 'transparent',
          marginLeft: '4px',
          fontSize: '12px'
        }
      }, getSortIcon('recStatus'))
    ]),
    key: 'recStatus',
    width: 100,
    align: 'center',
    render(row) {
      const statusMap = {
        online: { type: 'success', text: '在线' },
        offline: { type: 'default', text: '离线' },
        error: { type: 'error', text: '错误' }
      }
      const status = statusMap[row.recStatus]
      return h(
        NTag,
        {
          type: status.type as 'success' | 'default' | 'error' | 'warning' | 'info' | 'primary',
          size: 'small'
        },
        { default: () => status.text }
      )
    }
  },
  {
    title: () => h('div', { 
      class: 'sortable-header', 
      onClick: () => handleSortChange('totalRooms') 
    }, [
      '监控中',
      h('span', { 
        class: 'sort-icon',
        style: {
          color: sortConfig.value.key === 'totalRooms' ? 'var(--n-primary-color)' : 'transparent',
          marginLeft: '4px',
          fontSize: '12px'
        }
      }, getSortIcon('totalRooms'))
    ]),
    key: 'totalRooms',
    align: 'center',
    minWidth: 80
  },
  {
    title: () => h('div', { 
      class: 'sortable-header', 
      onClick: () => handleSortChange('streamingRooms') 
    }, [
      '直播中',
      h('span', { 
        class: 'sort-icon',
        style: {
          color: sortConfig.value.key === 'streamingRooms' ? 'var(--n-primary-color)' : 'transparent',
          marginLeft: '4px',
          fontSize: '12px'
        }
      }, getSortIcon('streamingRooms'))
    ]),
    key: 'streamingRooms',
    align: 'center',
    minWidth: 80,
    render(row) {
      return h('span', {
        class: { 'highlight': row.streamingRooms && row.streamingRooms > 0 }
      }, row.streamingRooms || 0)
    }
  },
  {
    title: () => h('div', { 
      class: 'sortable-header', 
      onClick: () => handleSortChange('recordingRooms') 
    }, [
      '录制中',
      h('span', { 
        class: 'sort-icon',
        style: {
          color: sortConfig.value.key === 'recordingRooms' ? 'var(--n-primary-color)' : 'transparent',
          marginLeft: '4px',
          fontSize: '12px'
        }
      }, getSortIcon('recordingRooms'))
    ]),
    key: 'recordingRooms',
    align: 'center',
    minWidth: 80,
    render(row) {
      return h('span', {
        class: { 'highlight': row.recordingRooms && row.recordingRooms > 0 }
      }, row.recordingRooms || 0)
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    align: 'center',
    fixed: 'right',
    render(row) {
      return h(
        NDropdown,
        {
          trigger: 'click',
          options: [
            {
              label: '删除录播机',
              key: 'delete',
              icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
              props: {
                class: 'dropdown-danger-item'
              }
            }
          ],
          onSelect: (key: string) => handleActionSelect(key, row)
        },
        {
          default: () => h(
            NButton,
            {
              quaternary: true,
              circle: true,
              size: 'small'
            },
            { default: () => h(NIcon, null, { default: () => h(EllipsisHorizontalOutline) }) }
          )
        }
      )
    }
  }
]

// 单个添加表单模型
const singleFormModel = ref({
  recType: 'recheme',
  recName: '',
  url: '',
  manage: true,
  authType: 'global',
  basicUser: '',
  basicPass: '',
  basicKey: ''
})

// 批量添加表单模型
const batchFormModel = ref({
  servers: ''
})

const serverRules = {
  recName: {
    required: true,
    message: '请输入录播机名称',
    trigger: 'blur'
  },
  url: [
    {
      required: true,
      message: '请输入录播机地址',
      trigger: 'blur'
    },
    {
      pattern: /^https?:\/\/.+/,
      message: 'URL必须以http://或https://开头',
      trigger: 'blur'
    }
  ],
  basicUser: {
    required: true,
    message: '请输入认证用户名',
    trigger: 'blur',
    validator: (_rule: any, value: string) => {
      if (singleFormModel.value.authType === 'enable' && 
          singleFormModel.value.recType === 'recheme' && 
          !value) {
        return new Error('请输入认证用户名')
      }
      return true
    }
  },
  basicPass: {
    required: true,
    message: '请输入认证密码',
    trigger: 'blur',
    validator: (_rule: any, value: string) => {
      if (singleFormModel.value.authType === 'enable' && 
          singleFormModel.value.recType === 'recheme' && 
          !value) {
        return new Error('请输入认证密码')
      }
      return true
    }
  },
  basicKey: {
    required: true,
    message: '请输入认证密钥',
    trigger: 'blur',
    validator: (_rule: any, value: string) => {
      if (singleFormModel.value.authType === 'enable' && 
          singleFormModel.value.recType === 'blrec' && 
          !value) {
        return new Error('请输入认证密钥')
      }
      return true
    }
  }
}

// 示例数据
function fillBatchExampleData() {
  batchFormModel.value.servers = JSON.stringify([
    {
      recType: "recheme",
      recName: "录播机名字11",
      url: "http://192.168.1.100:2356",
      manage: true,
      basic: false
    },
    {
      recType: "recheme",
      recName: "录播机名字4",
      url: "http://192.168.1.101:2356",
      manage: true,
      basic: true,
      basicUser: "admin",
      basicPass: "password123"
    },
    {
      recType: "blrec",
      recName: "录播机名字51",
      url: "http://192.168.1.200:2233",
      basic: false
    },
    {
      recType: "blrec",
      recName: "录播机名字4",
      url: "http://192.168.1.201:2233",
      basic: true,
      basicKey: "custom_secret_key"
    }
  ], null, 2)
}

// 添加录播机
async function handleAddSingleServer() {
  try {
    await singleFormRef.value?.validate()
    submitting.value = true
    
    const serverData = {
      recType: singleFormModel.value.recType,
      recName: singleFormModel.value.recName,
      url: singleFormModel.value.url,
      manage: singleFormModel.value.manage,
      ...(singleFormModel.value.authType === 'basic' && {
        basic: true,
        basicUser: singleFormModel.value.basicUser,
        basicPass: singleFormModel.value.basicPass
      }),
      ...(singleFormModel.value.authType === 'key' && {
        basicKey: singleFormModel.value.basicKey
      })
    }
    
    const result = await addServer(serverData)
    message.success(`成功添加录播机: ${result.data.recName}`)
    showAddServerModal.value = false
    resetForms()
    handleRefresh()
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    submitting.value = false
  }
}

// 批量添加录播机
async function handleAddBatchServers() {
  try {
    submitting.value = true
    
    let servers
    try {
      servers = JSON.parse(batchFormModel.value.servers)
    } catch (error) {
      throw new Error('JSON格式错误，请检查输入')
    }
    
    if (!Array.isArray(servers)) {
      throw new Error('请提供录播机数组，格式为 [...]')
    }
    
    servers.forEach((server, index) => {
      if (!server.recType) {
        throw new Error(`第${index + 1}个录播机缺少recType字段`)
      }
      if (!['recheme', 'blrec'].includes(server.recType)) {
        throw new Error(`第${index + 1}个录播机的recType必须是recheme或blrec`)
      }
      if (!server.recName) {
        throw new Error(`第${index + 1}个录播机缺少recName字段`)
      }
      if (!server.url) {
        throw new Error(`第${index + 1}个录播机缺少url字段`)
      }
      if (!/^https?:\/\//.test(server.url)) {
        throw new Error(`第${index + 1}个录播机的url必须以http://或https://开头`)
      }
    })
    
    const response = await fetch('/api/server', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ servers })
    })
    
    const result = await response.json()
    
    if (!response.ok) {
      throw new Error(result.detail || '批量添加录播机失败')
    }
    
    message.success(`批量添加成功：共${result.total}个，成功${result.succeeded}个，失败${result.failed}个`)
    
    if (result.errors && result.errors.length > 0) {
      const errorDetails = result.errors.map((err: any) => 
        `${err.recName}(${err.recType}): ${err.error}`
      ).join('\n');
      
      notification.warning({
        title: '部分录播机添加失败',
        content: errorDetails,
        duration: 10000,
        keepAliveOnHover: true
      });
    }
    
    showAddServerModal.value = false
    resetForms()
    roomStore.fetchRooms()
    
  } catch (error) {
    message.error((error as Error).message)
  } finally {
    submitting.value = false
  }
}

// 重置表单
function resetForms() {
  singleFormModel.value = {
    recType: 'recheme',
    recName: '',
    url: '',
    manage: true,
    authType: 'global',
    basicUser: '',
    basicPass: '',
    basicKey: ''
  }
  batchFormModel.value.servers = ''
}

async function handleRefresh() {
  await Promise.all([
    serverStore.fetchServers(),
    roomStore.fetchRooms()
  ])
}

const lastUpdatedText = computed(() => serverStore.lastUpdatedText)

const handleCloseServerDetail = () => {
  nextTick(() => {
    showDetail.value = false
    setTimeout(() => {
      selectedRoom.value = null
    }, 300)
  })
}

const handleServerDetailVisibility = (visible: boolean) => {
  if (!visible) {
    handleCloseServerDetail()
  } else {
    showDetail.value = true
  }
}

// 房间删除
const handleRoomDeleted = () => {
  console.log('房间已删除')
}

const handleActionSelect = (key: string, row: RecServer) => {
  if (key === 'delete') {
    confirmDeleteServer(row)
  }
}

const confirmDeleteServer = (server: RecServer) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除录播机 "${server.recName}" 吗？此操作不可撤销，且会导致该录播机下的所有房间记录被删除。`,
    positiveText: '确定删除',
    negativeText: '取消',
    onPositiveClick: () => deleteServerHandler(server)
  })
}

const deleteServerHandler = async (server: RecServer) => {
  try {
    message.loading('正在删除录播机...')
    await deleteServers([{
      recName: server.recName,
      recType: server.recType
    }])
    message.success(`录播机 "${server.recName}" 已成功删除`)
    handleRefresh()
  } catch (error) {
    message.error(`删除失败: ${(error as Error).message}`)
  }
}

// TODO
// @ts-ignore
const showRoomDetail = (room: RoomData) => {
  selectedRoom.value = room
  nextTick(() => {
    showDetail.value = true
  })
}
</script>

<style scoped lang="scss">
.servers {
  height: 100%;
  
  .server-scrollbar {
    .server-container {
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
        }
      }
      
      .server-table {
        width: fit-content;
        min-width: 100%;
        
        :deep(.n-data-table-td) {
          padding: 12px;
        }

        .recording-row {
          background-color: rgba(var(--n-success-color-rgb), 0.1);
        }

        .streaming-row {
          background-color: rgba(var(--n-error-color-rgb), 0.1);
        }

        .highlight {
          color: var(--n-primary-color);
          font-weight: bold;
        }
      }
    }
  }
}

html.dark {
  .servers {
    .server-table {
      border-color: var(--border-color);
    }
  }
}

.action-btns {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.server-url {
  display: flex;
  flex-direction: column;
  gap: 4px;
  
  .server-name {
    font-weight: bold;
    color: var(--n-primary-color);
  }
  
  .url-text {
    color: var(--text-color-secondary);
    font-family: monospace;
  }
}

.n-data-table .n-data-table-tr {
  &.is-offline {
    opacity: 0.6;
  }
  
  &.is-error {
    background-color: rgba(var(--error-color), 0.1);
  }
  
  &.is-recording {
    background-color: rgba(var(--success-color), 0.1);
  }
  
  &.is-streaming {
    background-color: rgba(var(--warning-color), 0.1);
  }
}

.sortable-header {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  
  &:hover {
    color: var(--n-primary-color);
  }
}
</style> 