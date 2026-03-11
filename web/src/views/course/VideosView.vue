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
            <router-link
              to="/videos"
              class="videos-nav-link"
              :class="{ active: $route.path === '/videos' }"
              @click.prevent="handleVideosNavClick"
            >
              视频
            </router-link>
            <router-link to="/mall" class="videos-nav-link" :class="{ active: $route.path === '/mall' }">积分商城</router-link>
            <router-link v-if="userStore.isAdmin" to="/ops" class="videos-nav-link" :class="{ active: $route.path === '/ops' }">运维</router-link>
            <router-link to="/guide" class="videos-nav-link" :class="{ active: $route.path === '/guide' }">使用指南</router-link>
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
      <div class="videos-filter-section" v-if="chapters.length > 0 && !currentVideo">
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

      <!-- 页面内视频播放区（选中视频时显示） -->
      <section v-if="currentVideo" class="videos-player-section">
        <div class="videos-player-header">
          <button type="button" class="videos-back-btn" @click="closeVideo">
            <i class="fa fa-arrow-left"></i> 返回列表
          </button>
          <h2 class="videos-player-title">{{ currentVideo.name }}</h2>
          <div class="videos-player-actions">
            <button
              type="button"
              class="videos-summary-btn"
              :disabled="summaryLoading"
              @click.stop="openSummary"
            >
              {{ summaryLoading ? '加载中…' : '总结视频' }}
            </button>
          </div>
        </div>
        <div class="videos-player-wrap">
          <video
            ref="videoEl"
            :src="videoUrl"
            controls
            autoplay
            class="videos-player"
            @timeupdate="onVideoTimeUpdate"
          >
            您的浏览器不支持视频播放
          </video>
          <div v-if="currentSubtitle" class="videos-subtitle-overlay">
            {{ currentSubtitle }}
          </div>
        </div>
        <!-- 分段总结面板 -->
        <div v-if="showSummaryPanel" class="videos-summary-panel">
          <h4 class="videos-summary-title">分段总结</h4>
          <p v-if="summaryLoading" class="videos-summary-empty">加载中…</p>
          <div v-else-if="videoSummary && videoSummary.segments && videoSummary.segments.length" class="videos-summary-list">
            <button
              v-for="(seg, i) in videoSummary.segments"
              :key="i"
              type="button"
              class="videos-summary-item"
              @click="seekTo(seg.start_sec)"
            >
              <span class="videos-summary-time">{{ formatTimeRange(seg.start_sec, seg.end_sec) }}</span>
              <span class="videos-summary-text">{{ seg.title }}</span>
            </button>
          </div>
          <p v-else-if="videoSummaryError" class="videos-summary-error">{{ videoSummaryError }}</p>
          <p v-else class="videos-summary-empty">暂无总结，请运行脚本生成</p>
        </div>
      </section>

      <!-- 视频列表（无选中视频时显示） -->
      <div v-if="!currentVideo" class="videos-list-section">
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
              <video
                class="videos-card-video"
                :src="getVideoUrl(video.id)"
                preload="metadata"
                muted
                playsinline
              />
              <div class="videos-card-play-overlay">
                <span class="videos-card-play-triangle" aria-hidden="true"></span>
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
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { listVideos, getVideoUrl, getVideoCaption, getVideoSummary } from '@/apis/courseApi.js';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const handleLogout = () => { userStore.logout(); };
const handleSwitchAccount = () => { userStore.logout(); };

const chapters = ref([]);
const selectedChapter = ref(null);
const currentVideo = ref(null);
const videoEl = ref(null);
const captionSentences = ref([]);
const currentSubtitle = ref('');
const showSummaryPanel = ref(false);
const videoSummary = ref(null);
const videoSummaryError = ref('');
const summaryLoading = ref(false);

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
  syncVideoToQuery();
};

// 关闭视频，回到列表
function closeVideo() {
  currentVideo.value = null;
  videoEl.value = null;
  captionSentences.value = [];
  currentSubtitle.value = '';
  showSummaryPanel.value = false;
  videoSummary.value = null;
  videoSummaryError.value = '';
  if (route.query.video) {
    router.replace({ path: '/videos', query: {} });
  }
}

// 同步当前播放视频到 URL，便于刷新恢复；进入播放时 push 以支持浏览器后退回列表
function syncVideoToQuery() {
  const video = currentVideo.value;
  if (!video) {
    if (route.query.video) {
      router.replace({ path: '/videos', query: {} });
    }
    return;
  }
  const next = { path: '/videos', query: { video: String(video.id) } };
  if (route.query.video !== next.query.video) {
    const isEnteringPlayer = !route.query.video;
    if (isEnteringPlayer) {
      router.push(next);
    } else {
      router.replace(next);
    }
  }
}

// 点击顶部「视频」：若已在播放页则回列表，否则跳转到视频
function handleVideosNavClick() {
  if (route.path === '/videos' && currentVideo.value) {
    closeVideo();
  } else {
    router.push('/videos');
  }
}

// 浏览器后退时：若回到 /videos 且无 video 参数，则关闭播放器显示列表
watch(
  () => ({ path: route.path, video: route.query.video }),
  ({ path, video }) => {
    if (path === '/videos' && !video && currentVideo.value) {
      currentVideo.value = null;
    }
  }
);

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
};

// 格式化时间范围（秒 -> "0:00~1:30"）
function formatTimeRange(startSec, endSec) {
  const m1 = Math.floor(startSec / 60);
  const s1 = Math.floor(startSec % 60);
  const m2 = Math.floor(endSec / 60);
  const s2 = Math.floor(endSec % 60);
  return `${m1}:${String(s1).padStart(2, '0')}~${m2}:${String(s2).padStart(2, '0')}`;
}

// 视频 timeupdate：根据当前时间显示对应字幕（sentence_timestamps 中 start/end 为毫秒）
function onVideoTimeUpdate() {
  const video = videoEl.value;
  const list = captionSentences.value;
  if (!video || !list.length) {
    currentSubtitle.value = '';
    return;
  }
  const tMs = video.currentTime * 1000;
  const cur = list.find((s) => tMs >= s.start && tMs <= s.end);
  currentSubtitle.value = cur ? cur.text : '';
}

// 加载当前视频字幕
async function loadCaption() {
  if (!currentVideo.value) return;
  captionSentences.value = [];
  try {
    const data = await getVideoCaption(currentVideo.value.id);
    const list = data.sentence_timestamps || [];
    captionSentences.value = list.map((s) => ({ text: s.text || '', start: Number(s.start) || 0, end: Number(s.end) || 0 }));
  } catch (_) {
    captionSentences.value = [];
  }
}

// 打开总结面板并拉取总结
async function openSummary() {
  if (!currentVideo.value) return;
  showSummaryPanel.value = true;
  videoSummaryError.value = '';
  videoSummary.value = null;
  summaryLoading.value = true;
  try {
    const data = await getVideoSummary(currentVideo.value.id);
    videoSummary.value = data;
  } catch (e) {
    videoSummaryError.value = e?.message || '加载总结失败';
    videoSummary.value = null;
  } finally {
    summaryLoading.value = false;
  }
  // 展开后滚动到总结面板便于查看
  await nextTick();
  const panel = document.querySelector('.videos-summary-panel');
  if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 点击时间跳转到指定秒数
function seekTo(seconds) {
  const video = videoEl.value;
  if (!video) return;
  video.currentTime = Number(seconds) || 0;
  video.play();
}

// 当 currentVideo 变化时加载字幕
watch(currentVideo, (v) => {
  if (v) {
    loadCaption();
    showSummaryPanel.value = false;
    videoSummary.value = null;
    videoSummaryError.value = '';
  }
});

onMounted(async () => {
  await loadVideos();
  const videoId = route.query.video;
  if (videoId && chapters.value.length > 0) {
    const allVideos = chapters.value.flatMap((ch) => ch.videos);
    const video = allVideos.find((v) => String(v.id) === String(videoId));
    if (video) {
      currentVideo.value = video;
    }
  }
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

.videos-card-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
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
  z-index: 2;
  transition: all 0.3s ease;
}

.videos-card-play-triangle {
  width: 0;
  height: 0;
  margin-left: 4px;
  border-style: solid;
  border-width: 12px 0 12px 22px;
  border-color: transparent transparent transparent #fff;
}

.videos-card:hover .videos-card-play-overlay {
  background-color: var(--primary-color);
  transform: translate(-50%, -50%) scale(1.1);
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

/* 页面内视频播放区 */
.videos-player-section {
  margin-bottom: 32px;
  background: var(--white);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-light);
}

.videos-player-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--gray-200);
}

.videos-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 14px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--white);
  color: var(--gray-600);
  cursor: pointer;
}

.videos-back-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.videos-player-title {
  flex: 1;
  min-width: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0;
}

.videos-player-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.videos-summary-btn {
  padding: 6px 14px;
  font-size: 14px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--white);
  color: var(--gray-600);
  cursor: pointer;
}

.videos-summary-btn:hover:not(:disabled) {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.videos-summary-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.videos-player-wrap {
  position: relative;
  width: 100%;
  background: #000;
}

.videos-player {
  width: 100%;
  display: block;
  max-height: 70vh;
}

.videos-subtitle-overlay {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  max-width: 90%;
  padding: 6px 12px;
  font-size: 16px;
  line-height: 1.4;
  border-radius: 4px;
  text-align: center;
  pointer-events: none;
  color: #fff;
  background: rgba(0, 0, 0, 0.4);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.videos-summary-panel {
  padding: 16px 20px;
  border-top: 1px solid var(--gray-200);
  max-height: 280px;
  overflow-y: auto;
  background: var(--gray-50);
}

.videos-summary-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0 0 12px 0;
}

.videos-summary-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.videos-summary-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 10px;
  text-align: left;
  border: none;
  border-radius: 6px;
  background: var(--white);
  cursor: pointer;
  font-size: 14px;
  color: var(--dark-text);
  transition: background 0.2s, color 0.2s;
}

.videos-summary-item:hover {
  background: var(--light-bg);
  color: var(--primary-color);
}

.videos-summary-time {
  flex-shrink: 0;
  color: var(--gray-500);
  font-variant-numeric: tabular-nums;
}

.videos-summary-text {
  flex: 1;
}

.videos-summary-error,
.videos-summary-empty {
  margin: 0;
  font-size: 14px;
  color: var(--gray-500);
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
  
  .videos-player-section {
    border-radius: 0;
  }
  
  .videos-player {
    max-height: 50vh;
  }
}
</style>
