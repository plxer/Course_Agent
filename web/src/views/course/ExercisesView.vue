<template>
  <div class="exercises-container">
    <header class="exercises-header">
      <div class="exercises-header-content">
        <router-link to="/" class="exercises-logo">
          <span class="exercises-logo-text">天津大学《计算机网络》课程数智化平台</span>
        </router-link>
        <div class="exercises-right">
          <div class="exercises-nav">
            <router-link to="/conversation" class="exercises-nav-link" :class="{ active: $route.path === '/conversation' || $route.path === '/course' }">对话</router-link>
            <router-link to="/exercises" class="exercises-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>
            <router-link to="/reading" class="exercises-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
            <router-link to="/videos" class="exercises-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
            <router-link v-if="userStore.isAdmin" to="/ops" class="exercises-nav-link" :class="{ active: $route.path === '/ops' }">运维</router-link>
          </div>
          <div class="exercises-auth">
            <template v-if="!userStore.isLoggedIn">
              <router-link to="/login" class="exercises-auth-link">登录</router-link>
              <router-link to="/register" class="exercises-auth-link primary">注册</router-link>
            </template>
            <template v-else>
              <router-link to="/mall" class="exercises-points-link" title="积分商城">
                <span class="exercises-points-num">{{ pointsDisplay }}</span>
                <span class="exercises-points-label">积分</span>
              </router-link>
              <button type="button" class="exercises-auth-btn" @click="openWrongModal">错题分析</button>
              <span class="exercises-username">{{ userStore.username || userStore.userIdLogin }}</span>
              <button type="button" class="exercises-auth-btn" @click="handleSwitchAccount">切换账号</button>
              <button type="button" class="exercises-auth-btn" @click="handleLogout">退出</button>
            </template>
          </div>
        </div>
      </div>
    </header>

    <main class="exercises-main">
      <div class="exercises-title-section">
        <h1 class="exercises-title">习题推荐</h1>
        <p class="exercises-subtitle">选择题型与知识点，智能体出题；答对积 1 分，可到积分商城兑换称号</p>
      </div>

      <!-- 题型 + 知识点选择 -->
      <section class="exercises-select-section">
        <h2 class="exercises-section-title">选择题型</h2>
        <div class="exercises-type-row">
          <button
            v-for="t in questionTypes"
            :key="t.value"
            type="button"
            class="exercises-type-btn"
            :class="{ active: selectedType === t.value }"
            @click="selectedType = t.value"
          >
            {{ t.label }}
          </button>
        </div>

        <h2 class="exercises-section-title">选择知识点</h2>
        <div class="exercises-knowledge-grid">
          <button
            v-for="ch in chapters"
            :key="ch.id"
            type="button"
            class="exercises-knowledge-btn"
            :class="{ active: selectedKnowledge === ch.title }"
            @click="selectedKnowledge = ch.title"
          >
            {{ ch.title }}
          </button>
        </div>

        <div class="exercises-generate-row">
          <button
            type="button"
            class="exercises-generate-btn"
            :disabled="!selectedType || !selectedKnowledge || generating"
            @click="doGenerate"
          >
            {{ generating ? '生成中…' : '生成题目' }}
          </button>
        </div>
      </section>

      <!-- 题目与作答 -->
      <section v-if="currentQuestion.content" class="exercises-question-section">
        <div class="exercises-question-card">
          <div class="exercises-question-body">
            <p class="exercises-question-text">{{ currentQuestion.content }}</p>
          </div>
          <div v-if="!submitted" class="exercises-answer-area">
            <textarea
              v-model="userAnswer"
              class="exercises-answer-input"
              placeholder="请输入你的答案（仅可提交一次）"
              rows="4"
            />
            <button
              type="button"
              class="exercises-submit-btn"
              :disabled="!userAnswer.trim() || submitting"
              @click="doSubmit"
            >
              {{ submitting ? '批改中…' : '提交答案' }}
            </button>
          </div>
          <div v-else class="exercises-result-area">
            <div class="exercises-result-badge" :class="resultCorrect ? 'correct' : 'wrong'">
              {{ resultCorrect ? '回答正确' : '回答错误' }}
            </div>
            <p class="exercises-result-answer">你的答案：{{ userAnswer }}</p>
            <p v-if="resultExplanation" class="exercises-result-explanation">{{ resultExplanation }}</p>
            <button type="button" class="exercises-next-btn" @click="resetQuestion">再做一题</button>
          </div>
        </div>
      </section>
      <section v-else class="exercises-empty-hint">
        请选择题型与知识点，点击「生成题目」开始练习。
      </section>
    </main>

    <!-- 错题分析弹窗 -->
    <a-modal
      v-model:open="wrongModalVisible"
      title="错题情况分析"
      width="720"
      :footer="null"
      destroy-on-close
      @afterOpenChange="onWrongModalOpen"
    >
      <div class="wrong-modal-content">
        <div ref="wrongChartRef" class="wrong-chart" />
        <div class="wrong-list">
          <h4>错题记录</h4>
          <div v-if="wrongList.length === 0" class="wrong-list-empty">暂无错题记录</div>
          <div v-else class="wrong-list-items">
            <div v-for="item in wrongList" :key="item.id" class="wrong-list-item">
              <p class="wrong-item-question">{{ item.question_content }}</p>
              <p class="wrong-item-meta">知识点：{{ item.knowledge_point }} · 你的答案：{{ item.user_answer }}</p>
              <p v-if="item.explanation" class="wrong-item-explanation">{{ item.explanation }}</p>
            </div>
          </div>
          <a-pagination
            v-if="wrongTotal > pageSize"
            v-model:current="wrongPage"
            :total="wrongTotal"
            :page-size="pageSize"
            show-size-changer="false"
            @change="loadWrongList"
          />
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import * as echarts from 'echarts'
import {
  exerciseGenerate,
  exerciseSubmit,
  exerciseWrongStats,
  exerciseWrongList,
  getPoints
} from '@/apis/courseApi'

const router = useRouter()
const userStore = useUserStore()
const handleLogout = () => {
  userStore.logout()
  router.push('/course')
}
const handleSwitchAccount = () => {
  userStore.logout()
  router.push('/login')
}

const questionTypes = [
  { value: 'choice', label: '选择题' },
  { value: 'fill', label: '填空题' },
  { value: 'short_answer', label: '简答题' }
]

const chapters = [
  { id: 1, title: '第1章 计算机网络和因特网' },
  { id: 2, title: '第2章 应用层' },
  { id: 3, title: '第3章 传输层' },
  { id: 4, title: '第4章 网络层' },
  { id: 5, title: '第5章 链路层' },
  { id: 6, title: '第6章 无线网络与移动网络' }
]

const selectedType = ref('')
const selectedKnowledge = ref('')
const generating = ref(false)
const currentQuestion = ref({ content: '', correct_answer: '', scoring_points: [], question_type: '' })
const userAnswer = ref('')
const submitted = ref(false)
const submitting = ref(false)
const resultCorrect = ref(false)
const resultExplanation = ref('')
const pointsDisplay = computed(() => userStore.userPoints === null ? '—' : (userStore.userPoints ?? 0))

const wrongModalVisible = ref(false)
const wrongChartRef = ref(null)
const wrongStats = ref([])
const wrongList = ref([])
const wrongTotal = ref(0)
const wrongPage = ref(1)
const pageSize = 20

async function loadPoints() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await getPoints()
    userStore.setUserPoints(res.points ?? 0)
  } catch (_) {}
}

async function doGenerate() {
  if (!selectedType.value || !selectedKnowledge.value) return
  generating.value = true
  currentQuestion.value = {}
  userAnswer.value = ''
  submitted.value = false
  try {
    const res = await exerciseGenerate(selectedType.value, selectedKnowledge.value)
    currentQuestion.value = {
      content: res.content || '',
      correct_answer: res.correct_answer || '',
      scoring_points: res.scoring_points || [],
      question_type: res.question_type || selectedType.value
    }
  } catch (e) {
    console.error(e)
  } finally {
    generating.value = false
  }
}

async function doSubmit() {
  if (!userAnswer.value.trim() || !currentQuestion.value.content) return
  submitting.value = true
  try {
    const res = await exerciseSubmit({
      question_type: currentQuestion.value.question_type,
      knowledge_point: selectedKnowledge.value,
      question_content: currentQuestion.value.content,
      correct_answer: currentQuestion.value.correct_answer,
      scoring_points: currentQuestion.value.scoring_points || [],
      user_answer: userAnswer.value.trim()
    })
    resultCorrect.value = res.is_correct === 1
    resultExplanation.value = res.explanation || ''
    submitted.value = true
    await loadPoints()
  } catch (e) {
    console.error(e)
  } finally {
    submitting.value = false
  }
}

function resetQuestion() {
  currentQuestion.value = {}
  userAnswer.value = ''
  submitted.value = false
  resultExplanation.value = ''
}

function openWrongModal() {
  wrongModalVisible.value = true
}

async function onWrongModalOpen(open) {
  if (!open) return
  await loadWrongStats()
  await loadWrongList()
  drawWrongChart()
}

async function loadWrongStats() {
  try {
    const res = await exerciseWrongStats()
    wrongStats.value = res.by_knowledge_point || []
  } catch (_) {
    wrongStats.value = []
  }
}

async function loadWrongList() {
  try {
    const res = await exerciseWrongList(wrongPage.value, pageSize)
    wrongList.value = res.items || []
    wrongTotal.value = res.total || 0
  } catch (_) {
    wrongList.value = []
    wrongTotal.value = 0
  }
}

function drawWrongChart() {
  if (!wrongChartRef.value || !wrongStats.value.length) return
  const chart = echarts.init(wrongChartRef.value)
  const data = wrongStats.value.map((s) => ({ name: s.name, value: s.count }))
  chart.setOption({
    tooltip: { trigger: 'item' },
    color: ['#3996ae', '#5ad8a6', '#f6bd16', '#f27c7c', '#9581cc', '#6dc8ec'],
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        label: { show: true, formatter: '{b}：{c} 次' },
        data
      }
    ]
  })
}

onMounted(() => {
  loadPoints()
})
</script>

<style scoped>
/* 与课程智能体其他界面一致（VideosView / ConversationView） */
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

.exercises-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: var(--gray-50);
  min-height: 100vh;
  color: var(--dark-text);
}

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

.exercises-right {
  display: flex;
  align-items: center;
  gap: 32px;
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

.exercises-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.exercises-points-link {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 6px;
  background-color: var(--light-bg);
  color: var(--primary-color);
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s, background 0.2s;
}

.exercises-points-num {
  font-weight: 600;
}

.exercises-username {
  font-size: 14px;
  color: var(--gray-600);
  margin-right: 4px;
}

.exercises-auth-btn {
  font-size: 14px;
  padding: 6px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background-color: var(--white);
  color: var(--gray-600);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.exercises-auth-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.exercises-main {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px;
}

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

.exercises-select-section {
  margin-bottom: 32px;
}

.exercises-section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.exercises-type-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.exercises-type-btn {
  padding: 8px 16px;
  border: 1px solid var(--gray-200);
  border-radius: 20px;
  background-color: var(--white);
  color: var(--gray-600);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.exercises-type-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.exercises-type-btn.active {
  background-color: var(--primary-color);
  color: var(--white);
  border-color: var(--primary-color);
}

.exercises-knowledge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.exercises-knowledge-btn {
  padding: 8px 16px;
  border: 1px solid var(--gray-200);
  border-radius: 20px;
  background-color: var(--white);
  color: var(--gray-600);
  font-size: 14px;
  text-align: left;
  cursor: pointer;
  transition: all 0.3s ease;
}

.exercises-knowledge-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.exercises-knowledge-btn.active {
  background-color: var(--primary-color);
  color: var(--white);
  border-color: var(--primary-color);
}

.exercises-generate-row {
  margin-top: 16px;
}

.exercises-generate-btn {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  background-color: var(--primary-color);
  color: var(--white);
  font-size: 15px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.exercises-generate-btn:hover:not(:disabled) {
  background-color: #153e68;
}

.exercises-generate-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.exercises-question-section {
  margin-top: 24px;
}

.exercises-question-card {
  background-color: var(--white);
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-light);
  transition: all 0.3s ease;
}

.exercises-question-body {
  margin-bottom: 20px;
}

.exercises-question-text {
  font-size: 15px;
  line-height: 1.7;
  margin: 0;
  white-space: pre-wrap;
  color: var(--dark-text);
}

.exercises-answer-area textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  box-sizing: border-box;
}

.exercises-submit-btn {
  margin-top: 12px;
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  background-color: var(--primary-color);
  color: var(--white);
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.exercises-submit-btn:hover:not(:disabled) {
  background-color: #153e68;
}

.exercises-submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.exercises-result-area {
  padding-top: 12px;
}

.exercises-result-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
}

.exercises-result-badge.correct {
  background-color: #d1fae8;
  color: #047857;
}

.exercises-result-badge.wrong {
  background-color: #fee2e2;
  color: #b91c1c;
}

.exercises-result-answer,
.exercises-result-explanation {
  font-size: 14px;
  color: var(--gray-600);
  margin: 4px 0;
  line-height: 1.5;
}

.exercises-next-btn {
  margin-top: 16px;
  padding: 8px 20px;
  border: 1px solid var(--primary-color);
  border-radius: 8px;
  background: transparent;
  color: var(--primary-color);
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
}

.exercises-next-btn:hover {
  background-color: var(--light-bg);
}

.exercises-empty-hint {
  text-align: center;
  color: var(--gray-500);
  font-size: 14px;
  padding: 40px 0;
}

/* 错题弹窗 */
.wrong-modal-content {
  min-height: 320px;
}

.wrong-chart {
  height: 260px;
  margin-bottom: 20px;
}

.wrong-list h4 {
  font-size: 14px;
  color: var(--dark-text);
  margin: 0 0 12px 0;
}

.wrong-list-empty {
  color: var(--gray-500);
  font-size: 14px;
  padding: 16px 0;
}

.wrong-list-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--gray-200);
  font-size: 13px;
}

.wrong-item-question {
  margin: 0 0 6px 0;
  color: var(--dark-text);
  line-height: 1.5;
}

.wrong-item-meta {
  margin: 0 0 4px 0;
  color: var(--gray-500);
}

.wrong-item-explanation {
  margin: 0;
  color: var(--gray-600);
  line-height: 1.4;
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
}
</style>
