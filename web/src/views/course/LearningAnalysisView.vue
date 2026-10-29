<template>
  <div class="learning-page course-page">
    <CourseTopbar @logout="handleLogout" @switch-account="handleSwitchAccount" />
    <main class="learning-main page-shell">
      <CoursePageHero eyebrow="Learning analytics" title="学情分析" />
      <p class="hero-description">
        <a-tooltip :trigger="['hover', 'click']" placement="right">
          <template #title>
            <div class="definition-tooltip">
              <strong>统计口径</strong>
              <span
                >概览与错题统计范围为近30天；活跃学生指期间有 AI
                提问、习题作答或阅读记录的学生。</span
              >
            </div>
          </template>
          <InfoCircleOutlined class="definition-icon" tabindex="0" aria-label="查看统计口径" />
        </a-tooltip>
        <span>基于学生实际对话、习题作答和阅读记录进行统计。</span>
      </p>

      <a-spin :spinning="loading">
        <section class="section-block">
          <h2>学情概览</h2>
          <div class="metric-grid">
            <article class="metric-card">
              <span>近30天活跃学生</span><strong>{{ data.active_students ?? 0 }}</strong
              ><small>人</small>
            </article>
            <article class="metric-card">
              <span>近30天 AI 提问</span><strong>{{ data.question_count ?? 0 }}</strong
              ><small>次</small>
            </article>
            <article class="metric-card">
              <span>近30天做题量</span><strong>{{ exercise.attempt_count ?? 0 }}</strong
              ><small>题</small>
            </article>
            <article class="metric-card">
              <span>近30天正确率</span><strong>{{ percent(exercise.accuracy) }}</strong
              ><small>基于已提交作答</small>
            </article>
          </div>
        </section>

        <section class="section-block panel-card heatmap-card">
          <div class="section-heading">
            <div>
              <h2>近7日学生在线学习热力图</h2>
              <p>按 4 小时时段统计有学习记录的学生人数，颜色越深表示人数越多</p>
            </div>
          </div>
          <div class="heatmap-grid" role="img" aria-label="近7日学生在线学习热力图">
            <span class="heatmap-corner"></span>
            <span v-for="day in heatmap.days" :key="day.date" class="heatmap-day">{{
              day.label
            }}</span>
            <template v-for="slot in heatmap.slots" :key="slot.start_hour">
              <span class="heatmap-time">{{ `${String(slot.end_hour).padStart(2, '0')}:00` }}</span>
              <a-tooltip
                v-for="cell in slot.cells"
                :key="`${cell.date}-${slot.start_hour}`"
                :title="`${cell.date} ${slot.label} · ${cell.active_students} 名活跃学生 · ${cell.activity_count} 条学习记录`"
                placement="top"
              >
                <span
                  class="heatmap-cell"
                  :style="{ backgroundColor: heatColor(cell.active_students) }"
                  :aria-label="`${cell.date} ${slot.label}，${cell.active_students} 名活跃学生`"
                  tabindex="0"
                ></span>
              </a-tooltip>
            </template>
            <span class="heatmap-time">00:00</span>
            <span
              class="heatmap-bottom"
              v-for="day in heatmap.days"
              :key="`${day.date}-bottom`"
            ></span>
          </div>
        </section>

        <section class="section-block">
          <h2>AI 对话统计</h2>
          <div class="metric-grid">
            <article class="metric-card">
              <span>学生提问数</span><strong>{{ data.question_count ?? 0 }}</strong
              ><small>近30天</small>
            </article>
            <article class="metric-card">
              <span>对话数</span><strong>{{ data.conversation_count ?? 0 }}</strong
              ><small>含学生提问的对话</small>
            </article>
            <article class="metric-card">
              <span>参与学生</span><strong>{{ data.participating_students ?? 0 }}</strong
              ><small>近30天</small>
            </article>
            <article class="metric-card">
              <span>人均提问数</span><strong>{{ data.average_questions_per_student ?? 0 }}</strong
              ><small>参与学生平均值</small>
            </article>
          </div>
        </section>

        <div class="analysis-grid">
          <section class="section-block panel-card">
            <div class="section-heading">
              <div>
                <h2>近七日提问趋势</h2>
                <p>对比最近7天与此前7天，按相对日期对齐</p>
              </div>
              <div class="legend">
                <span class="legend-recent"></span>最近7天<span class="legend-previous"></span
                >此前7天
              </div>
            </div>
            <div v-if="trendRecent.length" class="chart-wrap">
              <svg viewBox="0 0 760 250" role="img" aria-label="近七日提问趋势对比折线图">
                <g v-for="tick in 5" :key="tick">
                  <line
                    x1="54"
                    :y1="chartY(tick - 1)"
                    x2="738"
                    :y2="chartY(tick - 1)"
                    class="grid-line"
                  />
                  <text x="42" :y="chartY(tick - 1) + 4" class="axis-label" text-anchor="end">
                    {{ chartMax - ((tick - 1) * chartMax) / 4 }}
                  </text>
                </g>
                <polyline :points="chartPoints(trendPrevious)" class="line-previous" />
                <polyline :points="chartPoints(trendRecent)" class="line-recent" />
                <g v-for="(point, index) in trendRecent" :key="point.date">
                  <circle
                    :cx="chartX(index)"
                    :cy="chartValueY(point.questions)"
                    r="4"
                    class="dot-recent"
                  />
                  <circle
                    :cx="chartX(index)"
                    :cy="chartValueY(trendPrevious[index]?.questions || 0)"
                    r="4"
                    class="dot-previous"
                  />
                  <text :x="chartX(index)" y="232" class="axis-label" text-anchor="middle">
                    {{ `第${index + 1}天` }}
                  </text>
                </g>
              </svg>
            </div>
            <a-empty v-else description="暂无对话数据" />
          </section>
          <section class="section-block panel-card">
            <h2>学生提问频次分布</h2>
            <p>按每名学生近7天的提问消息条数分组</p>
            <div class="bar-list">
              <div v-for="item in data.frequency_7_days || []" :key="item.range" class="bar-row">
                <span>{{ item.range }}</span>
                <div class="bar-track"><i :style="{ width: barWidth(item.students) }"></i></div>
                <b>{{ item.students }}人</b>
              </div>
            </div>
          </section>
        </div>

        <section class="section-block panel-card">
          <div class="section-heading">
            <div>
              <h2>错题与知识点</h2>
              <p>近30天习题提交记录</p>
            </div>
          </div>
          <div class="metric-grid metric-grid--compact">
            <article class="metric-card">
              <span>作答总数</span><strong>{{ exercise.attempt_count ?? 0 }}</strong
              ><small>题</small>
            </article>
            <article class="metric-card">
              <span>错题数</span><strong>{{ exercise.wrong_count ?? 0 }}</strong
              ><small>题</small>
            </article>
            <article class="metric-card">
              <span>总体正确率</span><strong>{{ percent(exercise.accuracy) }}</strong
              ><small>近30天</small>
            </article>
            <article class="metric-card">
              <span>有错题学生</span><strong>{{ exercise.students_with_wrong ?? 0 }}</strong
              ><small>人</small>
            </article>
          </div>
          <a-table
            class="knowledge-table"
            :columns="knowledgeColumns"
            :data-source="exercise.knowledge_points || []"
            :pagination="{ pageSize: 8, showTotal: (total) => `共 ${total} 个知识点` }"
            row-key="knowledge_point"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'accuracy'">{{ percent(record.accuracy) }}</template>
            </template>
          </a-table>
          <a-empty v-if="!exercise.knowledge_points?.length" description="暂无习题记录" />
        </section>

        <section class="section-block panel-card">
          <div class="section-heading">
            <div>
              <h2>学生详情</h2>
              <p>选择学生查看提问、作答、错题知识点和阅读位置</p>
            </div>
            <a-input-search
              v-model:value="studentFilter"
              placeholder="按姓名或学号筛选"
              allow-clear
              style="max-width: 260px"
            />
          </div>
          <a-table
            :columns="studentColumns"
            :data-source="filteredStudents"
            :loading="loadingStudents"
            :pagination="{ pageSize: 8, showTotal: (total) => `共 ${total} 名学生` }"
            row-key="id"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'last_login'">{{
                formatDate(record.last_login)
              }}</template>
              <template v-if="column.key === 'actions'"
                ><a-button type="link" @click="showStudent(record)">查看详情</a-button></template
              >
            </template>
          </a-table>
        </section>
      </a-spin>

      <a-modal
        v-model:open="studentModalOpen"
        :title="summary?.student?.student_name || '学生学情详情'"
        width="760px"
        :footer="null"
        destroy-on-close
      >
        <a-spin :spinning="loadingSummary">
          <template v-if="summary">
            <p class="detail-meta">
              学号：{{ summary.student.user_login }} · 最近活动：{{
                formatDate(summary.latest_activity)
              }}
            </p>
            <div class="metric-grid metric-grid--compact">
              <article class="metric-card">
                <span>AI提问数</span><strong>{{ summary.question_count }}</strong
                ><small>学生消息</small>
              </article>
              <article class="metric-card">
                <span>做题量</span><strong>{{ summary.attempt_count }}</strong
                ><small>题</small>
              </article>
              <article class="metric-card">
                <span>正确率</span><strong>{{ percent(summary.accuracy) }}</strong
                ><small>全部作答</small>
              </article>
              <article class="metric-card">
                <span>错题数</span><strong>{{ summary.wrong_count }}</strong
                ><small>题</small>
              </article>
            </div>
            <h3>错题知识点</h3>
            <a-table
              :columns="studentWrongColumns"
              :data-source="summary.wrong_knowledge_points"
              :pagination="false"
              row-key="knowledge_point"
              size="small"
            />
            <h3>最后阅读位置</h3>
            <a-table
              :columns="readingColumns"
              :data-source="summary.reading_positions"
              :pagination="false"
              row-key="book_id"
              size="small"
            >
              <template #bodyCell="{ column, record }"
                ><template v-if="column.key === 'updated_at'">{{
                  formatDate(record.updated_at)
                }}</template></template
              >
            </a-table>
            <p class="detail-meta">
              学习时长未统计：当前没有可用于计算时长的开始、暂停和结束记录。
            </p>
          </template>
        </a-spin>
      </a-modal>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { InfoCircleOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import CourseTopbar from '@/components/course/CourseTopbar.vue'
import CoursePageHero from '@/components/course/CoursePageHero.vue'
import { useUserStore } from '@/stores/user'
import { dashboardApi } from '@/apis/dashboard_api'
import dayjs from '@/utils/time'

const userStore = useUserStore()
const data = ref({})
const students = ref([])
const loading = ref(false)
const loadingStudents = ref(false)
const studentFilter = ref('')
const studentModalOpen = ref(false)
const loadingSummary = ref(false)
const summary = ref(null)
const exercise = computed(() => data.value.exercise || {})
const heatmap = computed(() => data.value.activity_heatmap || { days: [], slots: [] })
const handleLogout = () => userStore.logout()
const handleSwitchAccount = () => userStore.logout()

const knowledgeColumns = [
  { title: '知识点', dataIndex: 'knowledge_point', key: 'knowledge_point' },
  { title: '作答数', dataIndex: 'attempt_count', key: 'attempt_count', width: 100 },
  { title: '错题数', dataIndex: 'wrong_count', key: 'wrong_count', width: 100 },
  { title: '正确率', dataIndex: 'accuracy', key: 'accuracy', width: 100 }
]
const studentColumns = [
  { title: '姓名', dataIndex: 'student_name', key: 'student_name' },
  { title: '学号', dataIndex: 'user_login', key: 'user_login' },
  { title: '最近登录', dataIndex: 'last_login', key: 'last_login' },
  { title: '操作', key: 'actions', width: 100 }
]
const studentWrongColumns = [
  { title: '知识点', dataIndex: 'knowledge_point', key: 'knowledge_point' },
  { title: '错题数', dataIndex: 'count', key: 'count', width: 100 }
]
const readingColumns = [
  { title: '书籍', dataIndex: 'book_id', key: 'book_id' },
  { title: '最后阅读页', dataIndex: 'page', key: 'page', width: 120 },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at' }
]
const filteredStudents = computed(() => {
  const term = studentFilter.value.trim().toLowerCase()
  if (!term) return students.value
  return students.value.filter((student) =>
    `${student.student_name || ''} ${student.user_login || ''}`.toLowerCase().includes(term)
  )
})
const trendRecent = computed(() =>
  (data.value.trend_14_days || []).filter((item) => item.period === 'recent')
)
const trendPrevious = computed(() =>
  (data.value.trend_14_days || []).filter((item) => item.period === 'previous')
)
const chartMax = computed(() =>
  Math.max(4, ...[...trendRecent.value, ...trendPrevious.value].map((item) => item.questions))
)
const chartX = (index) => 64 + index * 96
const chartY = (tick) => 20 + tick * 40
const chartValueY = (value) => 180 - (value / chartMax.value) * 160
const chartPoints = (items) =>
  items.map((item, index) => `${chartX(index)},${chartValueY(item.questions)}`).join(' ')
const barWidth = (count) =>
  `${data.value.student_count ? Math.min(100, (count / data.value.student_count) * 100) : 0}%`
const heatmapMax = computed(() =>
  Math.max(
    1,
    ...heatmap.value.slots.flatMap((slot) => slot.cells.map((cell) => cell.active_students))
  )
)
const heatColor = (count) => {
  const opacity = count ? 0.12 + (count / heatmapMax.value) * 0.72 : 0.08
  return `rgba(52, 211, 153, ${opacity})`
}
const percent = (value) => (value == null ? '—' : `${(value * 100).toFixed(1)}%`)
const formatDate = (value) =>
  value && dayjs(value).isValid() ? dayjs(value).format('YYYY-MM-DD HH:mm') : '—'

async function loadData() {
  loading.value = true
  loadingStudents.value = true
  try {
    const [analysis, studentRows] = await Promise.all([
      dashboardApi.getLearningAnalysis(),
      dashboardApi.getStudents()
    ])
    data.value = analysis
    students.value = studentRows
  } catch (error) {
    console.error('加载学情分析失败:', error)
    message.error('加载学情分析失败')
  } finally {
    loading.value = false
    loadingStudents.value = false
  }
}

async function showStudent(student) {
  studentModalOpen.value = true
  loadingSummary.value = true
  summary.value = null
  try {
    summary.value = await dashboardApi.getStudentLearningSummary(student.id)
  } catch (error) {
    console.error('加载学生学情详情失败:', error)
    message.error('加载学生学情详情失败')
    studentModalOpen.value = false
  } finally {
    loadingSummary.value = false
  }
}

onMounted(loadData)
</script>

<style scoped lang="less">
.learning-main {
  padding-bottom: 48px;
}
.hero-description {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: -4px 0 24px;
  color: var(--text-secondary);
  font-size: 15px;
}
.definition-icon {
  color: var(--accent-primary);
  cursor: help;
  font-size: 16px;
}
.definition-tooltip {
  display: grid;
  max-width: 340px;
  gap: 6px;
  line-height: 1.6;
}
.section-block {
  margin: 24px 0;
}
.section-block h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
}
.section-block p {
  margin: 6px 0 16px;
  color: var(--text-secondary);
  font-size: 13px;
}
.panel-card {
  padding: 22px;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--surface-panel);
}
.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
.metric-grid--compact {
  margin: 18px 0;
}
.metric-card {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-height: 104px;
  padding: 18px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface-panel);
}
.metric-card span {
  color: var(--text-secondary);
  font-size: 13px;
}
.metric-card strong {
  color: var(--text-primary);
  font-size: 28px;
  line-height: 1.15;
}
.metric-card small {
  color: var(--text-muted);
  font-size: 12px;
}
.legend {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}
.legend-recent,
.legend-previous {
  width: 9px;
  height: 9px;
  margin-left: 12px;
  border-radius: 50%;
  background: #3478f6;
}
.legend-previous {
  background: #95a3b8;
}
.chart-wrap {
  width: 100%;
  overflow-x: auto;
}
.chart-wrap svg {
  display: block;
  width: 100%;
  min-width: 600px;
}
.grid-line {
  stroke: var(--border-subtle);
  stroke-dasharray: 3 4;
}
.axis-label {
  fill: var(--text-muted);
  font-size: 11px;
}
.line-recent,
.line-previous {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.line-recent {
  stroke: #3478f6;
}
.line-previous {
  stroke: #95a3b8;
}
.dot-recent {
  fill: #3478f6;
}
.dot-previous {
  fill: #95a3b8;
}
.analysis-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.heatmap-card {
  margin-top: 24px;
}
.heatmap-grid {
  display: grid;
  grid-template-columns: 58px repeat(7, minmax(28px, 1fr));
  align-items: center;
  gap: 3px;
  margin-top: 12px;
}
.heatmap-day,
.heatmap-time {
  color: var(--text-muted);
  font-size: 11px;
  text-align: center;
  white-space: nowrap;
}
.heatmap-day {
  padding-bottom: 4px;
}
.heatmap-time {
  padding-right: 6px;
  text-align: right;
}
.heatmap-cell {
  display: block;
  height: 36px;
  border: 1px solid rgba(31, 95, 153, 0.04);
  border-radius: 3px;
  cursor: default;
  outline-offset: 2px;
}
.heatmap-cell:hover {
  outline: 1px solid var(--accent-primary);
}
.heatmap-bottom {
  height: 1px;
}
.bar-list {
  display: grid;
  gap: 15px;
  margin-top: 22px;
}
.bar-row {
  display: grid;
  grid-template-columns: 76px 1fr 48px;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 12px;
}
.bar-row b {
  color: var(--text-primary);
  font-weight: 500;
  text-align: right;
}
.bar-track {
  height: 10px;
  overflow: hidden;
  border-radius: 6px;
  background: var(--surface-page-alt);
}
.bar-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--accent-primary);
}
.knowledge-table {
  margin-top: 18px;
}
.detail-meta {
  color: var(--text-secondary);
  font-size: 13px;
}
h3 {
  margin: 20px 0 10px;
  font-size: 15px;
}
@media (max-width: 760px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .analysis-grid {
    grid-template-columns: 1fr;
  }
  .section-heading {
    flex-direction: column;
  }
  .heatmap-grid {
    grid-template-columns: 46px repeat(7, minmax(22px, 1fr));
    gap: 2px;
  }
  .heatmap-cell {
    height: 28px;
  }
}
</style>
