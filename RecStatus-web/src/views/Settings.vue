<template>
  <div v-if="!canViewSettings" class="settings-login-state">
    <n-result status="403" title="请登录" />
  </div>

  <div v-else class="settings-page">
    <n-page-header title="系统设置">
      <template #subtitle>
        <n-text depth="3">全局配置保存到后端 data/config.json</n-text>
      </template>
      <template #extra>
        <n-space>
          <n-button :loading="loading" @click="loadConfig">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            刷新
          </n-button>
          <n-button type="primary" :loading="saving" @click="saveConfig">
            <template #icon>
              <n-icon><CreateOutline /></n-icon>
            </template>
            保存
          </n-button>
        </n-space>
      </template>
    </n-page-header>

    <n-alert v-if="restartRequired" type="warning" class="restart-alert" closable>
      监听地址或端口已保存，重启服务后生效
    </n-alert>

    <n-spin :show="loading">
      <n-form label-placement="left" label-width="140" require-mark-placement="right-hanging">
        <n-card title="基础监听" class="setting-section">
          <n-grid responsive="screen" cols="1 m:2" :x-gap="24" :y-gap="4">
            <n-gi>
            <n-form-item label="监听地址">
              <n-input v-model:value="form.HOST" placeholder="0.0.0.0" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="监听端口">
              <n-input-number v-model:value="form.PORT" :min="1" :max="65535" />
            </n-form-item>
            </n-gi>
          </n-grid>
        </n-card>

        <n-card title="认证" class="setting-section">
          <n-grid responsive="screen" cols="1 m:2" :x-gap="24" :y-gap="4">
            <n-gi>
            <n-form-item label="启用认证">
              <n-switch v-model:value="form.AUTH.ENABLE" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="Token 过期分钟">
              <n-input-number v-model:value="form.AUTH.AUTH_KEY_EXPIRE" :min="1" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="认证密钥">
              <n-space class="field-actions" align="center" :wrap="false">
                <n-input
                  v-model:value="form.AUTH.AUTH_KEY"
                  type="password"
                  show-password-on="click"
                  placeholder="留空则保留"
                />
                <n-button secondary @click="form.AUTH.clearAuthKey = true">清空</n-button>
                <n-tag v-if="form.AUTH.clearAuthKey" type="warning" closable @close="form.AUTH.clearAuthKey = false">
                  将清空
                </n-tag>
              </n-space>
            </n-form-item>
            </n-gi>
          </n-grid>

          <n-space class="section-toolbar" align="center" justify="space-between">
            <n-text strong>用户</n-text>
            <n-button size="small" type="primary" @click="addUser">
              <template #icon>
                <n-icon><AddOutline /></n-icon>
              </template>
              添加用户
            </n-button>
          </n-space>

          <n-list bordered>
            <n-list-item v-for="(user, index) in form.AUTH.users" :key="user.id">
              <n-grid responsive="screen" cols="1 s:2 l:6" :x-gap="8" :y-gap="8" item-responsive>
                <n-gi>
                  <n-input v-model:value="user.key" placeholder="配置名" />
                </n-gi>
                <n-gi>
                  <n-input v-model:value="user.USER" placeholder="登录用户名" />
                </n-gi>
                <n-gi span="1 s:2 l:2">
                  <n-input
                    v-model:value="user.PASS"
                    type="password"
                    show-password-on="click"
                    placeholder="留空则保留密码"
                  />
                </n-gi>
                <n-gi>
                  <n-space align="center" :wrap="false">
                    <n-button secondary @click="user.clearPass = true">清空密码</n-button>
                    <n-button circle secondary type="error" @click="removeUser(index)">
                      <template #icon>
                        <n-icon><TrashOutline /></n-icon>
                      </template>
                    </n-button>
                  </n-space>
                </n-gi>
                <n-gi>
                  <n-tag v-if="user.clearPass" type="warning" closable @close="user.clearPass = false">
                    将清空密码
                  </n-tag>
                </n-gi>
              </n-grid>
            </n-list-item>
          </n-list>
        </n-card>

        <n-card title="全局 Cookie" class="setting-section">
          <n-grid responsive="screen" cols="1 m:2" :x-gap="24" :y-gap="4">
            <n-gi>
            <n-form-item label="启用 Cookie">
              <n-switch v-model:value="form.COOKIE.ENABLE" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="配置块名称">
              <n-input v-model:value="form.COOKIE.name" placeholder="C1" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="服务器地址/值">
              <n-input v-model:value="form.COOKIE.VALUE" placeholder="http://127.0.0.1:18000" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="Token">
              <n-space class="field-actions" align="center" :wrap="false">
                <n-input
                  v-model:value="form.COOKIE.TOKEN"
                  type="password"
                  show-password-on="click"
                  placeholder="留空则保留"
                />
                <n-button secondary @click="form.COOKIE.clearToken = true">清空</n-button>
                <n-tag v-if="form.COOKIE.clearToken" type="warning" closable @close="form.COOKIE.clearToken = false">
                  将清空
                </n-tag>
              </n-space>
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="模式">
              <n-select v-model:value="form.COOKIE.MODE" :options="cookieModeOptions" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="检查间隔秒">
              <n-input-number v-model:value="form.COOKIE.CHECK_INTERVAL" :min="1" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="随机更换间隔秒">
              <n-input-number v-model:value="form.COOKIE.RANDOM_CHANGE_INTERVAL" :min="1" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="请求超时秒">
              <n-input-number v-model:value="form.COOKIE.REQUEST_TIMEOUT" :min="1" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="最大重试次数">
              <n-input-number v-model:value="form.COOKIE.MAX_RETRIES" :min="0" />
            </n-form-item>
            </n-gi>
          </n-grid>
        </n-card>

        <n-card title="录播姬全局设置" class="setting-section">
          <n-grid responsive="screen" cols="1 m:2" :x-gap="24" :y-gap="4">
            <n-gi>
            <n-form-item label="隐藏 URL">
              <n-switch v-model:value="form.RECHEME.URL_HIDDEN" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="启用 Basic">
              <n-switch v-model:value="form.RECHEME.BASIC" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="Basic 用户">
              <n-input v-model:value="form.RECHEME.BASIC_USER" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="Basic 密码">
              <n-space class="field-actions" align="center" :wrap="false">
                <n-input
                  v-model:value="form.RECHEME.BASIC_PASS"
                  type="password"
                  show-password-on="click"
                  placeholder="留空则保留"
                />
                <n-button secondary @click="form.RECHEME.clearBasicPass = true">清空</n-button>
                <n-tag
                  v-if="form.RECHEME.clearBasicPass"
                  type="warning"
                  closable
                  @close="form.RECHEME.clearBasicPass = false"
                >
                  将清空
                </n-tag>
              </n-space>
            </n-form-item>
            </n-gi>
          </n-grid>

          <n-divider />

          <n-grid responsive="screen" cols="1 m:2" :x-gap="24" :y-gap="4">
            <n-gi>
            <n-form-item label="启用 Cookie">
              <n-switch v-model:value="form.RECHEME_COOKIE.ENABLE" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="配置块名称">
              <n-input v-model:value="form.RECHEME_COOKIE.name" placeholder="C1" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="服务器地址/值">
              <n-input v-model:value="form.RECHEME_COOKIE.VALUE" placeholder="http://127.0.0.1:18000" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="Token">
              <n-space class="field-actions" align="center" :wrap="false">
                <n-input
                  v-model:value="form.RECHEME_COOKIE.TOKEN"
                  type="password"
                  show-password-on="click"
                  placeholder="留空则保留"
                />
                <n-button secondary @click="form.RECHEME_COOKIE.clearToken = true">清空</n-button>
                <n-tag
                  v-if="form.RECHEME_COOKIE.clearToken"
                  type="warning"
                  closable
                  @close="form.RECHEME_COOKIE.clearToken = false"
                >
                  将清空
                </n-tag>
              </n-space>
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="模式">
              <n-select v-model:value="form.RECHEME_COOKIE.MODE" :options="cookieModeOptions" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="检查间隔秒">
              <n-input-number v-model:value="form.RECHEME_COOKIE.CHECK_INTERVAL" :min="1" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="随机更换间隔秒">
              <n-input-number v-model:value="form.RECHEME_COOKIE.RANDOM_CHANGE_INTERVAL" :min="1" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="请求超时秒">
              <n-input-number v-model:value="form.RECHEME_COOKIE.REQUEST_TIMEOUT" :min="1" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="最大重试次数">
              <n-input-number v-model:value="form.RECHEME_COOKIE.MAX_RETRIES" :min="0" />
            </n-form-item>
            </n-gi>
          </n-grid>
        </n-card>

        <n-card title="BLREC 全局设置" class="setting-section">
          <n-grid responsive="screen" cols="1 m:2" :x-gap="24" :y-gap="4">
            <n-gi>
            <n-form-item label="隐藏 URL">
              <n-switch v-model:value="form.BLREC.URL_HIDDEN" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="启用 Basic">
              <n-switch v-model:value="form.BLREC.BASIC" />
            </n-form-item>
            </n-gi>
            <n-gi>
            <n-form-item label="API 密钥">
              <n-space class="field-actions" align="center" :wrap="false">
                <n-input
                  v-model:value="form.BLREC.BASIC_KEY"
                  type="password"
                  show-password-on="click"
                  placeholder="留空则保留"
                />
                <n-button secondary @click="form.BLREC.clearBasicKey = true">清空</n-button>
                <n-tag
                  v-if="form.BLREC.clearBasicKey"
                  type="warning"
                  closable
                  @close="form.BLREC.clearBasicKey = false"
                >
                  将清空
                </n-tag>
              </n-space>
            </n-form-item>
            </n-gi>
          </n-grid>
        </n-card>
      </n-form>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import {
  NAlert,
  NButton,
  NCard,
  NDivider,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NInputNumber,
  NGi,
  NGrid,
  NList,
  NListItem,
  NPageHeader,
  NResult,
  NSelect,
  NSpace,
  NSpin,
  NSwitch,
  NTag,
  NText,
  useMessage
} from 'naive-ui'
import { AddOutline, CreateOutline, RefreshOutline, TrashOutline } from '@vicons/ionicons5'
import { computed, reactive, ref, watch } from 'vue'
import { fetchSystemConfig, updateSystemConfig } from '@/lib/utils/api'
import type { CookieBlockConfig, CookieConfig, SystemConfig } from '@/lib/types/api'
import { useAuthStore } from '@/lib/store/auth'

interface UserForm {
  id: number
  key: string
  USER: string
  PASS: string
  clearPass: boolean
}

interface CookieForm {
  ENABLE: boolean
  name: string
  VALUE: string
  TOKEN: string
  clearToken: boolean
  MODE: string
  CHECK_INTERVAL: number
  RANDOM_CHANGE_INTERVAL: number
  REQUEST_TIMEOUT: number
  MAX_RETRIES: number
}

interface SettingsForm {
  HOST: string
  PORT: number
  AUTH: {
    ENABLE: boolean
    AUTH_KEY: string
    clearAuthKey: boolean
    AUTH_KEY_EXPIRE: number
    users: UserForm[]
  }
  COOKIE: CookieForm
  RECHEME: {
    URL_HIDDEN: boolean
    BASIC: boolean
    BASIC_USER: string
    BASIC_PASS: string
    clearBasicPass: boolean
  }
  RECHEME_COOKIE: CookieForm
  BLREC: {
    URL_HIDDEN: boolean
    BASIC: boolean
    BASIC_KEY: string
    clearBasicKey: boolean
  }
}

const message = useMessage()
const authStore = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const restartRequired = ref(false)
const canViewSettings = computed(() => authStore.checked && authStore.isAuthenticated)
let userId = 0

const cookieModeOptions = [
  { label: 'random', value: 'random' },
  { label: 'onlysync', value: 'onlysync' }
]

const form = reactive<SettingsForm>({
  HOST: '0.0.0.0',
  PORT: 11111,
  AUTH: {
    ENABLE: true,
    AUTH_KEY: '',
    clearAuthKey: false,
    AUTH_KEY_EXPIRE: 1919810,
    users: []
  },
  COOKIE: createCookieForm(),
  RECHEME: {
    URL_HIDDEN: false,
    BASIC: false,
    BASIC_USER: '',
    BASIC_PASS: '',
    clearBasicPass: false
  },
  RECHEME_COOKIE: createCookieForm(),
  BLREC: {
    URL_HIDDEN: false,
    BASIC: true,
    BASIC_KEY: '',
    clearBasicKey: false
  }
})

function createCookieForm(): CookieForm {
  return {
    ENABLE: false,
    name: 'C1',
    VALUE: '',
    TOKEN: '',
    clearToken: false,
    MODE: 'random',
    CHECK_INTERVAL: 3600,
    RANDOM_CHANGE_INTERVAL: 86400,
    REQUEST_TIMEOUT: 10,
    MAX_RETRIES: 3
  }
}

function nextUserId() {
  userId += 1
  return userId
}

function getCookieBlock(config?: CookieConfig): { name: string; block: CookieBlockConfig } {
  if (!config) {
    return { name: 'C1', block: {} }
  }
  const name = Object.keys(config).find(key => {
    const value = config[key]
    return key !== 'ENABLE' && value && typeof value === 'object'
  }) || 'C1'
  const block = config[name]
  return {
    name,
    block: block && typeof block === 'object' ? block as CookieBlockConfig : {}
  }
}

function assignCookieForm(target: CookieForm, config?: CookieConfig) {
  const { name, block } = getCookieBlock(config)
  target.ENABLE = Boolean(config?.ENABLE)
  target.name = name
  target.VALUE = block.VALUE || ''
  target.TOKEN = ''
  target.clearToken = false
  target.MODE = block.MODE || 'random'
  target.CHECK_INTERVAL = Number(block.CHECK_INTERVAL || 3600)
  target.RANDOM_CHANGE_INTERVAL = Number(block.RANDOM_CHANGE_INTERVAL || 86400)
  target.REQUEST_TIMEOUT = Number(block.REQUEST_TIMEOUT || 10)
  target.MAX_RETRIES = Number(block.MAX_RETRIES ?? 3)
}

function applyConfig(config: SystemConfig) {
  form.HOST = config.HOST || '0.0.0.0'
  form.PORT = Number(config.PORT || 11111)

  form.AUTH.ENABLE = Boolean(config.AUTH?.ENABLE)
  form.AUTH.AUTH_KEY = ''
  form.AUTH.clearAuthKey = false
  form.AUTH.AUTH_KEY_EXPIRE = Number(config.AUTH?.AUTH_KEY_EXPIRE || 1919810)
  form.AUTH.users = Object.entries(config.AUTH?.AUTH_USER || {}).map(([key, user]) => ({
    id: nextUserId(),
    key,
    USER: user.USER || key,
    PASS: '',
    clearPass: false
  }))

  assignCookieForm(form.COOKIE, config.COOKIE)

  form.RECHEME.URL_HIDDEN = Boolean(config.RECHEME?.URL_HIDDEN)
  form.RECHEME.BASIC = Boolean(config.RECHEME?.BASIC)
  form.RECHEME.BASIC_USER = config.RECHEME?.BASIC_USER || ''
  form.RECHEME.BASIC_PASS = ''
  form.RECHEME.clearBasicPass = false
  assignCookieForm(form.RECHEME_COOKIE, config.RECHEME?.COOKIE)

  form.BLREC.URL_HIDDEN = Boolean(config.BLREC?.URL_HIDDEN)
  form.BLREC.BASIC = config.BLREC?.BASIC !== undefined ? Boolean(config.BLREC.BASIC) : true
  form.BLREC.BASIC_KEY = ''
  form.BLREC.clearBasicKey = false
}

function addUser() {
  form.AUTH.users.push({
    id: nextUserId(),
    key: '',
    USER: '',
    PASS: '',
    clearPass: false
  })
}

function removeUser(index: number) {
  form.AUTH.users.splice(index, 1)
}

function buildCookiePayload(cookie: CookieForm): CookieConfig {
  const name = cookie.name.trim() || 'C1'
  const block: CookieBlockConfig = {
    VALUE: cookie.VALUE,
    MODE: cookie.MODE,
    CHECK_INTERVAL: Number(cookie.CHECK_INTERVAL),
    RANDOM_CHANGE_INTERVAL: Number(cookie.RANDOM_CHANGE_INTERVAL),
    REQUEST_TIMEOUT: Number(cookie.REQUEST_TIMEOUT),
    MAX_RETRIES: Number(cookie.MAX_RETRIES)
  }
  if (cookie.TOKEN || cookie.clearToken) {
    block.TOKEN = cookie.clearToken ? '' : cookie.TOKEN
  }
  return {
    ENABLE: cookie.ENABLE,
    [name]: block
  }
}

function buildPayload(): Partial<SystemConfig> {
  const authUsers: Record<string, { USER: string; PASS?: string }> = {}
  for (const user of form.AUTH.users) {
    const key = user.key.trim()
    if (!key) continue
    const nextUser: { USER: string; PASS?: string } = {
      USER: user.USER.trim() || key
    }
    if (user.PASS || user.clearPass) {
      nextUser.PASS = user.clearPass ? '' : user.PASS
    }
    authUsers[key] = nextUser
  }

  const payload: Partial<SystemConfig> = {
    HOST: form.HOST.trim(),
    PORT: Number(form.PORT),
    AUTH: {
      ENABLE: form.AUTH.ENABLE,
      AUTH_KEY_EXPIRE: Number(form.AUTH.AUTH_KEY_EXPIRE),
      AUTH_USER: authUsers
    },
    COOKIE: buildCookiePayload(form.COOKIE),
    RECHEME: {
      URL_HIDDEN: form.RECHEME.URL_HIDDEN,
      BASIC: form.RECHEME.BASIC,
      BASIC_USER: form.RECHEME.BASIC_USER,
      COOKIE: buildCookiePayload(form.RECHEME_COOKIE)
    },
    BLREC: {
      URL_HIDDEN: form.BLREC.URL_HIDDEN,
      BASIC: form.BLREC.BASIC
    }
  }

  if (form.AUTH.AUTH_KEY || form.AUTH.clearAuthKey) {
    payload.AUTH!.AUTH_KEY = form.AUTH.clearAuthKey ? '' : form.AUTH.AUTH_KEY
  }
  if (form.RECHEME.BASIC_PASS || form.RECHEME.clearBasicPass) {
    payload.RECHEME!.BASIC_PASS = form.RECHEME.clearBasicPass ? '' : form.RECHEME.BASIC_PASS
  }
  if (form.BLREC.BASIC_KEY || form.BLREC.clearBasicKey) {
    payload.BLREC!.BASIC_KEY = form.BLREC.clearBasicKey ? '' : form.BLREC.BASIC_KEY
  }

  return payload
}

async function loadConfig() {
  if (!canViewSettings.value) return

  loading.value = true
  try {
    const response = await fetchSystemConfig()
    applyConfig(response.config)
  } catch (error) {
    message.error(error instanceof Error ? error.message : '获取系统配置失败')
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  if (!form.HOST.trim()) {
    message.error('监听地址不能为空')
    return
  }
  if (!form.PORT || form.PORT < 1 || form.PORT > 65535) {
    message.error('监听端口必须在 1 到 65535 之间')
    return
  }

  saving.value = true
  try {
    const response = await updateSystemConfig(buildPayload())
    restartRequired.value = Boolean(response.restartRequired)
    applyConfig(response.config)
    if (response.restartRequired) {
      message.warning('配置已保存，监听地址或端口需要重启后生效')
    } else {
      message.success('配置已保存')
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存系统配置失败')
  } finally {
    saving.value = false
  }
}

watch(canViewSettings, async canView => {
  if (canView) {
    await loadConfig()
    return
  }

  restartRequired.value = false
}, { immediate: true })
</script>

<style scoped lang="scss">
.settings-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px;
}

.settings-login-state {
  min-height: calc(100vh - 104px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.restart-alert {
  margin: 16px 0;
}

.setting-section {
  margin-top: 16px;
}

.field-actions {
  width: 100%;
}

.field-actions :deep(.n-input) {
  flex: 1;
  min-width: 0;
}

.section-toolbar {
  margin: 8px 0 12px;
}

@media (max-width: 900px) {
  .settings-page {
    padding: 16px;
  }
}
</style>
