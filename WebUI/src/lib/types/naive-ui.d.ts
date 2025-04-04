import type { DialogApiInjection } from 'naive-ui/lib/dialog/src/DialogProvider'
import type { MessageApiInjection } from 'naive-ui/lib/message/src/MessageProvider'
import type { NotificationApiInjection } from 'naive-ui/lib/notification/src/NotificationProvider'
import type { LoadingBarApiInjection } from 'naive-ui/lib/loading-bar/src/LoadingBarProvider'

declare module 'naive-ui' {
  import type { Component } from 'vue'
  
  export const create: (options: { components: any[] }) => {
    install: (app: any) => void
  }
  
  export const darkTheme: any
  export const lightTheme: any
  
  export const NMessageProvider: Component
  export const NDialogProvider: Component
  export const NNotificationProvider: Component
  export const NLoadingBarProvider: Component
  export const NMenu: Component
  export const NIcon: Component
  export const NButton: Component
  export const NTag: Component
  export const NCard: Component
  export const NAlert: Component
  export const NSpin: Component
  export const NConfigProvider: Component
  export const NDrawer: Component
  export const NDrawerContent: Component
  export const NDescriptions: Component
  export const NDescriptionsItem: Component
  export const NRadioGroup: Component
  export const NRadioButton: Component
  export const NDataTable: Component
  export const NScrollbar: Component
  export const NEmpty: Component
  export const NInput: Component
  
  export interface DialogReactive {
    destroy: () => void
  }
  
  export interface DialogOptions {
    title?: string
    content?: string
    positiveText?: string
    negativeText?: string
    onPositiveClick?: () => void
    onNegativeClick?: () => void
    onMaskClick?: () => void
    onClose?: () => void
  }
  
  export type DialogApi = DialogApiInjection
  export type MessageApi = MessageApiInjection
  export type NotificationApi = NotificationApiInjection
  export type LoadingBarApi = LoadingBarApiInjection
} 