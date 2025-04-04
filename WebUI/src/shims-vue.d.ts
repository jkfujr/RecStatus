declare module '@vicons/ionicons5';
declare module 'naive-ui';

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

export {}

// vite
interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare interface Window {
}

// naive-ui
declare module 'naive-ui' {
  export * from 'naive-ui/es/components'
  export * from 'naive-ui/es/composables'
  export * from 'naive-ui/es/locales'
  export * from 'naive-ui/es/themes'
  export interface GlobalTheme {
    common?: Record<string, unknown>
    self?: Record<string, unknown>
  }
}

// vicons 图标
declare module '@vicons/ionicons5' {
  export * from '@vicons/ionicons5/lib/index'
} 