<template>
  <div class="ops-container course-page">
    <CourseTopbar @logout="handleLogout" @switch-account="handleSwitchAccount" />

    <main class="ops-main page-shell">
      <CoursePageHero
        eyebrow="Operations"
        title="运维总览"
        subtitle="统一查看课程平台的用户、对话、做题与反馈数据。"
      />
      <div class="ops-dashboard">
        <a-card class="roster-card" title="学生实名注册名单">
          <a-space wrap>
            <span>当前名单：{{ studentRosterCount }} 人</span>
            <input
              ref="rosterFileInput"
              class="roster-file-input"
              type="file"
              accept=".csv,text/csv"
              @change="handleRosterFileChange"
            />
            <a-button @click="rosterFileInput?.click()">选择 CSV</a-button>
            <span>{{ selectedRosterFile?.name || '未选择文件' }}</span>
            <a-button
              type="primary"
              :disabled="!selectedRosterFile"
              :loading="loadingRoster"
              @click="uploadStudentRoster"
            >
              导入并替换名单
            </a-button>
          </a-space>
          <p class="roster-hint">
            CSV 必须为 UTF-8 编码且不超过 5 MB，表头为
            <code>student_id,name</code>。导入会整体替换当前名单，不会修改已注册账号。
          </p>
        </a-card>

        <a-card class="roster-card" title="学生学情">
          <a-table
            :columns="studentColumns"
            :data-source="students"
            :loading="loadingStudents"
            :pagination="{ pageSize: 10, showTotal: (total) => `共 ${total} 名学生` }"
            row-key="id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                {{ record.student_name || record.user_login }}
              </template>
              <template v-if="column.key === 'activity'">
                {{ formatFullDate(record.last_login) }}
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="link" size="small" @click="openStudentSummary(record)">
                  查看详情
                </a-button>
              </template>
            </template>
          </a-table>
        </a-card>

        <a-modal
          v-model:open="studentSummaryOpen"
          :title="studentSummary?.student?.student_name || '学生学情详情'"
          width="760px"
          :footer="null"
          destroy-on-close
        >
          <a-spin :spinning="loadingStudentSummary">
            <template v-if="studentSummary">
              <p class="roster-hint">
                学号：{{ studentSummary.student.user_login }} · 最近活动：{{
                  formatFullDate(studentSummary.latest_activity)
                }}
              </p>
              <div class="ops-overview">
                <div class="ops-stat-card">
                  <span class="ops-stat-value">{{ studentSummary.question_count }}</span
                  ><span class="ops-stat-label">AI提问数（学生消息）</span>
                </div>
                <div class="ops-stat-card">
                  <span class="ops-stat-value">{{ studentSummary.attempt_count }}</span
                  ><span class="ops-stat-label">做题量</span>
                </div>
                <div class="ops-stat-card">
                  <span class="ops-stat-value">{{
                    studentSummary.accuracy == null
                      ? '—'
                      : `${(studentSummary.accuracy * 100).toFixed(1)}%`
                  }}</span
                  ><span class="ops-stat-label">正确率</span>
                </div>
                <div class="ops-stat-card">
                  <span class="ops-stat-value">{{ studentSummary.wrong_count }}</span
                  ><span class="ops-stat-label">错题数</span>
                </div>
              </div>
              <h4>错题知识点</h4>
              <a-empty
                v-if="!studentSummary.wrong_knowledge_points.length"
                description="暂无错题"
              />
              <a-table
                v-else
                :columns="wrongPointColumns"
                :data-source="studentSummary.wrong_knowledge_points"
                :pagination="false"
                row-key="knowledge_point"
                size="small"
              />
              <h4>阅读位置</h4>
              <a-empty v-if="!studentSummary.reading_positions.length" description="暂无阅读记录" />
              <a-table
                v-else
                :columns="readingColumns"
                :data-source="studentSummary.reading_positions"
                :pagination="false"
                row-key="book_id"
                size="small"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'updated_at'">{{
                    formatFullDate(record.updated_at)
                  }}</template>
                </template>
              </a-table>
              <p class="roster-hint">
                提问按 role=user
                消息计数；正确率按全部已提交作答计算。系统目前没有学习计时事件，因此不显示学习时长。
              </p>
            </template>
          </a-spin>
        </a-modal>

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

        <div class="ops-grid">
          <div class="ops-chart">
            <CallStatsComponent :loading="loadingStats" />
          </div>
          <div class="ops-table-section">
            <a-card
              class="conversations-section"
              title="用户对话记录"
              :loading="loadingConversations"
            >
              <template #extra>
                <a-space>
                  <a-input
                    v-model:value="filters.user_id"
                    placeholder="用户"
                    size="small"
                    style="width: 100px"
                    @change="handleFilterChange"
                  />
                  <a-select
                    v-model:value="filters.status"
                    placeholder="状态"
                    size="small"
                    style="width: 90px"
                    @change="handleFilterChange"
                  >
                    <a-select-option value="active">活跃</a-select-option>
                    <a-select-option value="deleted">已删除</a-select-option>
                    <a-select-option value="all">全部</a-select-option>
                  </a-select>
                  <a-button size="small" @click="loadConversations" :loading="loadingConversations"
                    >刷新</a-button
                  >
                </a-space>
              </template>
              <a-table
                :columns="conversationColumns"
                :data-source="conversations"
                :loading="loadingConversations"
                :pagination="conversationPagination"
                @change="handleTableChange"
                row-key="thread_id"
                size="small"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'title'">
                    <a @click="handleViewConversationDetail(record)" class="feedback-title">{{
                      record.title || '未命名对话'
                    }}</a>
                  </template>
                  <template v-if="column.key === 'user_display'">
                    <span class="user-display">{{
                      record.student_name || record.user_login || record.user_id || '—'
                    }}</span>
                  </template>
                  <template v-if="column.key === 'status'">
                    <a-tag :color="record.status === 'active' ? 'green' : 'red'" size="small">{{
                      record.status === 'active' ? '活跃' : '已删除'
                    }}</a-tag>
                  </template>
                  <template v-if="column.key === 'updated_at'">
                    <span class="time-text">{{ formatDate(record.updated_at) }}</span>
                  </template>
                  <template v-if="column.key === 'actions'">
                    <a-button
                      type="link"
                      size="small"
                      @click="handleViewConversationDetail(record)"
                      :loading="loadingConversationDetail"
                      >详情</a-button
                    >
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
                  <a-button size="small" @click="loadExerciseAttempts" :loading="loadingExercises"
                    >刷新</a-button
                  >
                </a-space>
              </template>
              <a-table
                :columns="exerciseColumns"
                :data-source="exerciseAttempts"
                :loading="loadingExercises"
                :pagination="false"
                row-key="id"
                size="small"
                :expand-row-by-click="true"
              >
                <template #expandedRowRender="{ record }">
                  <div class="exercise-detail">
                    <div v-if="record.question_content" class="exercise-detail-row">
                      <strong>题目：</strong>
                      <div
                        class="exercise-detail-markdown"
                        v-html="renderMarkdown(record.question_content)"
                      ></div>
                    </div>
                    <div class="exercise-detail-row">
                      <strong>我的答案：</strong>
                      <div
                        v-if="record.user_answer"
                        class="exercise-detail-markdown"
                        v-html="renderMarkdown(record.user_answer)"
                      ></div>
                      <span v-else>—</span>
                    </div>
                    <div class="exercise-detail-row">
                      <strong>正确答案：</strong>
                      <div
                        v-if="record.correct_answer"
                        class="exercise-detail-markdown"
                        v-html="renderMarkdown(record.correct_answer)"
                      ></div>
                      <span v-else>—</span>
                    </div>
                    <div v-if="record.explanation" class="exercise-detail-row">
                      <strong>解析：</strong>
                      <div
                        class="exercise-detail-markdown"
                        v-html="renderMarkdown(record.explanation)"
                      ></div>
                    </div>
                    <p v-if="record.section_title" class="exercise-detail-row exercise-detail-meta">
                      <strong>章节：</strong>{{ record.section_title }}
                    </p>
                  </div>
                </template>
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'student_name'">
                    <span class="user-display">{{
                      record.student_name || record.user_login || '—'
                    }}</span>
                  </template>
                  <template v-if="column.key === 'is_correct'">
                    <a-tag :color="record.is_correct ? 'green' : 'red'" size="small">{{
                      record.is_correct ? '对' : '错'
                    }}</a-tag>
                  </template>
                  <template v-if="column.key === 'created_at'">
                    <span class="time-text">{{ formatFullDate(record.created_at) }}</span>
                  </template>
                </template>
              </a-table>
            </a-card>
          </div>
        </div>
      </div>

      <!-- 用户反馈区域 -->
      <div class="ops-feedback-section">
        <a-card class="feedback-card" title="用户反馈" :loading="loadingFeedbacks">
          <template #extra>
            <a-space>
              <a-select
                v-model:value="feedbackStatusFilter"
                placeholder="状态"
                size="small"
                style="width: 100px"
                @change="loadFeedbacks"
              >
                <a-select-option value="">全部</a-select-option>
                <a-select-option value="pending">待处理</a-select-option>
                <a-select-option value="processing">处理中</a-select-option>
                <a-select-option value="resolved">已解决</a-select-option>
                <a-select-option value="closed">已关闭</a-select-option>
              </a-select>
              <a-select
                v-model:value="feedbackCategoryFilter"
                placeholder="类别"
                size="small"
                style="width: 100px"
                @change="loadFeedbacks"
              >
                <a-select-option value="">全部</a-select-option>
                <a-select-option value="general">一般</a-select-option>
                <a-select-option value="bug">Bug</a-select-option>
                <a-select-option value="feature">功能建议</a-select-option>
                <a-select-option value="improvement">改进建议</a-select-option>
              </a-select>
              <a-button size="small" @click="loadFeedbacks" :loading="loadingFeedbacks"
                >刷新</a-button
              >
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
                <a @click="handleViewFeedbackDetail(record)" class="feedback-title">{{
                  record.title
                }}</a>
              </template>
              <template v-if="column.key === 'username'">
                <span class="user-display">{{ record.username || '匿名用户' }}</span>
              </template>
              <template v-if="column.key === 'created_at'">
                <span class="time-text">{{ formatDate(record.created_at) }}</span>
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="link" size="small" @click="handleViewFeedbackDetail(record)"
                  >详情</a-button
                >
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
                回复人: {{ selectedFeedback.replied_by }} |
                {{ formatFullDate(selectedFeedback.replied_at) }}
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
              <a-button type="primary" size="small" @click="handleReply" :loading="replying"
                >回复</a-button
              >
              <a-button size="small" @click="handleCloseFeedback" :loading="closing"
                >关闭反馈</a-button
              >
            </a-space>
          </div>
        </div>
      </template>
    </a-modal>

    <!-- 对话详情弹窗 -->
    <a-modal
      v-model:open="conversationDetailModalOpen"
      title="对话详情"
      width="720px"
      :footer="null"
      destroy-on-close
      class="conversation-detail-modal"
      @cancel="conversationDetail = null"
    >
      <template v-if="conversationDetail">
        <div class="feedback-detail">
          <div class="feedback-detail-item">
            <span class="detail-label">用户</span>
            <span class="detail-value">{{
              conversationDetail.student_name ||
              conversationDetail.user_login ||
              conversationDetail.user_id ||
              '—'
            }}</span>
          </div>
          <div class="feedback-detail-item">
            <span class="detail-label">标题</span>
            <span class="detail-value">{{ conversationDetail.title || '未命名对话' }}</span>
          </div>
          <div class="feedback-detail-item">
            <span class="detail-label">消息数</span>
            <span class="detail-value">{{ conversationDetail.message_count ?? 0 }}</span>
          </div>
          <div class="feedback-detail-item">
            <span class="detail-label">状态</span>
            <a-tag :color="conversationDetail.status === 'active' ? 'green' : 'red'" size="small">
              {{ conversationDetail.status === 'active' ? '活跃' : '已删除' }}
            </a-tag>
          </div>
          <div class="feedback-detail-content">
            <div class="detail-label">消息记录</div>
            <div
              v-if="conversationDetail.messages && conversationDetail.messages.length"
              class="detail-messages-list"
            >
              <div
                v-for="(msg, idx) in conversationDetail.messages"
                :key="msg.id || idx"
                class="detail-message-item"
                :class="msg.role"
              >
                <span class="detail-message-role">{{ msg.role === 'user' ? '用户' : 'AI' }}</span>
                <span class="detail-message-time">{{ formatFullDate(msg.created_at) }}</span>
                <div v-if="!msg.content" class="content-box">—</div>
                <div
                  v-else
                  class="content-box exercise-detail-markdown"
                  v-html="renderMarkdown(msg.content)"
                ></div>
              </div>
            </div>
            <div v-else class="content-box">暂无消息</div>
          </div>
        </div>
      </template>
      <div v-else class="content-box">加载中…</div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { marked } from 'marked'
import CourseTopbar from '@/components/course/CourseTopbar.vue'
import CoursePageHero from '@/components/course/CoursePageHero.vue'
import { useUserStore } from '@/stores/user'
import { initColorPalette } from '@/utils/chartColors'
import CallStatsComponent from '@/components/dashboard/CallStatsComponent.vue'
import { dashboardApi } from '@/apis/dashboard_api'
import { getAllFeedbacks, updateFeedback } from '@/apis/feedback_api'
import dayjs from '@/utils/time'

const userStore = useUserStore()

const handleLogout = () => {
  userStore.logout()
}
const handleSwitchAccount = () => {
  userStore.logout()
}

const basicStats = ref({})
const loadingStats = ref(false)
const studentRosterCount = ref('—')
const selectedRosterFile = ref(null)
const rosterFileInput = ref(null)
const loadingRoster = ref(false)
const conversations = ref([])
const loadingConversations = ref(false)
const loadingConversationDetail = ref(false)
const conversationDetailModalOpen = ref(false)
const conversationDetail = ref(null)
const exerciseAttempts = ref([])
const loadingExercises = ref(false)
const exerciseUserFilter = ref('')
const students = ref([])
const loadingStudents = ref(false)
const studentSummaryOpen = ref(false)
const loadingStudentSummary = ref(false)
const studentSummary = ref(null)

const studentColumns = [
  { title: '学生姓名', key: 'name' },
  { title: '学号', dataIndex: 'user_login', key: 'user_login' },
  { title: '最近登录', key: 'activity' },
  { title: '操作', key: 'actions', width: 90 }
]
const wrongPointColumns = [
  { title: '知识点', dataIndex: 'knowledge_point', key: 'knowledge_point' },
  { title: '错题数', dataIndex: 'count', key: 'count', width: 100 }
]
const readingColumns = [
  { title: '书籍', dataIndex: 'book_id', key: 'book_id' },
  { title: '最后阅读页', dataIndex: 'page', key: 'page', width: 110 },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at' }
]

const filters = reactive({
  user_id: '',
  status: 'active'
})

const conversationPagination = reactive({
  current: 1,
  pageSize: 8,
  total: 0,
  showSizeChanger: false,
  showQuickJumper: false,
  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`
})

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

const exerciseColumns = [
  { title: '用户', dataIndex: 'student_name', key: 'student_name', width: 90, ellipsis: true },
  { title: '题型', dataIndex: 'question_type', key: 'question_type', width: 80 },
  { title: '知识点', dataIndex: 'knowledge_point', key: 'knowledge_point', ellipsis: true },
  { title: '对/错', dataIndex: 'is_correct', key: 'is_correct', width: 64, align: 'center' },
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 150 }
]

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

function renderMarkdown(text) {
  if (!text || typeof text !== 'string') return ''
  return marked.parse(text, { gfm: true, breaks: true })
}

const loadStats = async () => {
  loadingStats.value = true
  try {
    basicStats.value = await dashboardApi.getStats()
  } catch (error) {
    console.error('加载统计数据失败:', error)
    message.error('加载统计数据失败')
  } finally {
    loadingStats.value = false
  }
}

const loadStudentRosterCount = async () => {
  try {
    const response = await dashboardApi.getStudentRosterCount()
    studentRosterCount.value = response.student_count
  } catch (error) {
    console.error('加载学生名单状态失败:', error)
    message.error('加载学生名单状态失败')
  }
}

const loadStudents = async () => {
  loadingStudents.value = true
  try {
    students.value = await dashboardApi.getStudents()
  } catch (error) {
    console.error('加载学生列表失败:', error)
    message.error('加载学生列表失败')
  } finally {
    loadingStudents.value = false
  }
}

const openStudentSummary = async (student) => {
  studentSummaryOpen.value = true
  loadingStudentSummary.value = true
  studentSummary.value = null
  try {
    studentSummary.value = await dashboardApi.getStudentLearningSummary(student.id)
  } catch (error) {
    console.error('加载学生学情失败:', error)
    message.error('加载学生学情失败')
    studentSummaryOpen.value = false
  } finally {
    loadingStudentSummary.value = false
  }
}

const handleRosterFileChange = (event) => {
  selectedRosterFile.value = event.target.files?.[0] || null
}

const uploadStudentRoster = async () => {
  if (!selectedRosterFile.value) return
  loadingRoster.value = true
  try {
    const response = await dashboardApi.importStudentRoster(selectedRosterFile.value)
    studentRosterCount.value = response.student_count
    selectedRosterFile.value = null
    if (rosterFileInput.value) rosterFileInput.value.value = ''
    message.success(`学生名单导入成功，共 ${response.student_count} 人`)
  } catch (error) {
    console.error('导入学生名单失败:', error)
    message.error(error.message || '导入学生名单失败')
  } finally {
    loadingRoster.value = false
  }
}

const loadConversations = async () => {
  loadingConversations.value = true
  try {
    const params = {
      user_id: filters.user_id || undefined,
      status: filters.status,
      limit: conversationPagination.pageSize,
      offset: (conversationPagination.current - 1) * conversationPagination.pageSize
    }

    const response = await dashboardApi.getConversations(params)
    conversations.value = response
    conversationPagination.total = response.length
  } catch (error) {
    console.error('加载对话列表失败:', error)
    message.error('加载对话列表失败')
  } finally {
    loadingConversations.value = false
  }
}

const handleFilterChange = () => {
  conversationPagination.current = 1
  loadConversations()
}

const handleTableChange = (pag) => {
  conversationPagination.current = pag.current
  conversationPagination.pageSize = pag.pageSize
  loadConversations()
}

const handleViewConversationDetail = async (record) => {
  try {
    loadingConversationDetail.value = true
    conversationDetail.value = null
    conversationDetailModalOpen.value = true
    conversationDetail.value = await dashboardApi.getConversationDetail(record.thread_id)
  } catch (error) {
    console.error('获取对话详情失败:', error)
    message.error('获取对话详情失败')
    conversationDetailModalOpen.value = false
  } finally {
    loadingConversationDetail.value = false
  }
}

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

let exerciseFilterTimer = null
watch(exerciseUserFilter, () => {
  if (exerciseFilterTimer) clearTimeout(exerciseFilterTimer)
  exerciseFilterTimer = setTimeout(() => loadExerciseAttempts(), 300)
})

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
  loadStudents()
  loadStudentRosterCount()
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

  loadStats()
  loadStudentRosterCount()
  loadConversations()
  loadExerciseAttempts()
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
  color: var(--accent-primary);
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
  color: var(--accent-primary);
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
  transition:
    color 0.2s,
    background 0.2s;
}

.ops-auth-link:hover {
  color: var(--accent-primary);
}

.ops-auth-link.primary {
  color: var(--gray-0);
  background: var(--accent-primary);
}

.ops-auth-link.primary:hover {
  background: var(--accent-primary-hover);
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
  transition:
    color 0.2s,
    border-color 0.2s;
}

.ops-auth-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.ops-main {
  width: 100%;
  padding: 0;
  min-height: calc(100vh - 52px);
}

/* 运维页容器 */
.ops-container {
}

.ops-overview {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px 16px 0;
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
}

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
}

.ops-chart :deep(.grid-item.call-stats) {
  flex: 1;
  min-height: 0;
}

.ops-chart :deep(.call-stats-container .chart-container),
.ops-chart :deep(.chart-container .chart) {
  min-height: 280px;
}

.ops-table-section {
  min-height: 280px;
}

.roster-file-input {
  display: none;
}

.roster-hint {
  margin: 12px 0 0;
  color: var(--gray-600);
  font-size: 13px;
}

.exercise-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.exercise-detail-row {
  font-size: 13px;
  color: var(--gray-800);
}

.exercise-detail-meta {
  margin: 0;
}

.exercise-detail-markdown :deep(p) {
  margin: 0 0 8px;
}

.exercise-detail-markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.detail-messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

.detail-message-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-message-role {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-700);
}

.detail-message-time {
  font-size: 12px;
  color: var(--gray-500);
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
</style>
