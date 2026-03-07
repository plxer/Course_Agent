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

/** 课程对话流（需登录），options.signal 可传入 AbortSignal 用于停止，options.meta 会传给后端，options.enableWebSearch 为 true 时本次对话启用网络搜索 */
export async function courseChatStream(query, threadId = null, onChunk = null, options = {}) {
  const userStore = (await import('@/stores/user')).useUserStore()
  const headers = { 'Content-Type': 'application/json', ...(userStore.getAuthHeaders?.() || {}) }
  if (!userStore.isLoggedIn && onChunk) {
    onChunk({ status: 'error', message: '请先登录后再使用对话功能' })
    throw new Error('请先登录后再使用对话功能')
  }

  const { signal, meta, enableWebSearch } = options
  const body = { query, thread_id: threadId, meta: meta || {} }
  if (enableWebSearch !== undefined && enableWebSearch !== null) {
    body.enable_web_search = Boolean(enableWebSearch)
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

/** 选中区域 OCR */
export function ocrTextSelection(bookId, pageNum, x, y, width, height) {
  return apiPost(
    '/api/course/books/ocr',
    { book_id: bookId, page_num: pageNum, x, y, width, height },
    {},
    false
  )
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

// --- 习题推荐 ---

/** 生成题目：题型 + 知识点 */
export function exerciseGenerate(questionType, knowledgePoint) {
  return apiPost('/api/course/exercises/generate', {
    question_type: questionType,
    knowledge_point: knowledgePoint
  }, {}, true)
}

/** 提交答案 */
export function exerciseSubmit(payload) {
  return apiPost('/api/course/exercises/submit', payload, {}, true)
}

/** 错题按知识点统计（环状图） */
export function exerciseWrongStats() {
  return apiGet('/api/course/exercises/wrong-stats', {}, true)
}

/** 错题列表分页 */
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
