<template>
  <div class="dashboard-container" :class="{ 'dashboard-embed': embedMode }">
    <template v-if="!embedMode">
      <div class="dashboard-page-header">
        <h1 class="dashboard-page-title">访问统计</h1>
        <p class="dashboard-page-desc">查看站点访问与使用情况，仅管理员可见</p>
      </div>
      <div class="modern-stats-header">
        <StatusBar />
        <StatsOverviewComponent :basic-stats="basicStats" />
      </div>
    </template>
    <template v-else>
      <!-- 课程运维精简：关键指标 4 卡 -->
      <div class="ops-overview">
        <div class="ops-stat-card">
          <span class="ops-stat-value">{{ basicStats?.total_users ?? '—' }}</span>
          <span class="ops-stat-label">用户数</span>
        </div>
        <div class="ops-stat-card">
          <span class="ops-stat-value">{{ basicStats?.total_conversations ?? '—' }}</span>
          <span class="ops-stat-label">总对话数</span>
        </div>
        <div class="ops-stat-card">
          <span class="ops-stat-value">{{ basicStats?.total_messages ?? '—' }}</span>
          <span class="ops-stat-label">总消息数</span>
        </div>
        <div class="ops-stat-card">
          <span class="ops-stat-value">{{ basicStats?.active_users_24h ?? '—' }}</span>
          <span class="ops-stat-label">24h 活跃用户</span>
        </div>
        <div class="ops-stat-card">
          <span class="ops-stat-value">{{ basicStats?.total_exercise_attempts ?? '—' }}</span>
          <span class="ops-stat-label">做题次数</span>
        </div>
      </div>
    </template>

    <!-- 非 embed：完整仪表盘网格 -->
    <div v-if="!embedMode" class="dashboard-grid">
      <CallStatsComponent :loading="loading" ref="callStatsRef" />
      <div class="grid-item user-stats">
        <UserStatsComponent :user-stats="allStatsData?.users" :loading="loading" ref="userStatsRef" />
      </div>
      <div class="grid-item agent-stats">
        <AgentStatsComponent :agent-stats="allStatsData?.agents" :loading="loading" ref="agentStatsRef" />
      </div>
      <div class="grid-item tool-stats">
        <ToolStatsComponent :tool-stats="allStatsData?.tools" :loading="loading" ref="toolStatsRef" />
      </div>
      <div class="grid-item knowledge-stats">
        <KnowledgeStatsComponent :knowledge-stats="allStatsData?.knowledge" :loading="loading" ref="knowledgeStatsRef" />
      </div>
      <div class="grid-item conversations">
        <a-card class="conversations-section" title="对话记录" :loading="loading">
          <template #extra>
            <a-space>
              <a-input v-model:value="filters.user_id" placeholder="用户ID" size="small" style="width: 120px" @change="handleFilterChange" />
              <a-select v-model:value="filters.status" placeholder="状态" size="small" style="width: 100px" @change="handleFilterChange">
                <a-select-option value="active">活跃</a-select-option>
                <a-select-option value="deleted">已删除</a-select-option>
                <a-select-option value="all">全部</a-select-option>
              </a-select>
              <a-button size="small" @click="loadConversations" :loading="loading">刷新</a-button>
              <a-button size="small" @click="feedbackModal.show()">反馈详情</a-button>
            </a-space>
          </template>
          <a-table
            :columns="conversationColumns"
            :data-source="conversations"
            :loading="loading"
            :pagination="conversationPagination"
            @change="handleTableChange"
            row-key="thread_id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'title'">
                <a @click="handleViewDetail(record)" class="conversation-title" :class="{ loading: loadingDetail }">{{ record.title || '未命名对话' }}</a>
              </template>
              <template v-if="column.key === 'user_display'">
                <span class="user-display">{{ record.user_login || record.user_id || '—' }}</span>
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'active' ? 'green' : 'red'" size="small">{{ record.status === 'active' ? '活跃' : '已删除' }}</a-tag>
              </template>
              <template v-if="column.key === 'updated_at'">
                <span class="time-text">{{ formatDate(record.updated_at) }}</span>
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="link" size="small" @click="handleViewDetail(record)" :loading="loadingDetail">详情</a-button>
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
    </div>

    <!-- 课程运维精简：智能体调用 + 对话记录 + 做题记录 -->
    <div v-else class="ops-grid">
      <div class="ops-chart">
        <CallStatsComponent :loading="loading" ref="callStatsRef" />
      </div>
      <div class="ops-table-section">
        <a-card class="conversations-section" title="用户对话记录" :loading="loading">
          <template #extra>
            <a-space>
              <a-input v-model:value="filters.user_id" placeholder="用户" size="small" style="width: 100px" @change="handleFilterChange" />
              <a-select v-model:value="filters.status" placeholder="状态" size="small" style="width: 90px" @change="handleFilterChange">
                <a-select-option value="active">活跃</a-select-option>
                <a-select-option value="deleted">已删除</a-select-option>
                <a-select-option value="all">全部</a-select-option>
              </a-select>
              <a-button size="small" @click="loadConversations" :loading="loading">刷新</a-button>
            </a-space>
          </template>
          <a-table
            :columns="conversationColumns"
            :data-source="conversations"
            :loading="loading"
            :pagination="conversationPagination"
            @change="handleTableChange"
            row-key="thread_id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'title'">
                <a @click="handleViewDetail(record)" class="conversation-title" :class="{ loading: loadingDetail }">{{ record.title || '未命名对话' }}</a>
              </template>
              <template v-if="column.key === 'user_display'">
                <span class="user-display">{{ record.user_login || record.user_id || '—' }}</span>
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'active' ? 'green' : 'red'" size="small">{{ record.status === 'active' ? '活跃' : '已删除' }}</a-tag>
              </template>
              <template v-if="column.key === 'updated_at'">
                <span class="time-text">{{ formatDate(record.updated_at) }}</span>
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="link" size="small" @click="handleViewDetail(record)" :loading="loadingDetail">详情</a-button>
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
      <div class="ops-table-section">
        <a-card class="conversations-section" title="做题记录" :loading="loadingExercises">
          <template #extra>
            <a-space>
              <a-input
                v-model:value="exerciseUserFilter"
                placeholder="用户"
                size="small"
                style="width: 100px"
                allow-clear
              />
              <a-button size="small" @click="loadExerciseAttempts" :loading="loadingExercises">刷新</a-button>
            </a-space>
          </template>
          <a-table
            :columns="exerciseColumns"
            :data-source="exerciseAttempts"
            :loading="loadingExercises"
            :pagination="false"
            row-key="id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'user_login'">
                <span class="user-display">{{ record.user_login }}</span>
              </template>
              <template v-if="column.key === 'is_correct'">
                <a-tag :color="record.is_correct ? 'green' : 'red'" size="small">{{ record.is_correct ? '对' : '错' }}</a-tag>
              </template>
              <template v-if="column.key === 'created_at'">
                <span class="time-text">{{ formatDetailTime(record.created_at) }}</span>
              </template>
            </template>
          </a-table>
        </a-card>
      </div>
    </div>

    <!-- 反馈模态框（仅完整仪表盘） -->
    <FeedbackModalComponent v-if="!embedMode" ref="feedbackModal" />

    <!-- 对话详情弹窗 -->
    <a-modal
      v-model:open="detailModalOpen"
      title="对话详情"
      width="720px"
      :footer="null"
      destroy-on-close
      class="conversation-detail-modal"
      @cancel="detailData = null"
    >
      <template v-if="detailData">
        <div class="detail-meta">
          <div class="detail-meta-row">
            <span class="detail-label">用户</span>
            <span class="detail-value">{{ detailData.user_login || detailData.user_id || '—' }}</span>
          </div>
          <div class="detail-meta-row">
            <span class="detail-label">标题</span>
            <span class="detail-value">{{ detailData.title || '未命名对话' }}</span>
          </div>
          <div class="detail-meta-row">
            <span class="detail-label">消息数</span>
            <span class="detail-value">{{ detailData.message_count ?? 0 }}</span>
          </div>
          <div class="detail-meta-row">
            <span class="detail-label">状态</span>
            <a-tag :color="detailData.status === 'active' ? 'green' : 'red'" size="small">
              {{ detailData.status === 'active' ? '活跃' : '已删除' }}
            </a-tag>
          </div>
        </div>
        <div class="detail-messages">
          <h4 class="detail-messages-title">消息记录</h4>
          <div v-if="detailData.messages && detailData.messages.length" class="detail-messages-list">
            <div
              v-for="(msg, idx) in detailData.messages"
              :key="msg.id || idx"
              class="detail-message-item"
              :class="msg.role"
            >
              <span class="detail-message-role">{{ msg.role === 'user' ? '用户' : 'AI' }}</span>
              <span class="detail-message-time">{{ formatDetailTime(msg.created_at) }}</span>
              <div class="detail-message-content">{{ msg.content || '—' }}</div>
            </div>
          </div>
          <div v-else class="detail-messages-empty">暂无消息</div>
        </div>
      </template>
      <div v-else class="detail-loading">加载中…</div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { dashboardApi } from '@/apis/dashboard_api'

const props = defineProps({
  embedMode: { type: Boolean, default: false }
})
import dayjs, { parseToShanghai } from '@/utils/time'

// 导入子组件
import StatusBar from '@/components/StatusBar.vue'
import UserStatsComponent from '@/components/dashboard/UserStatsComponent.vue'
import ToolStatsComponent from '@/components/dashboard/ToolStatsComponent.vue'
import KnowledgeStatsComponent from '@/components/dashboard/KnowledgeStatsComponent.vue'
import AgentStatsComponent from '@/components/dashboard/AgentStatsComponent.vue'
import CallStatsComponent from '@/components/dashboard/CallStatsComponent.vue'
import StatsOverviewComponent from '@/components/dashboard/StatsOverviewComponent.vue'
import FeedbackModalComponent from '@/components/dashboard/FeedbackModalComponent.vue'

// 组件引用
const feedbackModal = ref(null)

// 统计数据 - 使用新的响应式结构
const basicStats = ref({})
const allStatsData = ref({
  users: null,
  tools: null,
  knowledge: null,
  agents: null
})

// 过滤器
const filters = reactive({
  user_id: '',
  agent_id: '',
  status: 'active'
})

// 对话列表
const conversations = ref([])
const loading = ref(false)
const loadingDetail = ref(false)

// 做题记录（运维）
const exerciseAttempts = ref([])
const loadingExercises = ref(false)
const exerciseUserFilter = ref('')

// 详情弹窗
const detailModalOpen = ref(false)
const detailData = ref(null)

// 调用统计子组件引用
const callStatsRef = ref(null)

// 分页
const conversationPagination = reactive({
  current: 1,
  pageSize: 8,
  total: 0,
  showSizeChanger: false,
  showQuickJumper: false,
  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`
})

// 表格列定义
const conversationColumns = [
  {
    title: '对话标题',
    dataIndex: 'title',
    key: 'title',
    ellipsis: true
  },
  {
    title: '用户',
    key: 'user_display',
    width: '100px',
    ellipsis: true
  },
  {
    title: '消息数',
    dataIndex: 'message_count',
    key: 'message_count',
    width: '60px',
    align: 'center'
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: '70px',
    align: 'center'
  },
  {
    title: '更新时间',
    dataIndex: 'updated_at',
    key: 'updated_at',
    width: '120px'
  },
  {
    title: '操作',
    key: 'actions',
    width: '60px',
    align: 'center'
  }
]

// 做题记录列（运维）
const exerciseColumns = [
  { title: '用户', dataIndex: 'user_login', key: 'user_login', width: 90, ellipsis: true },
  { title: '题型', dataIndex: 'question_type', key: 'question_type', width: 80 },
  { title: '知识点', dataIndex: 'knowledge_point', key: 'knowledge_point', ellipsis: true },
  { title: '对/错', dataIndex: 'is_correct', key: 'is_correct', width: 64, align: 'center' },
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 150 }
]

// 子组件引用
const userStatsRef = ref(null)
const toolStatsRef = ref(null)
const knowledgeStatsRef = ref(null)
const agentStatsRef = ref(null)

// 加载统计数据
const loadAllStats = async () => {
  loading.value = true
  try {
    if (props.embedMode) {
      basicStats.value = await dashboardApi.getStats()
    } else {
      const response = await dashboardApi.getAllStats()
      basicStats.value = response.basic
      allStatsData.value = {
        users: response.users,
        tools: response.tools,
        knowledge: response.knowledge,
        agents: response.agents
      }
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
    message.error('加载统计数据失败')
    if (!props.embedMode) {
      try {
        basicStats.value = await dashboardApi.getStats()
      } catch {
        // ignore
      }
    }
  } finally {
    loading.value = false
  }
}

// 加载做题记录（运维）
const loadExerciseAttempts = async () => {
  loadingExercises.value = true
  try {
    const params = { limit: 50, offset: 0 }
    if (exerciseUserFilter.value?.trim()) params.user_login = exerciseUserFilter.value.trim()
    exerciseAttempts.value = await dashboardApi.getExerciseAttempts(params)
  } catch (error) {
    console.error('加载做题记录失败:', error)
    message.error('加载做题记录失败')
  } finally {
    loadingExercises.value = false
  }
}

// 用户筛选输入防抖后自动查询做题记录
let exerciseFilterTimer = null
watch(exerciseUserFilter, () => {
  if (exerciseFilterTimer) clearTimeout(exerciseFilterTimer)
  exerciseFilterTimer = setTimeout(() => loadExerciseAttempts(), 300)
})

// 保留原有的loadStats函数以兼容旧代码
const loadStats = loadAllStats

// 加载对话列表
const loadConversations = async () => {
  try {
    const params = {
      user_id: filters.user_id || undefined,
      agent_id: filters.agent_id || undefined,
      status: filters.status,
      limit: conversationPagination.pageSize,
      offset: (conversationPagination.current - 1) * conversationPagination.pageSize
    }

    const response = await dashboardApi.getConversations(params)
    conversations.value = response
    // Note: 由于后端没有返回总数，这里暂时设置为当前数据长度
    conversationPagination.total = response.length
  } catch (error) {
    console.error('加载对话列表失败:', error)
    message.error('加载对话列表失败')
  }
}

// 日期格式化
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const parsed = parseToShanghai(dateString)
  if (!parsed) return '-'
  const now = dayjs().tz('Asia/Shanghai')
  const diffDays = now.startOf('day').diff(parsed.startOf('day'), 'day')

  if (diffDays === 0) {
    return parsed.format('HH:mm')
  }
  if (diffDays === 1) {
    return '昨天'
  }
  if (diffDays < 7) {
    return `${diffDays}天前`
  }
  return parsed.format('MM-DD')
}

// 详情弹窗内时间格式
const formatDetailTime = (dateString) => {
  if (!dateString) return '—'
  const parsed = parseToShanghai(dateString)
  return parsed ? parsed.format('YYYY-MM-DD HH:mm:ss') : '—'
}

// 查看对话详情
const handleViewDetail = async (record) => {
  try {
    loadingDetail.value = true
    detailData.value = null
    detailModalOpen.value = true
    const detail = await dashboardApi.getConversationDetail(record.thread_id)
    detailData.value = detail
  } catch (error) {
    console.error('获取对话详情失败:', error)
    message.error('获取对话详情失败')
    detailModalOpen.value = false
  } finally {
    loadingDetail.value = false
  }
}

// 处理过滤器变化
const handleFilterChange = () => {
  conversationPagination.current = 1
  loadConversations()
}

// 处理表格变化
const handleTableChange = (pag) => {
  conversationPagination.current = pag.current
  conversationPagination.pageSize = pag.pageSize
  loadConversations()
}

// 清理函数 - 清理所有子组件的图表实例
const cleanupCharts = () => {
  if (userStatsRef.value?.cleanup) userStatsRef.value.cleanup()
  if (toolStatsRef.value?.cleanup) userStatsRef.value.cleanup()
  if (knowledgeStatsRef.value?.cleanup) knowledgeStatsRef.value.cleanup()
  if (agentStatsRef.value?.cleanup) agentStatsRef.value.cleanup()
  if (callStatsRef.value?.cleanup) callStatsRef.value.cleanup()
}

// 初始化
onMounted(() => {
  loadAllStats()
  loadConversations()
  if (props.embedMode) {
    loadExerciseAttempts()
  }
})

// 组件卸载时清理图表
onUnmounted(() => {
  if (exerciseFilterTimer) clearTimeout(exerciseFilterTimer)
  cleanupCharts()
})
</script>

<style scoped lang="less">
.dashboard-container {
  background-color: var(--gray-25);
  min-height: calc(100vh - 64px);
  overflow-x: hidden;

  &.dashboard-embed .modern-stats-header {
    padding-top: 16px;
  }
}

/* 课程运维精简：关键指标卡片 */
.ops-overview {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px 24px 0;
  margin-bottom: 16px;
}
.ops-stat-card {
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  padding: 12px 20px;
  min-width: 100px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  .ops-stat-value {
    font-size: 20px;
    font-weight: 700;
    color: var(--gray-1000);
    line-height: 1.2;
  }
  .ops-stat-label {
    font-size: 12px;
    color: var(--gray-600);
    margin-top: 4px;
  }
}

/* 课程运维精简：图表 + 两个表格 */
.ops-grid {
  display: grid;
  padding: 0 16px 24px;
  gap: 16px;
  grid-template-columns: 1fr;
  grid-template-rows: auto auto auto;
}
.ops-chart {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  :deep(.grid-item.call-stats) {
    flex: 1;
    min-height: 0;
  }
  :deep(.call-stats-container .chart-container),
  :deep(.chart-container .chart) {
    min-height: 280px;
  }
}
.ops-table-section {
  min-height: 280px;
}

.dashboard-page-header {
  padding: 16px 24px 0;
  margin-bottom: 8px;

  .dashboard-page-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--gray-1000);
    margin: 0 0 4px 0;
  }

  .dashboard-page-desc {
    font-size: 13px;
    color: var(--gray-600);
    margin: 0;
  }
}

// Dashboard 特有的网格布局
.dashboard-grid {
  display: grid;
  padding: 16px;
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 16px;
  margin-bottom: 24px;
  min-height: 600px;

  .grid-item {
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 300px;
    background-color: transparent;
    border: none;
    transition: all 0.2s ease;

    &:hover {
      .conversations-section,
      .call-stats-section {
        border-color: var(--gray-200);
        box-shadow: 0 1px 3px 0 var(--shadow-1);
      }
    }

    // 大页面布局：第一行 2x1 + 1x1，第二行 3x1x1
    &.call-stats {
      grid-column: 1 / 3;
      grid-row: 1 / 2;
      min-height: 400px;
    }

    &.user-stats {
      grid-column: 3 / 4;
      grid-row: 1 / 2;
      min-height: 400px;
    }

    &.agent-stats {
      grid-column: 1 / 2;
      grid-row: 2 / 3;
      min-height: 350px;
    }

    &.tool-stats {
      grid-column: 2 / 3;
      grid-row: 2 / 3;
      min-height: 350px;
    }

    &.knowledge-stats {
      grid-column: 3 / 4;
      grid-row: 2 / 3;
      min-height: 350px;
    }

    &.conversations {
      grid-column: 1 / 4;
      grid-row: 3 / 4;
      min-height: 300px;
    }
  }
}

// Dashboard 特有的卡片样式
.conversations-section,
.call-stats-section {
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

// Dashboard 特有的占位符样式
.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--gray-600);

  .placeholder-icon {
    width: 64px;
    height: 64px;
    background-color: var(--gray-100);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;

    .icon {
      width: 32px;
      height: 32px;
      color: var(--gray-500);
    }
  }

  .placeholder-text {
    font-size: 18px;
    font-weight: 600;
    color: var(--gray-800);
    margin-bottom: 8px;
  }

  .placeholder-subtitle {
    font-size: 14px;
    color: var(--gray-600);
  }
}

.user-display {
  color: var(--gray-800);
  font-size: 13px;
}

// Dashboard 特有的对话记录样式
.conversations-section {
  .conversation-title {
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

  .time-text {
    color: var(--gray-600);
    font-size: 12px;
  }
}

// 调用统计模块样式
.call-stats-section {
  .call-stats-container {
    .call-summary {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;

      .summary-card {
        background: linear-gradient(135deg, var(--gray-50) 0%, var(--gray-100) 100%);
        border: 1px solid var(--gray-200);
        border-radius: 8px;
        padding: 12px;
        text-align: center;

        .summary-value {
          font-size: 16px;
          font-weight: 600;
          color: var(--gray-800);
          margin-bottom: 4px;
        }

        .summary-label {
          font-size: 11px;
          color: var(--gray-500);
          font-weight: 500;
        }
      }
    }

    .chart-container {
      .chart {
        width: 100%;
        height: 280px;
        border-radius: 8px;
        overflow: hidden;
      }
    }
  }

  :deep(.ant-card-extra) {
    .ant-space {
      gap: 8px;
    }
  }
}

// Dashboard 特有的响应式设计
@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto auto;
    gap: 16px;

    .grid-item {
      // 小页面布局：第一行 2x1，第二行和第三行各是 2x1x1
      &.call-stats {
        grid-column: 1 / 3;
        grid-row: 1 / 2;
        min-height: 350px;
      }

      &.user-stats {
        grid-column: 1 / 2;
        grid-row: 2 / 3;
        min-height: 300px;
      }

      &.agent-stats {
        grid-column: 2 / 3;
        grid-row: 2 / 3;
        min-height: 300px;
      }

      &.tool-stats {
        grid-column: 1 / 2;
        grid-row: 3 / 4;
        min-height: 300px;
      }

      &.knowledge-stats {
        grid-column: 2 / 3;
        grid-row: 3 / 4;
        min-height: 300px;
      }

      &.conversations {
        grid-column: 1 / 3;
        grid-row: 4 / 5;
        min-height: 300px;
      }
    }
  }
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 16px;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
    gap: 12px;

    .grid-item {
      &.call-stats,
      &.agent-stats,
      &.user-stats,
      &.tool-stats,
      &.knowledge-stats,
      &.conversations {
        grid-column: 1 / 2;
        grid-row: auto;
        min-height: 300px;
      }
    }
  }

  .call-stats-section {
    .call-stats-container {
      .call-summary {
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;

        .summary-card {
          padding: 12px;

          .summary-value {
            font-size: 18px;
          }

          .summary-label {
            font-size: 11px;
          }
        }
      }

      .chart-container {
        .chart {
          height: 200px;
        }
      }
    }
  }

  .placeholder-content {
    height: 150px;

    .placeholder-icon {
      width: 48px;
      height: 48px;
      margin-bottom: 12px;

      .icon {
        width: 24px;
        height: 24px;
      }
    }

    .placeholder-text {
      font-size: 16px;
    }

    .placeholder-subtitle {
      font-size: 12px;
    }
  }
}
</style>

<style lang="less">
/* 对话详情弹窗（非 scoped：Modal 会挂载到 body） */
.conversation-detail-modal .detail-meta {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--gray-200);
}
.conversation-detail-modal .detail-meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 14px;
}
.conversation-detail-modal .detail-label {
  color: var(--gray-600);
  min-width: 64px;
}
.conversation-detail-modal .detail-value {
  color: var(--gray-1000);
}
.conversation-detail-modal .detail-messages-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-1000);
  margin: 0 0 12px 0;
}
.conversation-detail-modal .detail-messages-list {
  max-height: 360px;
  overflow-y: auto;
}
.conversation-detail-modal .detail-message-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  font-size: 13px;
  border: 1px solid var(--gray-200);
  background: var(--gray-25);
}
.conversation-detail-modal .detail-message-item.user {
  background: var(--main-50);
  border-color: var(--main-200);
}
.conversation-detail-modal .detail-message-item.ai {
  background: var(--gray-10);
}
.conversation-detail-modal .detail-message-role {
  font-weight: 600;
  color: var(--gray-700);
  margin-right: 8px;
}
.conversation-detail-modal .detail-message-time {
  font-size: 12px;
  color: var(--gray-500);
}
.conversation-detail-modal .detail-message-content {
  margin-top: 6px;
  color: var(--gray-1000);
  white-space: pre-wrap;
  word-break: break-word;
}
.conversation-detail-modal .detail-messages-empty,
.conversation-detail-modal .detail-loading {
  color: var(--gray-500);
  text-align: center;
  padding: 24px;
}
</style>
