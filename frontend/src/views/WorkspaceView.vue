<template>
  <div class="workspace">
    <section class="conversation-panel">
      <header class="workspace-header">
        <div>
          <span class="eyebrow">AI 法律咨询</span>
          <h1>{{ activeCase ? activeCase.title : '先说说你遇到了什么问题' }}</h1>
          <p>先描述你的情况，系统会一步步帮你梳理。</p>
        </div>
        <div class="connection" :class="`connection--${workspace.connection}`">
          <span class="connection__dot" />
          {{ connectionLabel }}
        </div>
      </header>

      <div v-if="activeCase" class="case-context-bar">
        <div>
          <span>当前案件</span>
          <strong>{{ dictionary.disputeLabels[activeCase.dispute_type] || activeCase.dispute_type }}</strong>
        </div>
        <button class="text-link" type="button" @click="router.push(`/cases/${activeCase.id}`)">
          打开案件工作台
          <ArrowRight :size="16" />
        </button>
      </div>

      <div class="chat-message-list" :class="{ 'chat-message-list--empty': messages.length === 0 }">
        <div v-if="messages.length === 0" class="conversation-stage">
          <div class="assistant-mark">
            <Scale :size="26" :stroke-width="1.7" />
          </div>
          <div class="assistant-message">
            <span class="assistant-message__label">劳务通 · 智能咨询</span>
            <h2>{{ auth.user?.display_name || '你好' }}，可以从最困扰你的事情说起</h2>
            <p>
              例如欠薪多久了、有没有签合同、老板是否还在联系你。信息不完整也没关系，我们会一步步补充。
            </p>
          </div>
        </div>

        <article
          v-for="message in messages"
          :key="message.id"
          class="chat-message"
          :class="`chat-message--${message.role}`"
        >
          <span class="chat-message__role">{{ message.role === 'user' ? '你' : '劳务通' }}</span>
          <SafeMarkdown :content="message.content" />
        </article>

        <div v-if="sending" class="chat-message chat-message--assistant">
          <span class="chat-message__role">劳务通</span>
          <p class="thinking-line"><span class="spinner-dot" /> 正在整理问题和上下文...</p>
        </div>
      </div>

      <div v-if="messages.length === 0" class="quick-topics" aria-label="常见问题">
        <button v-for="topic in topics" :key="topic" class="topic" @click="input = topic">
          <component :is="topicIcons[topic]" :size="17" />
          {{ topic }}
        </button>
      </div>

      <p v-if="error" class="inline-error">{{ error }}</p>

      <div class="composer">
        <ElInput
          v-model="input"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          resize="none"
          placeholder="描述情况，例如：我在工地干了三个月，没有签合同，老板一直不发工资……"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <div class="composer__footer">
          <span>
            <ShieldCheck :size="15" />
            AI 建议仅供参考，关键判断支持人工复核
          </span>
          <ElButton type="primary" :loading="sending" :disabled="!input.trim()" @click="sendMessage">
            发送问题
            <ArrowUpRight :size="17" />
          </ElButton>
        </div>
      </div>
    </section>

    <aside class="context-panel">
      <section class="context-card">
        <div class="context-card__heading">
          <div>
            <span class="eyebrow">当前阶段</span>
            <h2>{{ activeCase ? stageLabel(activeCase.stage) : '尚未创建案件' }}</h2>
          </div>
          <Clock3 :size="20" />
        </div>
        <p v-if="activeCase" class="next-step">
          {{ suggestedNextStep || '继续补充事实和现有材料。' }}
        </p>
        <p v-else>发送首条咨询后会自动创建案件。</p>
        <ol v-if="activeCase" class="stage-list">
          <li
            v-for="(stage, index) in dictionary.stages"
            :key="stage.value"
            :class="{ active: stage.value === activeCase.stage }"
          >
            <span>{{ index + 1 }}</span>
            <div>
              <strong>{{ stage.label }}</strong>
              <small>{{ stage.description }}</small>
            </div>
          </li>
        </ol>
        <div v-if="evidenceGaps.length" class="structured-hints">
          <strong>建议补充材料</strong>
          <div class="tag-row">
            <span v-for="item in evidenceGaps" :key="item" class="status-tag status-tag--warning">{{ item }}</span>
          </div>
        </div>
        <RouterLink v-if="activeCase" :to="`/cases/${activeCase.id}`" class="text-link">
          打开案件工作台
          <ArrowRight :size="16" />
        </RouterLink>
      </section>

      <section class="context-card context-card--soft">
        <details class="history-details">
          <summary>我的历史问题</summary>
          <div class="history-list">
            <button
              v-for="item in historyCases"
              :key="item.case_id"
              type="button"
              @click="router.push(`/cases/${item.case_id}`)"
            >
              <strong>{{ item.title }}</strong>
              <span>{{ dictionary.disputeLabels[item.dispute_type] || item.dispute_type }}</span>
            </button>
            <p v-if="!historyCases.length" class="muted-text">暂无历史案件。</p>
          </div>
        </details>
        <details class="history-details">
          <summary>大家在问</summary>
          <div class="topic-cloud">
            <span v-for="topic in topicSummary.topics" :key="topic.dispute_type">
              {{ topic.label }} · {{ topic.count }}
            </span>
          </div>
          <small>仅展示匿名聚合类型，不公开任何用户原始咨询。</small>
        </details>
      </section>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ElButton, ElInput } from 'element-plus'
import {
  ArrowRight,
  ArrowUpRight,
  Banknote,
  Clock3,
  FileWarning,
  Scale,
  ShieldCheck,
  UserRoundX,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { apiRequest } from '../api/http'
import SafeMarkdown from '../components/SafeMarkdown.vue'
import { useAuthStore } from '../stores/auth'
import { useDictionaryStore } from '../stores/dictionary'
import { useWorkspaceStore } from '../stores/workspace'
import type {
  CaseItem,
  ConsultationResponse,
  HistoryCaseSummary,
  MessageItem,
  TopicsResponse,
} from '../types/api'

const router = useRouter()
const auth = useAuthStore()
const workspace = useWorkspaceStore()
const activeCase = ref<CaseItem | null>(null)
const messages = ref<MessageItem[]>([])
const input = ref('')
const sending = ref(false)
const error = ref('')
const suggestedNextStep = ref('')
const evidenceGaps = ref<string[]>([])
const historyCases = ref<HistoryCaseSummary[]>([])
const topicSummary = ref<TopicsResponse>({ topics: [], total: 0 })

const topics = ['拖欠工资', '突然被辞退', '没有签合同', '工伤或受伤'] as const
const topicIcons = {
  拖欠工资: Banknote,
  突然被辞退: UserRoundX,
  没有签合同: FileWarning,
  工伤或受伤: ShieldCheck,
}
const dictionary = useDictionaryStore()

const connectionLabel = computed(() => {
  if (workspace.connection === 'online') return '服务已连接'
  if (workspace.connection === 'offline') return '服务未连接'
  return '正在检查服务'
})

function stageLabel(stage: string) {
  return dictionary.stageLabels[stage] ?? '识别问题'
}

async function loadInitialCase() {
  const [cases, history, topics] = await Promise.all([
    apiRequest<CaseItem[]>('/cases'),
    apiRequest<{ cases: HistoryCaseSummary[] }>('/analytics/history'),
    apiRequest<TopicsResponse>('/analytics/topics'),
  ])
  historyCases.value = history.cases
  topicSummary.value = topics
  if (!cases.length) return
  activeCase.value = cases[0]
  messages.value = await apiRequest<MessageItem[]>(`/cases/${cases[0].id}/messages`)
  if (messages.value.length) {
    const metadata = messages.value.at(-1)?.metadata_json ?? {}
    suggestedNextStep.value = String(metadata.suggested_next_step ?? '')
    const structured = metadata.structured as
      | { evidence_gaps?: string[] }
      | undefined
    evidenceGaps.value = structured?.evidence_gaps ?? []
  }
}

async function sendMessage() {
  const content = input.value.trim()
  if (!content || sending.value) return
  sending.value = true
  error.value = ''

  try {
    if (!activeCase.value) {
      activeCase.value = await apiRequest<CaseItem>('/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: content.slice(0, 30),
          facts: content,
          dispute_type: 'labor_other',
        }),
      })
    }

    const response = await apiRequest<ConsultationResponse>(
      `/cases/${activeCase.value.id}/consultations`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      },
    )
    activeCase.value = response.case
    messages.value.push(response.user_message, response.assistant_message)
    suggestedNextStep.value = response.suggested_next_step
    evidenceGaps.value = response.structured.evidence_gaps
    input.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发送失败'
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  void workspace.checkHealth()
  await dictionary.load()
  try {
    await loadInitialCase()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件加载失败'
  }
})
</script>
