<template>
  <div class="feedback-admin-container course-page">
    <CourseTopbar @logout="handleLogout" @switch-account="handleSwitchAccount" />

    <main class="feedback-admin-main page-shell">
      <div class="feedback-admin-content">
        <CoursePageHero
          eyebrow="Feedback"
          title="用户反馈管理"
          subtitle="查看、筛选和处理课程平台的反馈与建议。"
        />

        <!-- 统计卡片 -->
        <div class="feedback-stats-grid">
          <div class="feedback-stat-card">
            <div class="feedback-stat-value">{{ stats.total }}</div>
            <div class="feedback-stat-label">总反馈数</div>
          </div>
          <div class="feedback-stat-card pending">
            <div class="feedback-stat-value">{{ stats.pending }}</div>
            <div class="feedback-stat-label">待处理</div>
          </div>
          <div class="feedback-stat-card processing">
            <div class="feedback-stat-value">{{ stats.processing }}</div>
            <div class="feedback-stat-label">处理中</div>
          </div>
          <div class="feedback-stat-card resolved">
            <div class="feedback-stat-value">{{ stats.resolved }}</div>
            <div class="feedback-stat-label">已解决</div>
          </div>
          <div class="feedback-stat-card closed">
            <div class="feedback-stat-value">{{ stats.closed }}</div>
            <div class="feedback-stat-label">已关闭</div>
          </div>
        </div>

        <!-- 筛选和搜索 -->
        <div class="feedback-filter-section">
          <div class="feedback-filter-group">
            <label class="feedback-filter-label">状态筛选:</label>
            <select v-model="filterStatus" class="feedback-filter-select" @change="loadFeedbacks">
              <option value="">全部</option>
              <option value="pending">待处理</option>
              <option value="processing">处理中</option>
              <option value="resolved">已解决</option>
              <option value="closed">已关闭</option>
            </select>
          </div>
          <div class="feedback-filter-group">
            <label class="feedback-filter-label">类别筛选:</label>
            <select v-model="filterCategory" class="feedback-filter-select" @change="loadFeedbacks">
              <option value="">全部</option>
              <option value="general">一般反馈</option>
              <option value="bug">Bug 报告</option>
              <option value="feature">功能建议</option>
              <option value="improvement">体验优化</option>
            </select>
          </div>
          <button class="feedback-refresh-btn" @click="loadFeedbacks" :disabled="loading">
            <span v-if="loading">加载中...</span>
            <span v-else>刷新</span>
          </button>
        </div>

        <!-- 反馈列表 -->
        <div class="feedback-list-section">
          <div v-if="loading" class="feedback-loading">加载中...</div>
          <div v-else-if="feedbacks.length === 0" class="feedback-empty">暂无反馈数据</div>
          <div v-else class="feedback-list">
            <div
              v-for="feedback in feedbacks"
              :key="feedback.id"
              class="feedback-item"
              :class="`status-${feedback.status}`"
              @click="openDetail(feedback)"
            >
              <div class="feedback-item-header">
                <div class="feedback-item-info">
                  <span class="feedback-item-id">#{{ feedback.id }}</span>
                  <span class="feedback-item-category" :class="feedback.category">
                    {{ categoryText(feedback.category) }}
                  </span>
                  <span class="feedback-item-status" :class="feedback.status">
                    {{ statusText(feedback.status) }}
                  </span>
                </div>
                <span class="feedback-item-time">{{ formatTime(feedback.created_at) }}</span>
              </div>
              <div class="feedback-item-title">{{ feedback.title }}</div>
              <div class="feedback-item-preview">{{ truncateContent(feedback.content, 100) }}</div>
              <div class="feedback-item-footer">
                <span class="feedback-item-user">
                  用户: {{ feedback.username || '匿名用户' }}
                  <span v-if="feedback.contact" class="feedback-item-contact"
                    >({{ feedback.contact }})</span
                  >
                </span>
                <span v-if="feedback.admin_reply" class="feedback-item-replied">已回复</span>
              </div>
            </div>
          </div>

          <!-- 分页 -->
          <div v-if="total > pageSize" class="feedback-pagination">
            <button
              class="feedback-page-btn"
              :disabled="currentPage === 1"
              @click="changePage(currentPage - 1)"
            >
              上一页
            </button>
            <span class="feedback-page-info">第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
            <button
              class="feedback-page-btn"
              :disabled="currentPage >= totalPages"
              @click="changePage(currentPage + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- 详情弹窗 -->
    <div v-if="selectedFeedback" class="feedback-modal-overlay" @click.self="closeDetail">
      <div class="feedback-modal">
        <div class="feedback-modal-header">
          <h3 class="feedback-modal-title">反馈详情 #{{ selectedFeedback.id }}</h3>
          <button class="feedback-modal-close" @click="closeDetail">×</button>
        </div>
        <div class="feedback-modal-body">
          <div class="feedback-detail-section">
            <div class="feedback-detail-row">
              <span class="feedback-detail-label">类别:</span>
              <span class="feedback-detail-category" :class="selectedFeedback.category">
                {{ categoryText(selectedFeedback.category) }}
              </span>
            </div>
            <div class="feedback-detail-row">
              <span class="feedback-detail-label">状态:</span>
              <select
                v-model="selectedFeedback.status"
                class="feedback-detail-status-select"
                @change="updateStatus"
              >
                <option value="pending">待处理</option>
                <option value="processing">处理中</option>
                <option value="resolved">已解决</option>
                <option value="closed">已关闭</option>
              </select>
            </div>
            <div class="feedback-detail-row">
              <span class="feedback-detail-label">提交用户:</span>
              <span>{{ selectedFeedback.username || '匿名用户' }}</span>
            </div>
            <div v-if="selectedFeedback.contact" class="feedback-detail-row">
              <span class="feedback-detail-label">联系方式:</span>
              <span>{{ selectedFeedback.contact }}</span>
            </div>
            <div class="feedback-detail-row">
              <span class="feedback-detail-label">提交时间:</span>
              <span>{{ formatTime(selectedFeedback.created_at) }}</span>
            </div>
          </div>

          <div class="feedback-detail-section">
            <div class="feedback-detail-label">标题:</div>
            <div class="feedback-detail-content">{{ selectedFeedback.title }}</div>
          </div>

          <div class="feedback-detail-section">
            <div class="feedback-detail-label">详细内容:</div>
            <div class="feedback-detail-content">{{ selectedFeedback.content }}</div>
          </div>

          <div class="feedback-detail-section">
            <div class="feedback-detail-label">管理员回复:</div>
            <textarea
              v-model="replyContent"
              class="feedback-reply-textarea"
              rows="4"
              placeholder="输入回复内容..."
            ></textarea>
            <div class="feedback-reply-actions">
              <button class="feedback-reply-btn" @click="submitReply" :disabled="replying">
                <span v-if="replying">提交中...</span>
                <span v-else>提交回复</span>
              </button>
            </div>
            <div v-if="selectedFeedback.admin_reply" class="feedback-existing-reply">
              <div class="feedback-existing-reply-header">
                <span
                  >历史回复 ({{ selectedFeedback.replied_by }} -
                  {{ formatTime(selectedFeedback.replied_at) }})</span
                >
              </div>
              <div class="feedback-existing-reply-content">{{ selectedFeedback.admin_reply }}</div>
            </div>
          </div>
        </div>
        <div class="feedback-modal-footer">
          <button class="feedback-modal-btn danger" @click="deleteFeedback" :disabled="deleting">
            <span v-if="deleting">删除中...</span>
            <span v-else>删除反馈</span>
          </button>
          <button class="feedback-modal-btn primary" @click="closeDetail">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import CourseTopbar from '@/components/course/CourseTopbar.vue'
import CoursePageHero from '@/components/course/CoursePageHero.vue'
import { useUserStore } from '@/stores/user'
import { message } from 'ant-design-vue'
import {
  getAllFeedbacks,
  getFeedbackStats,
  updateFeedback,
  deleteFeedback as apiDeleteFeedback
} from '@/apis/feedback_api'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const feedbacks = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 10
const filterStatus = ref('')
const filterCategory = ref('')

const selectedFeedback = ref(null)
const replyContent = ref('')
const replying = ref(false)
const deleting = ref(false)

const stats = reactive({
  total: 0,
  pending: 0,
  processing: 0,
  resolved: 0,
  closed: 0
})

const totalPages = computed(() => Math.ceil(total.value / pageSize))

function categoryText(category) {
  const map = {
    general: '一般反馈',
    bug: 'Bug 报告',
    feature: '功能建议',
    improvement: '体验优化'
  }
  return map[category] || category
}

function statusText(status) {
  const map = {
    pending: '待处理',
    processing: '处理中',
    resolved: '已解决',
    closed: '已关闭'
  }
  return map[status] || status
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function truncateContent(content, maxLength) {
  if (!content) return ''
  return content.length > maxLength ? content.slice(0, maxLength) + '...' : content
}

async function loadFeedbacks() {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize,
      limit: pageSize
    }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterCategory.value) params.category = filterCategory.value

    const response = await getAllFeedbacks(params)
    feedbacks.value = response.items
    total.value = response.total
  } catch (error) {
    console.error('加载反馈失败:', error)
    message.error('加载反馈失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await getFeedbackStats()
    stats.total = response.total
    stats.pending = response.pending
    stats.processing = response.processing
    stats.resolved = response.resolved
    stats.closed = response.closed
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

function changePage(page) {
  currentPage.value = page
  loadFeedbacks()
}

function openDetail(feedback) {
  selectedFeedback.value = { ...feedback }
  replyContent.value = feedback.admin_reply || ''
}

function closeDetail() {
  selectedFeedback.value = null
  replyContent.value = ''
}

async function updateStatus() {
  if (!selectedFeedback.value) return
  try {
    await updateFeedback(selectedFeedback.value.id, {
      status: selectedFeedback.value.status
    })
    message.success('状态已更新')
    loadFeedbacks()
    loadStats()
  } catch (error) {
    console.error('更新状态失败:', error)
    message.error('更新状态失败: ' + error.message)
  }
}

async function submitReply() {
  if (!selectedFeedback.value) return
  if (!replyContent.value.trim()) {
    message.error('请输入回复内容')
    return
  }

  replying.value = true
  try {
    await updateFeedback(selectedFeedback.value.id, {
      admin_reply: replyContent.value.trim()
    })
    message.success('回复已提交')
    selectedFeedback.value.admin_reply = replyContent.value.trim()
    loadFeedbacks()
  } catch (error) {
    console.error('提交回复失败:', error)
    message.error('提交回复失败: ' + error.message)
  } finally {
    replying.value = false
  }
}

async function deleteFeedback() {
  if (!selectedFeedback.value) return
  if (!confirm('确定要删除这条反馈吗？此操作不可恢复。')) return

  deleting.value = true
  try {
    await apiDeleteFeedback(selectedFeedback.value.id)
    message.success('反馈已删除')
    closeDetail()
    loadFeedbacks()
    loadStats()
  } catch (error) {
    console.error('删除反馈失败:', error)
    message.error('删除反馈失败: ' + error.message)
  } finally {
    deleting.value = false
  }
}

function handleLogout() {
  userStore.logout()
}

onMounted(() => {
  loadFeedbacks()
  loadStats()
})
</script>

<style lang="less" scoped>
.feedback-admin-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: #f9fafb;
  min-height: 100vh;
  color: #2d3748;
}

.feedback-admin-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e5e7eb;
}

.feedback-admin-header-content {
  width: 100%;
  padding: 12px 24px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.feedback-admin-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.feedback-admin-logo-text {
  color: #1a365d;
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.feedback-admin-right {
  display: flex;
  align-items: center;
  gap: 32px;
}

.feedback-admin-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.feedback-admin-nav-link {
  color: #6b7280;
  text-decoration: none;
  font-size: 16px;
  transition: color 0.2s;
}

.feedback-admin-nav-link:hover {
  color: #1a365d;
}

.feedback-admin-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.feedback-admin-username {
  font-size: 14px;
  color: #4b5563;
}

.feedback-admin-auth-btn {
  font-size: 14px;
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #ffffff;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s;
}

.feedback-admin-auth-btn:hover {
  color: #1a365d;
  border-color: #1a365d;
}

.feedback-admin-main {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
  box-sizing: border-box;
}

.feedback-admin-content {
  background: #ffffff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.feedback-admin-title-section {
  margin-bottom: 24px;
}

.feedback-admin-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a365d;
  margin: 0 0 8px 0;
}

.feedback-admin-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

/* 统计卡片 */
.feedback-stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.feedback-stat-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.feedback-stat-card.pending {
  background: #fffbeb;
  border-color: #fbbf24;
}

.feedback-stat-card.processing {
  background: #eff6ff;
  border-color: #60a5fa;
}

.feedback-stat-card.resolved {
  background: #ecfdf5;
  border-color: #34d399;
}

.feedback-stat-card.closed {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.feedback-stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a365d;
  margin-bottom: 4px;
}

.feedback-stat-card.pending .feedback-stat-value {
  color: #d97706;
}

.feedback-stat-card.processing .feedback-stat-value {
  color: #2563eb;
}

.feedback-stat-card.resolved .feedback-stat-value {
  color: #059669;
}

.feedback-stat-card.closed .feedback-stat-value {
  color: #4b5563;
}

.feedback-stat-label {
  font-size: 14px;
  color: #6b7280;
}

/* 筛选 */
.feedback-filter-section {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 6px;
}

.feedback-filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.feedback-filter-label {
  font-size: 14px;
  color: #4b5563;
}

.feedback-filter-select {
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  background: #ffffff;
  cursor: pointer;
}

.feedback-refresh-btn {
  margin-left: auto;
  padding: 8px 16px;
  background: #1a365d;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.feedback-refresh-btn:hover:not(:disabled) {
  background: #153e68;
}

.feedback-refresh-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

/* 列表 */
.feedback-list-section {
  min-height: 200px;
}

.feedback-loading,
.feedback-empty {
  text-align: center;
  padding: 60px 20px;
  color: #6b7280;
  font-size: 14px;
}

.feedback-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feedback-item {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.feedback-item:hover {
  border-color: #1a365d;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.feedback-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.feedback-item-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.feedback-item-id {
  font-size: 13px;
  color: #9ca3af;
  font-family: monospace;
}

.feedback-item-category {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.feedback-item-category.general {
  background: #eff6ff;
  color: #2563eb;
}

.feedback-item-category.bug {
  background: #fef2f2;
  color: #dc2626;
}

.feedback-item-category.feature {
  background: #f5f3ff;
  color: #7c3aed;
}

.feedback-item-category.improvement {
  background: #f0fdf4;
  color: #16a34a;
}

.feedback-item-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.feedback-item-status.pending {
  background: #fffbeb;
  color: #d97706;
}

.feedback-item-status.processing {
  background: #eff6ff;
  color: #2563eb;
}

.feedback-item-status.resolved {
  background: #ecfdf5;
  color: #059669;
}

.feedback-item-status.closed {
  background: #f3f4f6;
  color: #4b5563;
}

.feedback-item-time {
  font-size: 13px;
  color: #9ca3af;
}

.feedback-item-title {
  font-size: 15px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 8px;
}

.feedback-item-preview {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.5;
  margin-bottom: 12px;
}

.feedback-item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feedback-item-user {
  font-size: 13px;
  color: #6b7280;
}

.feedback-item-contact {
  color: #9ca3af;
}

.feedback-item-replied {
  font-size: 12px;
  padding: 2px 8px;
  background: #ecfdf5;
  color: #059669;
  border-radius: 4px;
}

/* 分页 */
.feedback-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.feedback-page-btn {
  padding: 8px 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s;
}

.feedback-page-btn:hover:not(:disabled) {
  border-color: #1a365d;
  color: #1a365d;
}

.feedback-page-btn:disabled {
  background: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}

.feedback-page-info {
  font-size: 14px;
  color: #6b7280;
}

/* 弹窗 */
.feedback-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.feedback-modal {
  background: #ffffff;
  border-radius: 8px;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.feedback-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
}

.feedback-modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
}

.feedback-modal-close {
  font-size: 24px;
  color: #9ca3af;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.feedback-modal-close:hover {
  background: #f3f4f6;
  color: #4b5563;
}

.feedback-modal-body {
  padding: 20px;
}

.feedback-detail-section {
  margin-bottom: 20px;
}

.feedback-detail-section:last-child {
  margin-bottom: 0;
}

.feedback-detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.feedback-detail-row:last-child {
  margin-bottom: 0;
}

.feedback-detail-label {
  font-size: 14px;
  color: #6b7280;
  min-width: 80px;
}

.feedback-detail-category {
  font-size: 13px;
  padding: 2px 10px;
  border-radius: 4px;
  font-weight: 500;
}

.feedback-detail-category.general {
  background: #eff6ff;
  color: #2563eb;
}

.feedback-detail-category.bug {
  background: #fef2f2;
  color: #dc2626;
}

.feedback-detail-category.feature {
  background: #f5f3ff;
  color: #7c3aed;
}

.feedback-detail-category.improvement {
  background: #f0fdf4;
  color: #16a34a;
}

.feedback-detail-status-select {
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  font-size: 14px;
  background: #ffffff;
  cursor: pointer;
}

.feedback-detail-content {
  font-size: 14px;
  color: #2d3748;
  line-height: 1.6;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
  white-space: pre-wrap;
}

.feedback-reply-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  min-height: 100px;
  box-sizing: border-box;
}

.feedback-reply-textarea:focus {
  outline: none;
  border-color: #1a365d;
}

.feedback-reply-actions {
  margin-top: 12px;
}

.feedback-reply-btn {
  padding: 10px 20px;
  background: #1a365d;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.feedback-reply-btn:hover:not(:disabled) {
  background: #153e68;
}

.feedback-reply-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.feedback-existing-reply {
  margin-top: 16px;
  padding: 12px;
  background: #ecfdf5;
  border-radius: 6px;
}

.feedback-existing-reply-header {
  font-size: 13px;
  color: #059669;
  font-weight: 500;
  margin-bottom: 8px;
}

.feedback-existing-reply-content {
  font-size: 14px;
  color: #2d3748;
  line-height: 1.6;
  white-space: pre-wrap;
}

.feedback-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
}

.feedback-modal-btn {
  padding: 10px 20px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.feedback-modal-btn.primary {
  background: #1a365d;
  color: #ffffff;
  border-color: #1a365d;
}

.feedback-modal-btn.primary:hover {
  background: #153e68;
}

.feedback-modal-btn.danger {
  background: #fef2f2;
  color: #dc2626;
  border-color: #fecaca;
  margin-right: auto;
}

.feedback-modal-btn.danger:hover:not(:disabled) {
  background: #fee2e2;
}

.feedback-modal-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .feedback-admin-header-content {
    flex-wrap: wrap;
    gap: 12px;
  }

  .feedback-admin-right {
    width: 100%;
    justify-content: space-between;
  }

  .feedback-admin-nav {
    flex-wrap: wrap;
    gap: 12px;
  }

  .feedback-stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .feedback-filter-section {
    flex-wrap: wrap;
  }

  .feedback-filter-group {
    flex: 1;
    min-width: 140px;
  }

  .feedback-filter-select {
    flex: 1;
  }

  .feedback-refresh-btn {
    margin-left: 0;
    width: 100%;
  }

  .feedback-item-header {
    flex-wrap: wrap;
    gap: 8px;
  }

  .feedback-modal {
    max-height: 95vh;
  }
}
</style>
