<template>
  <div class="not-found">
    <n-result
      status="404"
      title="页面不存在"
      description="您访问的页面不存在或已被移除"
      :icon="() => h('div', { class: 'emoji-icon' }, '🤔')"
      size="large"
    >
      <template #footer>
        <n-space justify="center">
          <n-button
            type="primary"
            size="large"
            @click="router.push('/')"
          >
            <template #icon>
              <n-icon><component :is="HomeOutline" /></n-icon>
            </template>
            返回首页
          </n-button>
        </n-space>
      </template>
    </n-result>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { HomeOutline } from '@vicons/ionicons5'
import { h } from 'vue'

const router = useRouter()
</script>

<style scoped lang="scss">
.not-found {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background-color: var(--bg-color);
  transition: background-color 0.3s ease;

  :deep(.n-result) {
    background-color: transparent;
    
    .n-result-icon {
      margin-bottom: 24px;
    }

    .n-result-title {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 16px;
      color: var(--text-color);
    }

    .n-result-description {
      font-size: 16px;
      color: var(--text-color-secondary);
      margin-bottom: 32px;
    }
  }

  .emoji-icon {
    font-size: 64px;
    line-height: 1;
    margin-bottom: 24px;
  }
}

html.dark {
  .not-found {
    background-color: var(--n-color);
  }
}
</style> 