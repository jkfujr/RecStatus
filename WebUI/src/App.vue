<template>
  <n-config-provider :theme="themeStore.currentTheme">
    <n-loading-bar-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-message-provider>
            <global-provider>
              <router-view />
            </global-provider>
          </n-message-provider>
        </n-notification-provider>
      </n-dialog-provider>
    </n-loading-bar-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { useThemeStore } from '@/lib/store/theme'
import { useRoomStore } from '@/lib/store/room'
import GlobalProvider from '@/components/GlobalProvider.vue'
import { useAuthStore } from '@/lib/store/auth'

const themeStore = useThemeStore()
const roomStore = useRoomStore()
const authStore = useAuthStore()

onMounted(() => {
  themeStore.init()
  roomStore.init()
})

onMounted(async () => {
  await authStore.checkAuthStatus()
})

onUnmounted(() => {
  roomStore.stopAutoRefresh()
})
</script>

<style>
:root {
  --bg-color: #f0f2f5;
  --text-color: #333;
  --text-color-secondary: #666;
  --border-color: #dcdfe6;
  --hover-color: #f5f5f5;
  --hover-color-dark: #363636;
  --n-color-error-rgb: 243, 77, 77;
  --n-success-color-rgb: 63, 180, 111;
  --n-info-color-rgb: 144, 147, 153;
  --n-warning-color-rgb: 230, 162, 60;
}

html.dark {
  --bg-color: #18181c;
  --text-color: #CFD3DC;
  --text-color-secondary: #999;
  --border-color: #363637;
  --hover-color: #242424;
  --hover-color-dark: #363636;
  --n-color-error-rgb: 231, 91, 91;
  --n-success-color-rgb: 74, 201, 155;
  --n-info-color-rgb: 144, 147, 153;
  --n-warning-color-rgb: 230, 171, 88;
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue",
    STHeiti, "Microsoft YaHei", SimSun, sans-serif;
}

#app {
  height: 100%;
  overflow: hidden;
}

.global-error {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
  min-width: 300px;
}

.mb-4 {
  margin-bottom: 16px;
}

.ml-2 {
  margin-left: 8px;
}

.mr-2 {
  margin-right: 8px;
}

.mt-4 {
  margin-top: 16px;
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #909399;
}

html.dark {
  ::-webkit-scrollbar-thumb {
    background: #4c4d4f;
  }
  
  ::-webkit-scrollbar-thumb:hover {
    background: #5c5d5f;
  }
}
</style> 