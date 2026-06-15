<template>
  <div class="layout">
    <header class="header">
      <nav-header />
    </header>
    <div class="content-container">
      <aside class="sidebar" :class="{ collapsed: isCollapse }" :style="sidebarStyle">
        <n-menu
          :router="true"
          :value="route.path"
          :collapse="isCollapse"
          class="side-menu"
          :options="menuOptions"
          :collapsed-width="64"
          :collapsed-icon-size="22"
          :indent="20"
          @update:value="navigateTo"
        />
        <div class="collapse-trigger" @click="toggleCollapse">
          <n-icon size="18">
            <component :is="isCollapse ? ChevronForward : ChevronBack" />
          </n-icon>
        </div>
      </aside>
      <main class="main-content">
        <n-scrollbar class="main-scrollbar">
          <router-view />
        </n-scrollbar>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import NavHeader from '@/components/NavHeader.vue'
import { AnalyticsOutline, VideocamOutline, ServerOutline, ChevronForward, ChevronBack, SettingsOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import type { MenuOption } from 'naive-ui'
import { ref, computed, h } from 'vue'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(true)

const menuOptions: MenuOption[] = [
  {
    label: '总览',
    key: '/',
    icon: () => h(AnalyticsOutline)
  },
  {
    label: '房间列表',
    key: '/rooms',
    icon: () => h(VideocamOutline)
  },
  {
    label: '录播机列表',
    key: '/servers',
    icon: () => h(ServerOutline)
  },
  {
    label: '设置',
    key: '/settings',
    icon: () => h(SettingsOutline)
  }
]

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const navigateTo = (key: string) => {
  router.push(key)
}

const sidebarStyle = computed(() => ({
  width: isCollapse.value ? '64px' : '240px'
}))
</script>

<style scoped lang="scss">
.layout {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .header {
    height: 64px;
    border-bottom: 1px solid var(--border-color);
    background-color: #fff;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
  }

  .content-container {
    flex: 1;
    display: flex;
    margin-top: 64px;
    min-height: calc(100vh - 64px);
    position: relative;
    overflow: hidden;
  }

  .sidebar {
    width: 240px;
    height: 100%;
    background-color: #fff;
    border-right: 1px solid var(--border-color);
    position: fixed;
    left: 0;
    top: 64px;
    bottom: 0;
    transition: width 0.2s ease;
    z-index: 90;

    &.collapsed {
      width: 64px;
    }

    .side-menu {
      height: 100%;
      overflow: hidden;
    }

    .collapse-trigger {
      position: absolute;
      right: -11px;
      top: 50%;
      transform: translateY(-50%);
      width: 22px;
      height: 22px;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: #fff;
      border: 1px solid var(--border-color);
      border-radius: 50%;
      cursor: pointer;
      z-index: 10;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);

      &:hover {
        background-color: var(--hover-color);
      }
    }
  }
  
  .main-content {
    flex: 1;
    margin-left: 240px;
    transition: margin-left 0.2s ease;
    overflow: hidden;
    background-color: var(--bg-color);
    
    .main-scrollbar {
      height: calc(100vh - 64px);
      
      :deep(.n-scrollbar-container) {
        height: 100%;
      }
      
      :deep(.n-scrollbar-content) {
        padding: 20px;
        min-height: 100%;
      }
    }
  }

  .collapsed + .main-content {
    margin-left: 64px;
  }
}

html.dark {
  .layout {
    .header,
    .sidebar {
      background-color: #242424;
    }

    .collapse-trigger {
      background-color: #242424;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);

      &:hover {
        background-color: var(--hover-color-dark);
      }
    }
  }
}
</style> 