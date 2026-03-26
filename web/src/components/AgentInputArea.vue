<template>
  <MessageInputComponent
    ref="inputRef"
    :model-value="modelValue"
    @update:modelValue="updateValue"
    :is-loading="isLoading"
    :disabled="disabled"
    :send-button-disabled="sendButtonDisabled"
    :placeholder="placeholder"
    :force-multi-line="hasStateContent"
    :mention="mention"
    :show-stop-button="false"
    @send="handleSend"
    @keydown="handleKeyDown"
  >
    <template #top>
      <ImagePreviewComponent
        v-if="currentImage"
        :image-data="currentImage"
        @remove="handleImageRemoved"
        class="image-preview-wrapper"
      />
    </template>
    <template #options-inline>
      <a-tooltip title="选择图片" placement="top">
        <a-button
          type="text"
          class="input-inline-image-btn"
          aria-label="上传图片"
          :disabled="disabled"
          @click.stop="triggerInlineImagePick"
        >
          <template #icon>
            <PictureOutlined />
          </template>
        </a-button>
      </a-tooltip>
    </template>
    <template #options-left>
      <AttachmentOptionsComponent
        v-if="supportsFileUpload"
        :disabled="disabled"
        @upload="handleAttachmentUpload"
        @upload-image="handleImageUpload"
        @upload-image-success="handleImageUploadSuccess"
      />
    </template>
    <template #actions-left>
      <div class="input-actions-left">
        <!-- State Toggle Button -->
        <div
          v-if="hasStateContent"
          class="state-toggle-btn"
          :class="{ active: isPanelOpen }"
          @click="$emit('toggle-panel')"
          title="查看工作状态"
        >
          <FolderCode :size="14" />
          <span>状态</span>
        </div>
      </div>
    </template>
  </MessageInputComponent>
</template>

<script setup>
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import MessageInputComponent from '@/components/MessageInputComponent.vue'
import ImagePreviewComponent from '@/components/ImagePreviewComponent.vue'
import AttachmentOptionsComponent from '@/components/AttachmentOptionsComponent.vue'
import { threadApi } from '@/apis'
import { AgentValidator } from '@/utils/agentValidator'
import { handleChatError, handleValidationError } from '@/utils/errorHandler'
import { FolderCode } from 'lucide-vue-next'
import { PictureOutlined } from '@ant-design/icons-vue'
import { multimodalApi } from '@/apis/agent_api'

const props = defineProps({
  modelValue: { type: String, default: '' },
  isLoading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  sendButtonDisabled: { type: Boolean, default: false },
  placeholder: { type: String, default: '输入问题...' },
  supportsFileUpload: { type: Boolean, default: false },
  agentId: { type: String, default: '' },
  threadId: { type: String, default: null },
  ensureThread: { type: Function, required: true },
  hasStateContent: { type: Boolean, default: false },
  isPanelOpen: { type: Boolean, default: false },
  mention: { type: Object, default: () => null }
})

const emit = defineEmits([
  'update:modelValue',
  'send',
  'keydown',
  'attachment-changed',
  'toggle-panel'
])

const inputRef = ref(null)
const currentImage = ref(null)

const updateValue = (val) => {
  emit('update:modelValue', val)
}

const handleAttachmentUpload = async (files) => {
  if (!files?.length) return
  if (!AgentValidator.validateAgentIdWithError(props.agentId, '上传附件', handleValidationError))
    return

  const preferredTitle = files[0]?.name || '新的对话'
  let threadId = props.threadId

  if (!threadId) {
    try {
      threadId = await props.ensureThread(preferredTitle)
    } catch (e) {
      return
    }
  }

  if (!threadId) {
    message.error('创建对话失败，无法上传附件')
    return
  }

  try {
    for (const file of files) {
      await threadApi.uploadThreadAttachment(threadId, file)
      message.success(`${file.name} 上传成功`)
    }
    emit('attachment-changed', threadId)
  } catch (error) {
    handleChatError(error, 'upload')
  }
}

const handleImageUpload = (imageData) => {
  if (imageData && imageData.success) {
    currentImage.value = imageData
  }
}

/** 输入框旁常驻图片按钮，与「+」菜单内上传共用同一套处理 */
const triggerInlineImagePick = () => {
  if (props.disabled) return
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.multiple = false
  input.style.display = 'none'
  input.onchange = async (event) => {
    const file = event.target.files?.[0]
    if (file) await processPickedImageFile(file)
    document.body.removeChild(input)
  }
  document.body.appendChild(input)
  input.click()
}

const processPickedImageFile = async (file) => {
  try {
    if (file.size > 10 * 1024 * 1024) {
      message.error('图片文件过大，请选择小于10MB的图片')
      return
    }
    if (!file.type.startsWith('image/')) {
      message.error('请选择有效的图片文件')
      return
    }
    message.loading({ content: '正在处理图片...', key: 'image-upload' })
    const result = await multimodalApi.uploadImage(file)
    if (result.success) {
      message.success({ content: '图片处理成功', key: 'image-upload', duration: 2 })
      handleImageUpload({
        success: true,
        imageContent: result.image_content,
        thumbnailContent: result.thumbnail_content,
        width: result.width,
        height: result.height,
        format: result.format,
        mimeType: result.mime_type || file.type,
        sizeBytes: result.size_bytes,
        originalName: file.name
      })
      handleImageUploadSuccess()
    } else {
      message.error({ content: `图片处理失败: ${result.error}`, key: 'image-upload' })
    }
  } catch (error) {
    console.error('图片上传失败:', error)
    message.error({
      content: `图片上传失败: ${error.message || '未知错误'}`,
      key: 'image-upload'
    })
  }
}

const handleImageUploadSuccess = () => {
  if (inputRef.value) {
    inputRef.value.closeOptions()
  }
}

const handleImageRemoved = () => {
  currentImage.value = null
}

const handleSend = () => {
  emit('send', { image: currentImage.value })
  currentImage.value = null
}

const handleKeyDown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  } else {
    emit('keydown', e)
  }
}

defineExpose({
  focus: () => inputRef.value?.focus(),
  closeOptions: () => inputRef.value?.closeOptions()
})
</script>

<style lang="less" scoped>
.input-actions-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-inline-image-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-600);
  border: 1px solid transparent;
  background-color: transparent;

  &:hover:not(:disabled) {
    color: var(--main-color);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .anticon {
    font-size: 16px;
  }
}

.state-toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 8px;
  height: 28px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--gray-600);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  background: transparent;
  border: none;

  &:hover {
    color: var(--main-color);
    background: var(--gray-100);
  }

  &.active {
    color: var(--main-color);
    background: var(--main-50);
    font-weight: 500;
  }

  &:active {
    transform: scale(0.95);
  }

  &.disabled {
    opacity: 0.5;
    cursor: not-allowed;
    pointer-events: none;
  }

  span {
    line-height: 1;
  }
}
</style>
