<template>
  <div class="mall-container">
    <header class="mall-header">
      <div class="mall-header-content">
        <router-link to="/" class="mall-logo">
          <span class="mall-logo-text">天津大学《计算机网络》课程数智化平台</span>
        </router-link>
        <div class="mall-right">
          <div class="mall-nav">
            <router-link to="/conversation" class="mall-nav-link">对话</router-link>
            <router-link to="/exercises" class="mall-nav-link">习题推荐</router-link>
            <router-link to="/reading" class="mall-nav-link">课本伴读</router-link>
            <router-link to="/videos" class="mall-nav-link">视频</router-link>
            <router-link to="/mall" class="mall-nav-link" :class="{ active: $route.path === '/mall' }">积分商城</router-link>
            <router-link v-if="userStore.isAdmin" to="/ops" class="mall-nav-link" :class="{ active: $route.path === '/ops' }">运维</router-link>
          </div>
          <div class="mall-auth">
            <template v-if="!userStore.isLoggedIn">
              <router-link to="/login" class="mall-auth-link">登录</router-link>
              <router-link to="/register" class="mall-auth-link primary">注册</router-link>
            </template>
            <template v-else>
              <span class="mall-points">
                <span class="mall-points-num">{{ pointsDisplay }}</span> 积分
              </span>
              <span class="mall-username">{{ userStore.username || userStore.userIdLogin }}</span>
              <button type="button" class="mall-auth-btn" @click="handleSwitchAccount">切换账号</button>
              <button type="button" class="mall-auth-btn" @click="handleLogout">退出</button>
            </template>
          </div>
        </div>
      </div>
    </header>

    <main class="mall-main">
      <div class="mall-title-section">
        <h1 class="mall-title">积分商城</h1>
        <p class="mall-subtitle">答对一题积 1 分，用积分兑换称号，彰显学习成就</p>
      </div>

      <!-- 我的称号 -->
      <section v-if="myTitles.length > 0" class="mall-section">
        <h2 class="mall-section-title">我的称号</h2>
        <div class="mall-my-grid">
          <div v-for="entry in myTitles" :key="entry.item.id" class="mall-my-card">
            <span class="mall-my-icon">{{ entry.item.icon || '🏅' }}</span>
            <span class="mall-my-name">{{ entry.item.name }}</span>
            <span class="mall-my-date">获得于 {{ formatAcquiredAt(entry.acquired_at) }}</span>
          </div>
        </div>
      </section>

      <!-- 可兑换列表 -->
      <section class="mall-section">
        <h2 class="mall-section-title">可兑换称号</h2>
        <div class="mall-grid">
          <div v-for="item in mallItems" :key="item.id" class="mall-card">
            <div class="mall-card-icon">{{ item.icon || '🏅' }}</div>
            <h3 class="mall-card-name">{{ item.name }}</h3>
            <p v-if="item.description" class="mall-card-desc">{{ item.description }}</p>
            <div class="mall-card-cost">{{ item.cost }} 积分</div>
            <button
              type="button"
              class="mall-card-btn"
              :disabled="pointsNum < item.cost || ownedIds.has(item.id)"
              @click="purchase(item.id)"
            >
              {{ ownedIds.has(item.id) ? '已拥有' : pointsNum < item.cost ? '积分不足' : '兑换' }}
            </button>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/time'
import { mallList, mallPurchase, mallMyTitles, getPoints } from '@/apis/courseApi'

function formatAcquiredAt(isoString) {
  if (!isoString) return '—'
  return formatDateTime(isoString, 'YYYY-MM-DD HH:mm')
}

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

const mallItems = ref([])
const myTitles = ref([])

const ownedIds = computed(() => new Set(myTitles.value.map((t) => t.item.id)))
const pointsDisplay = computed(() => (userStore.userPoints === null ? '—' : (userStore.userPoints ?? 0)))
const pointsNum = computed(() => userStore.userPoints ?? 0)

async function loadPoints() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await getPoints()
    userStore.setUserPoints(res.points ?? 0)
  } catch (_) {}
}

async function loadMall() {
  try {
    const res = await mallList()
    mallItems.value = res.items || []
  } catch (_) {
    mallItems.value = []
  }
}

async function loadMyTitles() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await mallMyTitles()
    myTitles.value = res.items || []
  } catch (_) {
    myTitles.value = []
  }
}

async function purchase(itemId) {
  try {
    await mallPurchase(itemId)
    await loadPoints()
    await loadMyTitles()
  } catch (e) {
    console.error(e)
  }
}

onMounted(async () => {
  await loadMall()
  await loadPoints()
  await loadMyTitles()
})
</script>

<style scoped>
/* 与课程智能体其他界面一致（VideosView / ConversationView） */
:root {
  --primary-color: #1A365D;
  --secondary-color: #FF7D00;
  --light-bg: #F7F9FC;
  --dark-text: #2D3748;
  --gray-500: #6B7280;
  --gray-600: #4B5563;
  --white: #FFFFFF;
  --gray-200: #E5E7EB;
  --gray-50: #F9FAFB;
  --shadow-light: 0 4px 20px rgba(0, 0, 0, 0.05);
  --shadow-hover: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.mall-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: var(--gray-50);
  min-height: 100vh;
  color: var(--dark-text);
}

.mall-header {
  background-color: var(--white);
  border-bottom: 1px solid var(--gray-200);
}

.mall-header-content {
  width: 100%;
  padding: 12px 24px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.mall-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.mall-logo-text {
  margin-left: 0;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.mall-right {
  display: flex;
  align-items: center;
  gap: 32px;
}

.mall-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.mall-nav-link {
  color: var(--gray-500);
  text-decoration: none;
  transition: color 0.3s ease;
  font-size: 16px;
}

.mall-nav-link:hover {
  color: var(--primary-color);
}

.mall-nav-link.active {
  color: var(--primary-color);
  font-weight: 500;
}

.mall-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mall-points {
  font-size: 14px;
  color: var(--gray-600);
}

.mall-points-num {
  font-weight: 600;
  color: var(--primary-color);
}

.mall-username {
  font-size: 14px;
  color: var(--gray-600);
  margin-right: 4px;
}

.mall-auth-link {
  color: var(--gray-500);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;
}

.mall-auth-link:hover {
  color: var(--primary-color);
}

.mall-auth-link.primary {
  color: var(--white);
  background-color: var(--primary-color);
}

.mall-auth-link.primary:hover {
  background-color: #153e68;
  color: var(--white);
}

.mall-auth-btn {
  font-size: 14px;
  padding: 6px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background-color: var(--white);
  color: var(--gray-600);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.mall-auth-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.mall-main {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px;
}

.mall-title-section {
  text-align: center;
  margin-bottom: 32px;
}

.mall-title {
  font-size: 2.5rem;
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 16px;
}

.mall-subtitle {
  color: var(--gray-600);
  max-width: 600px;
  margin: 0 auto;
}

.mall-section {
  margin-bottom: 40px;
}

.mall-section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 24px;
}

.mall-my-grid,
.mall-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 24px;
}

.mall-my-card {
  background-color: var(--white);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  box-shadow: var(--shadow-light);
  transition: all 0.3s ease;
}

.mall-my-card:hover {
  box-shadow: var(--shadow-hover);
}

.mall-my-icon {
  font-size: 28px;
  display: block;
  margin-bottom: 8px;
}

.mall-my-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--dark-text);
  display: block;
}

.mall-my-date {
  font-size: 12px;
  color: var(--gray-500);
  display: block;
  margin-top: 4px;
}

.mall-card {
  background-color: var(--white);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  box-shadow: var(--shadow-light);
  transition: all 0.3s ease;
}

.mall-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-4px);
}

.mall-card-icon {
  font-size: 36px;
  margin-bottom: 10px;
}

.mall-card-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--dark-text);
  margin: 0 0 6px 0;
}

.mall-card-desc {
  font-size: 13px;
  color: var(--gray-600);
  margin: 0 0 12px 0;
  line-height: 1.4;
}

.mall-card-cost {
  font-size: 14px;
  color: var(--primary-color);
  font-weight: 500;
  margin-bottom: 12px;
}

.mall-card-btn {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--primary-color);
  border-radius: 8px;
  background-color: var(--white);
  color: var(--primary-color);
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
}

.mall-card-btn:hover:not(:disabled) {
  background-color: var(--light-bg);
}

.mall-card-btn:disabled {
  border-color: var(--gray-200);
  color: var(--gray-500);
  cursor: not-allowed;
}

@media (max-width: 639px) {
  .mall-header-content {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }
  .mall-logo-text {
    white-space: normal;
    text-align: center;
  }
  .mall-nav {
    gap: 16px;
  }
  .mall-nav-link {
    font-size: 14px;
  }
  .mall-title {
    font-size: 2rem;
  }
  .mall-main {
    padding: 24px 16px;
  }
  .mall-my-grid,
  .mall-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 16px;
  }
}
</style>
