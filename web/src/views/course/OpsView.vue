<template>
  <div class="ops-container">
    <header class="ops-header">
      <div class="ops-header-content">
        <router-link to="/" class="ops-logo">
          <span class="ops-logo-text">天津大学《计算机网络》课程数智化平台</span>
        </router-link>
        <div class="ops-right">
          <div class="ops-nav">
            <router-link to="/conversation" class="ops-nav-link" :class="{ active: $route.path === '/conversation' || $route.path === '/course' }">对话</router-link>
            <router-link to="/exercises" class="ops-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>
            <router-link to="/reading" class="ops-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
            <router-link to="/videos" class="ops-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
            <router-link to="/mall" class="ops-nav-link" :class="{ active: $route.path === '/mall' }">积分商城</router-link>
            <router-link v-if="userStore.isAdmin" to="/ops" class="ops-nav-link" :class="{ active: $route.path === '/ops' }">运维</router-link>
          </div>
          <div class="ops-auth">
            <template v-if="!userStore.isLoggedIn">
              <router-link to="/login" class="ops-auth-link">登录</router-link>
              <router-link to="/register" class="ops-auth-link primary">注册</router-link>
            </template>
            <template v-else>
              <span class="ops-username">{{ userStore.username || userStore.userIdLogin }}</span>
              <button type="button" class="ops-auth-btn" @click="handleSwitchAccount">切换账号</button>
              <button type="button" class="ops-auth-btn" @click="handleLogout">退出</button>
            </template>
          </div>
        </div>
      </div>
    </header>

    <main class="ops-main">
      <div class="ops-dashboard">
        <DashboardView :embed-mode="true" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { initColorPalette } from '@/utils/chartColors'
import DashboardView from '@/views/DashboardView.vue'

const router = useRouter()
const userStore = useUserStore()
const handleLogout = () => {
  userStore.logout()
  router.push('/course')
}
const handleSwitchAccount = () => {
  userStore.logout()
  router.push('/login')
}

const OPS_CHART_COLORS = [
  '#1A365D',
  '#2C5282',
  '#2B6CB0',
  '#3182CE',
  '#4299E1',
  '#63B3ED',
  '#90CDF4',
  '#BEE3F8',
  '#EBF8FF',
  '#4A5568'
]

onMounted(() => {
  const root = document.documentElement
  root.style.setProperty('--chart-palette-1', OPS_CHART_COLORS[0])
  root.style.setProperty('--chart-palette-2', OPS_CHART_COLORS[1])
  root.style.setProperty('--chart-palette-3', OPS_CHART_COLORS[2])
  root.style.setProperty('--chart-palette-4', OPS_CHART_COLORS[3])
  root.style.setProperty('--chart-palette-5', OPS_CHART_COLORS[4])
  root.style.setProperty('--chart-palette-6', OPS_CHART_COLORS[5])
  root.style.setProperty('--chart-palette-7', OPS_CHART_COLORS[6])
  root.style.setProperty('--chart-palette-8', OPS_CHART_COLORS[7])
  root.style.setProperty('--chart-palette-9', OPS_CHART_COLORS[8])
  root.style.setProperty('--chart-palette-10', OPS_CHART_COLORS[9])
  root.style.setProperty('--main-500', '#1A365D')
  initColorPalette()
})

onUnmounted(() => {
  const root = document.documentElement
  for (let i = 1; i <= 10; i++) root.style.removeProperty(`--chart-palette-${i}`)
  root.style.removeProperty('--main-500')
  initColorPalette()
})
</script>

<style scoped>
.ops-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: var(--gray-50);
  min-height: 100vh;
  color: var(--gray-1000);
}

.ops-header {
  background-color: var(--gray-0);
  border-bottom: 1px solid var(--gray-200);
}

.ops-header-content {
  width: 100%;
  padding: 12px 24px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.ops-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.ops-logo-text {
  margin-left: 0;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.ops-right {
  display: flex;
  align-items: center;
  gap: 32px;
}

.ops-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.ops-nav-link {
  color: var(--gray-600);
  text-decoration: none;
  transition: color 0.2s ease;
  font-size: 16px;
}

.ops-nav-link:hover,
.ops-nav-link.active,
.ops-nav-link.router-link-active {
  color: var(--primary-color);
  font-weight: 500;
}

.ops-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ops-auth-link {
  color: var(--gray-600);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;
}

.ops-auth-link:hover {
  color: var(--primary-color);
}

.ops-auth-link.primary {
  color: var(--gray-0);
  background: var(--primary-color);
}

.ops-auth-link.primary:hover {
  background: var(--primary-color-dark);
  color: var(--gray-0);
}

.ops-username {
  font-size: 14px;
  color: var(--gray-600);
  margin-right: 4px;
}

.ops-auth-btn {
  font-size: 14px;
  padding: 6px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--gray-0);
  color: var(--gray-600);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.ops-auth-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.ops-main {
  width: 100%;
  padding: 0;
  min-height: calc(100vh - 52px);
}

/* 运维页深蓝主色，与课程顶栏一致 */
.ops-container {
  --primary-color: #1A365D;
  --primary-color-dark: #153e68;
}

/* 运维内嵌仪表盘：统计卡片与图表统一深蓝风格 */
.ops-dashboard {
  --main-color: #1A365D;
  --main-500: #1A365D;
  --main-600: #2C5282;
  --main-700: #2B6CB0;
  --color-primary-50: #EBF8FF;
  --color-primary-100: #BEE3F8;
  --color-primary-500: #1A365D;
  --color-primary-700: #2C5282;
}

.ops-dashboard :deep(.dashboard-card),
.ops-dashboard :deep(.conversations-section),
.ops-dashboard :deep(.call-stats-section) {
  border-color: var(--gray-200);
}

.ops-dashboard :deep(.dashboard-card .ant-card-head-title),
.ops-dashboard :deep(.stat-value) {
  color: var(--primary-color);
}

.ops-dashboard :deep(.stat-card.primary .stat-icon),
.ops-dashboard :deep(.stat-card.secondary .stat-icon) {
  background-color: var(--color-primary-50);
  color: var(--primary-color);
}
</style>
