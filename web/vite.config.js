import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // loadEnv 只读 .env 文件，不含 Docker / shell 注入的变量；compose 的 VITE_API_URL 在 process.env
  const apiProxyTarget =
    process.env.VITE_API_URL || env.VITE_API_URL || 'http://127.0.0.1:5050'
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      proxy: {
        '^/api': {
          target: apiProxyTarget,
          changeOrigin: true
        }
      },
      watch: {
        usePolling: true,
        ignored: ['**/node_modules/**', '**/dist/**'],
      },
      host: '0.0.0.0',
    }
  }
})
