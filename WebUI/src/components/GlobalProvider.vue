<template>
  <slot></slot>
</template>

<script setup lang="ts">
import { useDialog, useMessage, useNotification, useLoadingBar } from 'naive-ui'
import { injectToGlobalService } from '@/lib/utils/globalService'

const message = useMessage()
const dialog = useDialog()
const notification = useNotification()
const loadingBar = useLoadingBar()


onMounted(() => {
  if (message && dialog && notification && loadingBar) {
    injectToGlobalService({
      message,
      dialog,
      notification,
      loadingBar
    })
  }
})
</script> 