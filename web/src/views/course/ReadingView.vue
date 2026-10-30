<template>
  <div class="reading-container course-page">
    <CourseTopbar
      @logout="handleLogout"
      @switch-account="handleSwitchAccount"
      :nav-items="navItems"
    />

    <main class="reading-main page-shell" v-if="!selectedBook">
      <CoursePageHero
        eyebrow="Reading"
        title="课本伴读"
        subtitle="以结构化阅读、页码跳转和课程语境问答，建立更清晰的教材理解路径。"
      />

      <!-- 课本与讲义 -->
      <div class="reading-list-section">
        <template v-if="books.length > 0">
          <div class="reading-library-layout">
            <section class="reading-textbook-panel">
              <div class="reading-section-heading">
                <span class="reading-section-kicker">Textbook</span>
                <h2 class="reading-list-title">课本</h2>
              </div>

              <div v-if="courseTextbooks.length" class="reading-cover-list">
                <article
                  v-for="book in courseTextbooks"
                  :key="book.id"
                  class="reading-cover-card"
                  @click="selectBook(book)"
                >
                  <div class="reading-cover-frame">
                    <img
                      :src="getBookPageUrl(book.id, 1, { thumb: true })"
                      :alt="book.name"
                      class="reading-cover-img"
                      loading="lazy"
                      decoding="async"
                    />
                  </div>
                  <div class="reading-cover-info">
                    <div class="reading-card-tags">
                      <span class="reading-card-tag">{{ book.book_label || '指定课本' }}</span>
                      <span class="reading-card-tag">PDF</span>
                    </div>
                    <h3 class="reading-cover-title">{{ book.name }}</h3>
                    <div class="reading-cover-meta">
                      <span>{{ formatFileSize(book.size) }}</span>
                      <a href="#" class="reading-card-action" @click.prevent="selectBook(book)">
                        开始阅读 <RightOutlined style="margin-left: 4px" />
                      </a>
                    </div>
                  </div>
                </article>
              </div>
            </section>

            <section class="reading-material-panel">
              <div class="reading-section-heading reading-section-heading--row">
                <div>
                  <span class="reading-section-kicker">Handouts</span>
                  <h2 class="reading-list-title">讲义</h2>
                </div>
                <span class="reading-material-count">{{ handoutBooks.length }} 份</span>
              </div>

              <div v-if="handoutBooks.length" class="reading-material-list">
                <article
                  v-for="(book, index) in handoutBooks"
                  :key="book.id"
                  class="reading-material-row"
                  @click="selectBook(book)"
                >
                  <span class="reading-material-index">{{ String(index + 1).padStart(2, '0') }}</span>
                  <div class="reading-material-main">
                    <div class="reading-material-topline">
                      <span class="reading-card-tag">{{ book.book_label || '讲义' }}</span>
                      <span class="reading-card-page">{{ formatFileSize(book.size) }}</span>
                    </div>
                    <h3 class="reading-material-title">{{ book.name }}</h3>
                  </div>
                  <RightOutlined class="reading-material-arrow" />
                </article>
              </div>

              <div v-if="supplementBooks.length" class="reading-supplement-block">
                <div class="reading-section-heading reading-section-heading--compact">
                  <span class="reading-section-kicker">Reference</span>
                  <h3 class="reading-subsection-title reading-subsection-title--secondary">拓展阅读</h3>
                </div>
                <div class="reading-material-list reading-material-list--compact">
                  <article
                    v-for="book in supplementBooks"
                    :key="book.id"
                    class="reading-material-row reading-material-row--supplement"
                    @click="selectBook(book)"
                  >
                    <div class="reading-material-main">
                      <div class="reading-material-topline">
                        <span class="reading-card-tag">{{ book.book_label || '拓展阅读' }}</span>
                        <span class="reading-card-page">{{ formatFileSize(book.size) }}</span>
                      </div>
                      <h3 class="reading-material-title">{{ book.name }}</h3>
                    </div>
                    <RightOutlined class="reading-material-arrow" />
                  </article>
                </div>
              </div>
            </section>
          </div>
        </template>

        <div v-else-if="booksLoadError" class="reading-empty reading-empty--error">
          <p>{{ booksLoadError }}</p>
        </div>
        <div v-else class="reading-empty">
          <div class="reading-empty-illustration" aria-hidden="true">
            <span></span>
            <span></span>
          </div>
          <h3>暂无课本资料</h3>
          <p>
            请将 PDF 放到仓库同级目录 yuxi-knowledgebase/books（也可通过环境变量
            KNOWLEDGEBASE_DIR 指定）
          </p>
        </div>
      </div>
    </main>

    <!-- PDF 阅读器 -->
    <main class="reading-reader" v-else>
      <div class="reading-reader-header">
        <button class="reading-back-btn" type="button" @click="handleReaderBack">
          <ArrowLeftOutlined /> 返回
        </button>
        <h2 class="reading-reader-title">
          {{ selectedBook.name }} · {{ selectedBook.book_label || '课本' }}
        </h2>
        <div class="reading-page-controls">
          <button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage <= 1 || totalPages === 0"
            :title="currentPage <= 1 ? '已经是第一页' : '上一页'"
            class="page-nav-btn"
          >
            <LeftOutlined /> 上一页
          </button>
          <div class="reading-page-jump">
            <span class="reading-page-info">{{ currentPage }} / {{ totalPages || '?' }}</span>
            <div class="page-jump-input-wrapper">
              <input
                type="number"
                v-model.number="jumpPageInput"
                :min="1"
                :max="totalPages || 1"
                class="page-jump-input"
                placeholder="跳转"
                @keydown.enter="handleJumpToPage"
                @blur="handleJumpToPage"
              />
              <button
                @click="handleJumpToPage"
                class="page-jump-btn"
                :disabled="!totalPages || totalPages === 0"
                title="跳转到指定页面"
              >
                跳转
              </button>
            </div>
          </div>
          <button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage >= totalPages || totalPages === 0"
            :title="currentPage >= totalPages ? '已经是最后一页' : '下一页'"
            class="page-nav-btn"
          >
            下一页 <RightOutlined />
          </button>
          <button
            @click="toggleChatPanel"
            class="page-nav-btn chat-toggle-btn"
            :class="{ active: showChatPanel }"
            title="打开/关闭对话"
          >
            <CommentOutlined /> {{ showChatPanel ? '关闭对话' : '打开对话' }}
          </button>
          <button
            v-if="selectedText && selectedText !== '正在识别...'"
            @click="openTranslate"
            class="page-nav-btn translate-toggle-btn"
            :class="{ active: showTranslatePanel }"
            title="翻译选中内容（英译汉）"
          >
            <TranslationOutlined /> {{ showTranslatePanel ? '关闭翻译' : '翻译' }}
          </button>
        </div>
      </div>

      <div
        class="reading-reader-wrapper"
        :class="{ 'with-chat': showChatPanel || showTranslatePanel }"
      >
        <div class="reading-reader-content">
          <!-- PDF 页面显示区域 -->
          <div
            class="reading-pdf-page"
            @mousedown="startSelection"
            @mousemove="updateSelection"
            @mouseup="endSelection"
            @mouseleave="cancelSelection"
          >
            <img
              :src="currentPageImage"
              alt="PDF Page"
              class="reading-page-img"
              @load="onImageLoad"
              @error="onImageError"
              ref="pageImage"
            />
            <!-- 选择框 -->
            <div
              v-if="selection.active"
              class="reading-selection-box"
              :style="selectionStyle"
            ></div>

            <!-- 选词操作栏 - 显示在选择区域旁边 -->
            <div
              v-if="selectedText"
              class="reading-selection-bar"
              :style="selectionBarStyle"
              @mousedown.stop
              @mouseup.stop
              @click.stop
            >
              <div class="reading-selected-text"><strong>已选文本：</strong>{{ selectedText }}</div>
              <div class="reading-selection-actions" @click.stop>
                <button
                  class="reading-action-btn"
                  @click.stop.prevent="sendToConversation"
                  @mousedown.stop.prevent
                  @mouseup.stop.prevent
                  type="button"
                >
                  <CommentOutlined /> 问问AI
                </button>
                <button
                  v-if="selectedText && selectedText !== '正在识别...'"
                  class="reading-action-btn reading-action-btn-translate"
                  @click.stop.prevent="openTranslate"
                  @mousedown.stop.prevent
                  @mouseup.stop.prevent
                  type="button"
                >
                  <TranslationOutlined /> 翻译
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 侧边栏对话面板 -->
        <div v-if="showChatPanel" class="reading-chat-panel">
          <div class="reading-chat-header">
            <h3 class="reading-chat-title">
              智能对话{{ selectedBook ? ` · ${selectedBook.name}` : '' }}
            </h3>
            <div class="reading-chat-header-actions">
              <button
                type="button"
                class="reading-chat-clear-ctx-btn"
                title="清除上下文（清空当前课本的对话，下次提问将重新开始）"
                @click="clearBookChatContext"
              >
                <DeleteOutlined /> 清除上下文
              </button>
              <button class="reading-chat-close" @click="showChatPanel = false">
                <CloseOutlined />
              </button>
            </div>
          </div>

          <div
            class="reading-chat-messages"
            ref="chatMessagesBox"
            @click="onReadingChatPageLinkClick"
          >
            <!-- AI欢迎消息 -->
            <div v-if="chatMessages.length === 0" class="reading-chat-message ai">
              <div class="reading-chat-avatar ai" title="AI 助手">
                <svg
                  class="reading-avatar-robot"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"
                  />
                </svg>
              </div>
              <div class="reading-chat-content ai">
                <div class="reading-chat-text">
                  你好！我是课程智能体，很高兴为你解答《计算机网络》学习中的问题。你可以框选文本后「问问AI」、直接输入问题，或使用下方图片按钮上传配图（需选用支持视觉的多模态对话模型）。
                </div>
              </div>
            </div>

            <!-- 消息列表 -->
            <div
              v-for="(msg, index) in chatMessages"
              :key="index"
              class="reading-chat-message"
              :class="msg.role"
            >
              <div v-if="msg.role === 'ai'" class="reading-chat-avatar ai" title="AI 助手">
                <svg
                  class="reading-avatar-robot"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"
                  />
                </svg>
              </div>
              <div class="reading-chat-content" :class="msg.role">
                <div v-if="msg.role === 'user'" class="reading-chat-user-msg">
                  <div v-if="msg.image_content" class="reading-chat-user-img-wrap">
                    <img :src="readingUserImageSrc(msg)" alt="" class="reading-chat-user-img" />
                  </div>
                  <div v-if="msg.content" class="reading-chat-text">{{ msg.content }}</div>
                </div>
                <div
                  v-else-if="msg.role === 'ai' && msg.content"
                  class="reading-chat-text reading-chat-markdown"
                  v-html="renderMarkdownWithPageLinks(msg.content)"
                />
              </div>
              <div v-if="msg.role === 'user'" class="reading-chat-avatar user">
                <span>我</span>
              </div>
            </div>

            <!-- 加载中状态 -->
            <div v-if="isChatLoading" class="reading-chat-message ai">
              <div class="reading-chat-avatar ai" title="AI 助手">
                <svg
                  class="reading-avatar-robot"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"
                  />
                </svg>
              </div>
              <div class="reading-chat-content ai loading">
                <div
                  v-if="currentChatMessage"
                  class="reading-chat-text reading-chat-markdown"
                  v-html="renderMarkdownWithPageLinks(stripPageFooterWhileStreaming(currentChatMessage))"
                />
                <div v-else class="reading-chat-typing">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="reading-chat-input-area">
            <div v-if="pendingChatImage" class="reading-chat-pending-img">
              <img :src="pendingChatImageThumbSrc" alt="" class="reading-chat-pending-thumb" />
              <button
                type="button"
                class="reading-chat-pending-remove"
                @click="clearPendingChatImage"
              >
                移除图片
              </button>
            </div>
            <div class="reading-chat-input-row">
              <a-dropdown
                v-if="figuresOnCurrentPage.length > 0"
                :trigger="['click']"
                :disabled="isChatLoading"
                placement="topLeft"
              >
                <button
                  type="button"
                  class="reading-chat-img-btn"
                  title="本页插图"
                  :disabled="isChatLoading"
                  @click.stop
                >
                  <Images :size="20" aria-hidden="true" />
                </button>
                <template #overlay>
                  <a-menu @click="onReadingFigureMenuClick">
                    <a-menu-item v-for="f in figuresOnCurrentPage" :key="f.filename">{{
                      f.label
                    }}</a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
              <button
                type="button"
                class="reading-chat-img-btn"
                title="选择图片"
                :disabled="isChatLoading"
                @click="pickChatImage"
              >
                <Image :size="20" aria-hidden="true" />
              </button>
              <textarea
                ref="chatTextarea"
                v-model="chatInputMessage"
                class="reading-chat-textarea"
                placeholder="本平台仅支持计算机网络相关知识点提问（如协议、TCP/IP、HTTP、DNS、SDN、路由、网络安全等），与课程无关的问题将无法解答。可附带上传配图。"
                @input="adjustTextareaHeight"
                @keydown.enter.exact.prevent="sendChatMessage"
                @keydown.enter.shift.exact="handleShiftEnter"
              ></textarea>
              <button
                v-if="!isChatLoading"
                class="reading-chat-send-btn"
                @click="sendChatMessage"
                :disabled="!chatInputMessage.trim() && !pendingChatImage"
              >
                发送
              </button>
              <button
                v-else
                type="button"
                class="reading-chat-stop-btn"
                @click="stopChatStream"
                title="停止生成"
              >
                停止
              </button>
            </div>
          </div>
        </div>

        <!-- 翻译面板（与对话面板互斥，关闭后不保留结果） -->
        <div v-if="showTranslatePanel" class="reading-translate-panel">
          <div class="reading-translate-header">
            <h3 class="reading-translate-title">翻译（英译汉）</h3>
            <button class="reading-translate-close" @click="closeTranslatePanel" title="关闭">
              <CloseOutlined />
            </button>
          </div>
          <div class="reading-translate-body">
            <div v-if="translateSourceText" class="reading-translate-source">
              <div class="reading-translate-label">原文</div>
              <div class="reading-translate-text">{{ translateSourceText }}</div>
            </div>
            <div class="reading-translate-result-wrap">
              <div class="reading-translate-label">译文</div>
              <div v-if="isTranslateLoading" class="reading-translate-loading">翻译中…</div>
              <div v-else class="reading-translate-text">{{ translateResult || '—' }}</div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick, h, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { renderCourseMarkdown } from '@/utils/courseMarkdown.js'
import { Image, Images } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import CourseTopbar from '@/components/course/CourseTopbar.vue'
import CoursePageHero from '@/components/course/CoursePageHero.vue'
import {
  LeftOutlined,
  RightOutlined,
  ArrowLeftOutlined,
  CommentOutlined,
  CloseOutlined,
  DeleteOutlined,
  TranslationOutlined
} from '@ant-design/icons-vue'
import {
  listBooks,
  getBookPages,
  getBookPageUrl,
  listBookFigures,
  getBookFigureImageUrl,
  ocrTextSelection,
  courseChatStream,
  translateText as translateTextApi,
  getReadingPosition as getReadingPositionApi,
  saveReadingPosition as saveReadingPositionApi,
  getCourseDefaultAgent,
  getCourseAgentHistory,
  listCourseThreads,
  uploadCourseImage
} from '@/apis/courseApi.js'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const navItems = [
  { to: '/conversation', label: '对话', match: ['/conversation', '/course'] },
  {
    to: '/reading',
    label: '课本伴读',
    match: ['/reading'],
    onClick: (event) => {
      event.preventDefault()
      handleReadingNavClick()
    }
  },
  { to: '/videos', label: '视频', match: ['/videos'] },
  { to: '/exercises', label: '习题推荐', match: ['/exercises'] },
  { to: '/ops', label: '运维', match: ['/ops'], adminOnly: true },
  { to: '/guide', label: '使用指南', match: ['/guide'] }
]
const handleLogout = () => {
  userStore.logout()
}
const handleSwitchAccount = () => {
  userStore.logout()
}

function renderMarkdown(text) {
  return renderCourseMarkdown(text)
}

/** 与课程对话页一致：课本页码 + 11 = PDF 页 */
const TEXTBOOK_PAGE_OFFSET = 11

function stripPageFooterWhileStreaming(text) {
  const src = text || ''
  const idx = src.lastIndexOf('对应课本页码')
  if (idx < 0) return src
  return src.slice(0, idx).replace(/\s+$/, '')
}

function renderMarkdownWithPageLinks(text) {
  if (!text || typeof text !== 'string') return ''
  const bookId = selectedBook.value?.id
  let html = renderMarkdown(text)
  if (!html || !bookId) return html
  const idx = html.lastIndexOf('对应课本页码')
  if (idx < 0) return html
  const after = html.slice(idx).replace(/(对应课本页码[：:]\s*)([\s\S]*)/, (_, label, rest) => {
    const linked = rest.replace(/\d+/g, (n, offset, s) => {
      const prefix = s.slice(0, offset)
      if (prefix.lastIndexOf('<') > prefix.lastIndexOf('>')) return n
      const printed = parseInt(n, 10)
      if (!printed) return n
      const pdfPage = printed + TEXTBOOK_PAGE_OFFSET
      return `<a href="/reading?book=${encodeURIComponent(bookId)}&page=${pdfPage}&from=reading" class="reading-chat-page-link" data-book-id="${encodeURIComponent(bookId)}" data-page="${pdfPage}">第${printed}页</a>`
    })
    return label + linked
  })
  return html.slice(0, idx) + after.replace(/<\/a>\s*页/g, '</a>')
}

function onReadingChatPageLinkClick(e) {
  const link = e.target.closest('.reading-chat-page-link')
  if (!link) return
  e.preventDefault()
  const bookId = link.getAttribute('data-book-id')
  const pageStr = link.getAttribute('data-page')
  if (!bookId || !pageStr) return
  const pdfPage = parseInt(pageStr, 10)
  if (Number.isNaN(pdfPage)) return
  if (selectedBook.value?.id === bookId) {
    goToPage(pdfPage)
  } else {
    router.push({
      path: '/reading',
      query: { book: bookId, page: String(pdfPage), from: 'reading' }
    })
  }
}

const books = ref([])
/** 拉取 /api/course/books 失败或返回非预期时展示，避免与「目录无 PDF」混淆 */
const booksLoadError = ref(null)
// 分类：第 1 本指定课本；第 2 本拓展阅读；其余为讲义
const courseTextbooks = computed(() => books.value.filter((b) => b.book_type === 'course_textbook'))
const supplementBooks = computed(() => books.value.filter((b) => b.book_type === 'supplement'))
const handoutBooks = computed(() => books.value.filter((b) => b.book_type === 'handout'))
const selectedBook = ref(null)
const currentPage = ref(1)
/** MinerU 导出插图列表；伴读右上角页码 = reader_page（= 文件名 _page_N 中的 N + 1） */
const bookFigures = ref([])
const totalPages = ref(0)
const currentPageImage = ref('')
const jumpPageInput = ref(null) // 页面跳转输入框的值
const pageImage = ref(null)
const selection = ref({
  active: false,
  startX: 0,
  startY: 0,
  endX: 0,
  endY: 0
})
const selectedText = ref('')
const isSelecting = ref(false)
const finalSelectionPosition = ref({ left: 0, top: 0, width: 0, height: 0 })
const isOcrProcessing = ref(false) // 防止重复 OCR 请求

const figuresOnCurrentPage = computed(() =>
  bookFigures.value.filter((f) => f.reader_page === currentPage.value)
)

async function loadBookFiguresForReading(bookId) {
  bookFigures.value = []
  if (!bookId) return
  try {
    const res = await listBookFigures(bookId)
    bookFigures.value = Array.isArray(res?.figures) ? res.figures : []
  } catch (_) {
    bookFigures.value = []
  }
}

watch(
  () => selectedBook.value?.id,
  (id) => {
    loadBookFiguresForReading(id)
  },
  { immediate: true }
)

// 对话面板相关（按课本分离：每个 bookId 独立一份对话；当前展示用 chatMessages/chatThreadId 与当前课本同步）
const showChatPanel = ref(false)
/** 翻译面板（与对话面板互斥，只显示当前一次翻译结果，关闭即不保留） */
const showTranslatePanel = ref(false)
const translateSourceText = ref('')
const translateResult = ref('')
const isTranslateLoading = ref(false)
/** bookId -> { messages: [], threadId: null }，用于切换课本时恢复 */
const bookChats = ref({})

function getBookChat(bookId) {
  if (!bookId) return { messages: [], threadId: null }
  if (!bookChats.value[bookId]) {
    bookChats.value[bookId] = { messages: [], threadId: null }
  }
  return bookChats.value[bookId]
}

/** 当前展示的消息列表（与当前选中课本的 getBookChat(selectedBook.id).messages 同一引用） */
const chatMessages = ref([])
const chatThreadId = ref(null)

const chatInputMessage = ref('')
const isChatLoading = ref(false)
const chatMessagesBox = ref(null)
const chatTextarea = ref(null)
const currentChatMessage = ref('')
const chatStreamController = ref(null)

/** 待发送的配图（走 /api/chat/image/upload，与课程流式接口的 image_content 一致） */
const pendingChatImage = ref(null)

const pendingChatImageThumbSrc = computed(() => {
  const p = pendingChatImage.value
  if (!p) return ''
  if (p.thumbnailContent) return `data:image/jpeg;base64,${p.thumbnailContent}`
  const mime = p.mimeType || 'image/jpeg'
  return `data:${mime};base64,${p.imageContent}`
})

function readingUserImageSrc(msg) {
  if (!msg?.image_content) return ''
  const mime = msg.image_mime_type || 'image/jpeg'
  return `data:${mime};base64,${msg.image_content}`
}

function clearPendingChatImage() {
  pendingChatImage.value = null
}

async function uploadImageFileToPending(file) {
  if (!file || isChatLoading.value) return
  if (file.size > 10 * 1024 * 1024) {
    message.error('图片需小于 10MB')
    return
  }
  if (!file.type.startsWith('image/')) {
    message.error('请选择有效的图片文件')
    return
  }
  message.loading({ content: '正在处理图片…', key: 'course-reading-img' })
  try {
    const res = await uploadCourseImage(file)
    if (res.success) {
      pendingChatImage.value = {
        imageContent: res.image_content,
        mimeType: res.mime_type || file.type || 'image/jpeg',
        thumbnailContent: res.thumbnail_content
      }
      message.success({ content: '已添加配图', key: 'course-reading-img', duration: 2 })
    } else {
      message.error({ content: res.error || '图片处理失败', key: 'course-reading-img' })
    }
  } catch (_) {
    message.error({ content: '图片上传失败', key: 'course-reading-img' })
  }
}

function pickChatImage() {
  if (isChatLoading.value) return
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = async (ev) => {
    try {
      const file = ev.target.files?.[0]
      if (file) await uploadImageFileToPending(file)
    } finally {
      if (input.parentNode) input.parentNode.removeChild(input)
    }
  }
  document.body.appendChild(input)
  input.click()
}

async function onReadingFigureMenuClick({ key }) {
  const filename = key != null ? String(key) : ''
  if (!filename || isChatLoading.value || !selectedBook.value?.id) return
  const url = getBookFigureImageUrl(selectedBook.value.id, filename)
  try {
    const r = await fetch(url)
    if (!r.ok) throw new Error(String(r.status))
    const blob = await r.blob()
    const file = new File([blob], filename, { type: blob.type || 'image/jpeg' })
    await uploadImageFileToPending(file)
  } catch (_) {
    message.error({ content: '插图加载失败', key: 'course-reading-fig', duration: 2 })
  }
}

/** 默认智能体 ID，用于拉取课本伴读对话列表与历史 */
const defaultAgentId = ref(null)

/** 将历史接口返回的 history 转为 { role, content }[] */
function historyToMessages(history) {
  if (!Array.isArray(history)) return []
  return history
    .filter((m) => m.type === 'human' || m.type === 'ai')
    .map((m) => ({ role: m.type === 'human' ? 'user' : 'ai', content: m.content || '' }))
}

/** 已登录时拉取课本伴读 thread 列表，按 book_id 填入 bookChats（仅 threadId，messages 在选书时按需拉取） */
async function loadReadingThreads() {
  if (!userStore.isLoggedIn || !defaultAgentId.value) return
  try {
    const list = await listCourseThreads(defaultAgentId.value, { source: 'reading' })
    if (!Array.isArray(list)) return
    for (const thread of list) {
      const bookId =
        thread.metadata && thread.metadata.book_id != null ? String(thread.metadata.book_id) : null
      if (!bookId) continue
      if (!bookChats.value[bookId]) {
        bookChats.value[bookId] = { messages: [], threadId: null }
      }
      bookChats.value[bookId].threadId = thread.id
    }
  } catch (err) {
    console.error('加载课本伴读对话列表失败:', err)
  }
}

/** 加载指定 thread 的历史到 chat.messages */
async function loadBookChatHistory(chat) {
  if (!defaultAgentId.value || !chat.threadId) return
  try {
    const res = await getCourseAgentHistory(defaultAgentId.value, chat.threadId)
    const list = res?.history ? historyToMessages(res.history) : []
    chat.messages = list
  } catch (err) {
    console.error('加载课本伴读历史失败:', err)
    chat.messages = chat.messages || []
  }
}

// 调整输入框高度
const adjustTextareaHeight = () => {
  if (chatTextarea.value) {
    chatTextarea.value.style.height = 'auto'
    chatTextarea.value.style.height = Math.min(chatTextarea.value.scrollHeight, 200) + 'px'
  }
}

// 处理 Shift+Enter
const handleShiftEnter = () => {
  chatInputMessage.value += '\n'
  nextTick(() => {
    adjustTextareaHeight()
  })
}

// 计算选择框样式
const selectionStyle = computed(() => {
  if (!selection.value.active) return {}
  const left = Math.min(selection.value.startX, selection.value.endX)
  const top = Math.min(selection.value.startY, selection.value.endY)
  const width = Math.abs(selection.value.endX - selection.value.startX)
  const height = Math.abs(selection.value.endY - selection.value.startY)
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`
  }
})

// 计算选择框工具栏的位置（显示在选择区域旁边）
const selectionBarStyle = computed(() => {
  if (!selectedText.value) return {}
  let containerWidth = 800
  let containerHeight = 600
  if (pageImage.value) {
    try {
      const rect = pageImage.value.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0) {
        containerWidth = rect.width
        containerHeight = rect.height
      }
    } catch (_) {
      /* 刷新或未挂载时可能取不到尺寸，用默认值 */
    }
  }
  const left =
    finalSelectionPosition.value.left || Math.min(selection.value.startX, selection.value.endX)
  const top =
    finalSelectionPosition.value.top || Math.min(selection.value.startY, selection.value.endY)
  const width =
    finalSelectionPosition.value.width || Math.abs(selection.value.endX - selection.value.startX)
  const height =
    finalSelectionPosition.value.height || Math.abs(selection.value.endY - selection.value.startY)
  const barWidth = 300
  const rightSpace = containerWidth - (left + width)
  let barLeft = left + width + 10
  let barTop = top
  if (rightSpace < barWidth) {
    barLeft = left - barWidth - 10
  }
  barLeft = Math.max(10, Math.min(barLeft, containerWidth - barWidth - 10))
  if (top + height > containerHeight - 150) {
    barTop = Math.max(10, top - 120)
  }
  return {
    left: `${barLeft}px`,
    top: `${barTop}px`,
    position: 'absolute',
    zIndex: 1000
  }
})

// 加载课本列表
const loadBooks = async () => {
  booksLoadError.value = null
  try {
    console.log('开始加载课本列表...')
    const response = await listBooks()
    console.log('API响应:', response)
    if (response == null || typeof response !== 'object' || !Array.isArray(response.books)) {
      books.value = []
      booksLoadError.value =
        '课本接口返回异常（常见原因：未通过同一站点访问 /api，或反向代理未把 /api 转到后端）。请从带 nginx 的 Web 入口打开，或检查 Vite 代理与 compose 挂载。'
      console.warn('课本列表响应非 JSON 或缺少 books 数组:', response)
      return
    }
    books.value = response.books
    console.log('加载的课本数量:', books.value.length)
    if (books.value.length === 0) {
      console.warn('未找到课本（后端 books 目录下无 PDF 或未挂载 knowledgebase），响应:', response)
    }
  } catch (error) {
    console.error('加载课本列表失败:', error)
    books.value = []
    booksLoadError.value =
      error?.name === 'AbortError'
        ? '加载课本超时，请检查网络后刷新重试。'
        : error?.message || '无法加载课本列表，请确认后端已启动且可访问 /api/course/books'
  }
}

const READING_POSITION_KEY = 'yuxi_reading_position'

function getReadingPositionKey(bookId) {
  const uid = userStore.userId || userStore.userIdLogin || 'guest'
  return `${READING_POSITION_KEY}_${uid}_${bookId}`
}

function saveReadingPosition(bookId, page) {
  if (!bookId || page < 1) return
  try {
    localStorage.setItem(getReadingPositionKey(bookId), JSON.stringify({ page }))
  } catch (_) {}
}

function loadReadingPosition(bookId) {
  if (!bookId) return null
  try {
    const raw = localStorage.getItem(getReadingPositionKey(bookId))
    const data = raw ? JSON.parse(raw) : null
    return data && typeof data.page === 'number' && data.page >= 1 ? data.page : null
  } catch (_) {
    return null
  }
}

/** 从课程对话页码链接进入伴读时携带，用于「返回」回到对话而非伴读首页 */
const READING_FROM_CONVERSATION = 'conversation'

function readingFromConversation() {
  return route.query.from === READING_FROM_CONVERSATION
}

// 同步当前书/页到 URL，便于刷新后恢复；从伴读首页进入阅读时 push 以支持浏览器后退回列表
function syncReaderToQuery() {
  const book = selectedBook.value
  const page = currentPage.value
  const fromQ = readingFromConversation() ? { from: READING_FROM_CONVERSATION } : {}
  if (!book) {
    if (route.query.book || route.query.page) {
      router.replace({ path: '/reading', query: {} })
    }
    return
  }
  const next = { path: '/reading', query: { book: book.id, page: String(page), ...fromQ } }
  const sameBook = route.query.book === next.query.book
  const samePage = route.query.page === next.query.page
  const sameFrom = (route.query.from || '') === (next.query.from || '')
  if (!sameBook || !samePage || !sameFrom) {
    const isEnteringReader = !route.query.book
    if (isEnteringReader) {
      router.push(next)
    } else {
      router.replace(next)
    }
  }
}

// 从对话跳转而来：返回对话；从伴读首页选书：回到伴读首页（与浏览器后退栈一致）
function handleReaderBack() {
  if (readingFromConversation()) {
    router.back()
    return
  }
  goToList()
}

// 返回课本列表（供导航“课本伴读”点击与浏览器后退后同步状态）
function goToList() {
  selectedBook.value = null
  selectedText.value = ''
  finalSelectionPosition.value = { left: 0, top: 0, width: 0, height: 0 }
  if (route.query.book || route.query.page) {
    router.replace({ path: '/reading', query: {} })
  }
}

// 点击顶部“课本伴读”：若已在阅读页则回列表，否则跳转到课本伴读
function handleReadingNavClick() {
  if (route.path === '/reading' && selectedBook.value) {
    goToList()
  } else {
    router.push('/reading')
  }
}

// 浏览器后退时：若回到 /reading 且无 book 参数，则显示课本列表
watch(
  () => ({ path: route.path, book: route.query.book }),
  ({ path, book }) => {
    if (path === '/reading' && !book && selectedBook.value) {
      goToList()
    }
  }
)

// 选择课本
const selectBook = async (book) => {
  selectedBook.value = book
  currentPage.value = 1
  selectedText.value = ''
  const chat = getBookChat(book.id)
  chatMessages.value = chat.messages
  chatThreadId.value = chat.threadId ?? null
  if (chat.threadId && chat.messages.length === 0 && defaultAgentId.value) {
    await loadBookChatHistory(chat)
    chatMessages.value = chat.messages
  }
  try {
    const response = await getBookPages(book.id)
    totalPages.value = response.page_count || 0
    let startPage = 1
    if (totalPages.value > 0) {
      if (userStore.isLoggedIn) {
        try {
          const pos = await getReadingPositionApi(book.id)
          if (pos != null && pos.page != null && pos.page >= 1 && pos.page <= totalPages.value) {
            startPage = pos.page
          }
        } catch (_) {}
      }
      if (startPage === 1) {
        const saved = loadReadingPosition(book.id)
        if (saved != null && saved >= 1 && saved <= totalPages.value) startPage = saved
      }
    }
    await loadPage(startPage)
    syncReaderToQuery()
  } catch (error) {
    console.error('加载课本信息失败:', error)
  }
}

// 加载页面
const loadPage = async (pageNum) => {
  if (!selectedBook.value) {
    console.error('没有选中的课本')
    return
  }
  if (pageNum < 1) {
    console.warn('页码不能小于1:', pageNum)
    return
  }
  if (totalPages.value > 0 && pageNum > totalPages.value) {
    console.warn('页码超出范围:', pageNum, '总页数:', totalPages.value)
    return
  }

  console.log('加载页面:', pageNum, '总页数:', totalPages.value)
  currentPage.value = pageNum
  saveReadingPosition(selectedBook.value.id, pageNum)
  if (userStore.isLoggedIn) {
    try {
      await saveReadingPositionApi(selectedBook.value.id, pageNum)
    } catch (_) {}
  }
  syncReaderToQuery()
  // 清空当前图片，强制重新加载
  currentPageImage.value = ''
  await nextTick()
  // 设置新的图片 URL
  currentPageImage.value = getBookPageUrl(selectedBook.value.id, pageNum)
  console.log('图片URL:', currentPageImage.value)
}

// 跳转到指定页面
const goToPage = (pageNum) => {
  console.log('翻页到:', pageNum, '总页数:', totalPages.value)
  if (pageNum < 1 || (totalPages.value > 0 && pageNum > totalPages.value)) {
    console.warn('页码超出范围:', pageNum)
    return
  }
  loadPage(pageNum)
}

// 处理页面跳转输入
const handleJumpToPage = () => {
  if (!jumpPageInput.value) {
    return
  }

  const targetPage = parseInt(jumpPageInput.value)

  if (isNaN(targetPage)) {
    console.warn('无效的页码:', jumpPageInput.value)
    jumpPageInput.value = null
    return
  }

  if (targetPage < 1) {
    console.warn('页码不能小于1:', targetPage)
    jumpPageInput.value = null
    return
  }

  if (totalPages.value > 0 && targetPage > totalPages.value) {
    console.warn('页码超出范围:', targetPage, '总页数:', totalPages.value)
    jumpPageInput.value = null
    return
  }

  // 如果目标页面就是当前页面，不需要跳转
  if (targetPage === currentPage.value) {
    jumpPageInput.value = null
    return
  }

  goToPage(targetPage)
  jumpPageInput.value = null // 清空输入框
}

// 图片加载完成
const onImageLoad = () => {
  // 可以在这里添加图片加载完成的处理
  console.log('图片加载成功')
}

// 图片加载错误
const onImageError = (e) => {
  console.error('图片加载失败:', e, 'URL:', currentPageImage.value)
  // 可以显示错误提示
}

// 开始选择
const startSelection = async (e) => {
  e.preventDefault()
  e.stopPropagation()
  if (!pageImage.value) {
    console.warn('图片未加载，无法开始选择')
    return
  }
  const container = e.currentTarget.getBoundingClientRect()
  const startX = e.clientX - container.left
  const startY = e.clientY - container.top

  // 清除之前的选择状态 - 完全重置
  selectedText.value = ''
  finalSelectionPosition.value = { left: 0, top: 0, width: 0, height: 0 }
  selection.value.active = false
  isSelecting.value = false
  isOcrProcessing.value = false

  // 等待一个 tick 确保状态完全清除
  await nextTick()

  selection.value = {
    active: true,
    startX,
    startY,
    endX: startX,
    endY: startY
  }
  isSelecting.value = true
  console.log('开始新选择，坐标:', selection.value, '已清除之前的状态')
}

// 更新选择
const updateSelection = (e) => {
  if (!isSelecting.value || !selection.value.active) return
  e.preventDefault()
  e.stopPropagation()
  const container = e.currentTarget.getBoundingClientRect()
  selection.value.endX = e.clientX - container.left
  selection.value.endY = e.clientY - container.top
}

// 结束选择
const endSelection = async (e) => {
  if (!isSelecting.value || !selection.value.active) {
    return
  }
  e.preventDefault()
  e.stopPropagation()
  isSelecting.value = false

  if (!pageImage.value || !selectedBook.value) {
    console.error('图片或课本未加载')
    selection.value.active = false
    return
  }

  // 防止重复 OCR 请求
  if (isOcrProcessing.value) {
    console.warn('OCR 正在处理中，忽略重复请求')
    return
  }

  const container = e.currentTarget.getBoundingClientRect()
  const imgRect = pageImage.value.getBoundingClientRect()
  const relativeX = imgRect.left - container.left
  const relativeY = imgRect.top - container.top

  const x = Math.min(selection.value.startX, selection.value.endX) - relativeX
  const y = Math.min(selection.value.startY, selection.value.endY) - relativeY
  const width = Math.abs(selection.value.endX - selection.value.startX)
  const height = Math.abs(selection.value.endY - selection.value.startY)

  console.log('选择区域:', { x, y, width, height })

  if (width < 10 || height < 10) {
    console.log('选择区域太小，取消选择')
    selection.value.active = false
    return
  }

  // 计算相对于图片的坐标（考虑图片缩放）
  // 注意：图片可能还没有加载完成，需要检查 naturalWidth 和 naturalHeight
  if (pageImage.value.naturalWidth === 0 || pageImage.value.naturalHeight === 0) {
    console.error('图片尺寸无效，无法计算坐标')
    selection.value.active = false
    return
  }

  const scaleX = imgRect.width / pageImage.value.naturalWidth
  const scaleY = imgRect.height / pageImage.value.naturalHeight

  // 计算相对于原始图片的坐标
  const relativeX_scaled = x / scaleX
  const relativeY_scaled = y / scaleY
  const width_scaled = width / scaleX
  const height_scaled = height / scaleY

  // 保存当前选择区域的坐标（用于后续显示工具栏）
  const currentSelectionPos = {
    left: Math.min(selection.value.startX, selection.value.endX),
    top: Math.min(selection.value.startY, selection.value.endY),
    width: width,
    height: height
  }

  console.log('OCR参数:', {
    bookId: selectedBook.value.id,
    pageNum: currentPage.value,
    x: relativeX_scaled,
    y: relativeY_scaled,
    width: width_scaled,
    height: height_scaled
  })

  // 清除之前的结果 - 确保完全清除
  selectedText.value = ''
  finalSelectionPosition.value = { left: 0, top: 0, width: 0, height: 0 }

  // 等待一个 tick 确保 UI 更新
  await nextTick()

  try {
    isOcrProcessing.value = true
    selectedText.value = '正在识别...'

    console.log('发送 OCR 请求，参数:', {
      bookId: selectedBook.value.id,
      pageNum: currentPage.value,
      x: relativeX_scaled,
      y: relativeY_scaled,
      width: width_scaled,
      height: height_scaled
    })

    const response = await ocrTextSelection(
      selectedBook.value.id,
      currentPage.value,
      relativeX_scaled,
      relativeY_scaled,
      width_scaled,
      height_scaled
    )

    console.log('OCR响应:', response)

    // 再次检查响应，确保是新的结果
    if (response && response.success && response.text) {
      const newText = response.text.trim()
      console.log('识别结果:', newText)
      selectedText.value = newText
      // 保存最终选择位置，用于显示工具栏
      finalSelectionPosition.value = currentSelectionPos
    } else {
      selectedText.value = response?.text || '未能识别文本，请重试'
    }
  } catch (error) {
    console.error('OCR 识别失败:', error)
    selectedText.value = `识别失败: ${error.message || '请重试'}`
  } finally {
    isOcrProcessing.value = false
    // 选择完成后，关闭选择框，但保留文本和位置用于显示工具栏
    selection.value.active = false
  }
}

// 取消选择
const cancelSelection = () => {
  if (!isSelecting.value) return
  isSelecting.value = false
  selection.value.active = false
}

// 清除选择
const clearSelection = () => {
  selection.value.active = false
  selectedText.value = ''
  finalSelectionPosition.value = { left: 0, top: 0, width: 0, height: 0 }
}

// 打开/关闭对话面板（与翻译面板互斥）
const toggleChatPanel = () => {
  if (showChatPanel.value) {
    showChatPanel.value = false
  } else {
    showTranslatePanel.value = false
    showChatPanel.value = true
  }
}

// 打开翻译面板并请求翻译（与对话面板互斥，结果不保留）
const openTranslate = async () => {
  const text = selectedText.value ? selectedText.value.trim() : ''
  if (!text) return
  showChatPanel.value = false
  showTranslatePanel.value = true
  translateSourceText.value = text
  translateResult.value = ''
  isTranslateLoading.value = true
  try {
    const res = await translateTextApi(text)
    translateResult.value = res && res.translated != null ? String(res.translated) : ''
  } catch (_) {
    translateResult.value = '翻译失败，请重试'
  } finally {
    isTranslateLoading.value = false
  }
}

// 关闭翻译面板（不保留本次翻译结果）
const closeTranslatePanel = () => {
  showTranslatePanel.value = false
  translateSourceText.value = ''
  translateResult.value = ''
}

// 发送到对话：仅填入输入框并追加提示语，由用户自行点击发送
const sendToConversation = async (e) => {
  if (e) {
    e.preventDefault()
    e.stopPropagation()
  }

  const textToSend = selectedText.value ? selectedText.value.trim() : ''
  if (!textToSend) {
    alert('请先选择要发送的文本')
    return
  }

  const suffix = '请解释以上计算机网络相关知识'
  const contentToFill = textToSend + '\n\n' + suffix

  showTranslatePanel.value = false
  showChatPanel.value = true

  await nextTick()
  await nextTick()

  chatInputMessage.value = contentToFill
  await nextTick()
  if (chatTextarea.value) {
    chatTextarea.value.value = contentToFill
    chatTextarea.value.dispatchEvent(new Event('input', { bubbles: true }))
  } else {
    setTimeout(() => {
      if (chatTextarea.value) {
        chatTextarea.value.value = contentToFill
        chatTextarea.value.dispatchEvent(new Event('input', { bubbles: true }))
      }
    }, 100)
  }
  adjustTextareaHeight()
  clearSelection()
}

// 清除当前课本的对话上下文（下次提问将使用新 thread）
const clearBookChatContext = () => {
  const book = selectedBook.value
  if (!book) return
  const chat = getBookChat(book.id)
  chat.messages = []
  chat.threadId = null
  chatMessages.value = chat.messages
  chatThreadId.value = null
}

// 发送对话消息
const sendChatMessage = async () => {
  const content = chatInputMessage.value.trim()
  const imgSnap = pendingChatImage.value
  console.log('sendChatMessage 被调用, content:', content, 'isChatLoading:', isChatLoading.value)

  if (!content && !imgSnap) {
    console.warn('消息内容为空，无法发送')
    return
  }

  if (isChatLoading.value) {
    console.warn('正在加载中，忽略重复请求')
    return
  }

  const book = selectedBook.value
  if (!book) return
  const chat = getBookChat(book.id)
  // 确保当前展示的是当前课本的 messages 引用
  if (chatMessages.value !== chat.messages) {
    chatMessages.value = chat.messages
  }

  const userBubbleText = content || '（附图）'
  const messageToSend = content
  chat.messages.push(
    imgSnap
      ? {
          role: 'user',
          content: userBubbleText,
          message_type: 'multimodal_image',
          image_content: imgSnap.imageContent,
          image_mime_type: imgSnap.mimeType
        }
      : { role: 'user', content: userBubbleText }
  )
  chatInputMessage.value = ''
  pendingChatImage.value = null

  // 滚动到底部
  await nextTick()
  scrollChatToBottom()

  // 设置加载状态并创建可中止的请求
  isChatLoading.value = true
  currentChatMessage.value = ''
  chatStreamController.value = new AbortController()

  let streamTextBuffer = ''
  let streamFlushRaf = null
  const flushStreamBuffer = () => {
    streamFlushRaf = null
    if (!streamTextBuffer) return
    currentChatMessage.value = (currentChatMessage.value || '') + streamTextBuffer
    streamTextBuffer = ''
    nextTick(() => scrollChatToBottom())
  }
  const scheduleStreamFlush = () => {
    if (streamFlushRaf != null) return
    streamFlushRaf = requestAnimationFrame(flushStreamBuffer)
  }
  const stopStreamFlush = () => {
    if (streamFlushRaf != null) {
      cancelAnimationFrame(streamFlushRaf)
      streamFlushRaf = null
    }
    flushStreamBuffer()
  }

  try {
    await courseChatStream(
      messageToSend,
      chat.threadId ?? chatThreadId.value,
      (chunk) => {
        if (chunk.status === 'init') {
          const tid = chunk.meta && chunk.meta.thread_id ? chunk.meta.thread_id : chunk.thread_id
          if (tid) {
            chat.threadId = tid
            chatThreadId.value = tid
          }
        } else if (chunk.status === 'loading' && chunk.response) {
          streamTextBuffer += chunk.response
          scheduleStreamFlush()
        } else if (chunk.status === 'finished') {
          stopStreamFlush()
          if (typeof chunk.response === 'string' && chunk.response.length) {
            currentChatMessage.value = chunk.response
          }
          if (currentChatMessage.value) {
            chat.messages.push({ role: 'ai', content: currentChatMessage.value })
            currentChatMessage.value = ''
          }
          isChatLoading.value = false
          scrollChatToBottom()
        } else if (chunk.status === 'error') {
          stopStreamFlush()
          chat.messages.push({
            role: 'ai',
            content:
              chunk.error_message || chunk.message || '抱歉，连接服务器失败，请检查网络或稍后再试。'
          })
          isChatLoading.value = false
          scrollChatToBottom()
        }
      },
      {
        signal: chatStreamController.value.signal,
        meta: {
          source: 'reading',
          book_id: book.id,
          book_type: book.book_type,
          book_label: book.book_label
        },
        knowledgeBase: 'computer_networking',
        imageContent: imgSnap?.imageContent,
        imageMimeType: imgSnap?.mimeType
      }
    )
  } catch (error) {
    stopStreamFlush()
    if (error.name === 'AbortError') {
      if (currentChatMessage.value) {
        chat.messages.push({ role: 'ai', content: currentChatMessage.value })
        currentChatMessage.value = ''
      }
    } else {
      console.error('发送消息失败:', error)
      chat.messages.push({ role: 'ai', content: '抱歉，连接服务器失败，请检查网络或稍后再试。' })
    }
    isChatLoading.value = false
    chatStreamController.value = null
    await nextTick()
    scrollChatToBottom()
  }
}

const stopChatStream = () => {
  if (chatStreamController.value) {
    chatStreamController.value.abort()
  }
}

// 滚动对话到底部
const scrollChatToBottom = () => {
  if (chatMessagesBox.value) {
    chatMessagesBox.value.scrollTop = chatMessagesBox.value.scrollHeight
  }
}

// 监听消息变化，自动滚动
watch(
  () => chatMessages.value.length,
  () => {
    nextTick(() => {
      scrollChatToBottom()
    })
  }
)

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

onMounted(async () => {
  await loadBooks()
  const q = route.query
  const bookId = q.book && String(q.book).trim()
  const pageNum = Math.max(1, parseInt(q.page, 10) || 1)
  if (bookId && books.value.length > 0) {
    const book = books.value.find((b) => b.id === bookId)
    if (book) {
      selectedBook.value = book
      currentPage.value = 1
      selectedText.value = ''
      const chat = getBookChat(book.id)
      chatMessages.value = chat.messages
      chatThreadId.value = chat.threadId ?? null
      if (chat.threadId && chat.messages.length === 0) {
        if (defaultAgentId.value) await loadBookChatHistory(chat)
        chatMessages.value = chat.messages
      }
      try {
        const response = await getBookPages(book.id)
        totalPages.value = response.page_count || 0
        const safePage = totalPages.value > 0 ? Math.min(pageNum, totalPages.value) : pageNum
        currentPage.value = safePage
        await loadPage(safePage)
        syncReaderToQuery()
        // 从 URL 进入指定页时，一并更新阅读缓存（本地 + 服务端），便于下次打开或刷新时停留在该页
        saveReadingPosition(book.id, safePage)
        if (userStore.isLoggedIn) {
          saveReadingPositionApi(book.id, safePage).catch(() => {})
        }
      } catch (err) {
        console.error('恢复阅读状态失败:', err)
      }
    }
  }
  if (userStore.isLoggedIn) {
    try {
      const res = await getCourseDefaultAgent()
      defaultAgentId.value = res?.agent_id ?? null
      if (defaultAgentId.value) await loadReadingThreads()
    } catch (err) {
      console.error('获取默认智能体失败:', err)
    }
  }
})
</script>

<style scoped>
.reading-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: var(--surface-page);
  min-height: 100vh;
  color: var(--text-primary);
}

/* 顶部导航样式 */
.reading-header {
  background-color: var(--surface-panel-2);
  border-bottom: 1px solid var(--border-subtle);
}

.reading-header-content {
  width: 100%;
  padding: 12px 24px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.reading-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.reading-logo-text {
  margin-left: 0;
  color: var(--accent-primary);
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.reading-right {
  display: flex;
  align-items: center;
  gap: 32px;
}

.reading-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.reading-auth-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  transition:
    color 0.2s,
    background 0.2s;
}

.reading-auth-link:hover {
  color: var(--accent-primary);
}

.reading-auth-link.primary {
  color: var(--surface-panel-2);
  background: var(--accent-primary);
}

.reading-auth-link.primary:hover {
  background: #153e68;
  color: var(--surface-panel-2);
}

.reading-username {
  font-size: 14px;
  color: var(--text-secondary);
  margin-right: 4px;
}

.reading-auth-btn {
  font-size: 14px;
  padding: 6px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--surface-panel-2);
  color: var(--text-secondary);
  cursor: pointer;
  transition:
    color 0.2s,
    border-color 0.2s;
}

.reading-auth-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.reading-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.reading-nav-link {
  color: var(--text-secondary);
  text-decoration: none;
  transition: color 0.3s ease;
  font-size: 16px;
}

.reading-nav-link:hover {
  color: var(--accent-primary);
}

.reading-nav-link.active {
  color: var(--accent-primary);
  font-weight: 500;
}

/* 主要内容区样式 */
.reading-main {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 32px 24px;
}

.reading-title-section {
  text-align: center;
  margin-bottom: 32px;
}

.reading-title {
  font-size: 2.5rem;
  font-weight: bold;
  color: var(--accent-primary);
  margin-bottom: 16px;
}

.reading-subtitle {
  color: var(--text-secondary);
  max-width: 600px;
  margin: 0 auto;
}

.reading-list-section {
  margin-bottom: 40px;
}

.reading-library-layout {
  display: grid;
  grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
}

.reading-textbook-panel,
.reading-material-panel {
  background-color: var(--surface-panel-2);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  box-shadow: 0 1px 0 var(--border-subtle);
}

.reading-textbook-panel {
  padding: 18px;
}

.reading-material-panel {
  padding: 16px;
}

.reading-section-heading {
  margin-bottom: 12px;
}

.reading-section-heading--row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.reading-section-heading--compact {
  margin-bottom: 10px;
}

.reading-section-kicker {
  display: block;
  margin-bottom: 4px;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.reading-list-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--accent-primary);
  margin: 0;
}

.reading-cover-list {
  display: grid;
  gap: 14px;
}

.reading-cover-card {
  display: grid;
  gap: 14px;
  cursor: pointer;
}

.reading-cover-frame {
  display: flex;
  justify-content: center;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: linear-gradient(180deg, var(--surface-page-alt), var(--surface-panel-2));
}

.reading-cover-img {
  width: 100%;
  max-height: 360px;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
}

.reading-cover-info {
  display: grid;
  gap: 10px;
}

.reading-cover-title {
  color: var(--accent-primary);
  font-size: 17px;
  font-weight: 650;
  line-height: 1.45;
  margin: 0;
}

.reading-cover-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.reading-material-count {
  flex: 0 0 auto;
  padding: 4px 10px;
  border-radius: 999px;
  background-color: var(--surface-page-alt);
  color: var(--text-secondary);
  font-size: 12px;
}

.reading-material-list {
  display: grid;
  gap: 8px;
}

.reading-material-list--compact {
  gap: 6px;
}

.reading-material-row {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background-color: var(--surface-panel-2);
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease;
}

.reading-material-row--supplement {
  grid-template-columns: minmax(0, 1fr) 18px;
}

.reading-material-row:hover {
  border-color: var(--border-accent);
  background-color: var(--surface-page-alt);
}

.reading-material-index {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background-color: var(--surface-page-alt);
  color: var(--accent-primary);
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.reading-material-main {
  min-width: 0;
}

.reading-material-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.reading-material-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 560;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reading-material-arrow {
  color: var(--text-secondary);
  font-size: 12px;
}

.reading-supplement-block {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border-subtle);
}

.reading-subsection {
  margin-bottom: 32px;
}

.reading-subsection:last-child {
  margin-bottom: 0;
}

.reading-subsection-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--accent-primary);
  margin: 0 0 16px 0;
}

.reading-subsection-title--secondary {
  font-size: 16px;
}

.reading-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.reading-card {
  background-color: var(--surface-panel-2);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 0 var(--border-subtle);
  transition: all 0.3s ease;
  cursor: pointer;
}

.reading-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transform: translateY(-4px);
}

.reading-card-header {
  margin-bottom: 16px;
}

.reading-card-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.reading-card-tag {
  background-color: var(--surface-page-alt);
  color: var(--accent-primary);
  padding: 3px 9px;
  border-radius: 9999px;
  font-size: 11px;
  line-height: 1.4;
}

.reading-card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--accent-primary);
  margin-bottom: 12px;
}

.reading-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.reading-card-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.reading-card-page {
  color: var(--text-secondary);
  font-size: 14px;
}

.reading-card-action {
  color: var(--accent-primary);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s ease;
  display: flex;
  align-items: center;
}

.reading-card-action:hover {
  color: #e07300;
}

.reading-empty {
  display: grid;
  place-items: center;
  gap: 14px;
  text-align: center;
  min-height: 280px;
  padding: 48px 32px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-lg);
  background: color-mix(in srgb, var(--accent-primary) 4%, var(--surface-panel));
  color: var(--text-secondary);
}

.reading-empty h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 560;
}

.reading-empty p {
  margin: 0;
  max-width: 620px;
  line-height: 1.8;
}

.reading-empty-illustration {
  position: relative;
  width: 86px;
  height: 66px;
  border: 2px solid var(--accent-primary);
  border-radius: 10px 10px 14px 14px;
  background: #ffffff;
  box-shadow: 0 12px 26px var(--shadow-1);
}

.reading-empty-illustration::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 10px;
  bottom: 10px;
  width: 1px;
  background: var(--border-accent);
}

.reading-empty-illustration span {
  position: absolute;
  top: 20px;
  width: 24px;
  height: 2px;
  border-radius: 999px;
  background: var(--border-accent);
}

.reading-empty-illustration span:first-child {
  left: 12px;
}

.reading-empty-illustration span:last-child {
  right: 12px;
}

.reading-empty--error {
  color: #c53030;
}

/* PDF 阅读器样式 */
.reading-reader {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.reading-reader-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 16px;
  background-color: var(--surface-panel-2);
  border-radius: 8px;
  box-shadow: 0 1px 0 var(--border-subtle);
}

.reading-back-btn {
  background-color: var(--border-subtle);
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 14px;
  transition: background-color 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.reading-back-btn:hover {
  background-color: var(--text-secondary);
  color: var(--surface-panel-2);
}

.reading-reader-title {
  flex: 1;
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: var(--accent-primary);
  margin: 0 16px;
}

.reading-page-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-nav-btn {
  background-color: var(--accent-primary);
  color: var(--surface-panel-2);
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
}

.page-nav-btn:hover:not(:disabled) {
  background-color: #153e68;
}

.page-nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background-color: var(--border-subtle);
  color: var(--text-secondary);
}

.chat-toggle-btn {
  background-color: var(--accent-primary);
}

.chat-toggle-btn:hover:not(:disabled) {
  background-color: #e07300;
}

.chat-toggle-btn.active {
  background-color: #e07300;
}

.translate-toggle-btn {
  background-color: var(--text-secondary);
}

.translate-toggle-btn:hover:not(:disabled) {
  background-color: var(--text-secondary);
}

.translate-toggle-btn.active {
  background-color: var(--text-primary);
}

.reading-page-info {
  font-size: 14px;
  color: var(--text-secondary);
  min-width: 80px;
  text-align: center;
}

.reading-page-jump {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.page-jump-input-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-jump-input {
  width: 60px;
  padding: 6px 8px;
  border: 1px solid var(--gray-300);
  border-radius: 4px;
  font-size: 14px;
  text-align: center;
  transition: border-color 0.3s ease;
}

.page-jump-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.page-jump-input::-webkit-inner-spin-button,
.page-jump-input::-webkit-outer-spin-button {
  opacity: 1;
}

.page-jump-btn {
  background-color: var(--accent-primary);
  color: var(--surface-panel-2);
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: background-color 0.3s ease;
  white-space: nowrap;
}

.page-jump-btn:hover:not(:disabled) {
  background-color: #153e68;
}

.page-jump-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background-color: var(--border-subtle);
  color: var(--text-secondary);
}

.reading-reader-wrapper {
  display: flex;
  gap: 0;
  align-items: stretch;
  width: 100%;
}

.reading-reader-wrapper.with-chat {
  min-height: calc(100vh - 195px);
}

.reading-reader-wrapper.with-chat .reading-reader-content {
  flex: 1;
  min-width: 400px;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.reading-reader-wrapper.with-chat .reading-chat-panel,
.reading-reader-wrapper.with-chat .reading-translate-panel {
  flex: 0 0 400px;
  margin-left: auto;
  align-self: stretch;
  height: auto;
  min-height: 100%;
}

.reading-reader-content {
  background-color: var(--surface-panel-2);
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 0 var(--border-subtle);
  position: relative;
  z-index: 1;
  flex: 1;
}

.reading-pdf-page {
  position: relative;
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
  user-select: none;
}

/* 与右侧对话栏同高时，让 PDF 区在左栏内上下居中并占满剩余空间 */
.reading-reader-wrapper.with-chat .reading-pdf-page {
  flex: 1;
  min-height: 0;
  margin-bottom: 0;
  align-items: center;
}

.reading-page-img {
  max-width: 100%;
  max-height: calc(100vh - 260px);
  width: auto;
  height: auto;
  object-fit: contain;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.reading-selection-box {
  position: absolute;
  border: 2px dashed var(--accent-primary);
  background-color: rgba(255, 125, 0, 0.1);
  pointer-events: none;
  z-index: 10;
}

.reading-selection-bar {
  background-color: var(--surface-panel-2);
  padding: 12px 16px;
  border-radius: 8px;
  position: absolute;
  z-index: 1000;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-subtle);
  min-width: 280px;
  max-width: 400px;
  pointer-events: auto; /* 确保可以点击 */
}

.reading-selection-actions {
  pointer-events: auto; /* 确保按钮可以点击 */
}

.reading-action-btn {
  pointer-events: auto; /* 确保按钮可以点击 */
  cursor: pointer;
  user-select: none;
}

.reading-selected-text {
  margin-bottom: 12px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap; /* 保留换行与空格，与 OCR 版式一致 */
  word-break: break-word;
  /* 覆盖 .reading-pdf-page 的 user-select: none，便于复制已选文本 */
  user-select: text;
}

.reading-selection-actions {
  display: flex;
  gap: 12px;
}

.reading-action-btn {
  background-color: var(--accent-primary);
  color: var(--surface-panel-2);
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.reading-action-btn:hover {
  background-color: #153e68;
}

.reading-action-btn-translate {
  background-color: var(--accent-primary);
}

.reading-action-btn-translate:hover {
  background-color: #e07300;
}

/* 翻译面板样式（与对话面板同槽位，互斥显示） */
.reading-translate-panel {
  width: 400px;
  background-color: var(--surface-panel-2);
  border-radius: 8px;
  box-shadow: 0 1px 0 var(--border-subtle);
  display: flex;
  flex-direction: column;
  position: relative;
  top: auto;
}

.reading-translate-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.reading-translate-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-primary);
  margin: 0;
}

.reading-translate-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.3s ease;
}

.reading-translate-close:hover {
  color: var(--accent-primary);
}

.reading-translate-body {
  flex: 1;
  overflow: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reading-translate-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.reading-translate-source .reading-translate-text,
.reading-translate-result-wrap .reading-translate-text {
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.reading-translate-loading {
  color: var(--text-secondary);
  font-style: italic;
}

.reading-action-btn:last-child {
  background-color: var(--text-secondary);
}

.reading-action-btn:last-child:hover {
  background-color: var(--text-secondary);
}

/* 对话面板样式 */
.reading-chat-panel {
  width: 400px;
  height: min(72vh, 760px);
  min-height: 420px;
  max-height: calc(100vh - 160px);
  flex-shrink: 0;
  background-color: var(--surface-panel-2);
  border-radius: 8px;
  box-shadow: 0 1px 0 var(--border-subtle);
  display: flex;
  flex-direction: column;
  position: relative;
  top: auto;
}

.reading-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.reading-chat-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-primary);
  margin: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reading-chat-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.reading-chat-clear-ctx-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  cursor: pointer;
  transition:
    color 0.2s ease,
    border-color 0.2s ease;
}

.reading-chat-clear-ctx-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.reading-chat-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.3s ease;
}

.reading-chat-close:hover {
  color: var(--accent-primary);
}

.reading-chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 24px 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 100%;
}

.reading-chat-message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.reading-chat-message.user {
  flex-direction: row-reverse;
}

.reading-chat-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
}

.reading-chat-avatar.ai {
  background-color: var(--accent-primary);
  color: var(--surface-panel-2);
}

.reading-chat-avatar.user {
  background-color: var(--accent-primary);
  color: var(--surface-panel-2);
}

.reading-chat-avatar .reading-avatar-robot {
  width: 18px;
  height: 18px;
}

.reading-chat-content {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
}

.reading-chat-content.ai {
  background-color: var(--surface-page-alt);
  color: var(--text-primary);
}

.reading-chat-content.user {
  background-color: var(--accent-primary);
  color: var(--surface-panel-2);
}

.reading-chat-content.loading {
  background-color: var(--surface-page-alt);
}

.reading-chat-text {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.reading-chat-markdown {
  white-space: normal;
}
.reading-chat-markdown h1,
.reading-chat-markdown h2,
.reading-chat-markdown h3 {
  margin: 1em 0 0.5em;
  font-weight: 600;
  color: inherit;
}
.reading-chat-markdown h1:first-child,
.reading-chat-markdown h2:first-child,
.reading-chat-markdown h3:first-child {
  margin-top: 0;
}
.reading-chat-markdown strong {
  font-weight: 700;
}
.reading-chat-markdown a {
  color: var(--accent-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
  word-break: break-all;
}
.reading-chat-markdown .reading-chat-page-link {
  color: var(--accent-primary);
  text-decoration: none;
  font-weight: 600;
  border-bottom: 1px solid var(--accent-primary);
  cursor: pointer;
  word-break: normal;
}
.reading-chat-markdown .reading-chat-page-link:hover {
  text-decoration: underline;
}
.reading-chat-markdown p {
  margin: 0 0 0.5em;
}
.reading-chat-markdown p:last-child {
  margin-bottom: 0;
}
.reading-chat-markdown ul,
.reading-chat-markdown ol {
  margin: 0.5em 0;
  padding-left: 1.5em;
}
.reading-chat-markdown code {
  background: var(--border-subtle);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
}
.reading-chat-markdown pre {
  margin: 0.5em 0;
  overflow-x: auto;
}
.reading-chat-markdown pre code {
  display: block;
  padding: 8px 12px;
}

.reading-chat-typing {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.reading-chat-typing span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--gray-400);
  animation: typing 1.4s infinite;
}

.reading-chat-typing span:nth-child(2) {
  animation-delay: 0.2s;
}

.reading-chat-typing span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.reading-chat-input-area {
  padding: 16px 24px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: stretch;
  background-color: var(--surface-panel-2);
  box-sizing: border-box;
}

.reading-chat-input-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  width: 100%;
}

.reading-chat-pending-img {
  display: flex;
  align-items: center;
  gap: 12px;
}

.reading-chat-pending-thumb {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
}

.reading-chat-pending-remove {
  padding: 6px 12px;
  font-size: 13px;
  border: 1px solid var(--gray-300);
  border-radius: 6px;
  background: var(--surface-panel-2);
  color: var(--text-primary);
  cursor: pointer;
}

.reading-chat-img-btn {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--gray-300);
  border-radius: 8px;
  background: var(--surface-panel-2);
  color: var(--text-primary);
  cursor: pointer;
  margin-bottom: 8px;
}

.reading-chat-img-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reading-chat-user-msg {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.reading-chat-user-img-wrap {
  max-width: 220px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.reading-chat-user-img {
  display: block;
  max-width: 100%;
  height: auto;
  vertical-align: middle;
}

.reading-chat-textarea {
  flex: 1;
  box-sizing: border-box;
  padding: 12px 16px;
  border: 1px solid var(--gray-300);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  min-height: 60px;
  max-height: 200px;
  line-height: 1.5;
  overflow-y: auto;
}

.reading-chat-textarea:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.reading-chat-send-btn,
.reading-chat-stop-btn {
  flex-shrink: 0;
  box-sizing: border-box;
  width: auto;
  height: 60px;
  min-height: 60px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}

.reading-chat-send-btn {
  background-color: var(--accent-primary);
  color: var(--surface-panel-2);
  border: 1px solid var(--accent-primary);
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.reading-chat-send-btn:hover:not(:disabled) {
  background-color: #153e68;
}

.reading-chat-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reading-chat-stop-btn {
  background-color: var(--border-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.reading-chat-stop-btn:hover {
  background-color: #d1d5db;
  color: var(--text-primary);
}

@media (max-width: 768px) {
  .reading-reader-header {
    flex-direction: column;
    gap: 12px;
  }

  .reading-reader-title {
    margin: 0;
  }

  .reading-logo-text {
    white-space: normal;
  }

  .reading-reader-wrapper {
    flex-direction: column;
  }

  .reading-reader-wrapper.with-chat {
    min-height: 0;
  }

  .reading-library-layout {
    grid-template-columns: 1fr;
  }

  .reading-cover-img {
    max-height: 320px;
  }

  .reading-chat-panel {
    width: 100%;
    height: 500px;
    position: relative;
    top: 0;
  }
}
</style>
