/**
 * 课程智能体 API（课本伴读、视频伴读、课程对话流）
 * 与后端 /api/course/* 对应
 */
import { apiGet, apiPost, apiPut } from './base'

/** 根据首轮一问一答生成对话标题（需登录） */
export async function generateConversationTitle(firstQuestion, firstAnswer) {
  const { useUserStore } = await import('@/stores/user')
  const userStore = useUserStore()
  const headers = { 'Content-Type': 'application/json', ...(userStore.getAuthHeaders?.() || {}) }
  if (!userStore.isLoggedIn) return null
  const response = await fetch('/api/course/chat/title', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      first_question: String(firstQuestion).slice(0, 500),
      first_answer: String(firstAnswer).slice(0, 500)
    })
  })
  if (!response.ok) return null
  const data = await response.json()
  return data?.title ?? null
}

/** 课程对话流（需登录），options.signal 可传入 AbortSignal 用于停止，options.meta 会传给后端，options.enableWebSearch 为 true 时本次对话启用网络搜索，options.knowledgeBase 为课程知识库 id 时先检索课本再作答 */
export async function courseChatStream(query, threadId = null, onChunk = null, options = {}) {
  const userStore = (await import('@/stores/user')).useUserStore()
  const headers = { 'Content-Type': 'application/json', ...(userStore.getAuthHeaders?.() || {}) }
  if (!userStore.isLoggedIn && onChunk) {
    onChunk({ status: 'error', message: '请先登录后再使用对话功能' })
    throw new Error('请先登录后再使用对话功能')
  }

  const { signal, meta, enableWebSearch, knowledgeBase, imageContent, imageMimeType } = options
  const body = { query, thread_id: threadId, meta: meta || {} }
  if (enableWebSearch !== undefined && enableWebSearch !== null) {
    body.enable_web_search = Boolean(enableWebSearch)
  }
  if (knowledgeBase !== undefined && knowledgeBase !== null && String(knowledgeBase).trim()) {
    body.knowledge_base = String(knowledgeBase).trim()
  }
  if (imageContent && String(imageContent).trim()) {
    body.image_content = String(imageContent).trim()
    if (imageMimeType && String(imageMimeType).trim()) {
      body.image_mime_type = String(imageMimeType).trim()
    }
  }
  const response = await fetch('/api/course/chat/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal
  })

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const err = await response.json()
      errorMessage = err.detail || err.message || errorMessage
    } catch (_) {}
    if (response.status === 401) errorMessage = '请先登录后再使用对话功能'
    if (onChunk) onChunk({ status: 'error', message: errorMessage })
    throw new Error(errorMessage)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let gotTerminal = false
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.trim()) continue
      try {
        const data = JSON.parse(line)
        if (data.status === 'finished' || data.status === 'error') gotTerminal = true
        if (onChunk) onChunk(data)
      } catch (e) {
        console.error('Parse chunk error:', e, line)
      }
    }
  }
  // 流结束但未收到 finished/error 时也结束加载，避免一直转圈
  if (onChunk && !gotTerminal) onChunk({ status: 'finished' })
}

/** 课本列表（可匿名） */
export function listBooks() {
  return apiGet('/api/course/books', {}, false)
}

/** 课本页数 */
export function getBookPages(bookId) {
  return apiGet(`/api/course/books/${encodeURIComponent(bookId)}/pages`, {}, false)
}

/** 课本某一页图片 URL */
export function getBookPageUrl(bookId, pageNum) {
  return `/api/course/books/${encodeURIComponent(bookId)}/page/${pageNum}`
}

/** 课本解析插图列表（_page_*，reader_page = extract_page + 1，与伴读右上角页码一致） */
export function listBookFigures(bookId) {
  return apiGet(`/api/course/books/${encodeURIComponent(bookId)}/figures`, {}, false)
}

/** 单张解析插图 URL（query name 为文件名） */
export function getBookFigureImageUrl(bookId, filename) {
  return `/api/course/books/${encodeURIComponent(bookId)}/figure?name=${encodeURIComponent(filename)}`
}

/** 选中区域 OCR */
export function ocrTextSelection(bookId, pageNum, x, y, width, height) {
  return apiPost(
    '/api/course/books/ocr',
    { book_id: bookId, page_num: pageNum, x, y, width, height },
    {},
    false
  )
}

/** 选区文本翻译（英译汉，需登录，结果不保留） */
export function translateText(text) {
  return apiPost('/api/course/translate', { text: String(text || '').trim() }, {}, true)
}

/** 获取阅读进度（需登录），返回 { page: number | null } */
export function getReadingPosition(bookId) {
  return apiGet(`/api/course/reading-position?book_id=${encodeURIComponent(bookId)}`, {}, true)
}

/** 保存阅读进度（需登录），永久记录 */
export function saveReadingPosition(bookId, page) {
  return apiPut('/api/course/reading-position', { book_id: bookId, page }, {}, true)
}

/** 视频列表（按章节） */
export function listVideos() {
  return apiGet('/api/course/videos', {}, false)
}

/** 视频播放 URL */
export function getVideoUrl(videoId) {
  return `/api/course/videos/${encodeURIComponent(videoId)}`
}

/** 视频字幕（sentence_timestamps 等），不存在则 404 */
export function getVideoCaption(videoId) {
  return apiGet(`/api/course/videos/${encodeURIComponent(videoId)}/caption`, {}, false)
}

/** 视频分段总结（用于总结视频按钮），不存在则 404 */
export function getVideoSummary(videoId) {
  return apiGet(`/api/course/videos/${encodeURIComponent(videoId)}/summary`, {}, false)
}

/** 课程对话可选的知识库列表（选中后对话会先检索对应课本再作答） */
export function listCourseKnowledgeBases() {
  return apiGet('/api/course/knowledge-bases', {}, false)
}

// --- 习题推荐 ---

/** 课本章节目录（先选章节再选知识点） */
export function getTextbookChapters() {
  return apiGet('/api/course/exercises/textbook-chapters', {}, false)
}

/** 生成题目：题型 + 知识点；可选 chapter、sectionId 以结合课本出题 */
export function exerciseGenerate(questionType, knowledgePoint, chapter = null, sectionId = null) {
  const body = {
    question_type: questionType,
    knowledge_point: knowledgePoint
  }
  if (chapter != null) body.chapter = chapter
  if (sectionId != null) body.section_id = sectionId
  return apiPost('/api/course/exercises/generate', body, {}, true)
}

/** 生成小测：一次性生成多题（多种题型 + 数量），可选知识点集合（默认空表示用该章节全部知识点） */
export function exerciseQuizGenerate({ chapter, question_type_counts, knowledge_point_ids = [] }) {
  return apiPost(
    '/api/course/exercises/generate-quiz',
    {
      chapter,
      question_type_counts,
      knowledge_point_ids
    },
    {},
    true
  )
}

/** 小测题位：仅返回题型+知识点列表（不调用 LLM），供前端逐题 exerciseGenerate 边生成边展示 */
export function exerciseQuizPlan({ chapter, question_type_counts, knowledge_point_ids = [] }) {
  return apiPost(
    '/api/course/exercises/quiz-plan',
    {
      chapter,
      question_type_counts,
      knowledge_point_ids
    },
    {},
    true
  )
}

/** 提交答案 */
export function exerciseSubmit(payload) {
  return apiPost('/api/course/exercises/submit', payload, {}, true)
}

/** 错题分析（与运维做题记录同源）：一次返回按知识点统计 + 错题列表第一页，用于弹窗作图与列表 */
export function exerciseWrongAnalysis(page = 1, pageSize = 20) {
  return apiGet(
    `/api/course/exercises/wrong-analysis?page=${page}&page_size=${pageSize}`,
    {},
    true
  )
}

/** 错题按知识点统计（环状图），与 wrong-analysis 同源 */
export function exerciseWrongStats() {
  return apiGet('/api/course/exercises/wrong-stats', {}, true)
}

/** 错题列表分页，与 wrong-analysis 同源 */
export function exerciseWrongList(page = 1, pageSize = 20) {
  return apiGet(
    `/api/course/exercises/wrong-list?page=${page}&page_size=${pageSize}`,
    {},
    true
  )
}

/** 当前用户积分 */
export function getPoints() {
  return apiGet('/api/course/points', {}, true)
}

// --- 积分商城 ---

/** 商城称号列表 */
export function mallList() {
  return apiGet('/api/course/mall', {}, true)
}

/** 兑换称号 */
export function mallPurchase(itemId) {
  return apiPost('/api/course/mall/purchase', { item_id: itemId }, {}, true)
}

/** 我的称号 */
export function mallMyTitles() {
  return apiGet('/api/course/mall/my-titles', {}, true)
}
