<template>
  <div class="videos-container">
    <!-- 顶部导航 -->
    <header class="videos-header">
      <div class="videos-header-content">
        <router-link to="/" class="videos-logo">
          <span class="videos-logo-text">天津大学《计算机网络》课程数智化平台</span>
        </router-link>
        <div class="videos-right">
          <div class="videos-nav">
            <router-link to="/conversation" class="videos-nav-link" :class="{ active: $route.path === '/conversation' || $route.path === '/course' }">对话</router-link>
            <router-link to="/exercises" class="videos-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>
            <router-link to="/reading" class="videos-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
            <router-link to="/videos" class="videos-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
          </div>
          <div class="videos-auth">
            <template v-if="!userStore.isLoggedIn">
              <router-link to="/login" class="videos-auth-link">登录</router-link>
              <router-link to="/register" class="videos-auth-link primary">注册</router-link>
            </template>
            <template v-else>
              <span class="videos-username">{{ userStore.username || userStore.userIdLogin }}</span>
              <button type="button" class="videos-auth-btn" @click="handleSwitchAccount">切换账号</button>
              <button type="button" class="videos-auth-btn" @click="handleLogout">退出</button>
            </template>
          </div>
        </div>
      </div>
    </header>

    <!-- 主要内容区 -->
    <main class="videos-main">
      <!-- 标题部分 -->
      <div class="videos-title-section">
        <h1 class="videos-title">视频学习</h1>
        <p class="videos-subtitle">生动直观的课程讲解，让学习更加高效有趣</p>
      </div>

      <!-- 章节筛选 -->
      <div class="videos-filter-section" v-if="chapters.length > 0">
        <div class="videos-filter-tabs">
          <button 
            class="videos-filter-tab" 
            :class="{ active: selectedChapter === null }"
            @click="selectedChapter = null"
          >
            全部
          </button>
          <button 
            v-for="chapter in chapters" 
            :key="chapter.chapter"
            class="videos-filter-tab"
            :class="{ active: selectedChapter === chapter.chapter }"
            @click="selectedChapter = chapter.chapter"
          >
            第{{ chapter.chapter }}章
          </button>
        </div>
      </div>

      <!-- 视频列表 -->
      <div class="videos-list-section">
        <h2 class="videos-list-title">
          {{ selectedChapter === null ? '所有视频' : `第${selectedChapter}章` }}
        </h2>
        
        <div class="videos-list-grid" v-if="filteredVideos.length > 0">
          <div 
            v-for="video in filteredVideos" 
            :key="video.id" 
            class="videos-card"
            @click="playVideo(video)"
          >
            <div class="videos-card-thumbnail">
              <div class="videos-card-play-overlay">
                <i class="fa fa-play"></i>
              </div>
              <div class="videos-card-placeholder">
                <i class="fa fa-video-camera"></i>
                <span>视频</span>
              </div>
            </div>
            <div class="videos-card-content">
              <h3 class="videos-card-title">{{ video.name }}</h3>
              <div class="videos-card-meta">
                <span class="videos-card-size">{{ formatFileSize(video.size) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="videos-empty">
          <p>暂无视频，请将视频文件放入 knowledgebase/videos 文件夹</p>
          <p class="videos-empty-hint">视频文件名应以 ChapterX 开头（X 为章节号）</p>
        </div>
      </div>
    </main>

    <!-- 视频播放器模态框 -->
    <div v-if="currentVideo" class="videos-modal" @click.self="closeVideo">
      <div class="videos-modal-content">
        <div class="videos-modal-header">
          <h3 class="videos-modal-title">{{ currentVideo.name }}</h3>
          <button class="videos-modal-close" @click="closeVideo">
            <i class="fa fa-times"></i>
          </button>
        </div>
        <div class="videos-modal-player">
          <video 
            :src="videoUrl" 
            controls 
            autoplay
            class="videos-player"
          >
            您的浏览器不支持视频播放
          </video>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { listVideos, getVideoUrl } from '@/apis/courseApi.js';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();
const handleLogout = () => { userStore.logout(); router.push('/course'); };
const handleSwitchAccount = () => { userStore.logout(); router.push('/login'); };

const chapters = ref([]);
const selectedChapter = ref(null);
const currentVideo = ref(null);

// 过滤后的视频列表
const filteredVideos = computed(() => {
  if (selectedChapter.value === null) {
    // 返回所有章节的视频
    return chapters.value.flatMap(ch => ch.videos);
  } else {
    // 返回指定章节的视频
    const chapter = chapters.value.find(ch => ch.chapter === selectedChapter.value);
    return chapter ? chapter.videos : [];
  }
});

// 视频URL
const videoUrl = computed(() => {
  if (!currentVideo.value) return '';
  return getVideoUrl(currentVideo.value.id);
});

// 加载视频列表
const loadVideos = async () => {
  try {
    const response = await listVideos();
    chapters.value = response.chapters || [];
    // 按章节号排序
    chapters.value.sort((a, b) => a.chapter - b.chapter);
  } catch (error) {
    console.error('加载视频列表失败:', error);
  }
};

// 播放视频
const playVideo = (video) => {
  currentVideo.value = video;
};

// 关闭视频
const closeVideo = () => {
  currentVideo.value = null;
};

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
};

onMounted(() => {
  loadVideos();
  // 确保Font Awesome已加载
  if (!document.querySelector('link[href*="font-awesome"]')) {
    const link = document.createElement('link');
    link.href = 'https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css';
    link.rel = 'stylesheet';
    document.head.appendChild(link);
  }
});
</script>

<style scoped>
/* 颜色变量 */
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

/* 容器样式 */
.videos-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: var(--gray-50);
  min-height: 100vh;
  color: var(--dark-text);
}

/* 顶部导航样式 */
.videos-header {
  background-color: var(--white);
  border-bottom: 1px solid var(--gray-200);
}

.videos-header-content {
  width: 100%;
  padding: 12px 24px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.videos-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.videos-logo-text {
  margin-left: 0;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.videos-right {
  display: flex;
  align-items: center;
  gap: 32px;
}

.videos-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.videos-auth-link {
  color: var(--gray-500);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;
}

.videos-auth-link:hover {
  color: var(--primary-color);
}

.videos-auth-link.primary {
  color: var(--white);
  background: var(--primary-color);
}

.videos-auth-link.primary:hover {
  background: #153e68;
  color: var(--white);
}

.videos-username {
  font-size: 14px;
  color: var(--gray-600);
  margin-right: 4px;
}

.videos-auth-btn {
  font-size: 14px;
  padding: 6px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--white);
  color: var(--gray-600);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.videos-auth-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.videos-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.videos-nav-link {
  color: var(--gray-500);
  text-decoration: none;
  transition: color 0.3s ease;
  font-size: 16px;
}

.videos-nav-link:hover {
  color: var(--primary-color);
}

.videos-nav-link.active {
  color: var(--primary-color);
  font-weight: 500;
}

/* 主要内容区样式 */
.videos-main {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px;
}

/* 标题部分 */
.videos-title-section {
  text-align: center;
  margin-bottom: 32px;
}

.videos-title {
  font-size: 2.5rem;
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 16px;
}

.videos-subtitle {
  color: var(--gray-600);
  max-width: 600px;
  margin: 0 auto;
}

/* 筛选条件 */
.videos-filter-section {
  margin-bottom: 32px;
}

.videos-filter-tabs {
  display: flex;
  overflow-x: auto;
  gap: 12px;
  padding-bottom: 8px;
}

.videos-filter-tab {
  padding: 8px 16px;
  border: 1px solid var(--gray-200);
  background-color: var(--white);
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.videos-filter-tab:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.videos-filter-tab.active {
  background-color: var(--primary-color);
  color: var(--white);
  border-color: var(--primary-color);
}

/* 推荐视频列表 */
.videos-list-section {
  margin-bottom: 40px;
}

.videos-list-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 24px;
}

.videos-list-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

/* 视频卡片样式 */
.videos-card {
  background-color: var(--white);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-light);
  transition: all 0.3s ease;
  cursor: pointer;
}

.videos-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-4px);
}

.videos-card-thumbnail {
  position: relative;
  padding-bottom: 56.25%; /* 16:9 宽高比 */
  overflow: hidden;
  background-color: var(--light-bg);
}

.videos-card-play-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 64px;
  height: 64px;
  background-color: rgba(26, 54, 93, 0.8);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--white);
  font-size: 24px;
  z-index: 2;
  transition: all 0.3s ease;
}

.videos-card:hover .videos-card-play-overlay {
  background-color: var(--primary-color);
  transform: translate(-50%, -50%) scale(1.1);
}

.videos-card-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--gray-500);
  font-size: 48px;
  gap: 8px;
}

.videos-card-placeholder span {
  font-size: 14px;
}

.videos-card-content {
  padding: 16px;
}

.videos-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--dark-text);
  margin-bottom: 8px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.videos-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.videos-card-size {
  color: var(--gray-500);
  font-size: 12px;
}

.videos-empty {
  text-align: center;
  padding: 40px;
  color: var(--gray-500);
}

.videos-empty-hint {
  margin-top: 8px;
  font-size: 14px;
  color: var(--gray-500);
}

/* 视频播放器模态框 */
.videos-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.videos-modal-content {
  background-color: var(--white);
  border-radius: 12px;
  width: 90%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.videos-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--gray-200);
}

.videos-modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0;
}

.videos-modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--gray-500);
  cursor: pointer;
  padding: 4px;
  transition: color 0.3s ease;
}

.videos-modal-close:hover {
  color: var(--dark-text);
}

.videos-modal-player {
  padding: 24px;
  display: flex;
  justify-content: center;
  background-color: #000;
}

.videos-player {
  width: 100%;
  max-width: 100%;
  max-height: calc(90vh - 100px);
}

/* 响应式设计 */
@media (max-width: 639px) {
  .videos-header-content {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }

  .videos-logo-text {
    white-space: normal;
    text-align: center;
  }
  
  .videos-nav {
    gap: 16px;
  }
  
  .videos-nav-link {
    font-size: 14px;
  }
  
  .videos-title {
    font-size: 2rem;
  }
  
  .videos-main {
    padding: 24px 16px;
  }
  
  .videos-list-grid {
    grid-template-columns: 1fr;
  }
  
  .videos-modal-content {
    width: 100%;
    height: 100%;
    max-height: 100%;
    border-radius: 0;
  }
  
  .videos-modal-player {
    padding: 0;
    height: calc(100vh - 80px);
  }
  
  .videos-player {
    height: 100%;
  }
}
</style>
