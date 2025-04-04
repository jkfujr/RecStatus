<template>
  <div class="empty-state">
    <n-empty :description="description">
      <template #extra>
        <slot name="extra"></slot>
      </template>
    </n-empty>
  </div>
</template>

<script setup lang="ts">
defineProps({
  description: {
    type: String,
    default: '暂无数据'
  }
})
</script>

<style scoped>
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
}
</style> 