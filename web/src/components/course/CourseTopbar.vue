<template>
  <header class="course-topbar">
    <div class="course-topbar__inner">
      <router-link :to="brandLink" class="course-topbar__brand">
        <span class="course-topbar__brand-mark"></span>
        <span class="course-topbar__brand-text">{{ title }}</span>
      </router-link>

      <div class="course-topbar__right">
        <nav class="course-topbar__nav">
          <router-link
            v-for="item in visibleNavItems"
            :key="item.to"
            :to="item.to"
            class="course-topbar__nav-link"
            :class="{ 'is-active': isActive(item) }"
            @click="item.onClick && item.onClick($event)"
          >
            {{ item.label }}
          </router-link>
        </nav>

        <div class="course-topbar__auth">
          <template v-if="!userStore.isLoggedIn">
            <router-link to="/login" class="course-topbar__ghost-link">登录</router-link>
            <router-link to="/register" class="course-topbar__primary-link">注册</router-link>
          </template>
          <template v-else>
            <slot name="auth-extra"></slot>
            <span class="course-topbar__username">{{
              userStore.username || userStore.userIdLogin
            }}</span>
            <button type="button" class="course-topbar__button" @click="handleSwitchAccount">
              切换账号
            </button>
            <button type="button" class="course-topbar__button" @click="handleLogout">退出</button>
          </template>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  title: {
    type: String,
    default: '天津大学《计算机网络》课程数智化平台'
  },
  brandLink: {
    type: String,
    default: '/course'
  },
  navItems: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['logout', 'switch-account'])

const route = useRoute()
const userStore = useUserStore()

const defaultNavItems = [
  { to: '/conversation', label: '对话', match: ['/conversation', '/course'] },
  { to: '/reading', label: '课本伴读', match: ['/reading'] },
  { to: '/videos', label: '视频', match: ['/videos'] },
  { to: '/exercises', label: '习题推荐', match: ['/exercises'] },
  { to: '/learning-analysis', label: '学情分析', match: ['/learning-analysis'], adminOnly: true },
  { to: '/ops', label: '运维', match: ['/ops'], adminOnly: true },
  { to: '/guide', label: '使用指南', match: ['/guide'] }
]

const visibleNavItems = computed(() => {
  const items = props.navItems.length ? props.navItems : defaultNavItems
  return items.filter((item) => !(item.adminOnly && !userStore.isAdmin))
})

function isActive(item) {
  const match = item.match || [item.to]
  return match.some((path) => route.path === path)
}

function handleLogout() {
  emit('logout')
}

function handleSwitchAccount() {
  emit('switch-account')
}
</script>

<style scoped lang="less">
.course-topbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  border-bottom: 1px solid var(--border-subtle);
  background: color-mix(in srgb, var(--surface-page) 96%, transparent);
  backdrop-filter: blur(16px);
}

.course-topbar__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  width: min(100%, 1440px);
  margin: 0 auto;
  padding: 12px 32px;
}

.course-topbar__brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  text-decoration: none;
  color: inherit;
}

.course-topbar__brand-mark {
  width: 18px;
  height: 18px;
  border: 1px solid var(--accent-primary);
  border-radius: 50%;
  background:
    linear-gradient(
      135deg,
      transparent 47%,
      var(--accent-primary) 48%,
      var(--accent-primary) 54%,
      transparent 55%
    ),
    var(--surface-page);
}

.course-topbar__brand-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 650;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.course-topbar__right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.course-topbar__nav {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.course-topbar__nav-link {
  position: relative;
  padding: 8px 2px;
  border: 0;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  line-height: 1;
  transition: color var(--transition-base);
}

.course-topbar__nav-link::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background: var(--accent-primary);
  opacity: 0;
}

.course-topbar__nav-link:hover {
  color: var(--accent-primary);
}

.course-topbar__nav-link.is-active {
  color: var(--accent-primary);
  font-weight: 650;
}

.course-topbar__nav-link.is-active::after {
  opacity: 1;
}

.course-topbar__auth {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.course-topbar__username {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
  font-size: 13px;
}

.course-topbar__ghost-link,
.course-topbar__primary-link,
.course-topbar__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  padding: 0 13px;
  border-radius: 999px;
  border: 1px solid var(--border-subtle);
  font-size: 13px;
  font-weight: 520;
  text-decoration: none;
  transition:
    color var(--transition-base),
    background-color var(--transition-base),
    border-color var(--transition-base);
}

.course-topbar__ghost-link,
.course-topbar__button,
:slotted(.course-topbar__button) {
  background: var(--surface-panel);
  color: var(--text-secondary);
}

.course-topbar__ghost-link:hover,
.course-topbar__button:hover,
:slotted(.course-topbar__button:hover) {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.course-topbar__primary-link {
  border-color: var(--accent-primary);
  background: var(--accent-primary);
  color: #ffffff;
}

.course-topbar__primary-link:hover {
  background: var(--accent-primary-hover);
  border-color: var(--accent-primary-hover);
}

:slotted(.course-topbar__button) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  padding: 0 13px;
  border-radius: 999px;
  border: 1px solid var(--border-subtle);
  font-size: 13px;
  font-weight: 520;
  transition:
    color var(--transition-base),
    background-color var(--transition-base),
    border-color var(--transition-base);
  cursor: pointer;
}

@media (max-width: 1200px) {
  .course-topbar__inner {
    flex-direction: column;
    align-items: stretch;
  }

  .course-topbar__right {
    flex-direction: column;
    align-items: stretch;
  }

  .course-topbar__nav {
    justify-content: flex-start;
    border-radius: var(--radius-lg);
  }

  .course-topbar__auth {
    flex-wrap: wrap;
  }
}

@media (max-width: 640px) {
  .course-topbar__inner {
    padding: 12px 18px;
  }

  .course-topbar__nav-link,
  .course-topbar__ghost-link,
  .course-topbar__primary-link,
  .course-topbar__button {
    height: 34px;
    padding: 0 11px;
  }

  .course-topbar__brand-text {
    font-size: 13px;
  }
}
</style>
