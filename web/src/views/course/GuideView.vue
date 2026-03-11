<template>
  <div class="guide-container">
    <header class="guide-header">
      <div class="guide-header-content">
        <router-link to="/" class="guide-logo">
          <span class="guide-logo-text">天津大学《计算机网络》课程数智化平台</span>
        </router-link>
        <div class="guide-right">
          <div class="guide-nav">
            <router-link to="/conversation" class="guide-nav-link" :class="{ active: $route.path === '/conversation' || $route.path === '/course' }">对话</router-link>
            <router-link to="/exercises" class="guide-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>
            <router-link to="/reading" class="guide-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
            <router-link to="/videos" class="guide-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
            <router-link to="/mall" class="guide-nav-link" :class="{ active: $route.path === '/mall' }">积分商城</router-link>
            <router-link v-if="userStore.isAdmin" to="/ops" class="guide-nav-link" :class="{ active: $route.path === '/ops' }">运维</router-link>
            <router-link to="/guide" class="guide-nav-link" :class="{ active: $route.path === '/guide' }">使用指南</router-link>
          </div>
          <div class="guide-auth">
            <template v-if="!userStore.isLoggedIn">
              <router-link to="/login" class="guide-auth-link">登录</router-link>
              <router-link to="/register" class="guide-auth-link primary">注册</router-link>
            </template>
            <template v-else>
              <span class="guide-username">{{ userStore.username || userStore.userIdLogin }}</span>
              <button type="button" class="guide-auth-btn" @click="handleSwitchAccount">切换账号</button>
              <button type="button" class="guide-auth-btn" @click="handleLogout">退出</button>
            </template>
          </div>
        </div>
      </div>
    </header>

    <main class="guide-main">
      <div class="guide-title-section">
        <h1 class="guide-title">使用指南</h1>
        <p class="guide-subtitle">
          本平台为天津大学《计算机网络》课程数智化学习平台，提供对话答疑、习题推荐、课本伴读、视频学习与积分商城等功能，帮助您更好地掌握课程内容。
        </p>
      </div>

      <section class="guide-section">
        <h2 class="guide-section-title">登录与账号</h2>
        <p class="guide-section-p">使用前请先注册并登录。登录后可在页面右上角看到用户名、积分（若当前页面有显示）、切换账号与退出按钮。切换账号可更换为其他账号登录，退出则清除当前登录状态。</p>
      </section>

      <section class="guide-section">
        <h2 class="guide-section-title">对话</h2>
        <p class="guide-section-p">在顶部导航点击「对话」进入课程智能体。您可以像与助教聊天一样提问，智能体会基于课程教材与知识库回答。支持多轮对话，可新建多个对话分别讨论不同主题。开启智能体功能后，回答中会标注参考来源，方便您回溯课本。</p>
      </section>

      <section class="guide-section">
        <h2 class="guide-section-title">习题推荐</h2>
        <p class="guide-section-p">「习题推荐」根据您的学习情况推荐练习题。答对题目可获得积分，积分可用于积分商城兑换称号。支持错题分析，帮助您针对薄弱知识点加强练习。</p>
      </section>

      <section class="guide-section">
        <h2 class="guide-section-title">课本伴读</h2>
        <p class="guide-section-p">「课本伴读」提供与教材对应的智能伴读。选择教材后可按章节阅读，在阅读过程中可随时向智能体提问当前页或相关知识点，便于边读边问、加深理解。</p>
      </section>

      <section class="guide-section">
        <h2 class="guide-section-title">视频</h2>
        <p class="guide-section-p">「视频」页面按课程章节组织视频资源。选择章节后即可观看对应讲解视频，适合配合课本与习题巩固学习。</p>
      </section>

      <section class="guide-section">
        <h2 class="guide-section-title">积分商城</h2>
        <p class="guide-section-p">通过习题推荐答对题目可获得积分。在「积分商城」中可使用积分兑换各类称号，展示您的学习成就。已获得的称号会显示在「我的称号」中。</p>
      </section>

    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

function handleSwitchAccount() {
  userStore.logout()
}

function handleLogout() {
  userStore.logout()
}
</script>

<style lang="less" scoped>
/* 与课程智能体其他界面一致（ExercisesView / ReadingView / MallView） */
:root {
  --primary-color: #1a365d;
  --light-bg: #f7f9fc;
  --dark-text: #2d3748;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --white: #ffffff;
  --gray-200: #e5e7eb;
  --gray-50: #f9fafb;
}

.guide-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: var(--gray-50);
  min-height: 100vh;
  color: var(--dark-text);
}

.guide-header {
  background-color: var(--white);
  border-bottom: 1px solid var(--gray-200);
}

.guide-header-content {
  width: 100%;
  padding: 12px 24px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.guide-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.guide-logo-text {
  margin-left: 0;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.guide-right {
  display: flex;
  align-items: center;
  gap: 32px;
}

.guide-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.guide-nav-link {
  color: var(--gray-500);
  text-decoration: none;
  transition: color 0.3s ease;
  font-size: 16px;
}

.guide-nav-link:hover {
  color: var(--primary-color);
}

.guide-nav-link.active {
  color: var(--primary-color);
  font-weight: 500;
}

.guide-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.guide-username {
  font-size: 14px;
  color: var(--gray-600);
  margin-right: 4px;
}

.guide-auth-link {
  color: var(--gray-500);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;
}

.guide-auth-link:hover {
  color: var(--primary-color);
}

.guide-auth-link.primary {
  color: var(--white);
  background-color: var(--primary-color);
}

.guide-auth-link.primary:hover {
  background-color: #153e68;
  color: var(--white);
}

.guide-auth-btn {
  font-size: 14px;
  padding: 6px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background-color: var(--white);
  color: var(--gray-600);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.guide-auth-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.guide-main {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px;
}

.guide-title-section {
  text-align: center;
  margin-bottom: 32px;
}

.guide-title {
  font-size: 2.5rem;
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 16px;
}

.guide-subtitle {
  color: var(--gray-600);
  max-width: 600px;
  margin: 0 auto;
  line-height: 1.6;
}

.guide-section {
  margin-bottom: 32px;
}

.guide-section:last-child {
  margin-bottom: 0;
}

.guide-section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.guide-section-p {
  font-size: 15px;
  color: var(--gray-600);
  line-height: 1.7;
  margin: 0;
}

@media (max-width: 768px) {
  .guide-header-content {
    flex-wrap: wrap;
    gap: 12px;
  }

  .guide-logo-text {
    white-space: normal;
  }

  .guide-right {
    width: 100%;
    justify-content: space-between;
  }

  .guide-nav {
    flex-wrap: wrap;
  }

  .guide-main {
    padding: 24px 16px;
  }
}
</style>
