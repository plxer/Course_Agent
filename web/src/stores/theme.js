import { ref } from 'vue'
import { defineStore } from 'pinia'
import { theme } from 'ant-design-vue'

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(localStorage.getItem('theme') === 'dark')

  const commonTheme = {
    token: {
      fontFamily: "'HarmonyOS Sans SC', 'Noto Sans SC', 'SF Pro Display', 'Segoe UI', sans-serif",
      colorPrimary: '#56b0cb',
      borderRadius: 14,
      wireframe: false,
      colorText: '#101418',
      colorTextSecondary: 'rgba(16, 20, 24, 0.72)',
      colorBgLayout: '#f5f7fa',
      colorBgContainer: 'rgba(255, 255, 255, 0.92)',
      colorBgElevated: 'rgba(255, 255, 255, 0.96)',
      colorBorder: 'rgba(16, 20, 24, 0.08)',
      colorBorderSecondary: 'rgba(16, 20, 24, 0.06)',
      boxShadowSecondary: '0 18px 48px rgba(11, 18, 28, 0.08)'
    }
  }

  const lightTheme = {
    ...commonTheme
  }

  const darkTheme = {
    ...commonTheme,
    algorithm: theme.darkAlgorithm,
    token: {
      ...commonTheme.token,
      colorPrimary: '#56b0cb',
      colorText: '#f3f7fb',
      colorTextSecondary: 'rgba(243, 247, 251, 0.72)',
      colorBgLayout: '#090d12',
      colorBgContainer: '#121922',
      colorBgElevated: '#161f2a',
      colorBorder: 'rgba(243, 247, 251, 0.08)',
      colorBorderSecondary: 'rgba(243, 247, 251, 0.06)',
      boxShadowSecondary: '0 24px 60px rgba(0, 0, 0, 0.35)'
    }
  }

  const currentTheme = ref(isDark.value ? darkTheme : lightTheme)

  function toggleTheme() {
    setTheme(!isDark.value)
  }

  function setTheme(dark) {
    isDark.value = dark
    currentTheme.value = dark ? darkTheme : lightTheme
    localStorage.setItem('theme', dark ? 'dark' : 'light')
    updateDocumentTheme()
  }

  function updateDocumentTheme() {
    if (isDark.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  updateDocumentTheme()

  return {
    isDark,
    currentTheme,
    toggleTheme,
    setTheme
  }
})
