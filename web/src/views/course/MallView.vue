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
            <router-link to="/reading" class="mall-nav-link">课本伴读</router-link>
            <router-link to="/videos" class="mall-nav-link">视频</router-link>
            <router-link to="/exercises" class="mall-nav-link">习题推荐</router-link>
            <router-link
              to="/mall"
              class="mall-nav-link"
              :class="{ active: $route.path === '/mall' }"
              >积分商城</router-link
            >
            <router-link
              v-if="userStore.isAdmin"
              to="/ops"
              class="mall-nav-link"
              :class="{ active: $route.path === '/ops' }"
              >运维</router-link
            >
            <router-link
              to="/guide"
              class="mall-nav-link"
              :class="{ active: $route.path === '/guide' }"
              >使用指南</router-link
            >
          </div>
          <div class="mall-auth">
            <template v-if="!userStore.isLoggedIn">
              <router-link to="/login" class="mall-auth-link">登录</router-link>
              <router-link to="/register" class="mall-auth-link primary">注册</router-link>
            </template>
            <template v-else>
              <span class="mall-points-pill" title="当前积分">
                <span class="mall-points-num">{{ pointsDisplay }}</span>
                <span class="mall-points-label">积分</span>
              </span>
              <span class="mall-username">{{ userStore.username || userStore.userIdLogin }}</span>
              <button type="button" class="mall-auth-btn" @click="handleSwitchAccount">
                切换账号
              </button>
              <button type="button" class="mall-auth-btn" @click="handleLogout">退出</button>
            </template>
          </div>
        </div>
      </div>
    </header>

    <main class="mall-main">
      <div class="mall-title-section">
        <div class="mall-title-row">
          <Sparkles class="mall-title-sparkle" :size="26" stroke-width="2" aria-hidden="true" />
          <h1 class="mall-title">积分商城</h1>
          <Sparkles
            class="mall-title-sparkle mall-title-sparkle--mirror"
            :size="26"
            stroke-width="2"
            aria-hidden="true"
          />
        </div>
        <p class="mall-subtitle">
          在「习题推荐」里答对题目就能攒积分，给自己一点小成就感。
        </p>
        <p v-if="userStore.isLoggedIn" class="mall-lead-actions">
          积分不够？
          <router-link to="/exercises" class="mall-inline-link">去习题推荐再练几题 →</router-link>
        </p>
        <p v-else class="mall-lead-actions mall-lead-actions--guest">
          <router-link to="/login" class="mall-inline-link">登录</router-link>
          后兑换；想先看看题目也可以
          <router-link to="/exercises" class="mall-inline-link">逛习题推荐</router-link>
        </p>
      </div>

      <section class="mall-section">
        <h2 class="mall-section-title">
          <span class="mall-section-icon-wrap" aria-hidden="true">
            <Trophy :size="22" stroke-width="2" />
          </span>
          我的称号
        </h2>
        <div v-if="myTitles.length > 0" class="mall-my-grid">
          <div v-for="entry in myTitles" :key="entry.item.id" class="mall-my-card">
            <div class="mall-my-icon-bubble">
              <span class="mall-my-icon">{{ entry.item.icon || '🏅' }}</span>
            </div>
            <span class="mall-my-name">{{ entry.item.name }}</span>
            <span class="mall-my-tag">已点亮</span>
            <span class="mall-my-date">获得于 {{ formatAcquiredAt(entry.acquired_at) }}</span>
          </div>
        </div>
        <p v-else class="mall-empty">
          展柜还空着——去「习题推荐」刷几题，你的第一枚称号正在路上。
        </p>
      </section>

      <section class="mall-section">
        <h2 class="mall-section-title">
          <span class="mall-section-icon-wrap" aria-hidden="true">
            <Gift :size="22" stroke-width="2" />
          </span>
          可兑换称号
        </h2>
        <div v-if="mallItems.length > 0" class="mall-grid">
          <div v-for="item in mallItems" :key="item.id" class="mall-card">
            <div class="mall-card-icon-bubble">
              <span class="mall-card-icon">{{ item.icon || '🏅' }}</span>
            </div>
            <h3 class="mall-card-name">{{ item.name }}</h3>
            <p v-if="item.description" class="mall-card-desc">{{ item.description }}</p>
            <div class="mall-card-cost">
              <span class="mall-card-cost-num">{{ item.cost }}</span>
              积分
            </div>
            <button
              type="button"
              class="mall-card-btn"
              :class="{ 'mall-card-btn--solid': !ownedIds.has(item.id) && pointsNum >= item.cost }"
              :disabled="pointsNum < item.cost || ownedIds.has(item.id)"
              @click="purchase(item.id)"
            >
              {{
                ownedIds.has(item.id) ? '已收下' : pointsNum < item.cost ? '还差一点点' : '兑换带走'
              }}
            </button>
          </div>
        </div>
        <p v-else class="mall-empty">货架正在补货，过几天再来瞅瞅～</p>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Sparkles, Trophy, Gift } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/time'
import { mallList, mallPurchase, mallMyTitles, getPoints } from '@/apis/courseApi'

function formatAcquiredAt(isoString) {
  if (!isoString) return '—'
  return formatDateTime(isoString, 'YYYY-MM-DD HH:mm')
}

const userStore = useUserStore()
const handleLogout = () => {
  userStore.logout()
}
const handleSwitchAccount = () => {
  userStore.logout()
}

const mallItems = ref([])
const myTitles = ref([])

const ownedIds = computed(() => new Set(myTitles.value.map((t) => t.item.id)))
const pointsDisplay = computed(() =>
  userStore.userPoints === null ? '—' : (userStore.userPoints ?? 0)
)
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
/* 与 GuideView / ExercisesView 同一套课程页变量 */
:root {
  --primary-color: #1a365d;
  --primary-hover: #153e68;
  --accent-color: #ff7d00;
  --light-bg: #f7f9fc;
  --dark-text: #2d3748;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --white: #ffffff;
  --gray-200: #e5e7eb;
  --gray-50: #f9fafb;
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

.mall-points-pill {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 6px;
  background-color: var(--light-bg);
  color: var(--primary-color);
  font-size: 14px;
}

.mall-points-num {
  font-weight: 600;
}

.mall-points-label {
  font-weight: 500;
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
  background-color: var(--primary-hover);
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

.mall-title-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 16px;
}

.mall-title-sparkle {
  flex-shrink: 0;
  color: var(--accent-color);
  animation: mall-sparkle 2.8s ease-in-out infinite;
}

.mall-title-sparkle--mirror {
  animation: mall-sparkle-mirror 2.8s ease-in-out infinite;
  animation-delay: 0.35s;
}

.mall-title {
  font-size: 2.5rem;
  font-weight: bold;
  color: var(--primary-color);
  margin: 0;
}

.mall-subtitle {
  color: var(--gray-600);
  max-width: 600px;
  margin: 0 auto;
  line-height: 1.65;
  font-size: 15px;
}

.mall-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 18px;
}

.mall-chip {
  display: inline-block;
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--primary-color);
  background: var(--light-bg);
  border: 1px solid rgba(26, 54, 93, 0.18);
  border-radius: 999px;
}

.mall-lead-actions {
  margin: 18px 0 0;
  font-size: 14px;
  color: var(--gray-600);
  line-height: 1.6;
}

.mall-lead-actions--guest {
  margin-top: 14px;
}

@keyframes mall-sparkle {
  0%,
  100% {
    opacity: 0.65;
    transform: rotate(-6deg);
  }
  50% {
    opacity: 1;
    transform: rotate(6deg);
  }
}

@keyframes mall-sparkle-mirror {
  0%,
  100% {
    opacity: 0.65;
    transform: scaleX(-1) rotate(6deg);
  }
  50% {
    opacity: 1;
    transform: scaleX(-1) rotate(-6deg);
  }
}

.mall-inline-link {
  color: var(--primary-color);
  font-weight: 500;
  text-decoration: none;
}

.mall-inline-link:hover {
  text-decoration: underline;
}

.mall-section {
  margin-bottom: 32px;
}

.mall-section:last-child {
  margin-bottom: 0;
}

.mall-section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0 0 24px;
}

.mall-section-icon-wrap {
  display: inline-flex;
  color: var(--primary-color);
  flex-shrink: 0;
}

.mall-empty {
  margin: 0;
  padding: 16px;
  text-align: center;
  font-size: 14px;
  color: var(--gray-600);
  line-height: 1.6;
  background: var(--light-bg);
  border-radius: 8px;
  border: 1px solid var(--gray-200);
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
  border: 1px solid var(--gray-200);
  transition: box-shadow 0.2s ease;
}

.mall-my-card:hover {
  box-shadow: var(--shadow-hover);
}

.mall-my-icon-bubble {
  width: 56px;
  height: 56px;
  margin: 0 auto 10px;
  border-radius: 50%;
  background: var(--light-bg);
  border: 1px solid rgba(26, 54, 93, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
}

.mall-my-icon {
  font-size: 28px;
  line-height: 1;
}

.mall-my-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--dark-text);
  display: block;
}

.mall-my-tag {
  display: inline-block;
  margin-top: 8px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--primary-color);
  background: var(--light-bg);
  border-radius: 999px;
  border: 1px solid rgba(26, 54, 93, 0.15);
}

.mall-my-date {
  font-size: 12px;
  color: var(--gray-500);
  display: block;
  margin-top: 8px;
}

.mall-card {
  background-color: var(--white);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  box-shadow: var(--shadow-light);
  border: 1px solid var(--gray-200);
  transition: box-shadow 0.2s ease;
}

.mall-card:hover {
  box-shadow: var(--shadow-hover);
}

.mall-card-icon-bubble {
  width: 64px;
  height: 64px;
  margin: 0 auto 12px;
  border-radius: 14px;
  background: var(--light-bg);
  border: 1px solid rgba(26, 54, 93, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
}

.mall-card-icon {
  font-size: 34px;
  line-height: 1;
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
  color: var(--gray-600);
  font-weight: 500;
  margin-bottom: 12px;
}

.mall-card-cost-num {
  font-weight: 700;
  color: var(--primary-color);
  margin-right: 2px;
}

.mall-card-btn {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--primary-color);
  border-radius: 8px;
  background-color: var(--white);
  color: var(--primary-color);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
}

.mall-card-btn--solid {
  background-color: var(--primary-color);
  color: var(--white);
  border-color: var(--primary-color);
}

.mall-card-btn--solid:hover:not(:disabled) {
  background-color: var(--primary-hover);
  border-color: var(--primary-hover);
  color: var(--white);
}

.mall-card-btn:hover:not(:disabled):not(.mall-card-btn--solid) {
  background-color: var(--light-bg);
}

.mall-card-btn:disabled {
  border-color: var(--gray-200);
  color: var(--gray-500);
  cursor: not-allowed;
  background-color: var(--white);
  font-weight: 400;
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
  .mall-title-row {
    gap: 8px;
  }

  .mall-title-sparkle :deep(svg) {
    width: 22px;
    height: 22px;
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
