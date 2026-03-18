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
            <router-link to="/mall" class="exercises-nav-link" :class="{ active: $route.path === '/mall' }">积分商城</router-link>
            <router-link v-if="userStore.isAdmin" to="/ops" class="exercises-nav-link" :class="{ active: $route.path === '/ops' }">运维</router-link>
            <router-link to="/guide" class="exercises-nav-link" :class="{ active: $route.path === '/guide' }">使用指南</router-link>
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
        <p class="exercises-subtitle">选择章节与题型数量，一次生成小测；默认按错题情况个性化抽取知识点</p>
      </div>

      <!-- 题型 + 知识点选择 -->
      <section class="exercises-select-section">
        <h2 class="exercises-section-title">选择题型</h2>
        <div class="exercises-type-row">
          <div
            v-for="t in questionTypes"
            :key="t.value"
            class="exercises-type-option"
            :class="{ 'exercises-type-option--selected': questionTypeCounts[t.value] > 0 }"
          >
            <label class="exercises-type-option-check">
              <input
                type="checkbox"
                :checked="questionTypeCounts[t.value] > 0"
                @change="toggleQuestionType(t.value)"
              />
              <span class="exercises-type-option-label">{{ t.label }}</span>
            </label>
            <input
              class="exercises-type-qty-input"
              type="number"
              min="1"
              step="1"
              :disabled="questionTypeCounts[t.value] === 0"
              v-model.number="questionTypeCounts[t.value]"
              @change="onQuestionTypeQtyChange(t.value)"
            />
          </div>
        </div>

        <h2 class="exercises-section-title">选择章节</h2>
        <div v-if="chaptersLoading" class="exercises-chapters-loading">加载章节目录中…</div>
        <div v-else-if="chaptersError" class="exercises-chapters-error">
          {{ chaptersError }}
          <button type="button" class="exercises-retry-btn" @click="loadChapters">重试</button>
        </div>
        <div v-else class="exercises-knowledge-grid">
          <button
            v-for="ch in chapters"
            :key="ch.id"
            type="button"
            class="exercises-knowledge-btn"
            :style="isChapterSelected(ch.id) ? selectedBtnStyle : undefined"
            @click="onSelectChapter(ch)"
          >
            {{ ch.title }}
          </button>
        </div>

        <h2 v-if="selectedChapter" class="exercises-section-title">选择知识点(可多选)</h2>
        <div v-if="selectedChapter" class="exercises-knowledge-grid">
          <button
            v-for="kp in selectedChapter.knowledge_points"
            :key="kp.id"
            type="button"
            class="exercises-knowledge-btn"
          :style="isKnowledgePointSelected(kp.id) ? selectedBtnStyle : undefined"
          @click="toggleKnowledgePoint(kp.id)"
          >
            {{ kp.title }}
          </button>
        </div>

        <div class="exercises-generate-row">
          <button
            type="button"
            class="exercises-generate-btn"
            :style="primaryBtnStyle"
          :disabled="!selectedChapter || totalQuestionCount <= 0 || generating"
            @click="doGenerate"
          >
            {{ generating ? '生成中…' : '生成题目' }}
          </button>
        <button
          type="button"
          class="exercises-clear-quiz-btn"
          :disabled="!quizQuestions.length || generating"
          @click="clearQuiz"
        >
          清除本次小测
        </button>
        </div>
      <p v-if="totalQuestionCount > 10" class="exercises-quiz-limit-hint">
        本次小测最多 10 道题（将自动截断生成到 10 道）
      </p>
      </section>

      <!-- 题目与作答 -->
      <section v-if="currentQuestion.content" class="exercises-question-section">
        <div class="exercises-question-card">
          <div v-if="currentQuestion.textbook_used" class="exercises-textbook-badge-row">
            <p class="exercises-textbook-badge">
              本题结合课本：第{{ currentQuestion.chapter }}章
              <template v-if="currentQuestion.section_id"> §{{ currentQuestion.section_id }}</template>
              <template v-if="currentQuestion.section_title"> {{ currentQuestion.section_title }}</template>
            </p>
            <button type="button" class="exercises-detail-btn" @click="textbookDetailVisible = true">详情</button>
          </div>
          <div class="exercises-question-body">
            <p class="exercises-question-text">{{ currentQuestion.content }}</p>
            <div v-if="currentQuestion.question_type === 'choice' && currentQuestion.options?.length" class="exercises-options">
              <div
                v-for="(opt, idx) in currentQuestion.options"
                :key="idx"
                class="exercises-option-row"
              >
                <input
                  :id="'opt-' + idx"
                  type="radio"
                  name="q-option"
                  :value="opt.charAt(0)"
                  v-model="userAnswer"
                  class="exercises-option-radio"
                />
                <label :for="'opt-' + idx" class="exercises-option-label">{{ opt }}</label>
              </div>
            </div>
          </div>
          <div v-if="!submitted" class="exercises-answer-area">
            <template v-if="currentQuestion.question_type === 'choice'">
              <p class="exercises-answer-hint">请在上方选择选项后提交。</p>
            </template>
            <template v-else>
              <textarea
                v-model="userAnswer"
                class="exercises-answer-input"
                placeholder="请输入你的答案（仅可提交一次）"
                rows="4"
              />
            </template>
            <button
              type="button"
              class="exercises-submit-btn"
              :style="primaryBtnStyle"
              :disabled="!canSubmit || submitting"
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
            <div v-if="resultExplanation" class="exercises-result-explanation-block">
              <h4 class="exercises-result-explanation-title">详细解析</h4>
              <div
                class="exercises-result-explanation exercises-result-explanation-markdown"
                v-html="renderTextbookMarkdown(resultExplanation)"
              />
            </div>
            <div class="exercises-quiz-actions">
              <button
                v-if="currentQuestionIndex > 0"
                type="button"
                class="exercises-prev-btn"
                @click="goPrevQuestion"
              >
                上一题
              </button>
              <button type="button" class="exercises-next-btn" @click="goNextQuestion">
                {{ currentQuestionIndex + 1 >= quizQuestions.length ? '完成小测' : '下一题' }}
              </button>
            </div>
          </div>
        </div>
      </section>
      <section v-else-if="quizFinished" class="exercises-empty-hint">
        本次小测已完成。你可以修改题型数量/知识点集合后再次点击「生成题目」。
      </section>
      <section v-else class="exercises-empty-hint">
        请先选择题型数量与章节，再点击「生成题目」开始练习（知识点可选）。
      </section>
    </main>

    <!-- 课本引用详情弹窗 -->
    <a-modal
      v-model:open="textbookDetailVisible"
      title="本题引用的课本内容"
      width="720"
      :footer="null"
      destroy-on-close
    >
      <div class="exercises-textbook-detail">
        <p class="exercises-textbook-detail-meta">
          第{{ currentQuestion.chapter }}章
          <template v-if="currentQuestion.section_id"> §{{ currentQuestion.section_id }}</template>
          <template v-if="currentQuestion.section_title"> {{ currentQuestion.section_title }}</template>
        </p>
        <div
          class="exercises-textbook-detail-content exercises-textbook-detail-markdown"
          v-html="renderTextbookMarkdown(currentQuestion.textbook_excerpt || '')"
        />
      </div>
    </a-modal>

    <!-- 错题分析弹窗：forceRender 保证打开时插槽已挂载、ref 可用，避免 destroy-on-close 导致内容延迟挂载显示不出 -->
    <a-modal
      v-model:open="wrongModalVisible"
      title="错题情况分析"
      width="720"
      :footer="null"
      :force-render="true"
      @afterOpenChange="onWrongModalOpen"
    >
      <div class="wrong-modal-content">
        <p class="wrong-debug-line">
          <span v-if="wrongAnalysisLoading">加载中…</span>
          <span v-else-if="wrongStatsLoadError || wrongListLoadError" class="wrong-debug-error">
            接口加载失败（请确认已登录）。
            <span v-if="wrongStatsErrorMessage">{{ wrongStatsErrorMessage }}</span>
            <a href="javascript:void(0)" @click.prevent="retryWrongLoad">重试</a>
          </span>
          <span v-else>
            当前账号（{{ wrongApiUserLogin || currentUserLabel }}）
            共 <strong>{{ wrongTotalAttempts ?? '—' }}</strong> 次作答，<strong>{{ wrongTotal }}</strong> 道错题
            按知识点：{{ (wrongStats || []).length }} 个
            <a href="javascript:void(0)" class="wrong-refresh-btn" @click.prevent="refreshWrongAnalysis" :class="{ loading: wrongAnalysisLoading }">刷新</a>
          </span>
        </p>
        <div ref="wrongChartRef" class="wrong-chart" />
        <div class="wrong-list">
          <h4>错题记录</h4>
          <div v-if="wrongList.length === 0" class="wrong-list-empty">
            <template v-if="wrongAnalysisLoading">加载错题记录中…</template>
            <template v-else-if="!wrongStatsLoadError && !wrongListLoadError">
              <template v-if="wrongTotalAttempts === 0">
                未查询到当前账号的作答记录。请确认：1）提交答案时已登录且为当前账号「{{ wrongApiUserLogin || currentUserLabel }}」；2）运维中若能看到作答记录，请确认筛选的用户与此处一致；3）提交后刷新或重新打开本弹窗。
                <span v-if="wrongDebugTableTotal != null" class="wrong-list-empty-hint">（表中总记录数：{{ wrongDebugTableTotal }}，若大于 0 说明其他用户有数据，当前账号筛选结果为空）</span>
              </template>
              <template v-else>
                暂无错题记录。答错题目并提交后，将在此显示按知识点的错题统计（环状图）与错题列表。
                <br /><span class="wrong-list-empty-hint">此处仅显示当前登录账号的错题；运维中的做题记录包含所有用户。</span>
              </template>
            </template>
            <template v-else>加载失败或未登录，请重试。</template>
          </div>
          <div v-else class="wrong-list-items">
            <div v-for="item in wrongList" :key="item.id" class="wrong-list-item">
              <div class="wrong-item-question wrong-item-markdown" v-html="renderTextbookMarkdown(item.question_content || '')"></div>
              <p class="wrong-item-meta">
            {{ item.question_type === 'choice' ? '选择题' : item.question_type === 'fill' ? '填空题' : '简答题' }}
            · 知识点：{{ item.knowledge_point }}
            {{ item.section_title ? ` · ${item.section_title}` : '' }}
          </p>
              <div v-if="item.user_answer" class="wrong-item-answer">
                <strong>你的答案：</strong>
                <div class="wrong-item-markdown" v-html="renderTextbookMarkdown(item.user_answer)"></div>
              </div>
              <div v-if="item.explanation" class="wrong-item-explanation wrong-item-markdown" v-html="renderTextbookMarkdown(item.explanation)"></div>
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
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { marked } from 'marked'
import * as echarts from 'echarts'
import {
  getTextbookChapters,
  exerciseQuizGenerate,
  exerciseSubmit,
  exerciseWrongAnalysis,
  exerciseWrongList,
  getPoints
} from '@/apis/courseApi'

const router = useRouter()
const userStore = useUserStore()
const handleLogout = () => {
  userStore.logout()
}
const handleSwitchAccount = () => {
  userStore.logout()
}

const questionTypes = [
  { value: 'choice', label: '选择题' },
  { value: 'fill', label: '填空题' },
  { value: 'short_answer', label: '简答题' }
]

const chapters = ref([])
const chaptersLoading = ref(true)
const chaptersError = ref('')
const selectedChapterId = ref(null)
const selectedKnowledgePointIds = ref([])
const quizQuestions = ref([])
const quizSubmissions = ref([]) // 每题是否已提交 + 判题结果，用于支持返回上一题
const currentQuestionIndex = ref(0)
const quizFinished = ref(false)
const questionTypeCounts = ref({
  choice: 0,
  fill: 0,
  short_answer: 0
})
const selectedChapter = computed(() => {
  if (selectedChapterId.value == null) return null
  return chapters.value.find((c) => String(c.id) === String(selectedChapterId.value)) ?? null
})

const selectedBtnStyle = { backgroundColor: '#1A365D', color: '#fff', borderColor: '#1A365D' }
const primaryBtnStyle = { backgroundColor: '#1A365D', color: '#fff' }

function isChapterSelected(id) {
  return selectedChapterId.value != null && String(selectedChapterId.value) === String(id)
}
function toggleQuestionType(type) {
  const cur = Number(questionTypeCounts.value[type] ?? 0)
  if (cur > 0) {
    questionTypeCounts.value[type] = 0
    return
  }
  questionTypeCounts.value[type] = 1
}

function onQuestionTypeQtyChange(type) {
  const v = Number(questionTypeCounts.value[type] ?? 0)
  if (!Number.isFinite(v) || v < 1) {
    questionTypeCounts.value[type] = 0
    return
  }
  questionTypeCounts.value[type] = Math.floor(v)
}

const totalQuestionCount = computed(() => {
  return Object.values(questionTypeCounts.value).reduce((sum, v) => sum + (Number(v) > 0 ? Number(v) : 0), 0)
})

function toggleKnowledgePoint(id) {
  const idx = selectedKnowledgePointIds.value.findIndex((x) => String(x) === String(id))
  if (idx >= 0) {
    selectedKnowledgePointIds.value.splice(idx, 1)
    return
  }
  selectedKnowledgePointIds.value.push(id)
}

function isKnowledgePointSelected(id) {
  return selectedKnowledgePointIds.value.some((x) => String(x) === String(id))
}

function renderTextbookMarkdown(text) {
  if (!text || !text.trim()) return ''
  try {
    return marked.parse(text.trim(), { gfm: true, breaks: true })
  } catch {
    return text.replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
}
const generating = ref(false)
const EMPTY_QUESTION = {
  content: '',
  correct_answer: '',
  scoring_points: [],
  question_type: '',
  options: [],
  textbook_used: false,
  chapter: null,
  section_id: null,
  section_title: '',
  textbook_excerpt: '',
  knowledge_point: ''
}
const currentQuestion = ref({ ...EMPTY_QUESTION })
const userAnswer = ref('')
const submitted = ref(false)
const submitting = ref(false)
const resultCorrect = ref(false)
const resultExplanation = ref('')
const pointsDisplay = computed(() => userStore.userPoints === null ? '—' : (userStore.userPoints ?? 0))
const currentUserLabel = computed(() => userStore.username || userStore.userIdLogin || '当前用户')

const canSubmit = computed(() => {
  if (currentQuestion.value.question_type === 'choice') {
    return ['A', 'B', 'C', 'D'].includes(String(userAnswer.value).trim().toUpperCase())
  }
  return String(userAnswer.value).trim().length > 0
})

function onSelectChapter(ch) {
  selectedChapterId.value = ch.id
  selectedKnowledgePointIds.value = []
}

async function loadChapters() {
  chaptersLoading.value = true
  chaptersError.value = ''
  try {
    const res = await getTextbookChapters()
    chapters.value = res.chapters || []
    if (!chapters.value.length) {
      chaptersError.value = '章节目录为空，请稍后重试'
    }
  } catch (e) {
    chapters.value = []
    chaptersError.value = '章节目录加载失败，请重试'
    console.error('loadChapters failed:', e)
  } finally {
    chaptersLoading.value = false
  }
}

const textbookDetailVisible = ref(false)
const wrongModalVisible = ref(false)
const wrongChartRef = ref(null)
const wrongStats = ref([])
const wrongList = ref([])
const wrongAnalysisLoading = ref(false) // 正在拉取错题分析，用于显示「加载中」
const wrongStatsLoadError = ref(false)
const wrongListLoadError = ref(false)
const wrongStatsErrorMessage = ref('') // 错题统计接口失败时的错误信息，便于排查
const wrongTotal = ref(0)
const wrongTotalAttempts = ref(null) // 该账号总作答次数（含对错），null 表示未拉取
const wrongApiUserLogin = ref('') // 接口返回的当前账号登录名，与后端一致便于排查
const wrongDebugTableTotal = ref(null) // 无数据时后端返回的 exercise_attempts 表总行数，便于排查
const wrongPage = ref(1)
const pageSize = 20

async function loadPoints() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await getPoints()
    userStore.setUserPoints(res.points ?? 0)
  } catch (_) {}
}

function getQuizStorageKey() {
  const login = String(userStore.userIdLogin || '').trim()
  return `course_exercises_quiz_v1_${login || 'anon'}`
}

function saveQuizState() {
  try {
    const payload = {
      chapterId: selectedChapterId.value,
      questionTypeCounts: questionTypeCounts.value,
      selectedKnowledgePointIds: selectedKnowledgePointIds.value,
      quizQuestions: quizQuestions.value,
      quizSubmissions: quizSubmissions.value,
      currentQuestionIndex: currentQuestionIndex.value,
      quizFinished: quizFinished.value
    }
    localStorage.setItem(getQuizStorageKey(), JSON.stringify(payload))
  } catch (e) {
    // localStorage 可能在无痕/受限环境不可用，这里静默失败即可
  }
}

function syncCurrentQuestionUI() {
  const idx = currentQuestionIndex.value
  const q = quizQuestions.value[idx]
  currentQuestion.value = q ? q : { ...EMPTY_QUESTION }

  const sub = quizSubmissions.value[idx]
  if (sub && sub.user_answer != null) {
    userAnswer.value = String(sub.user_answer ?? '')
    submitted.value = true
    resultCorrect.value = Number(sub.is_correct) === 1
    resultExplanation.value = String(sub.explanation ?? '')
  } else {
    userAnswer.value = ''
    submitted.value = false
    resultCorrect.value = false
    resultExplanation.value = ''
  }
}

function restoreQuizState() {
  try {
    const raw = localStorage.getItem(getQuizStorageKey())
    if (!raw) return
    const saved = JSON.parse(raw)
    if (!saved?.quizQuestions || !Array.isArray(saved.quizQuestions) || saved.quizQuestions.length === 0) return

    selectedChapterId.value = saved.chapterId ?? null
    questionTypeCounts.value = saved.questionTypeCounts || { choice: 0, fill: 0, short_answer: 0 }
    selectedKnowledgePointIds.value = Array.isArray(saved.selectedKnowledgePointIds) ? saved.selectedKnowledgePointIds : []

    quizQuestions.value = saved.quizQuestions
    quizSubmissions.value = Array.isArray(saved.quizSubmissions) ? saved.quizSubmissions : []
    currentQuestionIndex.value = Number(saved.currentQuestionIndex ?? 0)
    quizFinished.value = Boolean(saved.quizFinished)

    currentQuestionIndex.value = Math.min(Math.max(currentQuestionIndex.value, 0), quizQuestions.value.length - 1)
    syncCurrentQuestionUI()
  } catch (_) {
    // 解析失败直接忽略恢复
  }
}

function clearQuiz() {
  try {
    localStorage.removeItem(getQuizStorageKey())
  } catch (_) {}
  quizQuestions.value = []
  quizSubmissions.value = []
  currentQuestionIndex.value = 0
  quizFinished.value = false
  currentQuestion.value = { ...EMPTY_QUESTION }
  userAnswer.value = ''
  submitted.value = false
  resultCorrect.value = false
  resultExplanation.value = ''
}

async function doGenerate() {
  if (!selectedChapter.value) return
  if (totalQuestionCount.value <= 0) return

  // 单次小测最多 10 道，按题型顺序截断（choice -> fill -> short_answer）
  let remain = 10
  const questionTypeCountsPayload = {}
  for (const t of questionTypes) {
    if (remain <= 0) break
    const requested = Math.floor(Number(questionTypeCounts.value[t.value] ?? 0))
    if (!Number.isFinite(requested) || requested <= 0) continue
    const take = Math.min(requested, remain)
    if (take > 0) questionTypeCountsPayload[t.value] = take
    remain -= take
  }
  if (!Object.keys(questionTypeCountsPayload).length) return

  generating.value = true
  quizFinished.value = false
  quizQuestions.value = []
  quizSubmissions.value = []
  currentQuestionIndex.value = 0
  currentQuestion.value = { ...EMPTY_QUESTION }
  userAnswer.value = ''
  submitted.value = false

  try {
    const res = await exerciseQuizGenerate({
      chapter: selectedChapter.value.id,
      question_type_counts: questionTypeCountsPayload,
      knowledge_point_ids: selectedKnowledgePointIds.value
    })

    quizQuestions.value = Array.isArray(res?.questions) ? res.questions : []
    quizSubmissions.value = new Array(quizQuestions.value.length).fill(null)
    currentQuestionIndex.value = 0
    syncCurrentQuestionUI()
    saveQuizState()
  } catch (e) {
    console.error(e)
    // 失败时保持空状态，用户可重新操作
  } finally {
    generating.value = false
  }
}

async function doSubmit() {
  if (!canSubmit.value || !currentQuestion.value.content) return
  submitting.value = true
  const knowledgePoint = currentQuestion.value.knowledge_point ? String(currentQuestion.value.knowledge_point) : ''
  let answerToSend = String(userAnswer.value).trim()
  if (currentQuestion.value.question_type === 'choice') {
    answerToSend = answerToSend.toUpperCase().charAt(0)
  }
  let questionContent = currentQuestion.value.content
  if (currentQuestion.value.question_type === 'choice' && currentQuestion.value.options?.length) {
    questionContent = currentQuestion.value.content + '\n\n' + currentQuestion.value.options.join('\n')
  }
  try {
    const res = await exerciseSubmit({
      question_type: currentQuestion.value.question_type,
      knowledge_point: knowledgePoint,
      question_content: questionContent,
      correct_answer: currentQuestion.value.correct_answer,
      scoring_points: currentQuestion.value.scoring_points || [],
      user_answer: answerToSend,
      chapter: currentQuestion.value.chapter != null ? String(currentQuestion.value.chapter) : undefined,
      section_title: currentQuestion.value.section_title || undefined
    })
    resultCorrect.value = res.is_correct === 1
    resultExplanation.value = res.explanation || ''
    submitted.value = true
    quizSubmissions.value[currentQuestionIndex.value] = {
      user_answer: answerToSend,
      is_correct: res.is_correct,
      explanation: res.explanation || ''
    }
    saveQuizState()
    await loadPoints()
  } catch (e) {
    console.error(e)
  } finally {
    submitting.value = false
  }
}

function goNextQuestion() {
  // 如果是最后一题：不清空题目，只标记“已完成”，避免用户误触导致内容消失
  if (currentQuestionIndex.value + 1 >= quizQuestions.value.length) {
    quizFinished.value = true
    saveQuizState()
    return
  }

  currentQuestionIndex.value += 1
  quizFinished.value = false
  syncCurrentQuestionUI()
  saveQuizState()
}

function goPrevQuestion() {
  if (currentQuestionIndex.value <= 0) return
  currentQuestionIndex.value -= 1
  quizFinished.value = false
  syncCurrentQuestionUI()
  saveQuizState()
}

function openWrongModal() {
  wrongModalVisible.value = true
}

// 监听弹窗显隐：打开时主动拉取数据并绘图，避免依赖 afterOpenChange（部分环境下首次打开可能不触发）
watch(wrongModalVisible, async (open) => {
  if (open) {
    wrongStatsLoadError.value = false
    wrongListLoadError.value = false
    wrongStatsErrorMessage.value = ''
    wrongPage.value = 1
    await loadWrongAnalysis()
    await nextTick()
    scheduleDrawWrongChart()
  } else {
    if (wrongChartRef.value) {
      const chart = echarts.getInstanceByDom(wrongChartRef.value)
      if (chart) chart.dispose()
    }
    wrongAnalysisLoading.value = false
    wrongStatsLoadError.value = false
    wrongListLoadError.value = false
    wrongStatsErrorMessage.value = ''
    wrongApiUserLogin.value = ''
    wrongDebugTableTotal.value = null
  }
})

async function onWrongModalOpen(open) {
  if (!open) {
    if (wrongChartRef.value) {
      const chart = echarts.getInstanceByDom(wrongChartRef.value)
      if (chart) chart.dispose()
    }
    wrongAnalysisLoading.value = false
    wrongStatsLoadError.value = false
    wrongListLoadError.value = false
    wrongStatsErrorMessage.value = ''
    wrongApiUserLogin.value = ''
    wrongDebugTableTotal.value = null
  }
  // 打开时不再在此拉取数据，已由 watch(wrongModalVisible) 在打开时统一处理
}

function scheduleDrawWrongChart() {
  setTimeout(() => drawWrongChart(), 400)
}

function retryWrongLoad() {
  refreshWrongAnalysis()
}

/** 弹窗内刷新：重新请求错题数据并重绘图表 */
function refreshWrongAnalysis() {
  wrongStatsLoadError.value = false
  wrongListLoadError.value = false
  wrongStatsErrorMessage.value = ''
  wrongPage.value = 1
  loadWrongAnalysis().then(() => {
    nextTick()
    scheduleDrawWrongChart()
  })
}

/** 从与运维同源的接口一次拉取错题统计 + 列表第一页，用于生成图形并显示在错题分析弹窗 */
async function loadWrongAnalysis() {
  wrongAnalysisLoading.value = true
  wrongStatsLoadError.value = false
  wrongListLoadError.value = false
  wrongStatsErrorMessage.value = ''
  wrongTotalAttempts.value = null
  wrongTotal.value = 0
  wrongStats.value = []
  wrongList.value = []
  wrongDebugTableTotal.value = null
  try {
    const res = await exerciseWrongAnalysis(wrongPage.value, pageSize)
    const byKp = res.by_knowledge_point
    const totalAttempts = res.total_attempts
    const totalWrong = res.total_wrong ?? res.total
    wrongStats.value = Array.isArray(byKp) ? byKp : []
    wrongTotalAttempts.value = totalAttempts != null ? Number(totalAttempts) : null
    wrongTotal.value = totalWrong != null ? Number(totalWrong) : 0
    wrongList.value = Array.isArray(res.items) ? res.items : []
    wrongApiUserLogin.value = res.user_login != null && res.user_login !== '' ? String(res.user_login).trim() : ''
    wrongDebugTableTotal.value = res.debug_table_total != null ? Number(res.debug_table_total) : null
    console.log('[错题分析] 接口已返回并赋值:', {
      total_attempts: wrongTotalAttempts.value,
      total_wrong: wrongTotal.value,
      user_login: wrongApiUserLogin.value,
      by_knowledge_point_count: wrongStats.value.length,
      items_count: wrongList.value.length
    })
  } catch (e) {
    wrongStatsLoadError.value = true
    wrongListLoadError.value = true
    wrongStats.value = []
    wrongList.value = []
    wrongTotalAttempts.value = null
    wrongTotal.value = 0
    const msg = e?.message || e?.detail || String(e)
    wrongStatsErrorMessage.value = msg
    message.error('加载错题分析失败，请确认已登录')
  } finally {
    wrongAnalysisLoading.value = false
  }
}

/** 翻页时拉取错题列表（与运维同源） */
async function loadWrongList() {
  wrongListLoadError.value = false
  try {
    const res = await exerciseWrongList(wrongPage.value, pageSize)
    wrongList.value = res.items || []
    wrongTotal.value = res.total ?? wrongTotal.value
    if (res.user_login != null && !wrongApiUserLogin.value) wrongApiUserLogin.value = String(res.user_login).trim()
  } catch (e) {
    wrongListLoadError.value = true
    wrongList.value = []
    console.warn('[错题分析] wrong-list 请求失败:', e)
    message.error('加载错题列表失败')
  }
}

/** 用错题统计生成环状图（与运维同源数据 by_knowledge_point），在弹窗内渲染 */
function drawWrongChart() {
  const el = wrongChartRef.value
  if (!el) return
  if (el.offsetWidth === 0 || el.offsetHeight === 0) {
    setTimeout(() => drawWrongChart(), 200)
    return
  }
  const chart = echarts.getInstanceByDom(el) || echarts.init(el)
  const data = (wrongStats.value || [])
    .filter((s) => s != null && (s.name != null || s.count != null))
    .map((s) => ({ name: (s.name && String(s.name).trim()) || '未分类', value: Number(s.count) || 0 }))
    .filter((d) => d.value > 0)
  if (!data.length) {
    chart.setOption({ title: { text: '暂无错题统计', left: 'center', top: 'center', textStyle: { fontSize: 14, color: '#999' } }, series: [] })
    chart.resize()
    return
  }
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
  chart.resize()
}

onMounted(async () => {
  await loadChapters()
  await loadPoints()
  restoreQuizState()
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

.exercises-type-option {
  flex: 1;
  min-width: 160px;
  padding: 12px 14px;
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  background-color: var(--white);
  transition: all 0.25s ease;
}

.exercises-type-option--selected {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

.exercises-type-option-check {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  user-select: none;
}

.exercises-type-option-label {
  font-size: 14px;
  color: var(--gray-600);
}

.exercises-type-option--selected .exercises-type-option-label {
  color: var(--white);
}

.exercises-type-option--selected input[type='checkbox'] {
  accent-color: #fff;
}

.exercises-type-qty-input {
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--gray-200);
  font-size: 14px;
  box-sizing: border-box;
  background: var(--white);
  color: var(--gray-600);
}

.exercises-type-option--selected .exercises-type-qty-input {
  border-color: rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.08);
  color: var(--white);
}

.exercises-chapters-loading {
  color: var(--gray-500);
  font-size: 14px;
  padding: 16px 0;
  margin-bottom: 20px;
}

.exercises-chapters-error {
  color: var(--gray-600);
  font-size: 14px;
  padding: 16px 0;
  margin-bottom: 20px;
}

.exercises-retry-btn {
  margin-left: 12px;
  padding: 4px 12px;
  border: 1px solid var(--primary-color);
  border-radius: 6px;
  background: transparent;
  color: var(--primary-color);
  font-size: 13px;
  cursor: pointer;
}

.exercises-retry-btn:hover {
  background: var(--light-bg);
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

.exercises-select-section .exercises-knowledge-btn.exercises-knowledge-btn--selected,
.exercises-select-section .exercises-knowledge-btn[data-selected='true'] {
  background-color: var(--primary-color);
  color: var(--white);
  border-color: var(--primary-color);
}

.exercises-generate-row {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
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

.exercises-clear-quiz-btn {
  padding: 10px 18px;
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  background-color: var(--white);
  color: var(--gray-600);
  font-size: 15px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s, background-color 0.2s;
  white-space: nowrap;
}

.exercises-clear-quiz-btn:hover:not(:disabled) {
  color: var(--primary-color);
  border-color: var(--primary-color);
  background-color: var(--light-bg);
}

.exercises-clear-quiz-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.exercises-quiz-limit-hint {
  margin-top: 6px;
  color: var(--gray-500);
  font-size: 13px;
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

.exercises-textbook-badge-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.exercises-textbook-badge {
  font-size: 13px;
  color: var(--gray-500);
  margin: 0;
  padding: 6px 10px;
  background-color: var(--gray-50);
  border-radius: 6px;
  border-left: 3px solid #1A365D;
  flex: 1;
}

.exercises-detail-btn {
  padding: 4px 12px;
  font-size: 13px;
  border: 1px solid #1A365D;
  border-radius: 6px;
  background: transparent;
  color: #1A365D;
  cursor: pointer;
}

.exercises-detail-btn:hover {
  background-color: var(--gray-50);
}

.exercises-textbook-detail {
  max-height: 70vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.exercises-textbook-detail-meta {
  font-size: 13px;
  color: var(--gray-500);
  margin: 0 0 12px 0;
}

.exercises-textbook-detail-content {
  flex: 1;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.7;
  color: var(--dark-text);
  padding: 12px;
  background-color: var(--gray-50);
  border-radius: 8px;
  border: 1px solid var(--gray-200);
}

.exercises-textbook-detail-markdown h1,
.exercises-textbook-detail-markdown h2,
.exercises-textbook-detail-markdown h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--dark-text);
  margin: 12px 0 6px 0;
}
.exercises-textbook-detail-markdown h1:first-child,
.exercises-textbook-detail-markdown h2:first-child,
.exercises-textbook-detail-markdown h3:first-child {
  margin-top: 0;
}
.exercises-textbook-detail-markdown strong {
  font-weight: 600;
  color: var(--dark-text);
}
.exercises-textbook-detail-markdown p {
  margin: 0 0 8px 0;
}
.exercises-textbook-detail-markdown p:last-child {
  margin-bottom: 0;
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

.exercises-options {
  margin-top: 16px;
}

.exercises-option-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}

.exercises-option-radio {
  margin-top: 6px;
  cursor: pointer;
}

.exercises-option-label {
  flex: 1;
  font-size: 14px;
  line-height: 1.5;
  color: var(--dark-text);
  cursor: pointer;
}

.exercises-answer-hint {
  font-size: 14px;
  color: var(--gray-500);
  margin: 0 0 12px 0;
}

.exercises-result-explanation-block {
  margin-top: 12px;
  padding: 12px;
  background-color: var(--gray-50);
  border-radius: 8px;
  border: 1px solid var(--gray-200);
}

.exercises-result-explanation-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0 0 8px 0;
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

.exercises-result-explanation-markdown strong {
  font-weight: 600;
  color: var(--dark-text);
}
.exercises-result-explanation-markdown p {
  margin: 0 0 6px 0;
}
.exercises-result-explanation-markdown p:last-child {
  margin-bottom: 0;
}
.exercises-result-explanation-markdown ul,
.exercises-result-explanation-markdown ol {
  margin: 4px 0;
  padding-left: 20px;
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

.exercises-quiz-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}

.exercises-quiz-actions .exercises-next-btn {
  margin-top: 0;
}

.exercises-prev-btn {
  padding: 8px 20px;
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  background: transparent;
  color: var(--gray-600);
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
}

.exercises-prev-btn:hover:not(:disabled) {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background-color: var(--light-bg);
}

.exercises-prev-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
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

.wrong-debug-line {
  margin: 0 0 12px 0;
  font-size: 13px;
  color: var(--gray-500);
}

.wrong-debug-line .wrong-debug-error {
  color: #cf1322;
}

.wrong-refresh-btn {
  margin-left: 12px;
  color: var(--primary-color);
  font-size: 13px;
}

.wrong-refresh-btn:hover:not(.loading) {
  text-decoration: underline;
}

.wrong-refresh-btn.loading {
  color: var(--gray-500);
  cursor: not-allowed;
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

.wrong-list-empty-hint {
  display: inline-block;
  margin-top: 8px;
  font-size: 12px;
  color: var(--gray-400);
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

.wrong-item-correct {
  margin: 0 0 4px 0;
  color: var(--primary-color, #1A365D);
  font-size: 13px;
}

.wrong-item-explanation {
  margin: 0;
  color: var(--gray-600);
  line-height: 1.4;
}

.wrong-item-answer {
  margin: 0 0 4px 0;
  line-height: 1.5;
}

/* 错题列表中的 Markdown 渲染 */
.wrong-item-markdown {
  margin-top: 2px;
}
.wrong-item-markdown p {
  margin: 2px 0 6px;
}
.wrong-item-markdown p:last-child {
  margin-bottom: 0;
}
.wrong-item-markdown ul,
.wrong-item-markdown ol {
  margin: 4px 0;
  padding-left: 20px;
}
.wrong-item-markdown code {
  background: var(--gray-200);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}
.wrong-item-markdown pre {
  margin: 6px 0;
  padding: 10px;
  background: var(--gray-200);
  border-radius: 6px;
  overflow-x: auto;
}
.wrong-item-markdown pre code {
  padding: 0;
  background: none;
}
.wrong-item-markdown strong {
  font-weight: 600;
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
