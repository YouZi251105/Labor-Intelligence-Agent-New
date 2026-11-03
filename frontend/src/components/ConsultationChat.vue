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
        <SafeMarkdown :content="message.content" />
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
      <textarea v-model="draft" rows="3" placeholder="输入消息，双方记录都会留存。" />
      <button
        class="primary-action primary-action--compact"
        type="submit"
        :disabled="sending || !draft.trim()"
      >
        {{ sending ? '发送中...' : '发送' }}
      </button>
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
import { Lock } from '@lucide/vue'
import { nextTick, onMounted, ref, watch } from 'vue'

import { apiRequest } from '../api/http'
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
const loading = ref(false)
const sending = ref(false)
const closing = ref(false)
const error = ref('')
const listEl = ref<HTMLElement | null>(null)

const senderLabels: Record<string, string> = {
  user: '劳动者',
  lawyer: '律师',
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
  if (!content) return
  sending.value = true
  error.value = ''
  try {
    const message = await apiRequest<ConsultationMessageItem>(
      `/lawyer-service/sessions/${props.session.id}/messages`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      },
    )
    messages.value.push(message)
    draft.value = ''
    await scrollToBottom()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发送失败'
  } finally {
    sending.value = false
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
