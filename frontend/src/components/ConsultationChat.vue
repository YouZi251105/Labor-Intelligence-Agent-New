<template>
  <div class="consult-chat">
    <div ref="listEl" class="consult-chat__list">
      <article
        v-for="message in messages"
        :key="message.id"
        class="chat-message"
        :class="
          message.sender_role === senderRole ? 'chat-message--user' : 'chat-message--assistant'
        "
      >
        <span class="chat-message__role">{{ senderLabels[message.sender_role] }}</span>
        <SafeMarkdown v-if="message.content" :content="message.content" />
        <a
          v-if="message.attachment_name"
          class="chat-attachment"
          href="#"
          @click.prevent="downloadAttachment(message)"
        >
          <Paperclip :size="14" />
          <span class="chat-attachment__name">{{ message.attachment_name }}</span>
          <small v-if="message.attachment_size" class="chat-attachment__size">
            {{ formatSize(message.attachment_size) }}
          </small>
          <Download :size="14" />
        </a>
        <small class="consult-chat__time">
          {{ new Date(message.created_at).toLocaleString('zh-CN') }}
        </small>
      </article>
      <p v-if="loading && !messages.length" class="muted-text">正在加载对话记录...</p>
      <p v-if="!loading && !messages.length" class="muted-text">
        暂无对话内容，发送第一条消息开始沟通。
      </p>
    </div>
    <p v-if="error" class="inline-error">{{ error }}</p>
    <form v-if="session.status === 'active'" class="chat-compose-inline" @submit.prevent="send">
      <div v-if="attachment" class="chat-attachment-preview">
        <Paperclip :size="14" />
        <span class="chat-attachment__name">{{ attachment.name }}</span>
        <small class="chat-attachment__size">{{ formatSize(attachment.size) }}</small>
        <button class="chat-attachment-preview__remove" type="button" @click="clearAttachment">
          <X :size="14" />
        </button>
      </div>
      <textarea
        v-model="draft"
        rows="3"
        placeholder="输入消息，可附带 PDF、Word、图片等材料（10MB 以内），双方记录都会留存。"
      />
      <div class="chat-compose-inline__actions">
        <button
          class="secondary-action secondary-action--icon"
          type="button"
          title="添加附件"
          @click="fileInput?.click()"
        >
          <Paperclip :size="16" />
        </button>
        <button
          class="primary-action primary-action--compact"
          type="submit"
          :disabled="sending || (!draft.trim() && !attachment)"
        >
          {{ sending ? '发送中...' : '发送' }}
        </button>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept=".jpg,.jpeg,.png,.webp,.pdf,.txt,.doc,.docx"
        hidden
        @change="onFileSelected"
      />
    </form>
    <p v-else class="consult-chat__closed">
      <Lock :size="14" />
      会话已结束，历史消息双方留存可查，但不能继续发送。
    </p>
    <div v-if="session.status === 'active'" class="consult-chat__footer">
      <button class="secondary-action" type="button" :disabled="closing || sending" @click="close">
        {{ closing ? '结束中...' : '结束会话' }}
      </button>
      <small class="muted-text">结束后预约标记为已完成，历史记录保留。</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Download, Lock, Paperclip, X } from '@lucide/vue'
import { nextTick, onMounted, ref, watch } from 'vue'

import { apiFile, apiRequest } from '../api/http'
import SafeMarkdown from './SafeMarkdown.vue'
import type { ConsultationMessageItem, ConsultationSessionItem } from '../types/api'

const props = defineProps<{
  session: ConsultationSessionItem
  senderRole: 'user' | 'lawyer'
}>()

const emit = defineEmits<{
  closed: [session: ConsultationSessionItem]
}>()

const messages = ref<ConsultationMessageItem[]>([])
const draft = ref('')
const attachment = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const loading = ref(false)
const sending = ref(false)
const closing = ref(false)
const error = ref('')
const listEl = ref<HTMLElement | null>(null)

const senderLabels: Record<string, string> = {
  user: '劳动者',
  lawyer: '律师',
}

function formatSize(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  attachment.value = input.files?.[0] ?? null
  input.value = ''
}

function clearAttachment() {
  attachment.value = null
}

async function scrollToBottom() {
  await nextTick()
  listEl.value?.scrollTo({ top: listEl.value.scrollHeight, behavior: 'smooth' })
}

async function loadMessages() {
  loading.value = true
  error.value = ''
  try {
    messages.value = await apiRequest<ConsultationMessageItem[]>(
      `/lawyer-service/sessions/${props.session.id}/messages`,
    )
    await scrollToBottom()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '对话记录加载失败'
  } finally {
    loading.value = false
  }
}

async function send() {
  const content = draft.value.trim()
  if (!content && !attachment.value) return
  sending.value = true
  error.value = ''
  try {
    let message: ConsultationMessageItem
    if (attachment.value) {
      const form = new FormData()
      if (content) form.append('content', content)
      form.append('file', attachment.value)
      message = await apiRequest<ConsultationMessageItem>(
        `/lawyer-service/sessions/${props.session.id}/messages/file`,
        { method: 'POST', body: form },
      )
    } else {
      message = await apiRequest<ConsultationMessageItem>(
        `/lawyer-service/sessions/${props.session.id}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content }),
        },
      )
    }
    messages.value.push(message)
    draft.value = ''
    clearAttachment()
    await scrollToBottom()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发送失败'
  } finally {
    sending.value = false
  }
}

async function downloadAttachment(message: ConsultationMessageItem) {
  if (!message.attachment_name) return
  error.value = ''
  try {
    const blob = await apiFile(
      `/lawyer-service/sessions/${message.session_id}/messages/${message.id}/attachment`,
      { accept: '*/*' },
    )
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = message.attachment_name
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '附件下载失败'
  }
}

async function close() {
  closing.value = true
  error.value = ''
  try {
    const closed = await apiRequest<ConsultationSessionItem>(
      `/lawyer-service/sessions/${props.session.id}/close`,
      { method: 'POST' },
    )
    emit('closed', closed)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '会话关闭失败'
  } finally {
    closing.value = false
  }
}

watch(
  () => props.session.id,
  () => {
    void loadMessages()
  },
)
onMounted(() => {
  void loadMessages()
})

defineExpose({ reload: loadMessages })
</script>
