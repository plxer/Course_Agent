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
            <router-link to="/reading" class="guide-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
            <router-link to="/videos" class="guide-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
            <router-link to="/exercises" class="guide-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>

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
          本平台为天津大学《计算机网络》课程数智化学习平台，提供对话答疑、课本伴读、视频学习与习题推荐等功能，帮助您更好地掌握课程内容。
        </p>
      </div>

      <!-- 登录与账号 -->
      <section class="guide-section">
        <h2 class="guide-section-title">登录与账号</h2>
        <div class="guide-section-content">
          <p class="guide-section-p">使用前请先注册并登录。登录后可在页面右上角看到用户名、积分（若当前页面有显示）、切换账号与退出按钮。切换账号可更换为其他账号登录，退出则清除当前登录状态。</p>
          <div class="guide-actions">
            <template v-if="!userStore.isLoggedIn">
              <button class="guide-action-btn primary" @click="navigateTo('/login')">登录</button>
              <button class="guide-action-btn" @click="navigateTo('/register')">注册新账号</button>
            </template>
            <template v-else>
              <span class="guide-status-text">当前已登录: {{ userStore.username || userStore.userIdLogin }}</span>
              <button class="guide-action-btn" @click="handleSwitchAccount">切换账号</button>
              <button class="guide-action-btn" @click="handleLogout">退出登录</button>
            </template>
          </div>
        </div>
      </section>

      <!-- 详细功能说明 -->
      <section class="guide-section">
        <h2 class="guide-section-title">功能详解</h2>

        <div class="guide-detail-item">
          <h3 class="guide-detail-title">
            <span class="guide-detail-icon">💬</span>
            智能对话
            <button class="guide-goto-btn" @click="navigateTo('/conversation')">进入</button>
          </h3>
          <p class="guide-detail-desc">在顶部导航点击「对话」进入课程智能体。您可以像与助教聊天一样提问，智能体会基于课程教材与知识库回答。支持多轮对话，可新建多个对话分别讨论不同主题。开启智能体功能后，回答中会标注参考来源，方便您回溯课本。</p>
          <ul class="guide-feature-list">
            <li>支持多轮对话，保持上下文连贯</li>
            <li>可创建多个对话，分类讨论不同主题</li>
            <li>回答附带参考来源，便于追溯知识点</li>
            <li>支持图片上传和视觉理解</li>
          </ul>
        </div>

        <div class="guide-detail-item">
          <h3 class="guide-detail-title">
            <span class="guide-detail-icon">📚</span>
            课本伴读
            <button class="guide-goto-btn" @click="navigateTo('/reading')">进入</button>
          </h3>
          <p class="guide-detail-desc">「课本伴读」提供与教材对应的智能伴读。选择教材后可按章节阅读，在阅读过程中可随时向智能体提问当前页或相关知识点，便于边读边问、加深理解。</p>
          <ul class="guide-feature-list">
            <li>支持多本教材切换</li>
            <li>按章节导航，快速定位</li>
            <li>页内选中提问，精准解答</li>
            <li>阅读进度自动保存</li>
          </ul>
        </div>

        <div class="guide-detail-item">
          <h3 class="guide-detail-title">
            <span class="guide-detail-icon">🎥</span>
            视频学习
            <button class="guide-goto-btn" @click="navigateTo('/videos')">进入</button>
          </h3>
          <p class="guide-detail-desc">「视频」页面按课程章节组织视频资源。选择章节后即可观看对应讲解视频，适合配合课本与习题巩固学习。</p>
          <ul class="guide-feature-list">
            <li>按章节分类整理视频</li>
            <li>支持视频播放和进度控制</li>
            <li>图文结合，加深理解</li>
          </ul>
        </div>

        <div class="guide-detail-item">
          <h3 class="guide-detail-title">
            <span class="guide-detail-icon">✏️</span>
            习题推荐
            <button class="guide-goto-btn" @click="navigateTo('/exercises')">进入</button>
          </h3>
          <p class="guide-detail-desc">「习题推荐」根据您的学习情况推荐练习题。支持错题分析，帮助您针对薄弱知识点加强练习。</p>
          <ul class="guide-feature-list">
            <li>智能推荐个性化习题</li>
            <li>支持选择题、多选题、简答题等多种题型</li>
            <li>错题本功能，记录错题便于复习</li>
            <li>答对获得积分，可兑换称号</li>
          </ul>
        </div>

        <div class="guide-detail-item" v-if="userStore.isAdmin">
          <h3 class="guide-detail-title">
            <span class="guide-detail-icon">⚙️</span>
            运维管理
            <button class="guide-goto-btn" @click="navigateTo('/ops')">进入</button>
          </h3>
          <p class="guide-detail-desc">「运维」页面为管理员提供系统监控、用户管理、知识库管理等高级功能。</p>
          <ul class="guide-feature-list">
            <li>系统运行状态监控</li>
            <li>用户和部门管理</li>
            <li>知识库配置和维护</li>
            <li>用户反馈处理</li>
          </ul>
        </div>
      </section>

      <!-- 用户反馈 -->
      <section class="guide-section">
        <h2 class="guide-section-title">
          <span>意见反馈</span>
          <span v-if="userStore.isAdmin" class="guide-admin-badge" @click="navigateTo('/feedback-admin')">管理反馈</span>
        </h2>
        <div class="guide-feedback-section">
          <p class="guide-section-p">如果您在使用过程中遇到问题，或有任何建议和意见，欢迎通过下方表单提交反馈。我们将认真对待每一条反馈，持续改进平台体验。</p>

          <form class="guide-feedback-form" @submit.prevent="submitFeedback">
            <div class="guide-form-row">
              <div class="guide-form-item">
                <label class="guide-form-label">反馈类型</label>
                <select v-model="feedbackForm.category" class="guide-form-select" required>
                  <option value="general">一般反馈</option>
                  <option value="bug">Bug 报告</option>
                  <option value="feature">功能建议</option>
                  <option value="improvement">体验优化</option>
                </select>
              </div>
              <div class="guide-form-item">
                <label class="guide-form-label">联系方式（选填）</label>
                <input
                  v-model="feedbackForm.contact"
                  type="text"
                  class="guide-form-input"
                  placeholder="手机号或邮箱，便于我们联系您"
                  maxlength="255"
                />
              </div>
            </div>
            <div class="guide-form-item">
              <label class="guide-form-label">反馈标题 <span class="guide-required">*</span></label>
              <input
                v-model="feedbackForm.title"
                type="text"
                class="guide-form-input"
                placeholder="请简要描述您的问题或建议"
                maxlength="255"
                required
              />
            </div>
            <div class="guide-form-item">
              <label class="guide-form-label">详细描述 <span class="guide-required">*</span></label>
              <textarea
                v-model="feedbackForm.content"
                class="guide-form-textarea"
                placeholder="请详细描述您遇到的问题、期望的功能或改进建议..."
                rows="5"
                maxlength="5000"
                required
              ></textarea>
              <span class="guide-form-hint">已输入 {{ feedbackForm.content.length }}/5000 字</span>
            </div>
            <div class="guide-form-actions">
              <button type="submit" class="guide-submit-btn" :disabled="submitting">
                <span v-if="submitting">提交中...</span>
                <span v-else>提交反馈</span>
              </button>
            </div>
          </form>

          <!-- 提交成功提示 -->
          <div v-if="submitSuccess" class="guide-success-message">
            <span class="guide-success-icon">✓</span>
            <span>感谢您的反馈！我们会尽快处理并回复。</span>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { submitFeedback as apiSubmitFeedback } from '@/apis/feedback_api'
import { message } from 'ant-design-vue'

const router = useRouter()
const userStore = useUserStore()

const submitting = ref(false)
const submitSuccess = ref(false)

const feedbackForm = reactive({
  category: 'general',
  title: '',
  content: '',
  contact: ''
})

function navigateTo(path) {
  router.push(path)
}

function handleSwitchAccount() {
  userStore.logout()
}

function handleLogout() {
  userStore.logout()
}

async function submitFeedback() {
  if (!feedbackForm.title.trim()) {
    message.error('请输入反馈标题')
    return
  }
  if (!feedbackForm.content.trim()) {
    message.error('请输入反馈内容')
    return
  }

  submitting.value = true
  try {
    await apiSubmitFeedback({
      category: feedbackForm.category,
      title: feedbackForm.title.trim(),
      content: feedbackForm.content.trim(),
      contact: feedbackForm.contact.trim() || null
    })

    submitSuccess.value = true
    message.success('反馈提交成功！')

    // 重置表单
    feedbackForm.category = 'general'
    feedbackForm.title = ''
    feedbackForm.content = ''
    feedbackForm.contact = ''

    // 3秒后隐藏成功提示
    setTimeout(() => {
      submitSuccess.value = false
    }, 3000)
  } catch (error) {
    console.error('提交反馈失败:', error)
    message.error(error.message || '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
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
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-section-p {
  font-size: 15px;
  color: var(--gray-600);
  line-height: 1.7;
  margin: 0;
}

/* 功能详解 */
.guide-section-content {
  margin-top: 16px;
}

.guide-detail-item {
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
}

.guide-detail-item:last-child {
  margin-bottom: 0;
}

.guide-detail-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--dark-text);
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-detail-icon {
  font-size: 20px;
}

.guide-goto-btn {
  margin-left: auto;
  font-size: 13px;
  padding: 4px 12px;
  border: 1px solid var(--primary-color);
  border-radius: 4px;
  background: transparent;
  color: var(--primary-color);
  cursor: pointer;
  transition: all 0.2s;
}

.guide-goto-btn:hover {
  background: var(--primary-color);
  color: var(--white);
}

.guide-detail-desc {
  font-size: 14px;
  color: var(--gray-600);
  line-height: 1.6;
  margin: 0 0 12px 0;
}

.guide-feature-list {
  margin: 0;
  padding-left: 20px;
}

.guide-feature-list li {
  font-size: 14px;
  color: var(--gray-600);
  line-height: 1.6;
  margin-bottom: 6px;
}

.guide-feature-list li:last-child {
  margin-bottom: 0;
}

/* 操作按钮 */
.guide-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--gray-200);
}

.guide-action-btn {
  font-size: 14px;
  padding: 8px 16px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--white);
  color: var(--gray-600);
  cursor: pointer;
  transition: all 0.2s;
}

.guide-action-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.guide-action-btn.primary {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: var(--white);
}

.guide-action-btn.primary:hover {
  background: #153e68;
}

.guide-status-text {
  font-size: 14px;
  color: var(--gray-600);
  margin-right: 8px;
}

/* 反馈区域 */
.guide-feedback-section {
  margin-top: 16px;
}

.guide-admin-badge {
  font-size: 12px;
  padding: 2px 8px;
  background: var(--primary-color);
  color: var(--white);
  border-radius: 4px;
  cursor: pointer;
  margin-left: auto;
  transition: opacity 0.2s;
}

.guide-admin-badge:hover {
  opacity: 0.9;
}

.guide-feedback-form {
  margin-top: 20px;
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  padding: 20px;
}

.guide-form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.guide-form-item {
  margin-bottom: 16px;
}

.guide-form-item:last-child {
  margin-bottom: 0;
}

.guide-form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--dark-text);
  margin-bottom: 8px;
}

.guide-required {
  color: #e53e3e;
}

.guide-form-input,
.guide-form-select,
.guide-form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  font-size: 14px;
  color: var(--dark-text);
  background: var(--white);
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.guide-form-input:focus,
.guide-form-select:focus,
.guide-form-textarea:focus {
  outline: none;
  border-color: var(--primary-color);
}

.guide-form-textarea {
  resize: vertical;
  min-height: 120px;
  font-family: inherit;
}

.guide-form-hint {
  display: block;
  font-size: 12px;
  color: var(--gray-500);
  margin-top: 4px;
  text-align: right;
}

.guide-form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.guide-submit-btn {
  font-size: 14px;
  padding: 10px 24px;
  background: var(--primary-color);
  color: var(--white);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.guide-submit-btn:hover:not(:disabled) {
  background: #153e68;
}

.guide-submit-btn:disabled {
  background: var(--gray-500);
  cursor: not-allowed;
}

.guide-success-message {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  padding: 16px;
  background: #f0fff4;
  border: 1px solid #68d391;
  border-radius: 6px;
  color: #276749;
  font-size: 14px;
}

.guide-success-icon {
  font-size: 18px;
  font-weight: bold;
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

  .guide-form-row {
    grid-template-columns: 1fr;
  }

  .guide-actions {
    flex-wrap: wrap;
  }

  .guide-detail-title {
    flex-wrap: wrap;
  }

  .guide-goto-btn {
    margin-left: 0;
    margin-top: 8px;
    width: 100%;
  }
}
</style>
