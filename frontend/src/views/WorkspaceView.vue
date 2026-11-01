<template>
  <div class="workspace">
    <section class="conversation-panel">
      <header class="workspace-header">
        <div>
          <span class="eyebrow">AI 法律咨询</span>
          <h1>{{ activeCase ? activeCase.title : '先说说你遇到了什么问题' }}</h1>
          <p>
            系统会保留当前案件上下文，先判断问题类型，再询问必要信息并给出下一步建议。
          </p>
        </div>
        <div class="connection" :class="`connection--${workspace.connection}`">
          <span class="connection__dot" />
          {{ connectionLabel }}
        </div>
      </header>

      <div v-if="activeCase" class="case-context-bar">
        <div>
          <span>当前案件</span>
          <strong>#{{ activeCase.id }} · {{ disputeLabels[activeCase.dispute_type] || activeCase.dispute_type }}</strong>
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
          <p>{{ message.content }}</p>
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
            <span class="eyebrow">案件进度</span>
            <h2>{{ activeCase ? stageLabel(activeCase.stage) : '尚未创建案件' }}</h2>
          </div>
          <Clock3 :size="20" />
        </div>
        <p>
          {{ activeCase ? `案件 #${activeCase.id} 已保存当前对话和分类结果。` : '发送首条咨询后会自动创建案件。' }}
        </p>

        <ol class="stage-list">
          <li
            v-for="(stage, index) in stages"
            :key="stage.key"
            :class="{ active: activeCase?.stage === stage.key }"
          >
            <span>{{ index + 1 }}</span>
            <div>
              <strong>{{ stage.label }}</strong>
              <small>{{ stage.description }}</small>
            </div>
          </li>
        </ol>
      </section>

      <section v-if="activeCase" class="context-card context-card--soft">
        <span class="eyebrow">本轮建议</span>
        <h2>{{ classificationLabel }}</h2>
        <p>{{ suggestedNextStep || '继续补充事实和现有材料，系统会更新案件建议。' }}</p>
        <div class="tag-row">
          <span class="status-tag">{{ activeCase.legal_relationship === 'service' ? '劳务关系' : '劳动关系' }}</span>
          <span v-if="demoMode" class="status-tag status-tag--warning">演示规则</span>
        </div>
        <RouterLink :to="`/cases/${activeCase.id}`" class="text-link">
          查看证据与文书
          <ArrowRight :size="16" />
        </RouterLink>
      </section>

      <section class="context-card context-card--meta">
        <span>工作方式</span>
        <strong>先识别，再行动</strong>
        <p>
          系统不会直接替用户决定是否仲裁或起诉。关键路径会展示依据、风险与人工复核入口。
        </p>
        <small v-if="workspace.lastCheckedAt">
          最近检查：{{ workspace.lastCheckedAt.toLocaleTimeString('zh-CN') }}
        </small>
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
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'
import type { CaseItem, ConsultationResponse, MessageItem } from '../types/api'

const router = useRouter()
const auth = useAuthStore()
const workspace = useWorkspaceStore()
const activeCase = ref<CaseItem | null>(null)
const messages = ref<MessageItem[]>([])
const input = ref('')
const sending = ref(false)
const error = ref('')
const suggestedNextStep = ref('')
const demoMode = ref(false)

const topics = ['拖欠工资', '突然被辞退', '没有签合同', '工伤或受伤'] as const
const topicIcons = {
  拖欠工资: Banknote,
  突然被辞退: UserRoundX,
  没有签合同: FileWarning,
  工伤或受伤: ShieldCheck,
}
const disputeLabels: Record<string, string> = {
  wage: '欠薪',
  termination: '违法解除',
  contract: '劳动合同',
  overtime: '加班费',
  injury: '工伤待遇',
  insurance: '社会保险',
  service_pay: '劳务报酬',
  general: '待进一步识别',
}
const stages = [
  { key: 'intake', label: '识别问题', description: '判断关系和纠纷类型' },
  { key: 'evidence', label: '整理证据', description: '确认已有材料与缺口' },
  { key: 'procedure', label: '协商或程序', description: '选择处理路径' },
  { key: 'document', label: '文书准备', description: '生成可确认的草稿' },
  { key: 'lawyer_help', label: '律师协助', description: '人工复核与处理' },
]

const connectionLabel = computed(() => {
  if (workspace.connection === 'online') return '服务已连接'
  if (workspace.connection === 'offline') return '服务未连接'
  return '正在检查服务'
})
const classificationLabel = computed(() =>
  activeCase.value
    ? disputeLabels[activeCase.value.dispute_type] || activeCase.value.dispute_type
    : '等待识别',
)

function stageLabel(stage: string) {
  return stages.find((item) => item.key === stage)?.label ?? '识别问题'
}

async function loadInitialCase() {
  const cases = await apiRequest<CaseItem[]>('/cases')
  if (!cases.length) return
  activeCase.value = cases[0]
  messages.value = await apiRequest<MessageItem[]>(`/cases/${cases[0].id}/messages`)
  if (messages.value.length) {
    suggestedNextStep.value =
      String(messages.value.at(-1)?.metadata_json?.suggested_next_step ?? '')
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
          dispute_type: 'general',
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
    demoMode.value = response.demo_mode
    input.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发送失败'
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  void workspace.checkHealth()
  try {
    await loadInitialCase()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件加载失败'
  }
})
</script>
