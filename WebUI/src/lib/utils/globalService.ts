import { createDiscreteApi } from 'naive-ui'
import { darkTheme, lightTheme } from 'naive-ui'
import type { MessageApi, DialogApi, NotificationApi, LoadingBarApi } from 'naive-ui'

interface GlobalApiInstance {
  message: MessageApi
  dialog: DialogApi
  notification: NotificationApi
  loadingBar: LoadingBarApi
}

let isDarkTheme = false
let apiInstance: GlobalApiInstance | null = null
let hasInjectedProviders = false

export function injectToGlobalService(services: GlobalApiInstance) {
  apiInstance = services
  hasInjectedProviders = true
  console.log('Provider instances injected to globalService')
}

function createGlobalService(): GlobalApiInstance {
  if (apiInstance) return apiInstance

  console.log('Creating discrete API instances')
  const { message, dialog, notification, loadingBar } = createDiscreteApi(
    ['message', 'dialog', 'notification', 'loadingBar'],
    {
      configProviderProps: {
        theme: isDarkTheme ? darkTheme : lightTheme
      }
    }
  )

  apiInstance = { message, dialog, notification, loadingBar }
  return apiInstance
}

export const globalService = createGlobalService()

export function updateGlobalServiceTheme(dark: boolean) {
  isDarkTheme = dark
  
  if (hasInjectedProviders) return
  
  if (apiInstance) {
    const { message, dialog, notification, loadingBar } = createDiscreteApi(
      ['message', 'dialog', 'notification', 'loadingBar'],
      {
        configProviderProps: {
          theme: isDarkTheme ? darkTheme : lightTheme
        }
      }
    )
    
    apiInstance.message = message
    apiInstance.dialog = dialog  
    apiInstance.notification = notification
    apiInstance.loadingBar = loadingBar
    
    console.log('Discrete API instances updated with new theme')
  }
} 