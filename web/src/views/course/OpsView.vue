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
            <router-link to="/reading" class="ops-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
            <router-link to="/videos" class="ops-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
            <router-link to="/exercises" class="ops-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>

            <router-link v-if="userStore.isAdmin" to="/ops" class="ops-nav-link" :class="{ active: $route.path === '/ops' }">运维</router-link>
            <router-link to="/guide" class="ops-nav-link" :class="{ active: $route.path === '/guide' }">使用指南</router-link>
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

      <!-- 用户反馈区域 -->
      <div class="ops-feedback-section">
        <a-card class="feedback-card" title="用户反馈" :loading="loadingFeedbacks">
          <template #extra>
            <a-space>
              <a-select v-model:value="feedbackStatusFilter" placeholder="状态" size="small" style="width: 100px" @change="loadFeedbacks">
                <a-select-option value="">全部</a-select-option>
                <a-select-option value="pending">待处理</a-select-option>
                <a-select-option value="processing">处理中</a-select-option>
                <a-select-option value="resolved">已解决</a-select-option>
                <a-select-option value="closed">已关闭</a-select-option>
              </a-select>
              <a-select v-model:value="feedbackCategoryFilter" placeholder="类别" size="small" style="width: 100px" @change="loadFeedbacks">
                <a-select-option value="">全部</a-select-option>
                <a-select-option value="general">一般</a-select-option>
                <a-select-option value="bug">Bug</a-select-option>
                <a-select-option value="feature">功能建议</a-select-option>
                <a-select-option value="improvement">改进建议</a-select-option>
              </a-select>
              <a-button size="small" @click="loadFeedbacks" :loading="loadingFeedbacks">刷新</a-button>
            </a-space>
          </template>

          <a-table
            :columns="feedbackColumns"
            :data-source="feedbacks"
            :loading="loadingFeedbacks"
            :pagination="feedbackPagination"
            @change="handleFeedbackTableChange"
            row-key="id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'category'">
                <a-tag :color="getCategoryColor(record.category)" size="small">
                  {{ getCategoryLabel(record.category) }}
                </a-tag>
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="getStatusColor(record.status)" size="small">
                  {{ getStatusLabel(record.status) }}
                </a-tag>
              </template>
              <template v-if="column.key === 'title'">
                <a @click="handleViewFeedbackDetail(record)" class="feedback-title">{{ record.title }}</a>
              </template>
              <template v-if="column.key === 'username'">
                <span class="user-display">{{ record.username || '匿名用户' }}</span>
              </template>
              <template v-if="column.key === 'created_at'">
                <span class="time-text">{{ formatDate(record.created_at) }}</span>
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="link" size="small" @click="handleViewFeedbackDetail(record)">详情</a-button>
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
    </main>

    <!-- 反馈详情弹窗 -->
    <a-modal
      v-model:open="feedbackDetailModalOpen"
      title="反馈详情"
      width="600px"
      :footer="null"
      destroy-on-close
    >
      <template v-if="selectedFeedback">
        <div class="feedback-detail">
          <div class="feedback-detail-item">
            <span class="detail-label">标题</span>
            <span class="detail-value">{{ selectedFeedback.title }}</span>
          </div>
          <div class="feedback-detail-item">
            <span class="detail-label">用户</span>
            <span class="detail-value">{{ selectedFeedback.username || '匿名用户' }}</span>
          </div>
          <div class="feedback-detail-item">
            <span class="detail-label">类别</span>
            <a-tag :color="getCategoryColor(selectedFeedback.category)" size="small">
              {{ getCategoryLabel(selectedFeedback.category) }}
            </a-tag>
          </div>
          <div class="feedback-detail-item">
            <span class="detail-label">状态</span>
            <a-tag :color="getStatusColor(selectedFeedback.status)" size="small">
              {{ getStatusLabel(selectedFeedback.status) }}
            </a-tag>
          </div>
          <div class="feedback-detail-item">
            <span class="detail-label">提交时间</span>
            <span class="detail-value">{{ formatFullDate(selectedFeedback.created_at) }}</span>
          </div>
          <div class="feedback-detail-item" v-if="selectedFeedback.contact">
            <span class="detail-label">联系方式</span>
            <span class="detail-value">{{ selectedFeedback.contact }}</span>
          </div>
          <div class="feedback-detail-content">
            <div class="detail-label">反馈内容</div>
            <div class="content-box">{{ selectedFeedback.content }}</div>
          </div>
          <div class="feedback-detail-reply" v-if="selectedFeedback.admin_reply">
            <div class="detail-label">管理员回复</div>
            <div class="reply-box">
              <p>{{ selectedFeedback.admin_reply }}</p>
              <p class="reply-meta" v-if="selectedFeedback.replied_by">
                回复人: {{ selectedFeedback.replied_by }} | {{ formatFullDate(selectedFeedback.replied_at) }}
              </p>
            </div>
          </div>
          <div class="feedback-detail-actions" v-if="selectedFeedback.status !== 'closed'">
            <a-textarea
              v-model:value="replyContent"
              placeholder="输入回复内容..."
              :rows="3"
              style="margin-bottom: 12px"
            />
            <a-space>
              <a-button type="primary" size="small" @click="handleReply" :loading="replying">回复</a-button>
              <a-button size="small" @click="handleCloseFeedback" :loading="closing">关闭反馈</a-button>
            </a-space>
          </div>
        </div>
      </template>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { initColorPalette } from '@/utils/chartColors'
import DashboardView from '@/views/DashboardView.vue'
import { getAllFeedbacks, updateFeedback } from '@/apis/feedback_api'
import dayjs from '@/utils/time'

const router = useRouter()
const userStore = useUserStore()

const handleLogout = () => {
  userStore.logout()
}
const handleSwitchAccount = () => {
  userStore.logout()
}

// 反馈相关数据
const feedbacks = ref([])
const loadingFeedbacks = ref(false)
const feedbackStatusFilter = ref('')
const feedbackCategoryFilter = ref('')
const feedbackDetailModalOpen = ref(false)
const selectedFeedback = ref(null)
const replyContent = ref('')
const replying = ref(false)
const closing = ref(false)

const feedbackPagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: false,
  showQuickJumper: false,
  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`
})

const feedbackColumns = [
  {
    title: '标题',
    dataIndex: 'title',
    key: 'title',
    ellipsis: true
  },
  {
    title: '用户',
    key: 'username',
    width: '100px',
    ellipsis: true
  },
  {
    title: '类别',
    key: 'category',
    width: '80px',
    align: 'center'
  },
  {
    title: '状态',
    key: 'status',
    width: '80px',
    align: 'center'
  },
  {
    title: '提交时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: '120px'
  },
  {
    title: '操作',
    key: 'actions',
    width: '60px',
    align: 'center'
  }
]

const categoryMap = {
  general: { label: '一般', color: 'blue' },
  bug: { label: 'Bug', color: 'red' },
  feature: { label: '功能建议', color: 'green' },
  improvement: { label: '改进建议', color: 'orange' }
}

const statusMap = {
  pending: { label: '待处理', color: 'orange' },
  processing: { label: '处理中', color: 'blue' },
  resolved: { label: '已解决', color: 'green' },
  closed: { label: '已关闭', color: 'default' }
}

const getCategoryLabel = (category) => categoryMap[category]?.label || category
const getCategoryColor = (category) => categoryMap[category]?.color || 'default'
const getStatusLabel = (status) => statusMap[status]?.label || status
const getStatusColor = (status) => statusMap[status]?.color || 'default'

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const d = dayjs(dateString)
  if (!d.isValid()) return '-'
  const now = dayjs()
  const diffDays = now.startOf('day').diff(d.startOf('day'), 'day')
  if (diffDays === 0) return d.format('HH:mm')
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  return d.format('MM-DD')
}

const formatFullDate = (dateString) => {
  if (!dateString) return '—'
  const d = dayjs(dateString)
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : '—'
}

const loadFeedbacks = async () => {
  loadingFeedbacks.value = true
  try {
    const params = {
      skip: (feedbackPagination.current - 1) * feedbackPagination.pageSize,
      limit: feedbackPagination.pageSize
    }
    if (feedbackStatusFilter.value) params.status = feedbackStatusFilter.value
    if (feedbackCategoryFilter.value) params.category = feedbackCategoryFilter.value

    const response = await getAllFeedbacks(params)
    feedbacks.value = response.items || []
    feedbackPagination.total = response.total || 0
  } catch (error) {
    console.error('加载反馈列表失败:', error)
    message.error('加载反馈列表失败')
  } finally {
    loadingFeedbacks.value = false
  }
}

const handleFeedbackTableChange = (pag) => {
  feedbackPagination.current = pag.current
  feedbackPagination.pageSize = pag.pageSize
  loadFeedbacks()
}

const handleViewFeedbackDetail = (record) => {
  selectedFeedback.value = record
  replyContent.value = ''
  feedbackDetailModalOpen.value = true
}

const handleReply = async () => {
  if (!replyContent.value.trim()) {
    message.warning('请输入回复内容')
    return
  }
  replying.value = true
  try {
    await updateFeedback(selectedFeedback.value.id, {
      status: 'resolved',
      admin_reply: replyContent.value.trim()
    })
    message.success('回复成功')
    feedbackDetailModalOpen.value = false
    loadFeedbacks()
  } catch (error) {
    console.error('回复失败:', error)
    message.error('回复失败')
  } finally {
    replying.value = false
  }
}

const handleCloseFeedback = async () => {
  closing.value = true
  try {
    await updateFeedback(selectedFeedback.value.id, { status: 'closed' })
    message.success('反馈已关闭')
    feedbackDetailModalOpen.value = false
    loadFeedbacks()
  } catch (error) {
    console.error('关闭反馈失败:', error)
    message.error('关闭反馈失败')
  } finally {
    closing.value = false
  }
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

  // 加载反馈列表
  loadFeedbacks()
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

.ops-feedback-section {
  padding: 0 16px 24px;
}

.feedback-card {
  background-color: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  transition: all 0.2s ease;
  box-shadow: none;

  &:hover {
    background-color: var(--gray-25);
    border-color: var(--gray-200);
    box-shadow: 0 1px 3px 0 var(--shadow-1);
  }

  :deep(.ant-card-head) {
    border-bottom: 1px solid var(--gray-200);
    min-height: 56px;
    padding: 0 20px;
    background-color: var(--gray-0);

    .ant-card-head-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--gray-1000);
    }
  }

  :deep(.ant-card-body) {
    padding: 16px 20px;
    background-color: var(--gray-0);
  }

  :deep(.ant-card-extra) {
    .ant-space {
      gap: 8px;
    }
  }
}

.feedback-title {
  color: var(--main-500);
  text-decoration: none;
  font-weight: 500;
  font-size: 13px;
  transition: color 0.2s ease;

  &:hover {
    color: var(--main-600);
    text-decoration: underline;
  }
}

.user-display {
  color: var(--gray-800);
  font-size: 13px;
}

.time-text {
  color: var(--gray-600);
  font-size: 12px;
}


.feedback-detail {
  padding: 8px 0;
}

.feedback-detail-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 14px;
}

.detail-label {
  color: var(--gray-600);
  min-width: 80px;
  font-weight: 500;
}

.detail-value {
  color: var(--gray-1000);
}

.feedback-detail-content,
.feedback-detail-reply {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--gray-200);
}

.content-box,
.reply-box {
  margin-top: 8px;
  padding: 12px;
  background: var(--gray-50);
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--gray-800);
  word-break: break-word;
}

.reply-box {
  background: var(--color-success-50);
  border-left: 3px solid var(--color-success-500);
}

.reply-meta {
  margin-top: 8px;
  font-size: 12px;
  color: var(--gray-600);
}

.feedback-detail-actions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--gray-200);
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
