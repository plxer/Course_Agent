<template>
  <div class="conversation-view-container">
    <header class="conversation-view-header">
      <div class="conversation-view-header-content">
        <router-link to="/" class="conversation-view-logo">
          <span class="conversation-view-logo-text">天津大学《计算机网络》课程数智化平台</span>
        </router-link>
        <div class="conversation-view-right">
          <div class="conversation-view-nav">
            <router-link to="/conversation" class="conversation-view-nav-link" :class="{ active: $route.path === '/conversation' || $route.path === '/course' }">对话</router-link>
            <router-link to="/exercises" class="conversation-view-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>
            <router-link to="/reading" class="conversation-view-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
            <router-link to="/videos" class="conversation-view-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
          </div>
          <div class="conversation-view-auth">
            <template v-if="!userStore.isLoggedIn">
              <router-link to="/login" class="conversation-view-auth-link">登录</router-link>
              <router-link to="/register" class="conversation-view-auth-link primary">注册</router-link>
            </template>
            <template v-else>
              <span class="conversation-view-username">{{ userStore.username || userStore.userIdLogin }}</span>
              <button type="button" class="conversation-view-auth-btn" @click="handleSwitchAccount">切换账号</button>
              <button type="button" class="conversation-view-auth-btn" @click="handleLogout">退出</button>
            </template>
          </div>
        </div>
      </div>
    </header>

    <!-- 主要内容区 -->
    <main class="conversation-view-main">
      <!-- 对话界面 -->
      <div class="conversation-view-chat">
        <!-- 左侧对话列表 -->
        <div class="conversation-view-sidebar">
          <div class="conversation-sidebar-header">
            <h3 class="conversation-sidebar-title">对话列表</h3>
            <button type="button" class="conversation-sidebar-new-btn" @click="createNewChat" title="新建对话">
              <i class="fa fa-plus"></i> 新建对话
            </button>
          </div>
          <div class="conversation-sidebar-content">
            <div class="conversation-list">
              <div 
                v-for="(chat, index) in chatList" 
                :key="chat.id"
                class="conversation-item"
                :class="{ active: currentChatId === chat.id }"
                @click="switchChat(chat.id)"
              >
                <div class="conversation-item-title">{{ chat.title || `对话 ${index + 1}` }}</div>
                <button 
                  v-if="chatList.length > 1"
                  class="conversation-item-delete"
                  @click.stop="deleteChat(chat.id)"
                  title="删除对话"
                >
                  <i class="fa fa-times"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 右侧对话内容 -->
        <div class="conversation-view-content">
          <!-- 对话消息区域 -->
          <div class="conversation-view-message-box" ref="messageBox">
            <!-- AI欢迎消息 -->
            <div v-if="messages.length === 0" class="conversation-view-message-item">
              <div class="conversation-view-message-avatar ai" title="AI 助手">
                <svg class="avatar-robot" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"/></svg>
              </div>
              <div class="conversation-view-message-content ai">
                <div class="message-text">你好！我是课程智能体，很高兴为你解答学习中的问题。请问有什么我可以帮助你的吗？</div>
              </div>
            </div>

            <!-- 动态消息列表 -->
          <div v-for="(message, index) in messages" :key="index" class="conversation-view-message-item" :class="message.role">
            <div v-if="message.role === 'ai'" class="conversation-view-message-avatar ai" title="AI 助手">
              <svg class="avatar-robot" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"/></svg>
            </div>
            <div class="conversation-view-message-content" :class="message.role">
              <div class="message-text">{{ message.content }}</div>
            </div>
            <div v-if="message.role === 'user'" class="conversation-view-message-avatar user">
              <i class="fa fa-user"></i>
            </div>
          </div>

          <!-- 加载中状态（仅当前发起请求的对话显示） -->
          <div v-if="isLoading && currentChatId === activeRequestChatId" class="conversation-view-message-item">
            <div class="conversation-view-message-avatar ai" title="AI 助手">
              <svg class="avatar-robot" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"/></svg>
            </div>
            <div class="conversation-view-message-content ai loading">
              <div v-if="currentAiMessage" class="message-text" :key="`loading-${currentAiMessage.length}`">{{ currentAiMessage }}</div>
              <div v-else class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

          <!-- 输入区域 -->
          <div class="conversation-view-input-area">
            <textarea 
              ref="inputTextarea"
              v-model="inputMessage" 
              class="conversation-view-textarea" 
              placeholder="请输入你的问题..."
              @input="adjustTextareaHeight"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.enter.shift.exact="handleShiftEnter"
            ></textarea>
            <button 
              v-if="!isLoading || currentChatId !== activeRequestChatId"
              class="conversation-view-send-btn" 
              @click="sendMessage"
              :disabled="!inputMessage.trim() || isLoading"
            >
              <i class="fa fa-paper-plane mr-2"></i>发送
            </button>
            <button 
              v-else
              type="button"
              class="conversation-view-stop-btn"
              @click="stopStream"
              title="停止生成"
            >
              <i class="fa fa-stop"></i> 停止
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { courseChatStream } from '@/apis/courseApi.js';
import { agentApi, threadApi } from '@/apis';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();
const inputMessage = ref('');

const handleLogout = () => {
  userStore.logout();
  router.push('/course');
};
const handleSwitchAccount = () => {
  userStore.logout();
  router.push('/login');
};
const messages = ref([]);
const isLoading = ref(false);
const messageBox = ref(null);
const inputTextarea = ref(null);
const threadId = ref(null);
const currentAiMessage = ref('');
const streamController = ref(null);

// 对话列表相关
const chatList = ref([]);
const currentChatId = ref(null);
/** 新建对话序号（删除不影响已有对话的序号） */
const nextChatNumber = ref(1);
/** 当前正在收流的对话 id，用于仅在该对话中显示加载和追加回复 */
const activeRequestChatId = ref(null);
/** 课程使用的默认智能体 id，与后端 /course/chat/stream 一致，用于拉取/创建 thread */
const defaultAgentId = ref(null);

// 用首条用户消息生成简短标题（首轮对话后调用），并同步到后端
const summarizeChatTitle = (chat) => {
  const userMsg = chat.messages?.find(m => m.role === 'user');
  if (!userMsg?.content) return;
  const text = userMsg.content.trim();
  const maxLen = 20;
  chat.title = text.length <= maxLen ? text : text.slice(0, maxLen) + '…';
  if (userStore.isLoggedIn && defaultAgentId.value && chat.id) {
    threadApi.updateThread(chat.id, chat.title).catch((err) => console.error('更新对话标题失败:', err));
  }
};

// 从后端历史记录格式转为页面使用的 messages
function historyToMessages(history) {
  if (!Array.isArray(history)) return [];
  return history
    .filter((m) => m.type === 'human' || m.type === 'ai')
    .map((m) => ({ role: m.type === 'human' ? 'user' : 'ai', content: m.content || '' }));
}

// 加载指定 thread 的历史并填入 chat.messages
async function loadThreadHistory(chat) {
  if (!defaultAgentId.value || !chat.id) return;
  try {
    const res = await agentApi.getAgentHistory(defaultAgentId.value, chat.id);
    const list = res?.history ? historyToMessages(res.history) : [];
    chat.messages = list;
  } catch (err) {
    console.error('加载对话历史失败:', err);
    chat.messages = chat.messages || [];
  }
}

// 创建新对话（已登录时调用后端创建 thread 并加入列表）
const createNewChat = async () => {
  if (userStore.isLoggedIn && defaultAgentId.value) {
    try {
      const title = `对话 ${nextChatNumber.value}`;
      nextChatNumber.value += 1;
      const thread = await threadApi.createThread(defaultAgentId.value, title);
      const newChat = {
        id: thread.id,
        title: thread.title || title,
        messages: [],
        threadId: thread.id
      };
      chatList.value.push(newChat);
      switchChat(newChat.id);
    } catch (err) {
      console.error('创建对话失败:', err);
      createNewChatLocal();
    }
  } else {
    createNewChatLocal();
  }
};

function createNewChatLocal() {
  const newChat = {
    id: Date.now().toString(),
    title: `对话 ${nextChatNumber.value}`,
    messages: [],
    threadId: null
  };
  nextChatNumber.value += 1;
  chatList.value.push(newChat);
  switchChat(newChat.id);
}

// 切换对话（已登录时从后端拉取该 thread 的历史）
const switchChat = async (chatId) => {
  const chat = chatList.value.find((c) => c.id === chatId);
  if (!chat) return;

  currentChatId.value = chatId;
  threadId.value = chat.threadId ?? chat.id;
  inputMessage.value = '';

  if (userStore.isLoggedIn && defaultAgentId.value) {
    if (chat.messages.length === 0) await loadThreadHistory(chat);
    messages.value = chat.messages || [];
  } else {
    messages.value = chat.messages || [];
  }

  nextTick(() => {
    scrollToBottom();
    adjustTextareaHeight();
  });
};

// 删除对话（已登录时同时删除后端 thread）
const deleteChat = async (chatId) => {
  const index = chatList.value.findIndex((c) => c.id === chatId);
  if (index === -1) return;

  if (userStore.isLoggedIn && defaultAgentId.value) {
    try {
      await threadApi.deleteThread(chatId);
    } catch (err) {
      console.error('删除对话失败:', err);
    }
  }

  chatList.value.splice(index, 1);

  if (currentChatId.value === chatId) {
    if (chatList.value.length > 0) {
      switchChat(chatList.value[0].id);
    } else {
      createNewChat();
    }
  }
};

// 发送消息（使用课程对话流接口，由后端根据 DEFAULT_AGENT_ID 决定智能体，固定为 ChatbotAgent）
const sendMessage = async () => {
  const content = inputMessage.value.trim();
  if (!content || isLoading.value) return;

  const chatIdForThisRequest = currentChatId.value;
  const chat = chatList.value.find(c => c.id === chatIdForThisRequest);
  if (!chat) return;

  activeRequestChatId.value = chatIdForThisRequest;
  chat.messages.push({ role: 'user', content });
  inputMessage.value = '';
  await nextTick();
  scrollToBottom();

  isLoading.value = true;
  currentAiMessage.value = '';
  streamController.value = new AbortController();

  try {
    if (!threadId.value) {
      threadId.value = chat.threadId || chat.id || Date.now().toString() + Math.random().toString(36).substr(2, 9);
    }
    chat.threadId = threadId.value;

    await courseChatStream(
      content,
      threadId.value,
      (chunk) => {
        const targetChat = chatList.value.find(c => c.id === chatIdForThisRequest);
        if (!targetChat) return;

        if (chunk.status === 'init') {
          const tid = (chunk.meta && chunk.meta.thread_id) ? chunk.meta.thread_id : chunk.thread_id;
          if (tid) {
            threadId.value = tid;
            targetChat.threadId = tid;
          }
        } else if (chunk.status === 'loading' && chunk.response !== undefined) {
          if (chunk.response) {
            currentAiMessage.value = (currentAiMessage.value || '') + chunk.response;
          }
          if (currentChatId.value === chatIdForThisRequest) nextTick(() => scrollToBottom());
        } else if (chunk.status === 'finished') {
          if (currentAiMessage.value) {
            targetChat.messages.push({ role: 'ai', content: currentAiMessage.value });
            if (targetChat.messages.length === 2) summarizeChatTitle(targetChat);
            currentAiMessage.value = '';
          }
          isLoading.value = false;
          activeRequestChatId.value = null;
          if (currentChatId.value === chatIdForThisRequest) nextTick(() => scrollToBottom());
        } else if (chunk.status === 'error') {
          const errMsg = chunk.error_message || chunk.message || '抱歉，连接服务器失败，请检查网络或稍后再试。';
          targetChat.messages.push({ role: 'ai', content: errMsg });
          isLoading.value = false;
          currentAiMessage.value = '';
          activeRequestChatId.value = null;
          if (currentChatId.value === chatIdForThisRequest) nextTick(() => scrollToBottom());
        }
      },
      { signal: streamController.value.signal }
    );
  } catch (error) {
    const targetChat = chatList.value.find(c => c.id === chatIdForThisRequest);
    if (targetChat) {
      if (error.name === 'AbortError') {
        if (currentAiMessage.value) {
          targetChat.messages.push({ role: 'ai', content: currentAiMessage.value });
          if (targetChat.messages.length === 2) summarizeChatTitle(targetChat);
        }
      } else {
        console.error('发送消息失败:', error);
        const networkMsg = '无法连接服务器，请确认：1) 后端服务已启动；2) 浏览器访问的地址已正确代理到后端（如 localhost:5173 的 /api 会转发到后端）。若未登录，请先登录。';
        targetChat.messages.push({ role: 'ai', content: networkMsg });
      }
    }
    currentAiMessage.value = '';
    isLoading.value = false;
    activeRequestChatId.value = null;
    streamController.value = null;
    if (currentChatId.value === chatIdForThisRequest) await nextTick(() => scrollToBottom());
  }
};

const stopStream = () => {
  if (streamController.value) {
    streamController.value.abort();
  }
};

// 初始化：已登录时从后端拉取对话列表并选中第一个；未登录时仅创建本地对话
onMounted(async () => {
  if (!document.querySelector('link[href*="font-awesome"]')) {
    const link = document.createElement('link');
    link.href = 'https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css';
    link.rel = 'stylesheet';
    document.head.appendChild(link);
  }

  if (!userStore.isLoggedIn) {
    if (chatList.value.length === 0) createNewChat();
    return;
  }

  try {
    const defaultRes = await agentApi.getDefaultAgent();
    const agentId = defaultRes?.default_agent_id;
    if (!agentId) {
      if (chatList.value.length === 0) createNewChatLocal();
      return;
    }
    defaultAgentId.value = agentId;

    const threads = await threadApi.getThreads(agentId);
    const list = Array.isArray(threads) ? threads : [];
    chatList.value = list.map((t) => ({
      id: t.id,
      title: t.title || `对话 ${t.id}`,
      messages: [],
      threadId: t.id
    }));
    nextChatNumber.value = chatList.value.length + 1;

    if (chatList.value.length > 0) {
      await switchChat(chatList.value[0].id);
    } else {
      createNewChat();
    }
  } catch (err) {
    console.error('加载课程对话列表失败:', err);
    if (chatList.value.length === 0) createNewChatLocal();
  }
});

// 自动调整文本框高度
const adjustTextareaHeight = () => {
  if (inputTextarea.value) {
    inputTextarea.value.style.height = 'auto';
    inputTextarea.value.style.height = Math.min(inputTextarea.value.scrollHeight, 200) + 'px';
  }
};

// 处理 Shift+Enter
const handleShiftEnter = () => {
  inputMessage.value += '\n';
  nextTick(() => {
    adjustTextareaHeight();
  });
};

// 滚动到底部
const scrollToBottom = () => {
  if (messageBox.value) messageBox.value.scrollTop = messageBox.value.scrollHeight;
};
</script>

<style>
/* 使用与index.html相同的颜色和样式配置 */
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

/* 重置默认样式 */
.conversation-view-container * {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.conversation-view-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: var(--gray-50);
  min-height: 100vh;
  color: var(--dark-text);
  display: flex;
  flex-direction: column;
}

/* 顶部导航样式 */
.conversation-view-header {
  background-color: var(--white);
  border-bottom: 1px solid var(--gray-200);
}

.conversation-view-header-content {
  width: 100%;
  padding: 12px 24px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.conversation-view-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.conversation-view-logo-text {
  margin-left: 0;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.conversation-view-message-avatar .avatar-robot {
  width: 22px;
  height: 22px;
}

.conversation-view-right {
  display: flex;
  align-items: center;
  gap: 32px;
}

.conversation-view-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.conversation-view-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.conversation-view-auth-link {
  color: var(--gray-500);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;
}

.conversation-view-auth-link:hover {
  color: var(--primary-color);
}

.conversation-view-auth-link.primary {
  color: var(--white);
  background: var(--primary-color);
}

.conversation-view-auth-link.primary:hover {
  background: #153e68;
  color: var(--white);
}

.conversation-view-username {
  font-size: 14px;
  color: var(--gray-600);
  margin-right: 4px;
}

.conversation-view-auth-btn {
  font-size: 14px;
  padding: 6px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--white);
  color: var(--gray-600);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.conversation-view-auth-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.conversation-view-nav-link {
  color: var(--gray-500);
  text-decoration: none;
  transition: color 0.3s ease;
  font-size: 16px;
}

.conversation-view-nav-link:hover,
.conversation-view-nav-link.active,
.conversation-view-nav-link.router-link-active {
  color: var(--primary-color);
  font-weight: 500;
}

/* 主要内容区样式 */
.conversation-view-main {
  width: 100%;
  margin: 0;
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.conversation-view-chat {
  width: 100%;
  height: calc(100vh - 80px);
  background-color: var(--white);
  display: flex;
  flex-direction: row;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 左侧对话列表 */
.conversation-view-sidebar {
  width: 280px;
  min-width: 280px;
  background-color: var(--light-bg);
  border-right: 1px solid var(--gray-200);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

.conversation-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--gray-200);
}

.conversation-sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0;
}

.conversation-sidebar-new-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 14px;
  font-weight: 500;
  color: var(--primary-color);
  background: transparent;
  border: 1px solid var(--primary-color);
  border-radius: 6px;
  cursor: pointer;
  transition: color 0.2s ease, background-color 0.2s ease;
}

.conversation-sidebar-new-btn:hover {
  color: var(--white);
  background-color: var(--primary-color);
}

.conversation-sidebar-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  position: relative;
}

.conversation-item:hover {
  background-color: var(--gray-100);
}

.conversation-item.active {
  background-color: var(--primary-color);
  color: var(--white);
}

.conversation-item-title {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-item-delete {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--gray-500);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease, color 0.2s ease;
}

.conversation-item:hover .conversation-item-delete {
  opacity: 1;
}

.conversation-item.active .conversation-item-delete {
  color: var(--white);
}

.conversation-item-delete:hover {
  color: var(--primary-color);
}

/* 右侧对话内容 */
.conversation-view-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

/* 消息区域 */
.conversation-view-message-box {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background-color: var(--white);
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.conversation-view-message-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 32px;
  gap: 12px;
  width: 100%;
  min-width: 0;
}

.conversation-view-message-item.user {
  flex-direction: row-reverse;
}

.conversation-view-message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 18px;
}

.conversation-view-message-avatar.ai {
  background-color: var(--primary-color);
  color: var(--white);
  margin-right: 12px;
}

.conversation-view-message-avatar.user {
  background-color: var(--gray-200);
  color: var(--gray-600);
  margin-left: 12px;
}

.conversation-view-message-content {
  min-width: 0;
  padding: 20px 24px;
  border-radius: 12px;
  font-size: 16px;
  line-height: 1.8;
  word-wrap: break-word;
  word-break: break-word;
  white-space: normal;
  overflow-wrap: break-word;
  box-sizing: border-box;
  display: inline-block;
  position: relative;
}

.conversation-view-message-content.ai {
  background-color: var(--light-bg);
  color: var(--gray-600);
  border-bottom-left-radius: 4px;
  max-width: 75%;
}

.conversation-view-message-content.user {
  background-color: var(--primary-color);
  color: var(--white);
  border-bottom-right-radius: 4px;
  max-width: 75%;
  width: auto;
  display: inline-block;
}

.conversation-view-message-content p {
  margin: 0 0 12px 0;
  padding: 0;
  font-size: 16px;
  line-height: 1.8;
  word-wrap: break-word;
  word-break: break-word;
  white-space: normal;
  overflow-wrap: break-word;
  width: 100%;
  display: block;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.conversation-view-message-content p:last-child {
  margin-bottom: 0;
}

.message-text {
  display: inline-block;
  word-wrap: break-word;
  word-break: break-word;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  box-sizing: border-box;
  font-size: 16px;
  line-height: 1.8;
  max-width: 100%;
  overflow: visible;
  text-overflow: clip;
}

/* 输入区域 */
.conversation-view-input-area {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 16px 24px;
  border-top: 1px solid var(--gray-200);
  background-color: var(--white);
  box-sizing: border-box;
}

.conversation-view-textarea {
  flex: 1;
  box-sizing: border-box;
  border: 1px solid var(--gray-200);
  border-right: none;
  border-bottom-left-radius: 8px;
  border-top-left-radius: 8px;
  padding: 12px 16px;
  font-size: 16px;
  resize: none;
  font-family: inherit;
  transition: all 0.3s ease;
  min-height: 60px;
  max-height: 200px;
  overflow-y: auto;
  line-height: 1.5;
}

.conversation-view-textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(26, 54, 93, 0.1);
}

.conversation-view-send-btn,
.conversation-view-stop-btn {
  flex-shrink: 0;
  box-sizing: border-box;
  width: auto;
  height: 60px;
  min-height: 60px;
  border-bottom-right-radius: 8px;
  border-top-right-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.conversation-view-send-btn {
  background-color: var(--primary-color);
  color: var(--white);
  border: 1px solid var(--primary-color);
  padding: 0 24px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.conversation-view-stop-btn {
  background-color: var(--gray-200);
  color: var(--gray-600);
  border: 1px solid var(--gray-200);
  padding: 0 24px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.conversation-view-stop-btn:hover {
  background-color: #d1d5db;
  color: var(--dark-text);
}

.conversation-view-send-btn:hover:not(:disabled) {
  background-color: #152A45;
}

.conversation-view-send-btn:disabled {
  background-color: var(--gray-200);
  border-color: var(--gray-200);
  cursor: not-allowed;
}

/* 常见问题 */
.conversation-view-quick-questions {
  margin-top: 24px;
}

.conversation-view-quick-questions-title {
  color: var(--gray-500);
  font-size: 14px;
  margin-bottom: 12px;
}

.conversation-view-quick-questions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.conversation-view-quick-question-btn {
  padding: 6px 12px;
  background-color: var(--light-bg);
  color: var(--primary-color);
  border: none;
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.conversation-view-quick-question-btn:hover {
  background-color: rgba(26, 54, 93, 0.1);
  transform: translateY(-1px);
}

/* 加载动画 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background-color: var(--primary-color);
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

/* 响应式设计 */
@media (max-width: 639px) {
  .conversation-view-header-content {
    padding: 16px;
    flex-direction: column;
    gap: 16px;
  }

  .conversation-view-logo-text {
    white-space: normal;
    text-align: center;
  }
  
  .conversation-view-nav {
    gap: 16px;
  }
  
  .conversation-view-nav-link {
    font-size: 14px;
  }
  
  .conversation-view-main {
    padding: 24px 16px;
  }
  
  .conversation-view-chat {
    padding: 16px;
  }
  
  .conversation-view-message-box {
    min-height: 200px;
    max-height: calc(100vh - 350px);
    flex: 1 1 auto;
  }
  
  .conversation-view-message-content {
    max-width: 85%;
    min-width: 0;
    padding: 16px 20px;
    font-size: 15px;
    flex: 1 1 auto;
  }
  
  .conversation-view-message-content p {
    font-size: 15px;
  }
  
  .message-text {
    font-size: 15px;
  }
  
  .conversation-view-textarea {
    font-size: 14px;
  }
  
  .conversation-view-send-btn,
  .conversation-view-stop-btn {
    font-size: 14px;
    padding: 12px 16px;
  }
}
</style>