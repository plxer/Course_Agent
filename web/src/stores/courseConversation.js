import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * 课程智能体对话状态持久化 store。
 * 切到视频/运维等页面再切回时保留对话列表与流式输出状态，避免对话消失和输出被打断。
 */
export const useCourseConversationStore = defineStore('courseConversation', () => {
  const chatList = ref([])
  const currentChatId = ref(null)
  const nextChatNumber = ref(1)
  const threadId = ref(null)
  const isLoading = ref(false)
  const activeRequestChatId = ref(null)
  const currentAiMessage = ref('')
  const defaultAgentId = ref(null)
  const streamController = ref(null)
  /** 当前轮次网络搜索状态：idle | searching | done */
  const searchStatus = ref('idle')
  /** 当前轮次搜索关键词（searching 时显示） */
  const searchQuery = ref('')
  /** 当前轮次搜索到的来源 { title, url }[] */
  const searchSources = ref([])

  const currentChat = computed(() =>
    currentChatId.value ? chatList.value.find((c) => c.id === currentChatId.value) : null
  )
  const messages = computed(() => currentChat.value?.messages ?? [])

  function setChatList(list) {
    chatList.value = list
  }

  function setCurrentChatId(id) {
    currentChatId.value = id
  }

  function setThreadId(id) {
    threadId.value = id
  }

  function setLoading(loading) {
    isLoading.value = loading
  }

  function setActiveRequestChatId(id) {
    activeRequestChatId.value = id
  }

  function appendCurrentAiMessage(text) {
    currentAiMessage.value = (currentAiMessage.value || '') + text
  }

  function clearCurrentAiMessage() {
    currentAiMessage.value = ''
  }

  function setDefaultAgentId(id) {
    defaultAgentId.value = id
  }

  function setStreamController(controller) {
    streamController.value = controller
  }

  function findChat(chatId) {
    return chatList.value.find((c) => c.id === chatId)
  }

  function setNextChatNumber(n) {
    nextChatNumber.value = n
  }

  function incrementNextChatNumber() {
    nextChatNumber.value += 1
  }

  /** 设置正在搜索（显示「正在搜索」提示） */
  function setSearching(query = '') {
    searchStatus.value = 'searching'
    searchQuery.value = query || ''
  }

  /** 追加当前轮次搜索来源（多次搜索时累加，不覆盖） */
  function appendSearchSources(sources) {
    searchStatus.value = 'done'
    const list = Array.isArray(sources) ? sources : []
    const seen = new Set(searchSources.value.map((s) => s.url))
    for (const s of list) {
      if (s.url && !seen.has(s.url)) {
        seen.add(s.url)
        searchSources.value.push({ title: s.title || s.url || '', url: s.url })
      }
    }
  }

  /** 清空当前轮次搜索状态（新消息发送或流结束时可调用） */
  function clearSearchState() {
    searchStatus.value = 'idle'
    searchQuery.value = ''
    searchSources.value = []
  }

  /** 重置流式相关状态（不清空对话列表），用于登出或希望清空加载状态时 */
  function resetStreamState() {
    isLoading.value = false
    activeRequestChatId.value = null
    currentAiMessage.value = ''
    streamController.value = null
    clearSearchState()
  }

  return {
    chatList,
    currentChatId,
    nextChatNumber,
    threadId,
    isLoading,
    activeRequestChatId,
    currentAiMessage,
    defaultAgentId,
    streamController,
    searchStatus,
    searchQuery,
    searchSources,
    currentChat,
    messages,
    setChatList,
    setCurrentChatId,
    setThreadId,
    setLoading,
    setActiveRequestChatId,
    appendCurrentAiMessage,
    clearCurrentAiMessage,
    setDefaultAgentId,
    setStreamController,
    setSearching,
    appendSearchSources,
    clearSearchState,
    findChat,
    setNextChatNumber,
    incrementNextChatNumber,
    resetStreamState
  }
})
