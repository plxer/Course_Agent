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
            <router-link to="/reading" class="conversation-view-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
            <router-link to="/videos" class="conversation-view-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
            <router-link to="/exercises" class="conversation-view-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>
            <router-link to="/mall" class="conversation-view-nav-link" :class="{ active: $route.path === '/mall' }">积分商城</router-link>
            <router-link v-if="userStore.isAdmin" to="/ops" class="conversation-view-nav-link" :class="{ active: $route.path === '/ops' }">运维</router-link>
            <router-link to="/guide" class="conversation-view-nav-link" :class="{ active: $route.path === '/guide' }">使用指南</router-link>
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
                  class="conversation-item-delete"
                  type="button"
                  :disabled="chatList.length === 1 && (chat.messages?.length ?? 0) === 0"
                  @click.stop="deleteChat(chat.id)"
                  :title="chatList.length === 1 && (chat.messages?.length ?? 0) === 0 ? '仅剩一个空对话，无法删除' : '删除对话'"
                  :aria-label="chatList.length === 1 && (chat.messages?.length ?? 0) === 0 ? '仅剩一个空对话，无法删除' : '删除对话'"
                >
                  <svg class="conversation-item-delete-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
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
                <div class="message-text">你好！我是课程智能体，很高兴为你解答《计算机网络》学习中的问题。请问有什么我可以帮助你的吗？</div>
              </div>
            </div>

            <!-- 动态消息列表 -->
          <div v-for="(message, index) in messages" :key="index" class="conversation-view-message-item" :class="message.role">
            <div v-if="message.role === 'ai'" class="conversation-view-message-avatar ai" title="AI 助手">
              <svg class="avatar-robot" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"/></svg>
            </div>
            <div class="conversation-view-message-content" :class="message.role">
              <div v-if="message.role === 'user'" class="conversation-view-user-msg">
                <div v-if="message.image_content" class="conversation-view-user-img-wrap">
                  <img :src="conversationUserImageSrc(message)" alt="" class="conversation-view-user-img" />
                </div>
                <div v-if="message.content" class="message-text">{{ message.content }}</div>
              </div>
              <template v-else-if="message.role === 'ai'">
                <div
                  v-if="message.sources && message.sources.length > 0"
                  class="conversation-view-msg-sources"
                >
                  <div class="msg-sources-title">参考来源（共 {{ message.sources.length }} 条）</div>
                  <ul class="msg-sources-list">
                    <li
                      v-for="(src, idx) in message.sources"
                      :key="idx"
                      class="msg-sources-item"
                    >
                      <a :href="src.url" target="_blank" rel="noopener noreferrer">{{ src.title || src.url }}</a>
                    </li>
                  </ul>
                </div>
                <div
                  v-if="message.content"
                  class="message-text conversation-view-markdown"
                  @click="onMessageContentClick"
                  v-html="renderMarkdownWithPageLinks(message.content)"
                />
              </template>
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
              <div
                v-if="searchSources.length > 0"
                class="conversation-view-search-sources"
              >
                <div class="search-sources-title">信息来源</div>
                <ul class="search-sources-list">
                  <li
                    v-for="(src, idx) in searchSources"
                    :key="idx"
                    class="search-sources-item"
                  >
                    <a :href="src.url" target="_blank" rel="noopener noreferrer">{{ src.title || src.url }}</a>
                  </li>
                </ul>
              </div>
              <div v-if="currentAiMessage" :key="`loading-${currentAiMessage.length}`" class="conversation-view-message-with-spinner">
                <div
                  class="message-text conversation-view-markdown"
                  @click="onMessageContentClick"
                  v-html="renderMarkdownWithPageLinks(currentAiMessage)"
                />
                <!-- 转圈单独一行，避免被遮挡；AI 说出「搜索」或收到 tool_calling 时显示 -->
                <div v-if="showSearchSpinner" class="conversation-view-spinner-row">
                  <span class="conversation-view-spinner-inline" aria-hidden="true"></span>
                  <span class="conversation-view-spinner-label">搜索中</span>
                </div>
              </div>
              <div v-else-if="searchSources.length === 0" class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

          <!-- 输入区域 -->
          <div class="conversation-view-input-wrap">
            <div class="conversation-view-input-options">
              <label class="conversation-view-web-search-opt">
                <input type="checkbox" v-model="enableWebSearch" class="conversation-view-web-search-cb" />
                <span>启用网络搜索</span>
              </label>
            </div>
            <div class="conversation-view-input-area">
              <div v-if="pendingConversationImage" class="conversation-view-pending-img">
                <img :src="pendingConversationImageThumbSrc" alt="" class="conversation-view-pending-thumb" />
                <button type="button" class="conversation-view-pending-remove" @click="clearPendingConversationImage">移除图片</button>
              </div>
              <div class="conversation-view-input-row">
              <button
                type="button"
                class="conversation-view-img-btn"
                title="选择图片"
                :disabled="isLoading && currentChatId === activeRequestChatId"
                @click="pickConversationImage"
              >
                <Image :size="20" class="conversation-view-img-btn-icon" aria-hidden="true" />
              </button>
              <textarea
                ref="inputTextarea"
                v-model="inputMessage"
                class="conversation-view-textarea"
                placeholder="本平台仅支持计算机网络相关知识点提问（如协议、TCP/IP、HTTP、DNS、SDN、路由、网络安全等），与课程无关的问题将无法解答。可附带上传配图。"
                @input="adjustTextareaHeight"
                @keydown.enter.exact.prevent="sendMessage"
                @keydown.enter.shift.exact="handleShiftEnter"
              ></textarea>
            <button 
              v-if="!isLoading || currentChatId !== activeRequestChatId"
              class="conversation-view-send-btn" 
              @click="sendMessage"
              :disabled="(!inputMessage.trim() && !pendingConversationImage) || isLoading"
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
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { useRouter } from 'vue-router';
import { marked } from 'marked';
import { message } from 'ant-design-vue';
import { Image } from 'lucide-vue-next';
import { courseChatStream, generateConversationTitle, listCourseKnowledgeBases, saveReadingPosition } from '@/apis/courseApi.js';
import { agentApi, threadApi, multimodalApi } from '@/apis';
import { useUserStore } from '@/stores/user';
import { useCourseConversationStore } from '@/stores/courseConversation';

const router = useRouter();
const userStore = useUserStore();
const store = useCourseConversationStore();
const inputMessage = ref('');
/** 待发送的课程对话配图 */
const pendingConversationImage = ref(null);

const pendingConversationImageThumbSrc = computed(() => {
  const p = pendingConversationImage.value;
  if (!p) return '';
  if (p.thumbnailContent) return `data:image/jpeg;base64,${p.thumbnailContent}`;
  const mime = p.mimeType || 'image/jpeg';
  return `data:${mime};base64,${p.imageContent}`;
});

function conversationUserImageSrc(msg) {
  if (!msg?.image_content) return '';
  const mime = msg.image_mime_type || 'image/jpeg';
  return `data:${mime};base64,${msg.image_content}`;
}

function clearPendingConversationImage() {
  pendingConversationImage.value = null;
}

function pickConversationImage() {
  if (store.isLoading && store.currentChatId === store.activeRequestChatId) return;
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  input.onchange = async (ev) => {
    const file = ev.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      message.error('图片需小于 10MB');
      return;
    }
    message.loading({ content: '正在处理图片…', key: 'course-conv-img' });
    try {
      const res = await multimodalApi.uploadImage(file);
      if (res.success) {
        pendingConversationImage.value = {
          imageContent: res.image_content,
          mimeType: res.mime_type || file.type || 'image/jpeg',
          thumbnailContent: res.thumbnail_content
        };
        message.success({ content: '已添加配图', key: 'course-conv-img', duration: 2 });
      } else {
        message.error({ content: res.error || '图片处理失败', key: 'course-conv-img' });
      }
    } catch (_) {
      message.error({ content: '图片上传失败', key: 'course-conv-img' });
    }
  };
  input.click();
}

/** 启用网络搜索：与当前对话绑定，切换对话或切回页面时从 store 恢复 */
const enableWebSearch = ref(false);
/** 课程知识库列表（从接口拉取，用于 textbookPdfBookId 等） */
const courseKnowledgeBases = ref([]);

/** 默认知识库 id（计算机网络）。仅用于新建对话的初始值；某对话改为「无」后只影响该对话，新建对话仍用此默认。 */
const DEFAULT_KNOWLEDGE_BASE_ID = 'computer_networking';

/** 课本伴读 PDF 的 book_id（用于页码跳转），仅针对计算机网络知识库 */
const textbookPdfBookId = computed(() => {
  const kb = courseKnowledgeBases.value.find((k) => k.id === 'computer_networking');
  return kb?.pdf_book_id || 'ComputerNetworking-TopDown-v8-2021';
});

// 启用网络搜索与当前对话绑定：切换勾选时写入当前对话，切到别的界面再回来仍保留
watch(enableWebSearch, (val) => {
  const chat = store.currentChat;
  if (chat) chat.enableWebSearch = Boolean(val);
});

function renderMarkdown(text) {
  if (!text || typeof text !== 'string') return '';
  return marked.parse(text, { gfm: true, breaks: true });
}

/** PDF 页索引 = 课本页码 + 11（封面等占前 11 页） */
const TEXTBOOK_PAGE_OFFSET = 11;

/** 将「对应课本页码：15、16」等裸数字转为 **15** 以便转成可点击的课本页链接 */
function preprocessTextbookPageLineForMarkdown(text) {
  if (!text || typeof text !== 'string') return text;
  return text.replace(
    /(对应课本页码[：:]\s*)(\d+(?:\s*[、，,]\s*\d+)*)/g,
    (_, label, group) => {
      const nums = group.match(/\d+/g);
      if (!nums?.length) return label + group;
      return label + nums.map((n) => `**${n}**`).join('、');
    }
  );
}

/** 渲染 AI 消息：将 **数字**（课本页码）转为链接——文案显示课本页，跳转使用 PDF 页（课本页码 + 11） */
function renderMarkdownWithPageLinks(text) {
  let html = renderMarkdown(preprocessTextbookPageLineForMarkdown(text));
  if (!html || !textbookPdfBookId.value) return html;
  const bookId = textbookPdfBookId.value;
  html = html.replace(/<strong>(\d+)<\/strong>/g, (_, page) => {
    const printed = parseInt(page, 10);
    const pdfPage = printed + TEXTBOOK_PAGE_OFFSET;
    return `<a href="/reading?book=${encodeURIComponent(bookId)}&page=${pdfPage}&from=conversation" class="conversation-view-page-link" data-book-id="${encodeURIComponent(bookId)}" data-page="${pdfPage}">第${printed}页</a>`;
  });
  html = html.replace(/<\/a>\s*页/g, '</a>');
  return html;
}

function onMessageContentClick(e) {
  const link = e.target.closest('.conversation-view-page-link');
  if (!link) return;
  e.preventDefault();
  const bookId = link.getAttribute('data-book-id');
  const page = link.getAttribute('data-page');
  if (bookId && page) goToReadingPage(bookId, parseInt(page, 10));
}

function goToReadingPage(bookId, page) {
  if (!bookId || !page || page < 1) return;
  if (userStore.isLoggedIn) saveReadingPosition(bookId, page).catch(() => {});
  router.push({
    path: '/reading',
    query: { book: bookId, page: String(page), from: 'conversation' },
  });
}

const handleLogout = () => {
  store.resetStreamState();
  userStore.logout();
};
const handleSwitchAccount = () => {
  store.resetStreamState();
  userStore.logout();
};

const messageBox = ref(null);
const inputTextarea = ref(null);

// 从 store 取状态，便于模板和逻辑中使用
const chatList = computed(() => store.chatList);
const currentChatId = computed(() => store.currentChatId);
const messages = computed(() => store.messages);
const isLoading = computed(() => store.isLoading);
const threadId = computed(() => store.threadId);
const currentAiMessage = computed(() => store.currentAiMessage);
const activeRequestChatId = computed(() => store.activeRequestChatId);
const searchStatus = computed(() => store.searchStatus);
const searchQuery = computed(() => store.searchQuery);
const searchSources = computed(() => store.searchSources);
/** 是否显示搜索中转圈：仅当 searchStatus 为 searching 时显示，搜索完成(done)后不再显示 */
const showSearchSpinner = computed(() => {
  if (store.searchStatus === 'searching') return true;
  if (store.searchStatus === 'done') return false;
  if (store.isLoading && store.currentAiMessage && /搜索/.test(store.currentAiMessage)) return true;
  return false;
});

// 根据首条用户问题 + 首条智能体回答，调用模型生成简短标题并同步到后端
const summarizeChatTitle = async (chat) => {
  const userMsg = chat.messages?.find(m => m.role === 'user');
  const aiMsg = chat.messages?.find(m => m.role === 'ai');
  if (!userMsg?.content) return;
  const firstQuestion = userMsg.content.trim();
  const firstAnswer = (aiMsg?.content || '').trim();
  let title = firstQuestion.length <= 20 ? firstQuestion : firstQuestion.slice(0, 20) + '…';
  if (userStore.isLoggedIn && firstAnswer) {
    try {
      const generated = await generateConversationTitle(firstQuestion, firstAnswer);
      if (generated) title = generated;
    } catch (_) {}
  }
  chat.title = title;
  if (userStore.isLoggedIn && store.defaultAgentId && chat.id) {
    threadApi.updateThread(chat.id, title).catch((err) => console.error('更新对话标题失败:', err));
  }
};

// 从后端历史记录格式转为页面使用的 messages（保留 tool_calls，并从网络搜索结果中提取 sources 用于展示链接）
function historyToMessages(history) {
  if (!Array.isArray(history)) return [];
  return history
    .filter((m) => m.type === 'human' || m.type === 'ai')
    .map((m) => {
      const role = m.type === 'human' ? 'user' : 'ai';
      const base = { role, content: m.content || '' };
      if (role !== 'ai') return base;
      // 从 AI 消息的 tool_calls 中提取网络搜索来源，供「参考来源」展示
      const toolCalls = m.tool_calls;
      if (!Array.isArray(toolCalls) || toolCalls.length === 0) return base;
      const sources = [];
      for (const tc of toolCalls) {
        const name = (tc.name || tc.function?.name || '').toLowerCase();
        if (!name.includes('tavily')) continue;
        const resultContent = tc.tool_call_result?.content;
        if (!resultContent) continue;
        let data;
        try {
          data = typeof resultContent === 'string' ? JSON.parse(resultContent) : resultContent;
        } catch {
          continue;
        }
        if (Array.isArray(data.results)) {
          for (const r of data.results) {
            if (r?.url) sources.push({ title: r.title || r.url || '', url: r.url });
          }
        }
      }
      if (sources.length > 0) base.sources = sources;
      if (toolCalls.length > 0) base.tool_calls = toolCalls;
      return base;
    });
}

// 加载指定 thread 的历史并填入 chat.messages
async function loadThreadHistory(chat) {
  if (!store.defaultAgentId || !chat.id) return;
  try {
    const res = await agentApi.getAgentHistory(store.defaultAgentId, chat.id);
    const list = res?.history ? historyToMessages(res.history) : [];
    chat.messages = list;
  } catch (err) {
    console.error('加载对话历史失败:', err);
    chat.messages = chat.messages || [];
  }
}

// 新对话编号 = 当前用户未删除的对话数 + 1
const getNextConversationNumber = () => store.chatList.length + 1;

// 将左侧当前选中的对话项滚动到可见区域（新建对话后列表超出屏幕时自动跟到底部）
const scrollActiveConversationIntoView = () => {
  nextTick(() => {
    const active = document.querySelector('.conversation-view-sidebar .conversation-item.active');
    if (active) active.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  });
};

// 创建新对话（已登录时调用后端创建 thread 并加入列表）
const createNewChat = async () => {
  const nextNum = getNextConversationNumber();
  const title = `对话 ${nextNum}`;
  if (userStore.isLoggedIn && store.defaultAgentId) {
    try {
      const thread = await threadApi.createThread(store.defaultAgentId, title);
      // 新建对话一律使用默认值，不继承当前对话的知识库/网络搜索选择
      const newChat = {
        id: thread.id,
        title: thread.title || title,
        messages: [],
        threadId: thread.id,
        knowledgeBase: DEFAULT_KNOWLEDGE_BASE_ID,
        enableWebSearch: false
      };
      store.chatList.push(newChat);
      switchChat(newChat.id);
      scrollActiveConversationIntoView();
    } catch (err) {
      console.error('创建对话失败:', err);
      createNewChatLocal(title);
    }
  } else {
    createNewChatLocal(title);
  }
};

function createNewChatLocal(title) {
  const finalTitle = title || `对话 ${getNextConversationNumber()}`;
  // 新建对话一律使用默认值，不继承当前对话的知识库/网络搜索选择
  const newChat = {
    id: Date.now().toString(),
    title: finalTitle,
    messages: [],
    threadId: null,
    knowledgeBase: DEFAULT_KNOWLEDGE_BASE_ID,
    enableWebSearch: false
  };
  store.chatList.push(newChat);
  switchChat(newChat.id);
  scrollActiveConversationIntoView();
}

// 切换对话（已登录时从后端拉取该 thread 的历史）
const switchChat = async (chatId) => {
  const chat = store.findChat(chatId);
  if (!chat) return;

  store.setCurrentChatId(chatId);
  store.setThreadId(chat.threadId ?? chat.id);
  inputMessage.value = '';
  enableWebSearch.value = Boolean(chat.enableWebSearch);

  if (userStore.isLoggedIn && store.defaultAgentId) {
    if (chat.messages.length === 0) await loadThreadHistory(chat);
  }

  nextTick(() => {
    scrollToBottom();
    adjustTextareaHeight();
  });
};

// 删除对话（已登录时同时删除后端 thread）
const deleteChat = async (chatId) => {
  const index = store.chatList.findIndex((c) => c.id === chatId);
  if (index === -1) return;
  const chat = store.chatList[index];
  if (store.chatList.length === 1 && (chat.messages?.length ?? 0) === 0) return;

  if (userStore.isLoggedIn && store.defaultAgentId) {
    try {
      await threadApi.deleteThread(chatId);
    } catch (err) {
      console.error('删除对话失败:', err);
    }
  }

  store.chatList.splice(index, 1);

  // 仅剩一个对话且该对话未被命名时，改名为「对话1」（未命名 = 无标题或标题为默认「对话 N」；不影响首轮对话总结）
  if (store.chatList.length === 1) {
    const remaining = store.chatList[0];
    const title = remaining.title ? String(remaining.title).trim() : '';
    const isUnnamed = !title || /^对话\s*\d+$/.test(title);
    if (isUnnamed) {
      remaining.title = '对话1';
      if (userStore.isLoggedIn && store.defaultAgentId && remaining.id) {
        threadApi.updateThread(remaining.id, '对话1').catch((err) => console.error('更新对话标题失败:', err));
      }
    }
  }

  if (store.currentChatId === chatId) {
    if (store.chatList.length > 0) {
      // 优先切到“被删除窗口的前一个”
      // 由于这里已 splice(index, 1)，所以 index-1 对应的是删除前的前一个元素
      const prevIndex = Math.max(0, index - 1);
      const prevChat = store.chatList[prevIndex];
      if (prevChat?.id) {
        switchChat(prevChat.id);
      } else {
        // 理论上不会到这里：chatList.length > 0 且 prevIndex >= 0
        switchChat(store.chatList[0].id);
      }
    } else {
      await createNewChat();
    }
  }
};

// 发送消息（使用课程对话流接口，由后端根据 DEFAULT_AGENT_ID 决定智能体，固定为 ChatbotAgent）
// 流式回调内通过 store 更新状态，切到其他页面再切回时仍能保留对话且不打断输出
const sendMessage = async () => {
  const content = inputMessage.value.trim();
  const imgSnap = pendingConversationImage.value;
  if ((!content && !imgSnap) || store.isLoading) return;

  const chatIdForThisRequest = store.currentChatId;
  const chat = store.findChat(chatIdForThisRequest);
  if (!chat) return;

  store.setActiveRequestChatId(chatIdForThisRequest);
  const userBubbleText = content || '（附图）';
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
  );
  inputMessage.value = '';
  pendingConversationImage.value = null;
  await nextTick();
  scrollToBottom();

  store.setLoading(true);
  store.clearCurrentAiMessage();
  store.clearSearchState();
  const controller = new AbortController();
  store.setStreamController(controller);

  let tid = store.threadId || chat.threadId || chat.id || Date.now().toString() + Math.random().toString(36).substr(2, 9);
  if (!chat.threadId) chat.threadId = tid;
  store.setThreadId(tid);

  /** 后端 400 等错误会先通过 onChunk(status:'error') 展示，再 throw，避免 catch 里重复追加同一条或通用网络提示 */
  let errorAlreadyShown = false;

  // 流式缓冲：减少逐字更新 DOM，每 50ms 或结束时批量写入，使输出更流畅
  const STREAM_FLUSH_MS = 50;
  let streamTextBuffer = '';
  let streamFlushTimer = null;
  const flushStreamBuffer = () => {
    if (streamTextBuffer.length === 0) return;
    const convStore = useCourseConversationStore();
    convStore.appendCurrentAiMessage(streamTextBuffer);
    streamTextBuffer = '';
    if (convStore.currentChatId === chatIdForThisRequest) nextTick(() => scrollToBottom());
  };
  const scheduleStreamFlush = () => {
    if (streamFlushTimer != null) return;
    streamFlushTimer = setTimeout(() => {
      streamFlushTimer = null;
      flushStreamBuffer();
    }, STREAM_FLUSH_MS);
  };

  try {
    await courseChatStream(
      content,
      tid,
      (chunk) => {
        const convStore = useCourseConversationStore();
        const targetChat = convStore.findChat(chatIdForThisRequest);
        if (!targetChat) return;

        if (chunk.status === 'init') {
          const fromChunk = (chunk.meta && chunk.meta.thread_id) ? chunk.meta.thread_id : chunk.thread_id;
          if (fromChunk) {
            convStore.setThreadId(fromChunk);
            targetChat.threadId = fromChunk;
          }
        } else if (chunk.status === 'loading') {
          if (chunk.response !== undefined) {
            if (chunk.response) {
              streamTextBuffer += chunk.response;
              scheduleStreamFlush();
            }
          }
          if (chunk.tool_calling?.name && String(chunk.tool_calling.name).toLowerCase().includes('tavily')) {
            convStore.setSearching(chunk.tool_calling.query || '');
          }
          const msg = chunk.msg;
          const hasToolCalls = Array.isArray(msg?.tool_calls) && msg.tool_calls.length > 0;
          const isAiLike = msg?.type === 'ai' || msg?.type === 'AIMessage' || msg?.type === 'AIMessageChunk';
          if (hasToolCalls && isAiLike) {
            const tavilyCall = msg.tool_calls.find((tc) => (tc.name || tc.function?.name || '').toLowerCase().includes('tavily'));
            if (tavilyCall) {
              let q = '';
              const args = tavilyCall.args ?? tavilyCall.function?.arguments;
              if (typeof args === 'string') {
                try {
                  const p = JSON.parse(args);
                  q = p.query ?? p.q ?? '';
                } catch (_) {}
              } else if (args && typeof args === 'object') {
                q = args.query ?? args.q ?? '';
              }
              convStore.setSearching(q);
            }
          }
          const isTool = msg?.type === 'tool' || msg?.type === 'ToolMessage';
          if (isTool) {
            const name = (msg.name || '').toLowerCase();
            if (name.includes('tavily')) {
              let raw = msg.content;
              if (Array.isArray(raw)) {
                const textBlock = raw.find((b) => b?.type === 'text');
                raw = textBlock?.text ?? (typeof raw[0] === 'string' ? raw[0] : '');
              }
              let list = [];
              if (typeof raw === 'string') {
                try {
                  const data = JSON.parse(raw);
                  if (Array.isArray(data.results)) {
                    list = data.results.map((r) => ({ title: r.title || r.url || '', url: r.url || '#' }));
                  }
                } catch (_) {}
              }
              convStore.appendSearchSources(list);
            }
          }
          if (convStore.currentChatId === chatIdForThisRequest) nextTick(() => scrollToBottom());
        } else if (chunk.status === 'finished') {
          if (streamFlushTimer != null) {
            clearTimeout(streamFlushTimer);
            streamFlushTimer = null;
          }
          flushStreamBuffer();
          if (convStore.currentAiMessage) {
            const sources = convStore.searchSources.length ? [...convStore.searchSources] : undefined;
            targetChat.messages.push({
              role: 'ai',
              content: convStore.currentAiMessage,
              sources
            });
            if (targetChat.messages.length === 2) summarizeChatTitle(targetChat).catch(() => {});
            convStore.clearCurrentAiMessage();
          }
          convStore.clearSearchState();
          convStore.setLoading(false);
          convStore.setActiveRequestChatId(null);
          if (convStore.currentChatId === chatIdForThisRequest) nextTick(() => scrollToBottom());
        } else if (chunk.status === 'error') {
          errorAlreadyShown = true;
          if (streamFlushTimer != null) {
            clearTimeout(streamFlushTimer);
            streamFlushTimer = null;
          }
          flushStreamBuffer();
          const errMsg = chunk.error_message || chunk.message || '抱歉，连接服务器失败，请检查网络或稍后再试。';
          targetChat.messages.push({ role: 'ai', content: errMsg });
          convStore.setLoading(false);
          convStore.clearCurrentAiMessage();
          convStore.setActiveRequestChatId(null);
          if (convStore.currentChatId === chatIdForThisRequest) nextTick(() => scrollToBottom());
        }
      },
      {
        signal: controller.signal,
        enableWebSearch: store.currentChat?.enableWebSearch ?? enableWebSearch.value,
        knowledgeBase: DEFAULT_KNOWLEDGE_BASE_ID,
        imageContent: imgSnap?.imageContent,
        imageMimeType: imgSnap?.mimeType
      }
    );
  } catch (error) {
    if (streamFlushTimer != null) {
      clearTimeout(streamFlushTimer);
      streamFlushTimer = null;
    }
    flushStreamBuffer();
    const targetChat = store.findChat(chatIdForThisRequest);
    if (targetChat) {
      if (error.name === 'AbortError') {
        if (store.currentAiMessage || store.searchSources.length) {
          const sources = store.searchSources.length ? [...store.searchSources] : undefined;
          targetChat.messages.push({
            role: 'ai',
            content: store.currentAiMessage || '',
            ...(sources ? { sources } : {})
          });
          if (targetChat.messages.length === 2) summarizeChatTitle(targetChat).catch(() => {});
        }
      } else {
        console.error('发送消息失败:', error);
        if (!errorAlreadyShown) {
          const networkMsg = '无法连接服务器，请确认：1) 后端服务已启动；2) 浏览器访问的地址已正确代理到后端（如 localhost:5173 的 /api 会转发到后端）。若未登录，请先登录。';
          targetChat.messages.push({ role: 'ai', content: networkMsg });
        }
      }
    }
    store.clearCurrentAiMessage();
    store.clearSearchState();
    store.setLoading(false);
    store.setActiveRequestChatId(null);
    store.setStreamController(null);
    if (store.currentChatId === chatIdForThisRequest) await nextTick(() => scrollToBottom());
  }
};

const stopStream = () => {
  if (store.streamController) {
    store.streamController.abort();
  }
};

// 初始化：已登录时从后端拉取对话列表并选中第一个；未登录时仅创建本地对话
// 若 store 中已有数据（如从其他页面切回），则不再覆盖，避免对话消失
onMounted(async () => {
  if (!document.querySelector('link[href*="font-awesome"]')) {
    const link = document.createElement('link');
    link.href = 'https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css';
    link.rel = 'stylesheet';
    document.head.appendChild(link);
  }

  listCourseKnowledgeBases()
    .then((res) => {
      courseKnowledgeBases.value = Array.isArray(res?.knowledge_bases) ? res.knowledge_bases : [];
    })
    .catch(() => {});

  if (!userStore.isLoggedIn) {
    if (store.chatList.length === 0) createNewChat();
    else enableWebSearch.value = Boolean(store.currentChat?.enableWebSearch);
    return;
  }

  if (store.chatList.length > 0) {
    enableWebSearch.value = Boolean(store.currentChat?.enableWebSearch);
    return;
  }

  try {
    const defaultRes = await agentApi.getDefaultAgent();
    const agentId = defaultRes?.default_agent_id;
    if (!agentId) {
      createNewChatLocal();
      return;
    }
    store.setDefaultAgentId(agentId);

    const threads = await threadApi.getThreads(agentId);
    const list = Array.isArray(threads) ? threads : [];
    store.setChatList(list.map((t) => ({
      id: t.id,
      title: t.title || `对话 ${t.id}`,
      messages: [],
      threadId: t.id,
      knowledgeBase: DEFAULT_KNOWLEDGE_BASE_ID,
      enableWebSearch: false
    })));

    if (store.chatList.length > 0) {
      await switchChat(store.chatList[0].id);
    } else {
      createNewChat();
    }
  } catch (err) {
    console.error('加载课程对话列表失败:', err);
    createNewChatLocal();
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
  height: 100vh;
  min-height: 100vh;
  color: var(--dark-text);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部导航样式：固定在顶部，不随内容滚动 */
.conversation-view-header {
  flex-shrink: 0;
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

/* 主要内容区：仅中间消息区可滚动，左侧与底部固定 */
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
  flex: 1;
  min-height: 0;
  background-color: var(--white);
  display: flex;
  flex-direction: row;
  overflow: hidden;
}

/* 左侧对话列表：固定宽度，不随消息区滚动 */
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
  width: 28px;
  height: 28px;
  min-width: 28px;
  min-height: 28px;
  background: var(--gray-200);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: #374151;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s ease, color 0.2s ease;
}

.conversation-item-delete-icon {
  width: 14px;
  height: 14px;
}

.conversation-item-delete:hover:not(:disabled) {
  background: #fecaca;
  color: #b91c1c;
}

.conversation-item-delete:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.conversation-item.active .conversation-item-delete {
  background: rgba(255, 255, 255, 0.2);
  color: var(--white);
}

.conversation-item.active .conversation-item-delete:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.35);
  color: var(--white);
}

.conversation-item.active .conversation-item-delete:disabled {
  opacity: 0.5;
}

/* 右侧对话内容：仅消息区可滚动，输入区固定在底部 */
.conversation-view-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

/* 消息区域：唯一可滚动区域 */
.conversation-view-message-box {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 24px;
  background-color: var(--white);
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
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

/* 流式输出时减少重排，使文字出现更顺畅 */
.conversation-view-message-with-spinner .message-text {
  contain: layout style;
}

/* Markdown 渲染（marked + v-html）：无额外背景，与气泡一致 */
.conversation-view-markdown {
  white-space: normal;
}
.conversation-view-markdown h1,
.conversation-view-markdown h2,
.conversation-view-markdown h3 {
  margin: 1em 0 0.5em;
  font-weight: 600;
  color: inherit;
}
.conversation-view-markdown h1:first-child,
.conversation-view-markdown h2:first-child,
.conversation-view-markdown h3:first-child {
  margin-top: 0;
}
.conversation-view-markdown strong {
  font-weight: 700;
}
.conversation-view-markdown p {
  margin: 0 0 0.5em;
}
.conversation-view-markdown p:last-child {
  margin-bottom: 0;
}
.conversation-view-markdown ul,
.conversation-view-markdown ol {
  margin: 0.5em 0;
  padding-left: 1.5em;
}
.conversation-view-markdown code {
  background: var(--gray-200);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-size: 0.9em;
}
.conversation-view-markdown pre {
  margin: 0.5em 0;
  overflow-x: auto;
}
.conversation-view-markdown pre code {
  display: block;
  padding: 8px 12px;
}

.conversation-view-markdown .conversation-view-page-link {
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 600;
  border-bottom: 1px solid var(--primary-color);
  cursor: pointer;
}

.conversation-view-markdown .conversation-view-page-link:hover {
  text-decoration: underline;
}

/* 流式消息末尾的搜索转圈（单独一行，避免被遮挡） */
.conversation-view-spinner-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  min-height: 22px;
}
.conversation-view-spinner-inline {
  display: inline-block;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  border: 2px solid var(--gray-200);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: conversation-view-spin 0.8s linear infinite;
}
.conversation-view-spinner-label {
  font-size: 14px;
  color: var(--gray-500);
}
@keyframes conversation-view-spin {
  to {
    transform: rotate(360deg);
  }
}

/* 信息来源（流式加载中） */
.conversation-view-search-sources {
  margin-bottom: 12px;
  padding: 10px 12px;
  background: var(--gray-0);
  border-radius: 8px;
  border: 1px solid var(--gray-200);
}
.conversation-view-search-sources .search-sources-title {
  font-size: 12px;
  color: var(--gray-500);
  margin-bottom: 6px;
}
.conversation-view-search-sources .search-sources-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: 13px;
}
.conversation-view-search-sources .search-sources-item {
  margin-bottom: 4px;
}
.conversation-view-search-sources .search-sources-item a {
  color: var(--primary-color);
  text-decoration: none;
}
.conversation-view-search-sources .search-sources-item a:hover {
  text-decoration: underline;
}

/* 历史消息中的参考来源（总结） */
.conversation-view-msg-sources {
  margin-bottom: 12px;
  padding: 10px 12px;
  background: var(--gray-0);
  border-radius: 8px;
  border: 1px solid var(--gray-200);
}
.conversation-view-msg-sources .msg-sources-title {
  font-size: 12px;
  color: var(--gray-500);
  margin-bottom: 6px;
}
.conversation-view-msg-sources .msg-sources-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: 13px;
}
.conversation-view-msg-sources .msg-sources-item {
  margin-bottom: 4px;
}
.conversation-view-msg-sources .msg-sources-item a {
  color: var(--primary-color);
  text-decoration: none;
}
.conversation-view-msg-sources .msg-sources-item a:hover {
  text-decoration: underline;
}

/* 输入区域：固定在底部，不随消息滚动 */
.conversation-view-input-wrap {
  flex-shrink: 0;
  border-top: 1px solid var(--gray-200);
  background-color: var(--white);
}

.conversation-view-input-options {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px 24px;
  padding: 8px 24px 0;
}

.conversation-view-web-search-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 14px;
  color: var(--gray-600);
  cursor: pointer;
  user-select: none;
}

.conversation-view-web-search-cb {
  width: 16px;
  height: 16px;
  accent-color: var(--primary-color);
  cursor: pointer;
}

.conversation-view-input-area {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  padding: 16px 24px;
  box-sizing: border-box;
}

.conversation-view-input-row {
  display: flex;
  align-items: stretch;
  width: 100%;
  gap: 0;
}

.conversation-view-pending-img {
  display: flex;
  align-items: center;
  gap: 12px;
}

.conversation-view-pending-thumb {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--gray-200);
}

.conversation-view-pending-remove {
  padding: 6px 12px;
  font-size: 13px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--white);
  color: var(--gray-700);
  cursor: pointer;
}

.conversation-view-img-btn {
  flex-shrink: 0;
  width: 48px;
  min-height: 60px;
  border: 1px solid var(--gray-200);
  border-right: none;
  border-bottom-left-radius: 8px;
  border-top-left-radius: 8px;
  background: var(--white);
  color: var(--gray-700);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.conversation-view-img-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.conversation-view-img-btn-icon {
  flex-shrink: 0;
  color: var(--gray-700);
  stroke-width: 2;
}

.conversation-view-user-msg {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.conversation-view-user-img-wrap {
  max-width: 240px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--gray-200);
}

.conversation-view-user-img {
  display: block;
  max-width: 100%;
  height: auto;
}

.conversation-view-textarea {
  flex: 1;
  box-sizing: border-box;
  border: 1px solid var(--gray-200);
  border-right: none;
  border-radius: 0;
  border-bottom-left-radius: 0;
  border-top-left-radius: 0;
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