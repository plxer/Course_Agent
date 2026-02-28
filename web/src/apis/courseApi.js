/**
 * 课程智能体 API（课本伴读、视频伴读、课程对话流）
 * 与后端 /api/course/* 对应
 */
import { apiGet, apiPost } from './base'

/** 课程对话流（需登录），options.signal 可传入 AbortSignal 用于停止，options.meta 会传给后端（如 source: "reading" 表示课本伴读，不在问答页展示） */
export async function courseChatStream(query, threadId = null, onChunk = null, options = {}) {
  const userStore = (await import('@/stores/user')).useUserStore()
  const headers = { 'Content-Type': 'application/json', ...(userStore.getAuthHeaders?.() || {}) }
  if (!userStore.isLoggedIn && onChunk) {
    onChunk({ status: 'error', message: '请先登录后再使用对话功能' })
    throw new Error('请先登录后再使用对话功能')
  }

  const { signal, meta } = options
  const response = await fetch('/api/course/chat/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify({ query, thread_id: threadId, meta: meta || {} }),
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

/** 视频列表（按章节） */
export function listVideos() {
  return apiGet('/api/course/videos', {}, false)
}

/** 视频播放 URL */
export function getVideoUrl(videoId) {
  return `/api/course/videos/${encodeURIComponent(videoId)}`
}
