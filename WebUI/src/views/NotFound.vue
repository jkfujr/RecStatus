<template>
  <div class="not-found">
    <n-result 
      status="404"
      title="页面不存在"
      description="您访问的页面不存在或已被移除"
    >
      <template #footer>
        <n-button type="primary" @click="router.push('/')">返回首页</n-button>
      </template>
    </n-result>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped lang="scss">
.not-found {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style> 