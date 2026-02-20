<template>
  <div class="exercises-container">
    <!-- 顶部导航 -->
    <header class="exercises-header">
      <div class="exercises-header-content">
        <router-link to="/" class="exercises-logo">
          <span class="exercises-logo-text">天津大学《计算机网络》课程数智化平台</span>
        </router-link>
        <div class="exercises-nav">
          <router-link to="/conversation" class="exercises-nav-link" :class="{ active: $route.path === '/conversation' || $route.path === '/course' }">对话</router-link>
          <router-link to="/exercises" class="exercises-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>
          <router-link to="/reading" class="exercises-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
          <router-link to="/videos" class="exercises-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
        </div>
      </div>
    </header>

    <!-- 主要内容区 -->
    <main class="exercises-main">
      <!-- 标题部分 -->
      <div class="exercises-title-section">
        <h1 class="exercises-title">习题推荐</h1>
        <p class="exercises-subtitle">个性化习题匹配，巩固薄弱点，提升学习效率</p>
      </div>

      <!-- 按章节出题 -->
      <div class="exercises-chapters-section">
        <h2 class="exercises-list-title">章节练习</h2>
        <p class="exercises-chapters-hint">选择章节生成或查看该章节的习题</p>
        <div class="exercises-chapters-grid">
          <div
            v-for="ch in chapters"
            :key="ch.id"
            class="exercises-chapter-card"
          >
            <h3 class="exercises-chapter-title">{{ ch.title }}</h3>
            <p class="exercises-chapter-desc">{{ ch.desc }}</p>
            <div class="exercises-chapter-actions">
              <button
                class="exercises-chapter-btn primary"
                :disabled="chapterGenerating === ch.id"
                @click="generateForChapter(ch.id)"
              >
                <i class="fa fa-magic"></i>
                {{ chapterGenerating === ch.id ? '生成中…' : '生成题目' }}
              </button>
              <button
                class="exercises-chapter-btn secondary"
                @click="viewChapterQuestions(ch.id)"
              >
                <i class="fa fa-list"></i> 查看题目
              </button>
            </div>
            <div v-if="selectedChapterId === ch.id && chapterQuestions.length > 0" class="exercises-chapter-questions">
              <div
                v-for="(q, qIdx) in chapterQuestions"
                :key="qIdx"
                class="exercises-question-item"
              >
                <span class="exercises-question-num">第 {{ qIdx + 1 }} 题</span>
                <p class="exercises-question-text">{{ q.content }}</p>
              </div>
            </div>
            <div v-else-if="selectedChapterId === ch.id" class="exercises-chapter-empty">
              暂无题目，请先点击「生成题目」
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

// 按章节出题：计算机网络 第1–6章
const chapters = [
  { id: 1, title: '第1章 计算机网络和因特网', desc: '概述、网络边缘与核心、接入网与物理媒体' },
  { id: 2, title: '第2章 应用层', desc: '应用层协议、HTTP、DNS、P2P 等' },
  { id: 3, title: '第3章 传输层', desc: '多路复用、UDP、TCP、拥塞控制' },
  { id: 4, title: '第4章 网络层', desc: 'IP、路由、IPv4/IPv6' },
  { id: 5, title: '第5章 链路层', desc: '以太网、交换机、ARP' },
  { id: 6, title: '第6章 无线网络与移动网络', desc: 'WiFi、移动 IP、4G/5G 概述' }
]

const chapterGenerating = ref(null)
const selectedChapterId = ref(null)
const chapterQuestions = ref([])

const generateForChapter = (chapterId) => {
  chapterGenerating.value = chapterId
  // 占位：后续可对接按章节生成题目的 API
  setTimeout(() => {
    chapterGenerating.value = null
    chapterQuestions.value = []
    selectedChapterId.value = null
  }, 1500)
}

const viewChapterQuestions = (chapterId) => {
  if (selectedChapterId.value === chapterId) {
    selectedChapterId.value = null
    chapterQuestions.value = []
    return
  }
  selectedChapterId.value = chapterId
  // 占位：后续可对接按章节获取题目列表的 API
  chapterQuestions.value = []
}

onMounted(() => {
  if (!document.querySelector('link[href*="font-awesome"]')) {
    const link = document.createElement('link')
    link.href = 'https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css'
    link.rel = 'stylesheet'
    document.head.appendChild(link)
  }
})
</script>

<style scoped>
/* 颜色变量 */
:root {
  --primary-color: #1A365D;      /* 深蓝主色 */
  --secondary-color: #FF7D00;    /* 橙色强调色 */
  --light-bg: #F7F9FC;          /* 浅色背景 */
  --dark-text: #2D3748;         /* 深色文字 */
  --gray-500: #6B7280;          /* 灰色文字 */
  --gray-600: #4B5563;          /* 更深灰色文字 */
  --white: #FFFFFF;             /* 白色 */
  --gray-200: #E5E7EB;          /* 浅灰色边框 */
  --gray-50: #F9FAFB;           /* 最浅灰色背景 */
  --shadow-light: 0 4px 20px rgba(0, 0, 0, 0.05);
  --shadow-hover: 0 10px 25px rgba(0, 0, 0, 0.1);
}

/* 容器样式 */
.exercises-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: var(--gray-50);
  min-height: 100vh;
  color: var(--dark-text);
}

/* 顶部导航样式 */
.exercises-header {
  background-color: var(--white);
  border-bottom: 1px solid var(--gray-200);
}

.exercises-header-content {
  width: 100%;
  padding: 12px 24px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.exercises-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.exercises-logo-text {
  margin-left: 0;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.exercises-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.exercises-nav-link {
  color: var(--gray-500);
  text-decoration: none;
  transition: color 0.3s ease;
  font-size: 16px;
}

.exercises-nav-link:hover {
  color: var(--primary-color);
}

.exercises-nav-link.active {
  color: var(--primary-color);
  font-weight: 500;
}

/* 主要内容区样式 */
.exercises-main {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px;
}

/* 标题部分 */
.exercises-title-section {
  text-align: center;
  margin-bottom: 32px;
}

.exercises-title {
  font-size: 2.5rem;
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 16px;
}

.exercises-subtitle {
  color: var(--gray-600);
  max-width: 600px;
  margin: 0 auto;
}

/* 按章节出题 */
.exercises-chapters-section {
  margin-bottom: 40px;
}

.exercises-list-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 8px;
}

.exercises-chapters-hint {
  color: var(--gray-600);
  font-size: 14px;
  margin-bottom: 24px;
}

.exercises-chapters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.exercises-chapter-card {
  background-color: var(--white);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow-light);
  transition: box-shadow 0.3s ease;
}

.exercises-chapter-card:hover {
  box-shadow: var(--shadow-hover);
}

.exercises-chapter-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0 0 8px 0;
}

.exercises-chapter-desc {
  font-size: 13px;
  color: var(--gray-600);
  margin: 0 0 16px 0;
  line-height: 1.5;
}

.exercises-chapter-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.exercises-chapter-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: background-color 0.2s ease;
}

.exercises-chapter-btn.primary {
  background-color: var(--primary-color);
  color: var(--white);
}

.exercises-chapter-btn.primary:hover:not(:disabled) {
  background-color: #153e68;
}

.exercises-chapter-btn.primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.exercises-chapter-btn.secondary {
  background-color: var(--light-bg);
  color: var(--primary-color);
  border: 1px solid var(--gray-200);
}

.exercises-chapter-btn.secondary:hover {
  background-color: var(--gray-200);
}

.exercises-chapter-questions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--gray-200);
}

.exercises-question-item {
  margin-bottom: 12px;
}

.exercises-question-num {
  font-size: 12px;
  color: var(--gray-500);
  margin-right: 8px;
}

.exercises-question-text {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: var(--dark-text);
  line-height: 1.5;
}

.exercises-chapter-empty {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--gray-200);
  font-size: 14px;
  color: var(--gray-500);
}

/* 响应式设计 */
@media (min-width: 768px) {
  .exercises-chapters-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 639px) {
  .exercises-header-content {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }

  .exercises-logo-text {
    white-space: normal;
    text-align: center;
  }
  
  .exercises-nav {
    gap: 16px;
  }
  
  .exercises-nav-link {
    font-size: 14px;
  }
  
  .exercises-title {
    font-size: 2rem;
  }
  
  .exercises-main {
    padding: 24px 16px;
  }
  
  .exercises-card-header,
  .exercises-card-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>