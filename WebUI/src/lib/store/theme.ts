import { defineStore } from 'pinia'
import { darkTheme } from 'naive-ui'
import type { GlobalTheme } from 'naive-ui'
import { updateGlobalServiceTheme } from '@/lib/utils/globalService'

interface ThemeState {
  isDark: boolean
  theme: GlobalTheme | null
}

export const useThemeStore = defineStore('theme', {
  state: (): ThemeState => ({
    isDark: false,
    theme: null
  }),

  getters: {
    currentTheme: (state: ThemeState) => state.isDark ? darkTheme : null,
    isLightTheme: (state: ThemeState) => !state.isDark
  },

  actions: {
    init() {
      const savedTheme = localStorage.getItem('theme')
      if (savedTheme) {
        this.$patch({ isDark: savedTheme === 'dark' })
      } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        this.$patch({ isDark: prefersDark })
      }
      
      this.applyTheme()

      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
          this.$patch({ isDark: e.matches })
          this.applyTheme()
        }
      })
    },

    toggleTheme() {
      this.$patch({ isDark: !this.isDark })
      this.applyTheme()
      localStorage.setItem('theme', this.isDark ? 'dark' : 'light')
    },

    applyTheme() {
      document.documentElement.classList.toggle('dark', this.isDark)
      this.$patch({ 
        theme: this.isDark ? darkTheme : null as any 
      })
      updateGlobalServiceTheme(this.isDark)
    }
  }
}) 