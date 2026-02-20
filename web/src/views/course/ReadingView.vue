<template>
  <div class="reading-container">
    <!-- 顶部导航 -->
    <header class="reading-header">
      <div class="reading-header-content">
        <router-link to="/" class="reading-logo">
          <span class="reading-logo-text">天津大学《计算机网络》课程数智化平台</span>
        </router-link>
        <div class="reading-nav">
          <router-link to="/conversation" class="reading-nav-link" :class="{ active: $route.path === '/conversation' || $route.path === '/course' }">对话</router-link>
          <router-link to="/exercises" class="reading-nav-link" :class="{ active: $route.path === '/exercises' }">习题推荐</router-link>
          <router-link to="/reading" class="reading-nav-link" :class="{ active: $route.path === '/reading' }">课本伴读</router-link>
          <router-link to="/videos" class="reading-nav-link" :class="{ active: $route.path === '/videos' }">视频</router-link>
        </div>
      </div>
    </header>

    <!-- 主要内容区 -->
    <main class="reading-main" v-if="!selectedBook">
      <!-- 标题部分 -->
      <div class="reading-title-section">
        <h1 class="reading-title">课本伴读</h1>
        <p class="reading-subtitle">智能解析教材内容，深入理解知识点，轻松掌握重点难点</p>
      </div>

      <!-- 课本列表 -->
      <div class="reading-list-section">
        <h2 class="reading-list-title">可用课本</h2>
        
        <div class="reading-list" v-if="books.length > 0">
          <div 
            v-for="book in books" 
            :key="book.id" 
            class="reading-card" 
            @click="selectBook(book)"
          >
            <div class="reading-card-header">
              <div class="reading-card-tags">
                <span class="reading-card-tag">PDF</span>
              </div>
            </div>
            <h3 class="reading-card-title">{{ book.name }}</h3>
            <div class="reading-card-footer">
              <div class="reading-card-info">
                <span class="reading-card-page">{{ formatFileSize(book.size) }}</span>
              </div>
              <a href="#" class="reading-card-action" @click.prevent="selectBook(book)">
                开始阅读 <RightOutlined style="margin-left: 4px;" />
              </a>
            </div>
          </div>
        </div>
        <div v-else class="reading-empty">
          <p>暂无可用课本，请将 PDF 文件放入 knowledgebase/books 文件夹</p>
        </div>
      </div>
    </main>

    <!-- PDF 阅读器 -->
    <main class="reading-reader" v-else>
      <div class="reading-reader-header">
        <button class="reading-back-btn" @click="selectedBook = null">
          <ArrowLeftOutlined /> 返回
        </button>
        <h2 class="reading-reader-title">{{ selectedBook.name }}</h2>
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
            @click="showChatPanel = !showChatPanel"
            class="page-nav-btn chat-toggle-btn"
            :class="{ active: showChatPanel }"
            title="打开/关闭对话"
          >
            <CommentOutlined /> {{ showChatPanel ? '关闭对话' : '打开对话' }}
          </button>
        </div>
      </div>

      <div class="reading-reader-wrapper" :class="{ 'with-chat': showChatPanel }">
        <div class="reading-reader-content">
        <!-- PDF 页面显示区域 -->
        <div class="reading-pdf-page" 
             @mousedown="startSelection"
             @mousemove="updateSelection"
             @mouseup="endSelection"
             @mouseleave="cancelSelection">
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
            <div class="reading-selected-text">
              <strong>已选文本：</strong>{{ selectedText }}
            </div>
            <div class="reading-selection-actions" @click.stop>
              <button 
                class="reading-action-btn" 
                @click.stop.prevent="sendToConversation"
                @mousedown.stop.prevent
                @mouseup.stop.prevent
                type="button"
              >
                <CommentOutlined /> 发送到对话
              </button>
            </div>
          </div>
        </div>
        </div>

        <!-- 侧边栏对话面板 -->
        <div v-if="showChatPanel" class="reading-chat-panel">
          <div class="reading-chat-header">
            <h3 class="reading-chat-title">智能对话</h3>
            <button class="reading-chat-close" @click="showChatPanel = false">
              <CloseOutlined />
            </button>
          </div>
          
          <div class="reading-chat-messages" ref="chatMessagesBox">
            <!-- AI欢迎消息 -->
            <div v-if="chatMessages.length === 0" class="reading-chat-message ai">
              <div class="reading-chat-avatar ai" title="AI 助手">
                <svg class="reading-avatar-robot" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"/></svg>
              </div>
              <div class="reading-chat-content ai">
                <div class="reading-chat-text">你好！我是课程智能体，很高兴为你解答学习中的问题。你可以选择文本后发送到对话，或直接输入问题。</div>
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
                <svg class="reading-avatar-robot" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"/></svg>
              </div>
              <div class="reading-chat-content" :class="msg.role">
                <div class="reading-chat-text">{{ msg.content }}</div>
              </div>
              <div v-if="msg.role === 'user'" class="reading-chat-avatar user">
                <span>我</span>
              </div>
            </div>

            <!-- 加载中状态 -->
            <div v-if="isChatLoading" class="reading-chat-message ai">
              <div class="reading-chat-avatar ai" title="AI 助手">
                <svg class="reading-avatar-robot" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h2v1h2v2h2v2h1c.55 0 1 .45 1 1v2h1v2h-1v2H4v-2H3v-2h1v-2c0-.55.45-1 1-1h1v-2h2V8h2V7h2V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M8 18h8v-2H8v2m-1-5h2v2H7v-2m8 0v2h-2v-2h2m-3-3h2v2h-2v-2m-4 0v2H7v-2h2z"/></svg>
              </div>
              <div class="reading-chat-content ai loading">
                <div v-if="currentChatMessage" class="reading-chat-text">{{ currentChatMessage }}</div>
                <div v-else class="reading-chat-typing">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <button type="button" class="reading-chat-stop-btn" @click="stopChatStream" title="停止生成">停止</button>
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="reading-chat-input-area">
            <textarea 
              ref="chatTextarea"
              v-model="chatInputMessage" 
              class="reading-chat-textarea" 
              placeholder="请输入你的问题..."
              @input="adjustTextareaHeight"
              @keydown.enter.exact.prevent="sendChatMessage"
              @keydown.enter.shift.exact="handleShiftEnter"
            ></textarea>
            <button 
              v-if="!isChatLoading"
              class="reading-chat-send-btn" 
              @click="sendChatMessage"
              :disabled="!chatInputMessage.trim()"
            >
              发送
            </button>
            <button 
              v-else
              type="button"
              class="reading-chat-stop-btn-inline"
              @click="stopChatStream"
              title="停止生成"
            >
              停止
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick, h, watch } from 'vue';
import { useRouter } from 'vue-router';
import { LeftOutlined, RightOutlined, ArrowLeftOutlined, CommentOutlined, CloseOutlined } from '@ant-design/icons-vue';
import { listBooks, getBookPages, getBookPageUrl, ocrTextSelection, courseChatStream } from '@/apis/courseApi.js';

const router = useRouter();
const books = ref([]);
const selectedBook = ref(null);
const currentPage = ref(1);
const totalPages = ref(0);
const currentPageImage = ref('');
const jumpPageInput = ref(null); // 页面跳转输入框的值
const pageImage = ref(null);
const selection = ref({
  active: false,
  startX: 0,
  startY: 0,
  endX: 0,
  endY: 0
});
const selectedText = ref('');
const isSelecting = ref(false);
const finalSelectionPosition = ref({ left: 0, top: 0, width: 0, height: 0 });
const isOcrProcessing = ref(false); // 防止重复 OCR 请求

// 对话面板相关
const showChatPanel = ref(false);
const chatMessages = ref([]);
const chatInputMessage = ref('');
const isChatLoading = ref(false);
const chatMessagesBox = ref(null);
const chatTextarea = ref(null);
const chatThreadId = ref(null);
const currentChatMessage = ref('');
const chatStreamController = ref(null);

// 调整输入框高度
const adjustTextareaHeight = () => {
  if (chatTextarea.value) {
    chatTextarea.value.style.height = 'auto';
    chatTextarea.value.style.height = Math.min(chatTextarea.value.scrollHeight, 200) + 'px';
  }
};

// 处理 Shift+Enter
const handleShiftEnter = () => {
  chatInputMessage.value += '\n';
  nextTick(() => {
    adjustTextareaHeight();
  });
};

// 计算选择框样式
const selectionStyle = computed(() => {
  if (!selection.value.active) return {};
  const left = Math.min(selection.value.startX, selection.value.endX);
  const top = Math.min(selection.value.startY, selection.value.endY);
  const width = Math.abs(selection.value.endX - selection.value.startX);
  const height = Math.abs(selection.value.endY - selection.value.startY);
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`
  };
});

// 计算选择框工具栏的位置（显示在选择区域旁边）
const selectionBarStyle = computed(() => {
  if (!selectedText.value) return {};
  
  // 使用保存的最终选择位置或当前选择位置
  const left = finalSelectionPosition.value.left || Math.min(selection.value.startX, selection.value.endX);
  const top = finalSelectionPosition.value.top || Math.min(selection.value.startY, selection.value.endY);
  const width = finalSelectionPosition.value.width || Math.abs(selection.value.endX - selection.value.startX);
  const height = finalSelectionPosition.value.height || Math.abs(selection.value.endY - selection.value.startY);
  
  // 在选择区域右侧显示，如果右侧空间不够则在左侧显示
  const barWidth = 300; // 选择框的预估宽度
  const containerWidth = pageImage.value ? pageImage.value.getBoundingClientRect().width : 800;
  const rightSpace = containerWidth - (left + width);
  
  let barLeft = left + width + 10; // 默认显示在右侧
  let barTop = top;
  
  // 如果右侧空间不够，显示在左侧
  if (rightSpace < barWidth) {
    barLeft = left - barWidth - 10;
  }
  
  // 确保不超出容器边界
  if (barLeft < 0) {
    barLeft = 10;
  }
  if (barLeft + barWidth > containerWidth) {
    barLeft = containerWidth - barWidth - 10;
  }
  
  // 如果选择区域在底部，工具栏显示在上方
  const containerHeight = pageImage.value ? pageImage.value.getBoundingClientRect().height : 600;
  if (top + height > containerHeight - 150) {
    barTop = Math.max(10, top - 120); // 工具栏高度约120px
  }
  
  return {
    left: `${barLeft}px`,
    top: `${barTop}px`,
    position: 'absolute',
    zIndex: 1000
  };
});

// 加载课本列表
const loadBooks = async () => {
  try {
    console.log('开始加载课本列表...');
    const response = await listBooks();
    console.log('API响应:', response);
    books.value = response?.books || [];
    console.log('加载的课本数量:', books.value.length);
    if (books.value.length === 0) {
      console.warn('未找到课本，响应数据:', response);
    }
  } catch (error) {
    console.error('加载课本列表失败:', error);
    books.value = [];
  }
};

// 选择课本
const selectBook = async (book) => {
  selectedBook.value = book;
  currentPage.value = 1;
  selectedText.value = '';
  
  try {
    const response = await getBookPages(book.id);
    totalPages.value = response.page_count || 0;
    await loadPage(1);
  } catch (error) {
    console.error('加载课本信息失败:', error);
  }
};

// 加载页面
const loadPage = async (pageNum) => {
  if (!selectedBook.value) {
    console.error('没有选中的课本');
    return;
  }
  if (pageNum < 1) {
    console.warn('页码不能小于1:', pageNum);
    return;
  }
  if (totalPages.value > 0 && pageNum > totalPages.value) {
    console.warn('页码超出范围:', pageNum, '总页数:', totalPages.value);
    return;
  }
  
  console.log('加载页面:', pageNum, '总页数:', totalPages.value);
  currentPage.value = pageNum;
  // 清空当前图片，强制重新加载
  currentPageImage.value = '';
  await nextTick();
  // 设置新的图片 URL
  currentPageImage.value = getBookPageUrl(selectedBook.value.id, pageNum);
  console.log('图片URL:', currentPageImage.value);
};

// 跳转到指定页面
const goToPage = (pageNum) => {
  console.log('翻页到:', pageNum, '总页数:', totalPages.value);
  if (pageNum < 1 || (totalPages.value > 0 && pageNum > totalPages.value)) {
    console.warn('页码超出范围:', pageNum);
    return;
  }
  loadPage(pageNum);
};

// 处理页面跳转输入
const handleJumpToPage = () => {
  if (!jumpPageInput.value) {
    return;
  }
  
  const targetPage = parseInt(jumpPageInput.value);
  
  if (isNaN(targetPage)) {
    console.warn('无效的页码:', jumpPageInput.value);
    jumpPageInput.value = null;
    return;
  }
  
  if (targetPage < 1) {
    console.warn('页码不能小于1:', targetPage);
    jumpPageInput.value = null;
    return;
  }
  
  if (totalPages.value > 0 && targetPage > totalPages.value) {
    console.warn('页码超出范围:', targetPage, '总页数:', totalPages.value);
    jumpPageInput.value = null;
    return;
  }
  
  // 如果目标页面就是当前页面，不需要跳转
  if (targetPage === currentPage.value) {
    jumpPageInput.value = null;
    return;
  }
  
  goToPage(targetPage);
  jumpPageInput.value = null; // 清空输入框
};

// 图片加载完成
const onImageLoad = () => {
  // 可以在这里添加图片加载完成的处理
  console.log('图片加载成功');
};

// 图片加载错误
const onImageError = (e) => {
  console.error('图片加载失败:', e, 'URL:', currentPageImage.value);
  // 可以显示错误提示
};

// 开始选择
const startSelection = async (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (!pageImage.value) {
    console.warn('图片未加载，无法开始选择');
    return;
  }
  
  // 清除之前的选择状态 - 完全重置
  selectedText.value = '';
  finalSelectionPosition.value = { left: 0, top: 0, width: 0, height: 0 };
  selection.value.active = false;
  isSelecting.value = false;
  isOcrProcessing.value = false;
  
  // 等待一个 tick 确保状态完全清除
  await nextTick();
  
  const container = e.currentTarget.getBoundingClientRect();
  
  selection.value = {
    active: true,
    startX: e.clientX - container.left,
    startY: e.clientY - container.top,
    endX: e.clientX - container.left,
    endY: e.clientY - container.top
  };
  isSelecting.value = true;
  console.log('开始新选择，坐标:', selection.value, '已清除之前的状态');
};

// 更新选择
const updateSelection = (e) => {
  if (!isSelecting.value || !selection.value.active) return;
  e.preventDefault();
  e.stopPropagation();
  const container = e.currentTarget.getBoundingClientRect();
  selection.value.endX = e.clientX - container.left;
  selection.value.endY = e.clientY - container.top;
};

// 结束选择
const endSelection = async (e) => {
  if (!isSelecting.value || !selection.value.active) {
    return;
  }
  e.preventDefault();
  e.stopPropagation();
  isSelecting.value = false;
  
  if (!pageImage.value || !selectedBook.value) {
    console.error('图片或课本未加载');
    selection.value.active = false;
    return;
  }
  
  // 防止重复 OCR 请求
  if (isOcrProcessing.value) {
    console.warn('OCR 正在处理中，忽略重复请求');
    return;
  }
  
  const container = e.currentTarget.getBoundingClientRect();
  const imgRect = pageImage.value.getBoundingClientRect();
  const relativeX = imgRect.left - container.left;
  const relativeY = imgRect.top - container.top;
  
  const x = Math.min(selection.value.startX, selection.value.endX) - relativeX;
  const y = Math.min(selection.value.startY, selection.value.endY) - relativeY;
  const width = Math.abs(selection.value.endX - selection.value.startX);
  const height = Math.abs(selection.value.endY - selection.value.startY);
  
  console.log('选择区域:', { x, y, width, height });
  
  if (width < 10 || height < 10) {
    console.log('选择区域太小，取消选择');
    selection.value.active = false;
    return;
  }
  
  // 计算相对于图片的坐标（考虑图片缩放）
  // 注意：图片可能还没有加载完成，需要检查 naturalWidth 和 naturalHeight
  if (pageImage.value.naturalWidth === 0 || pageImage.value.naturalHeight === 0) {
    console.error('图片尺寸无效，无法计算坐标');
    selection.value.active = false;
    return;
  }
  
  const scaleX = imgRect.width / pageImage.value.naturalWidth;
  const scaleY = imgRect.height / pageImage.value.naturalHeight;
  
  // 计算相对于原始图片的坐标
  const relativeX_scaled = x / scaleX;
  const relativeY_scaled = y / scaleY;
  const width_scaled = width / scaleX;
  const height_scaled = height / scaleY;
  
  // 保存当前选择区域的坐标（用于后续显示工具栏）
  const currentSelectionPos = {
    left: Math.min(selection.value.startX, selection.value.endX),
    top: Math.min(selection.value.startY, selection.value.endY),
    width: width,
    height: height
  };
  
  console.log('OCR参数:', {
    bookId: selectedBook.value.id,
    pageNum: currentPage.value,
    x: relativeX_scaled,
    y: relativeY_scaled,
    width: width_scaled,
    height: height_scaled
  });
  
  // 清除之前的结果 - 确保完全清除
  selectedText.value = '';
  finalSelectionPosition.value = { left: 0, top: 0, width: 0, height: 0 };
  
  // 等待一个 tick 确保 UI 更新
  await nextTick();
  
  try {
    isOcrProcessing.value = true;
    selectedText.value = '正在识别...';
    
    console.log('发送 OCR 请求，参数:', {
      bookId: selectedBook.value.id,
      pageNum: currentPage.value,
      x: relativeX_scaled,
      y: relativeY_scaled,
      width: width_scaled,
      height: height_scaled
    });
    
    const response = await ocrTextSelection(
      selectedBook.value.id,
      currentPage.value,
      relativeX_scaled,
      relativeY_scaled,
      width_scaled,
      height_scaled
    );
    
    console.log('OCR响应:', response);
    
    // 再次检查响应，确保是新的结果
    if (response && response.success && response.text) {
      const newText = response.text.trim();
      console.log('识别结果:', newText);
      selectedText.value = newText;
      // 保存最终选择位置，用于显示工具栏
      finalSelectionPosition.value = currentSelectionPos;
    } else {
      selectedText.value = response?.text || '未能识别文本，请重试';
    }
  } catch (error) {
    console.error('OCR 识别失败:', error);
    selectedText.value = `识别失败: ${error.message || '请重试'}`;
  } finally {
    isOcrProcessing.value = false;
    // 选择完成后，关闭选择框，但保留文本和位置用于显示工具栏
    selection.value.active = false;
  }
};

// 取消选择
const cancelSelection = () => {
  if (!isSelecting.value) return;
  isSelecting.value = false;
  selection.value.active = false;
};

// 清除选择
const clearSelection = () => {
  selection.value.active = false;
  selectedText.value = '';
  finalSelectionPosition.value = { left: 0, top: 0, width: 0, height: 0 };
};

// 发送到对话
const sendToConversation = async (e) => {
  // 阻止事件冒泡和默认行为
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  
  console.log('=== sendToConversation 被调用 ===');
  console.log('selectedText.value:', selectedText.value);
  console.log('showChatPanel.value (调用前):', showChatPanel.value);
  
  const textToSend = selectedText.value ? selectedText.value.trim() : '';
  
  if (!textToSend) {
    console.warn('selectedText 为空，无法发送到对话');
    alert('请先选择要发送的文本');
    return;
  }
  
  console.log('准备发送的文本:', textToSend);
  
  // 打开对话面板
  showChatPanel.value = true;
  console.log('showChatPanel.value (设置后):', showChatPanel.value);
  
  // 等待面板完全渲染
  await nextTick();
  await nextTick();
  
  // 设置输入框的值 - 使用多种方式确保更新
  chatInputMessage.value = textToSend;
  console.log('chatInputMessage.value 已设置:', chatInputMessage.value);
  
  // 如果 textarea ref 存在，也直接设置其值（双重保险）
  await nextTick(); // 再等待一个 tick 确保 ref 已更新
  if (chatTextarea.value) {
    chatTextarea.value.value = textToSend;
    // 触发 input 事件确保 v-model 更新
    chatTextarea.value.dispatchEvent(new Event('input', { bubbles: true }));
    console.log('textarea.value 已直接设置:', chatTextarea.value.value);
  } else {
    console.warn('chatTextarea.value 不存在，等待更长时间...');
    // 如果 ref 还不存在，再等待一下
    setTimeout(() => {
      if (chatTextarea.value) {
        chatTextarea.value.value = textToSend;
        chatTextarea.value.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('延迟设置 textarea.value:', chatTextarea.value.value);
      }
    }, 100);
  }
  
  console.log('已将文本填充到输入框:', chatInputMessage.value, 'textarea.value:', chatTextarea.value?.value);
  
  // 等待一下确保输入框已更新，然后自动发送
  setTimeout(() => {
    const finalValue = chatInputMessage.value || chatTextarea.value?.value || '';
    console.log('准备自动发送消息, 最终值:', finalValue);
    
    // 如果 v-model 没有更新，手动设置
    if (!chatInputMessage.value && finalValue) {
      chatInputMessage.value = finalValue;
    }
    
    // 检查输入框是否有值
    if (chatInputMessage.value && chatInputMessage.value.trim()) {
      console.log('调用 sendChatMessage，内容:', chatInputMessage.value);
      sendChatMessage();
    } else {
      console.warn('输入框值为空，无法发送。尝试直接使用 textToSend');
      // 如果还是为空，直接使用原始值发送
      if (textToSend) {
        chatInputMessage.value = textToSend;
        console.log('使用 textToSend 直接设置并发送:', textToSend);
        sendChatMessage();
      } else {
        console.error('所有尝试都失败，无法发送消息');
      }
    }
    
    // 自动清除选择框
    clearSelection();
  }, 500); // 增加延迟时间到 500ms
};

// 发送对话消息
const sendChatMessage = async () => {
  const content = chatInputMessage.value.trim();
  console.log('sendChatMessage 被调用, content:', content, 'isChatLoading:', isChatLoading.value);
  
  if (!content) {
    console.warn('消息内容为空，无法发送');
    return;
  }
  
  if (isChatLoading.value) {
    console.warn('正在加载中，忽略重复请求');
    return;
  }

  // 添加用户消息
  chatMessages.value.push({ role: 'user', content });
  const messageToSend = content; // 保存要发送的内容
  chatInputMessage.value = '';
  
  // 滚动到底部
  await nextTick();
  scrollChatToBottom();

  // 设置加载状态并创建可中止的请求
  isChatLoading.value = true;
  currentChatMessage.value = '';
  chatStreamController.value = new AbortController();

  try {
    console.log('开始调用 courseChatStream, message:', messageToSend, 'threadId:', chatThreadId.value);
    await courseChatStream(
      messageToSend,
      chatThreadId.value,
      async (chunk) => {
      console.log('收到 chunk:', chunk);
      if (chunk.status === 'init') {
        chatThreadId.value = (chunk.meta && chunk.meta.thread_id) ? chunk.meta.thread_id : chunk.thread_id;
      } else if (chunk.status === 'loading' && chunk.response !== undefined) {
        // 追加增量内容
        if (chunk.response) {
          currentChatMessage.value = (currentChatMessage.value || '') + chunk.response;
        }
        await nextTick();
        scrollChatToBottom();
      } else if (chunk.status === 'finished') {
        if (currentChatMessage.value) {
          chatMessages.value.push({ role: 'ai', content: currentChatMessage.value });
          currentChatMessage.value = '';
        }
        isChatLoading.value = false;
        scrollChatToBottom();
      } else if (chunk.status === 'error') {
        chatMessages.value.push({ role: 'ai', content: chunk.error_message || chunk.message || '抱歉，连接服务器失败，请检查网络或稍后再试。' });
        isChatLoading.value = false;
        scrollChatToBottom();
      }
    },
    { signal: chatStreamController.value.signal }
    );
  } catch (error) {
    if (error.name === 'AbortError') {
      if (currentChatMessage.value) {
        chatMessages.value.push({ role: 'ai', content: currentChatMessage.value });
        currentChatMessage.value = '';
      }
    } else {
      console.error('发送消息失败:', error);
      chatMessages.value.push({ role: 'ai', content: '抱歉，连接服务器失败，请检查网络或稍后再试。' });
    }
    isChatLoading.value = false;
    chatStreamController.value = null;
    await nextTick();
    scrollChatToBottom();
  }
};

const stopChatStream = () => {
  if (chatStreamController.value) {
    chatStreamController.value.abort();
  }
};

// 滚动对话到底部
const scrollChatToBottom = () => {
  if (chatMessagesBox.value) {
    chatMessagesBox.value.scrollTop = chatMessagesBox.value.scrollHeight;
  }
};

// 监听消息变化，自动滚动
watch(() => chatMessages.value.length, () => {
  nextTick(() => {
    scrollChatToBottom();
  });
});

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
};

onMounted(() => {
  loadBooks();
});
</script>

<style scoped>
/* 使用与项目一致的颜色变量 */
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

.reading-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  background-color: var(--gray-50);
  min-height: 100vh;
  color: var(--dark-text);
}

/* 顶部导航样式 */
.reading-header {
  background-color: var(--white);
  border-bottom: 1px solid var(--gray-200);
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
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
}

.reading-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.reading-nav-link {
  color: var(--gray-500);
  text-decoration: none;
  transition: color 0.3s ease;
  font-size: 16px;
}

.reading-nav-link:hover {
  color: var(--primary-color);
}

.reading-nav-link.active {
  color: var(--primary-color);
  font-weight: 500;
}

/* 主要内容区样式 */
.reading-main {
  width: 100%;
  max-width: 1000px;
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
  color: var(--primary-color);
  margin-bottom: 16px;
}

.reading-subtitle {
  color: var(--gray-600);
  max-width: 600px;
  margin: 0 auto;
}

.reading-list-section {
  margin-bottom: 40px;
}

.reading-list-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 24px;
}

.reading-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.reading-card {
  background-color: var(--white);
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-light);
  transition: all 0.3s ease;
  cursor: pointer;
}

.reading-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-4px);
}

.reading-card-header {
  margin-bottom: 16px;
}

.reading-card-tags {
  display: flex;
  gap: 12px;
}

.reading-card-tag {
  background-color: var(--light-bg);
  color: var(--primary-color);
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 12px;
}

.reading-card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-color);
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
  color: var(--gray-500);
  font-size: 14px;
}

.reading-card-action {
  color: var(--secondary-color);
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
  text-align: center;
  padding: 40px;
  color: var(--gray-500);
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
  background-color: var(--white);
  border-radius: 8px;
  box-shadow: var(--shadow-light);
}

.reading-back-btn {
  background-color: var(--gray-200);
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--dark-text);
  font-size: 14px;
  transition: background-color 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.reading-back-btn:hover {
  background-color: var(--gray-500);
  color: var(--white);
}

.reading-reader-title {
  flex: 1;
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0 16px;
}

.reading-page-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-nav-btn {
  background-color: var(--primary-color);
  color: var(--white);
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
  background-color: var(--gray-200);
  color: var(--gray-500);
}

.chat-toggle-btn {
  background-color: var(--secondary-color);
}

.chat-toggle-btn:hover:not(:disabled) {
  background-color: #e07300;
}

.chat-toggle-btn.active {
  background-color: #e07300;
}

.reading-page-info {
  font-size: 14px;
  color: var(--gray-600);
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
  border-color: var(--primary-color);
}

.page-jump-input::-webkit-inner-spin-button,
.page-jump-input::-webkit-outer-spin-button {
  opacity: 1;
}

.page-jump-btn {
  background-color: var(--primary-color);
  color: var(--white);
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
  background-color: var(--gray-200);
  color: var(--gray-500);
}

.reading-reader-wrapper {
  display: flex;
  gap: 0;
  align-items: flex-start;
  width: 100%;
}

.reading-reader-wrapper.with-chat .reading-reader-content {
  flex: 1;
  min-width: 400px;
}

.reading-reader-wrapper.with-chat .reading-chat-panel {
  flex: 0 0 400px;
  margin-left: auto;
}

.reading-reader-content {
  background-color: var(--white);
  border-radius: 8px;
  padding: 24px;
  box-shadow: var(--shadow-light);
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

.reading-page-img {
  max-width: 100%;
  height: auto;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.reading-selection-box {
  position: absolute;
  border: 2px dashed var(--secondary-color);
  background-color: rgba(255, 125, 0, 0.1);
  pointer-events: none;
  z-index: 10;
}

.reading-selection-bar {
  background-color: var(--white);
  padding: 12px 16px;
  border-radius: 8px;
  position: absolute;
  z-index: 1000;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--gray-200);
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
  color: var(--dark-text);
  line-height: 1.6;
}

.reading-selection-actions {
  display: flex;
  gap: 12px;
}

.reading-action-btn {
  background-color: var(--primary-color);
  color: var(--white);
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

.reading-action-btn:last-child {
  background-color: var(--gray-500);
}

.reading-action-btn:last-child:hover {
  background-color: var(--gray-600);
}

/* 对话面板样式 */
.reading-chat-panel {
  width: 400px;
  background-color: var(--white);
  border-radius: 8px;
  box-shadow: var(--shadow-light);
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
  min-height: 600px;
  position: sticky;
  top: 24px;
}

.reading-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--gray-200);
}

.reading-chat-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0;
}

.reading-chat-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--gray-500);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.3s ease;
}

.reading-chat-close:hover {
  color: var(--primary-color);
}

.reading-chat-messages {
  flex: 1;
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
  background-color: var(--primary-color);
  color: var(--white);
}

.reading-chat-avatar.user {
  background-color: var(--secondary-color);
  color: var(--white);
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
  background-color: var(--light-bg);
  color: var(--dark-text);
}

.reading-chat-content.user {
  background-color: var(--primary-color);
  color: var(--white);
}

.reading-chat-content.loading {
  background-color: var(--light-bg);
}

.reading-chat-text {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
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
  0%, 60%, 100% {
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
  border-top: 1px solid var(--gray-200);
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background-color: var(--white);
}

.reading-chat-textarea {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--gray-300);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  min-height: 44px;
  max-height: 200px;
  line-height: 1.5;
  overflow-y: auto;
}

.reading-chat-textarea:focus {
  outline: none;
  border-color: var(--primary-color);
}

.reading-chat-send-btn {
  background-color: var(--primary-color);
  color: var(--white);
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.3s ease;
  white-space: nowrap;
}

.reading-chat-send-btn:hover:not(:disabled) {
  background-color: #153e68;
}

.reading-chat-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reading-chat-stop-btn,
.reading-chat-stop-btn-inline {
  background-color: var(--gray-200);
  color: var(--gray-600);
  border: 1px solid var(--gray-200);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  margin-top: 8px;
}

.reading-chat-stop-btn:hover,
.reading-chat-stop-btn-inline:hover {
  background-color: #d1d5db;
  color: var(--dark-text);
}

.reading-chat-stop-btn-inline {
  margin-top: 0;
  padding: 12px 24px;
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
  
  .reading-chat-panel {
    width: 100%;
    height: 500px;
    position: relative;
    top: 0;
  }
}
</style>
