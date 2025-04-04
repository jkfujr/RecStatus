<template>
  <div class="nav-header">
    <div class="logo-container">
      <img src="/favicon.svg" alt="Logo" class="header-logo" />
      <span class="logo-text">REC Status</span>
    </div>
    <div class="right-actions">
      
      <n-button 
        quaternary 
        circle 
        @click="toggleTheme" 
        @contextmenu="handleContextMenu"
        @touchstart="handleTouchStart"
        @touchend="handleTouchEnd"
      >
        <template #icon>
          <n-icon size="20">
            <component :is="isLightTheme ? Moon : Sunny" />
          </n-icon>
        </template>
      </n-button>
    </div>
    
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
    
    <n-modal v-model:show="showLoginModal" preset="dialog" title="登录">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px;">
          <n-icon><LockClosedOutline /></n-icon>
          <span>登录</span>
        </div>
      </template>
      
      <n-form
        ref="loginForm"
        :model="loginModel"
        :rules="loginRules"
        label-placement="left"
        label-width="80"
        style="max-width: 300px; margin: 0 auto;"
      >
        <n-form-item label="用户名" path="username">
          <n-input v-model:value="loginModel.username" placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input 
            v-model:value="loginModel.password" 
            type="password" 
            placeholder="请输入密码"
            show-password-on="click"
            @keyup.enter="handleLogin"
          />
        </n-form-item>
      </n-form>
      
      <template #action>
        <n-space justify="end">
          <n-button @click="showLoginModal = false">取消</n-button>
          <n-button type="primary" :loading="loginLoading" @click="handleLogin">登录</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { Moon, Sunny } from '@vicons/ionicons5'
import { useThemeStore } from '@/lib/store/theme'
import { useAuthStore } from '@/lib/store/auth'
import { LockClosedOutline, LogOutOutline, LogInOutline } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'
import type { FormInst } from 'naive-ui'

const themeStore = useThemeStore()
const authStore = useAuthStore()
const message = useMessage()

const isLightTheme = computed(() => !themeStore.isDark)
const toggleTheme = () => themeStore.toggleTheme()

const showDropdown = ref(false)
const dropdownX = ref(0)
const dropdownY = ref(0)
const clickCount = ref(0)
const clickTimer = ref<number | null>(null)
const touchStartTime = ref(0)

const showLoginModal = ref(false)
const loginLoading = ref(false)
const loginForm = ref<FormInst | null>(null)
const loginModel = ref({
  username: '',
  password: ''
})
const loginRules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' }
}

const dropdownOptions = computed(() => {
  const options = []
  
  if (authStore.isAuthenticated && authStore.authRequired) {
    options.push({
      label: '退出登录',
      key: 'logout',
      icon: () => h(LogOutOutline, { 
        style: { 
          color: 'var(--n-error-color)',
          width: '20px',
          height: '20px'
        } 
      })
    })
  } else {
    options.push({
      label: '登录',
      key: 'login',
      icon: () => h(LogInOutline, { 
        style: { 
          color: 'var(--n-error-color)',
          width: '20px',
          height: '20px'
        } 
      })
    })
  }
  
  return options
})

function handleContextMenu(e: MouseEvent) {
  e.preventDefault()
  
  clickCount.value++
  
  if (clickTimer.value) {
    clearTimeout(clickTimer.value)
  }
  
  clickTimer.value = window.setTimeout(() => {
    clickCount.value = 0
  }, 500)
  
  if (clickCount.value >= 2) {
    showDropdown.value = false
    nextTick().then(() => {
      dropdownX.value = e.clientX
      dropdownY.value = e.clientY
      showDropdown.value = true
      clickCount.value = 0
    })
  }
}

function handleTouchStart() {
  touchStartTime.value = Date.now()
}

function handleTouchEnd(e: TouchEvent) {
  const touchDuration = Date.now() - touchStartTime.value
  
  if (touchDuration >= 3000) {
    e.preventDefault()
    showDropdown.value = false
    nextTick().then(() => {
      const touch = e.changedTouches[0]
      dropdownX.value = touch.clientX
      dropdownY.value = touch.clientY
      showDropdown.value = true
    })
  }
}

async function handleDropdownSelect(key: string) {
  showDropdown.value = false
  
  if (key === 'login') {
    showLoginModal.value = true
  } else if (key === 'logout') {
    authStore.logout()
    message.success('已退出登录')
  }
}

async function handleLogin() {
  try {
    await loginForm.value?.validate()
    loginLoading.value = true
    
    const success = await authStore.login(loginModel.value.username, loginModel.value.password)
    
    if (success) {
      message.success('登录成功')
      showLoginModal.value = false
      loginModel.value.password = ''
      
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    }
  } catch (e) {
  } finally {
    loginLoading.value = false
  }
}
</script>

<style scoped>
.nav-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  height: 100%;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-logo {
  width: 30px;
  height: 30px;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  color: var(--text-color);
}

.right-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

html.dark .logo-text {
  color: var(--text-color);
}
</style> 