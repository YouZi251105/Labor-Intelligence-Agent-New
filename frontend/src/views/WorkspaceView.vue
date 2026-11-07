<template>
  <div class="workspace">
    <section class="conversation-panel">
      <header class="workspace-header">
        <div>
          <span class="eyebrow">AI 法律咨询</span>
          <div class="workspace-header__title-row">
            <select
              class="case-selector"
              :value="activeCase?.id ?? ''"
              @change="onCaseSelect"
              aria-label="选择案件"
            >
              <option value="" disabled>选择已有案件…</option>
              <option
                v-for="item in allCases"
                :key="item.id"
                :value="item.id"
              >
                {{ item.title }}（{{
                  dictionary.disputeLabels[item.dispute_type] || item.dispute_type
                }}）
              </option>
            </select>
            <h1
              v-if="activeCase"
              class="workspace-header__case-title"
            >
              {{ activeCase.title }}
            </h1>
            <h1 v-else>先说说你遇到了什么问题</h1>
          </div>
          <p v-if="activeCase">
            {{ dictionary.disputeLabels[activeCase.dispute_type] || activeCase.dispute_type }} · {{
              stageLabel(activeCase.stage)
            }}
          </p>
          <p v-else>
            先描述你的情况，系统会一步步帮你梳理。发送首条消息后会自动创建案件。
          </p>
        </div>
        <div class="workspace-header__actions">
          <button
            class="primary-action primary-action--compact"
            type="button"
            @click="startNewConversation"
          >
            <Plus :size="16" />
            新开一轮对话
          </button>
          <RouterLink
            v-if="auth.user?.role === 'user'"
            class="text-link"
            to="/cases"
          >
            我的案件
            <ArrowRight :size="16" />
          </RouterLink>
          <button
            v-if="auth.user?.role === 'user'"
            class="secondary-action secondary-action--compact"
            type="button"
            :disabled="!activeCase"
            @click="openLawyerIntervention"
          >
            <ShieldCheck :size="16" />
            申请律师介入
          </button>
          <div class="connection" :class="`connection--${workspace.connection}`">
            <span class="connection__dot" />
            {{ connectionLabel }}
          </div>
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

      <div
        v-if="auth.user?.role === 'user' && interventionRecommendation?.recommended"
        class="intervention-recommendation"
        :class="`intervention-recommendation--${interventionRecommendation.level}`"
      >
        <ShieldAlert :size="19" />
        <div>
          <strong>建议律师介入</strong>
          <p>{{ interventionRecommendation.reasons.join('；') }}</p>
        </div>
        <button
          class="primary-action primary-action--compact"
          type="button"
          @click="
            interventionRecommendation.action === 'filing_review'
              ? openFilingReview()
              : openLawyerIntervention()
          "
        >
          {{ interventionRecommendation.action === 'filing_review' ? '申请复核' : '预约律师' }}
        </button>
      </div>

      <div
        ref="chatMessageList"
        class="chat-message-list"
        :class="{ 'chat-message-list--empty': messages.length === 0 }"
        @scroll="onChatScroll"
      >
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
          <ReferenceMaterials
            v-if="message.role === 'assistant'"
            :references="referencesFromMessage(message)"
          />
          <div
            v-if="
              !sending &&
              message.role === 'assistant' &&
              activeFollowUpOptionsForMessage(message).length
            "
            class="follow-up-options"
            :data-message-id="message.id"
          >
            <span class="follow-up-options__label">猜你想问</span>
            <button
              v-for="option in activeFollowUpOptionsForMessage(message)"
              :key="option.id"
              type="button"
              class="follow-up-option"
              :data-kind="option.kind"
              :disabled="sending"
              @click="handleFollowUp(message, option)"
            >
              {{ option.label }}
              <ArrowUpRight :size="14" />
            </button>
          </div>
        </article>

        <div
          v-if="streamingReply"
          class="chat-message chat-message--assistant streaming-message"
          data-testid="streaming-assistant"
          aria-live="polite"
        >
          <span class="chat-message__role">劳务通</span>
          <SafeMarkdown
            v-if="streamingReply.content"
            :content="streamingReply.content"
            streaming
          />
          <p class="thinking-line streaming-status">
            <span class="spinner-dot" />
            {{ streamingReply.status }}
          </p>
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
          :autosize="{ minRows: 1, maxRows: 4 }"
          resize="none"
          placeholder="描述情况，例如：我在工地干了三个月，没有签合同，老板一直不发工资……"
          @keydown.enter.exact.prevent="sendMessage()"
        />
        <div class="composer__footer">
          <span>
            <ShieldCheck :size="15" />
            AI 建议仅供参考，关键判断支持人工复核
          </span>
          <ElButton type="primary" :loading="sending" :disabled="!input.trim()" @click="sendMessage()">
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
  Plus,
  Scale,
  ShieldAlert,
  ShieldCheck,
  UserRoundX,
} from '@lucide/vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { apiRequest, apiStream } from '../api/http'
import ReferenceMaterials from '../components/ReferenceMaterials.vue'
import SafeMarkdown from '../components/SafeMarkdown.vue'
import { useAuthStore } from '../stores/auth'
import { useDictionaryStore } from '../stores/dictionary'
import { useWorkspaceStore } from '../stores/workspace'
import type {
  CaseItem,
  ConsultationResponse,
  FollowUpOption,
  HistoryCaseSummary,
  InterventionRecommendation,
  MessageItem,
  ReferenceItem,
  TopicsResponse,
} from '../types/api'
import {
  activeFollowUpOptions,
  latestActionableAssistantMessageId,
} from '../utils/followUps'
import { referencesFromMessage } from '../utils/references'

const router = useRouter()
const auth = useAuthStore()
const workspace = useWorkspaceStore()
const allCases = ref<CaseItem[]>([])
const activeCase = ref<CaseItem | null>(null)
const messages = ref<MessageItem[]>([])
const chatMessageList = ref<HTMLElement | null>(null)
const input = ref('')
const sending = ref(false)
const streamingReply = ref<{
  status: string
  content: string
  references: ReferenceItem[]
} | null>(null)
const error = ref('')
const suggestedNextStep = ref('')
const evidenceGaps = ref<string[]>([])
const interventionRecommendation = ref<InterventionRecommendation | null>(null)
const historyCases = ref<HistoryCaseSummary[]>([])
const topicSummary = ref<TopicsResponse>({ topics: [], total: 0 })
const consumedFollowUpKeys = ref<string[]>([])
let streamingBuffer = ''
let streamFrame = 0
let keepScrolledToBottom = true
let persistTimer = 0

const WORKSPACE_STATE_KEY = 'labor-workspace-view-state'

interface WorkspaceViewState {
  caseId: number | null
  scrollTop: number
  atBottom: boolean
}

function readSavedViewState(): WorkspaceViewState | null {
  try {
    const raw = sessionStorage.getItem(WORKSPACE_STATE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<WorkspaceViewState>
    return {
      caseId: typeof parsed.caseId === 'number' ? parsed.caseId : null,
      scrollTop: typeof parsed.scrollTop === 'number' ? parsed.scrollTop : 0,
      atBottom: parsed.atBottom === true,
    }
  } catch {
    return null
  }
}

function saveViewState() {
  const element = chatMessageList.value
  const state: WorkspaceViewState = {
    caseId: activeCase.value?.id ?? null,
    scrollTop: element?.scrollTop ?? 0,
    atBottom: keepScrolledToBottom,
  }
  try {
    sessionStorage.setItem(WORKSPACE_STATE_KEY, JSON.stringify(state))
  } catch {
    // 隐私模式下存储不可用时忽略
  }
}

function scheduleSaveViewState() {
  if (persistTimer) window.clearTimeout(persistTimer)
  persistTimer = window.setTimeout(saveViewState, 200)
}

async function restoreChatScroll() {
  const saved = readSavedViewState()
  const sameCase = saved !== null && saved.caseId === (activeCase.value?.id ?? null)
  const savedScrollTop = saved?.scrollTop ?? 0
  const shouldKeepAtBottom = saved === null || saved.atBottom
  await nextTick()
  const apply = () => {
    const element = chatMessageList.value
    if (!element) return
    if (sameCase && !shouldKeepAtBottom) {
      element.scrollTop = Math.min(savedScrollTop, element.scrollHeight)
      keepScrolledToBottom = false
    } else {
      element.scrollTop = element.scrollHeight
      keepScrolledToBottom = true
    }
  }
  apply()
  // 富文本渲染完成后高度可能变化，再校正一次
  window.requestAnimationFrame(apply)
}

const latestAssistantMessageId = computed(() =>
  latestActionableAssistantMessageId(messages.value),
)

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

function onChatScroll() {
  const element = chatMessageList.value
  if (!element) return
  keepScrolledToBottom =
    element.scrollHeight - element.scrollTop - element.clientHeight < 80
  scheduleSaveViewState()
}

async function scrollToBottomIfNeeded() {
  if (!keepScrolledToBottom) return
  await nextTick()
  const element = chatMessageList.value
  if (element) element.scrollTop = element.scrollHeight
}

function flushStreamingBuffer() {
  streamFrame = 0
  if (!streamingReply.value || !streamingBuffer) return
  streamingReply.value = {
    ...streamingReply.value,
    content: streamingReply.value.content + streamingBuffer,
  }
  streamingBuffer = ''
  void scrollToBottomIfNeeded()
}

function appendStreamingText(text: string) {
  streamingBuffer += text
  if (!streamFrame) {
    streamFrame = window.requestAnimationFrame(flushStreamingBuffer)
  }
}

async function loadInitialCase() {
  const [cases, history, topics] = await Promise.all([
    apiRequest<CaseItem[]>('/cases'),
    apiRequest<{ cases: HistoryCaseSummary[] }>('/analytics/history'),
    apiRequest<TopicsResponse>('/analytics/topics'),
  ])
  allCases.value = cases
  historyCases.value = history.cases
  topicSummary.value = topics
  if (!cases.length) return
  const saved = readSavedViewState()
  if (saved && saved.caseId === null) {
    // 上次停留在「新开一轮对话」，保持空白会话
    return
  }
  const preferred =
    saved?.caseId != null ? cases.find((item) => item.id === saved.caseId) : undefined
  activeCase.value = preferred ?? cases[0]
  messages.value = await apiRequest<MessageItem[]>(
    `/cases/${activeCase.value.id}/messages`,
  )
  if (messages.value.length) {
    const metadata = messages.value.at(-1)?.metadata_json ?? {}
    suggestedNextStep.value = String(metadata.suggested_next_step ?? '')
    const structured = metadata.structured as
      | {
          evidence_gaps?: string[]
          intervention_recommendation?: InterventionRecommendation
        }
      | undefined
    evidenceGaps.value = structured?.evidence_gaps ?? []
    interventionRecommendation.value =
      structured?.intervention_recommendation ?? null
  }
  await restoreChatScroll()
}

function startNewConversation() {
  activeCase.value = null
  messages.value = []
  suggestedNextStep.value = ''
  evidenceGaps.value = []
  interventionRecommendation.value = null
  error.value = ''
  keepScrolledToBottom = true
  saveViewState()
}

async function selectCase(target: CaseItem) {
  activeCase.value = target
  messages.value = await apiRequest<MessageItem[]>(
    `/cases/${target.id}/messages`,
  )
  if (messages.value.length) {
    const metadata = messages.value.at(-1)?.metadata_json ?? {}
    suggestedNextStep.value = String(metadata.suggested_next_step ?? '')
    const structured = metadata.structured as
      | {
          evidence_gaps?: string[]
          intervention_recommendation?: InterventionRecommendation
        }
      | undefined
    evidenceGaps.value = structured?.evidence_gaps ?? []
    interventionRecommendation.value =
      structured?.intervention_recommendation ?? null
  } else {
    suggestedNextStep.value = ''
    evidenceGaps.value = []
    interventionRecommendation.value = null
  }
  await restoreChatScroll()
}

function onCaseSelect(event: Event) {
  const el = event.target as HTMLSelectElement
  const selectedId = Number(el.value)
  const target = allCases.value.find((item) => item.id === selectedId)
  if (target) void selectCase(target)
  else startNewConversation()
}

async function sendMessage(contentOverride?: string) {
  const content = (contentOverride ?? input.value).trim()
  if (!content || sending.value) return
  sending.value = true
  error.value = ''
  streamingBuffer = ''
  streamingReply.value = {
    status: '正在理解你的问题…',
    content: '',
    references: [],
  }
  let donePayload: ConsultationResponse | null = null

  try {
    const streamUrl = activeCase.value
      ? `/cases/${activeCase.value.id}/consultations/stream`
      : '/cases/consult/stream'

    await apiStream(
      streamUrl,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      },
      (event, data) => {
        const payload = (data ?? {}) as Record<string, unknown>
        if (event === 'status') {
          if (payload.case) {
            activeCase.value = payload.case as CaseItem
          }
          const userMessage = payload.user_message as MessageItem | undefined
          if (
            userMessage &&
            !messages.value.some((message) => message.id === userMessage.id)
          ) {
            messages.value.push(userMessage)
            void scrollToBottomIfNeeded()
          }
          if (streamingReply.value) {
            streamingReply.value = {
              ...streamingReply.value,
              status:
                typeof payload.label === 'string'
                  ? payload.label
                  : '正在生成回复…',
            }
          }
          return
        }
        if (event === 'delta') {
          if (typeof payload.text === 'string' && payload.text) {
            appendStreamingText(payload.text)
          }
          return
        }
        if (event === 'references') {
          const items = Array.isArray(payload.items)
            ? (payload.items as ReferenceItem[])
            : []
          if (streamingReply.value) {
            streamingReply.value = {
              ...streamingReply.value,
              references: items,
            }
          }
          return
        }
        if (event === 'done') {
          donePayload = payload as unknown as ConsultationResponse
          return
        }
        if (event === 'error') {
          throw new Error(
            typeof payload.detail === 'string'
              ? payload.detail
              : '回复生成失败，请稍后重试',
          )
        }
      },
    )
    const response = donePayload as ConsultationResponse | null
    if (!response) {
      throw new Error('流式回复提前结束，请重试')
    }
    if (streamFrame) {
      window.cancelAnimationFrame(streamFrame)
      streamFrame = 0
    }
    flushStreamingBuffer()
    activeCase.value = response.case
    // 无案件自动创建后，刷新下拉列表让新案件出现
    if (!allCases.value.some((item) => item.id === response.case.id)) {
      allCases.value = await apiRequest<CaseItem[]>('/cases')
    }
    messages.value = messages.value.filter(
      (message) =>
        message.id !== response.user_message.id &&
        message.id !== response.assistant_message.id,
    )
    messages.value.push(response.user_message, response.assistant_message)
    suggestedNextStep.value = response.suggested_next_step
    evidenceGaps.value = response.structured.evidence_gaps
    interventionRecommendation.value =
      response.structured.intervention_recommendation
    input.value = ''
    void scrollToBottomIfNeeded()
  } catch (err) {
    const partial = `${streamingReply.value?.content ?? ''}${streamingBuffer}`
    if (partial.trim()) {
      messages.value.push({
        id: -Date.now(),
        role: 'assistant',
        content: partial,
        metadata_json: { streaming_status: 'interrupted' },
        created_at: new Date().toISOString(),
      })
    }
    error.value = err instanceof Error ? err.message : '发送失败'
  } finally {
    if (streamFrame) {
      window.cancelAnimationFrame(streamFrame)
      streamFrame = 0
    }
    streamingBuffer = ''
    streamingReply.value = null
    sending.value = false
    void scrollToBottomIfNeeded()
  }
}

function followUpKey(message: MessageItem, option: FollowUpOption) {
  return `${message.id}:${option.id}`
}

function activeFollowUpOptionsForMessage(message: MessageItem) {
  return activeFollowUpOptions(
    message,
    latestAssistantMessageId.value,
    new Set(consumedFollowUpKeys.value),
  )
}

function handleFollowUp(message: MessageItem, option: FollowUpOption) {
  if (sending.value) return
  const key = followUpKey(message, option)
  if (!consumedFollowUpKeys.value.includes(key)) {
    consumedFollowUpKeys.value = [...consumedFollowUpKeys.value, key]
  }
  if (option.kind === 'lawyer_request') {
    openLawyerIntervention()
    return
  }
  if (option.kind === 'filing_review') {
    openFilingReview()
    return
  }
  if (option.kind === 'fill') {
    input.value = option.message
    document.querySelector<HTMLElement>('.composer textarea')?.focus()
    return
  }
  void sendMessage(option.message)
}

function openLawyerIntervention() {
  if (!activeCase.value) {
    error.value = '请先发送一条咨询，系统创建案件后才能预约律师。'
    return
  }
  void router.push({
    path: `/cases/${activeCase.value.id}`,
    query: { tab: 'lawyer', request: '1' },
  })
}

function openFilingReview() {
  if (!activeCase.value) {
    error.value = '请先发送一条咨询，系统创建案件后才能申请复核。'
    return
  }
  void router.push({
    path: `/cases/${activeCase.value.id}`,
    query: { tab: 'lawyer', review: '1' },
  })
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

onBeforeUnmount(() => {
  if (streamFrame) window.cancelAnimationFrame(streamFrame)
  if (persistTimer) window.clearTimeout(persistTimer)
  saveViewState()
})
</script>
