<template>
  <section class="content-page simulation-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">沟通训练</span>
        <h1>模拟对话训练</h1>
        <p>选择沟通对象和场景，练习如何陈述事实、提出诉求并保留证据。</p>
      </div>
      <div class="metric-chip">
        <strong>{{ currentScore?.overall ?? '--' }}</strong>
        <span>综合评分</span>
      </div>
    </header>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <div class="simulation-layout">
      <section class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">训练设置</span>
            <h2>选择场景</h2>
          </div>
          <Drama :size="22" />
        </div>
        <div class="form-grid">
          <label>
            <span>训练案件</span>
            <select v-model.number="selectedCaseId">
              <option :value="null">选择案件</option>
              <option v-for="item in cases" :key="item.id" :value="item.id">
                #{{ item.id }} {{ item.title }}
              </option>
            </select>
          </label>
          <label>
            <span>模拟角色</span>
            <select v-model="roleType">
              <option value="boss">单位负责人</option>
              <option value="hr">人事</option>
              <option value="arbitrator">仲裁员</option>
              <option value="judge">法官</option>
              <option value="lawyer">律师</option>
            </select>
          </label>
          <label class="form-grid__wide">
            <span>训练场景</span>
            <textarea
              v-model="scenario"
              rows="3"
              placeholder="例如：向老板确认拖欠工资的支付时间"
            />
          </label>
        </div>
        <div class="form-actions">
          <button
            class="primary-action primary-action--compact"
            type="button"
            :disabled="starting || !selectedCaseId || !scenario.trim()"
            @click="startSimulation"
          >
            {{ starting ? '创建中...' : '开始模拟' }}
          </button>
          <span class="muted-text">模拟内容不写入正式咨询记录。</span>
        </div>
      </section>

      <section v-if="currentSession" class="detail-card simulation-room">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">{{ roleLabels[currentSession.role_type] }}</span>
            <h2>{{ currentSession.scenario }}</h2>
          </div>
          <span class="status-tag">{{ currentSession.status === 'active' ? '训练中' : '已结束' }}</span>
        </div>

        <div class="simulation-messages">
          <article
            v-for="message in messages"
            :key="message.id"
            class="simulation-message"
            :class="`simulation-message--${message.role}`"
          >
            <span>{{ message.role === 'user' ? '你' : roleLabels[currentSession.role_type] }}</span>
            <SafeMarkdown :content="message.content" />
          </article>
          <p v-if="!messages.length" class="muted-text">
            可以先说明事实、金额和希望对方确认的内容。
          </p>
        </div>

        <label class="simulation-compose">
          <span>你的表达</span>
          <textarea
            v-model="messageInput"
            rows="4"
            placeholder="例如：请您确认9月和10月工资的支付时间，并书面确认金额。"
            @keydown.enter.exact.prevent="sendMessage"
          />
        </label>
        <div class="form-actions">
          <button
            class="primary-action primary-action--compact"
            type="button"
            :disabled="sending || !messageInput.trim()"
            @click="sendMessage"
          >
            {{ sending ? '评分中...' : '发送并评分' }}
          </button>
          <span class="muted-text">Enter 发送，Shift + Enter 换行。</span>
        </div>
      </section>

      <aside v-if="currentScore" class="detail-card score-panel">
        <span class="eyebrow">本轮教练反馈</span>
        <h2>综合评分 {{ currentScore.overall }}/10</h2>
        <div class="score-grid">
          <div><span>表达清晰</span><strong>{{ currentScore.clarity }}</strong></div>
          <div><span>证据意识</span><strong>{{ currentScore.evidence_awareness }}</strong></div>
          <div><span>表达适当</span><strong>{{ currentScore.legal_appropriateness }}</strong></div>
        </div>
        <ul class="coach-list">
          <li v-for="suggestion in currentScore.suggestions" :key="suggestion">
            {{ suggestion }}
          </li>
        </ul>
        <p class="muted-text">评分用于沟通训练，不构成正式法律意见。</p>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Drama } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { apiRequest } from '../api/http'
import SafeMarkdown from '../components/SafeMarkdown.vue'
import type {
  CaseItem,
  SimulationMessage,
  SimulationReply,
  SimulationRole,
  SimulationScore,
  SimulationSession,
  SimulationSessionDetail,
} from '../types/api'

const route = useRoute()
const cases = ref<CaseItem[]>([])
const selectedCaseId = ref<number | null>(
  Number(route.query.caseId) || null,
)
const roleType = ref<SimulationRole>('boss')
const scenario = ref('向老板确认拖欠工资的支付时间')
const currentSession = ref<SimulationSession | null>(null)
const messages = ref<SimulationMessage[]>([])
const messageInput = ref('')
const currentScore = ref<SimulationScore | null>(null)
const starting = ref(false)
const sending = ref(false)
const error = ref('')

const roleLabels: Record<SimulationRole, string> = {
  boss: '单位负责人',
  hr: '人事',
  arbitrator: '仲裁员',
  judge: '法官',
  lawyer: '律师',
}

async function startSimulation() {
  if (!selectedCaseId.value || !scenario.value.trim()) return
  starting.value = true
  error.value = ''
  try {
    currentSession.value = await apiRequest<SimulationSession>(
      `/cases/${selectedCaseId.value}/simulations`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role_type: roleType.value,
          scenario: scenario.value.trim(),
        }),
      },
    )
    messages.value = []
    currentScore.value = null
  } catch (err) {
    error.value = err instanceof Error ? err.message : '模拟创建失败'
  } finally {
    starting.value = false
  }
}

async function sendMessage() {
  const content = messageInput.value.trim()
  if (!content || !currentSession.value || sending.value) return
  sending.value = true
  error.value = ''
  try {
    const reply = await apiRequest<SimulationReply>(
      `/cases/${currentSession.value.case_id}/simulations/${currentSession.value.id}/messages`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      },
    )
    currentSession.value = reply.session
    messages.value.push(reply.user_message, reply.assistant_message)
    currentScore.value = reply.score
    messageInput.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '模拟消息发送失败'
  } finally {
    sending.value = false
  }
}

async function loadCase() {
  try {
    cases.value = await apiRequest<CaseItem[]>('/cases')
    if (!selectedCaseId.value && cases.value.length) {
      selectedCaseId.value = cases.value[0].id
    }
    if (selectedCaseId.value) {
      const sessions = await apiRequest<SimulationSession[]>(
        `/cases/${selectedCaseId.value}/simulations`,
      )
      if (sessions.length) {
        const detail = await apiRequest<SimulationSessionDetail>(
          `/cases/${selectedCaseId.value}/simulations/${sessions[0].id}`,
        )
        currentSession.value = detail
        messages.value = detail.messages
        const lastScored = [...detail.messages]
          .reverse()
          .find((message) => message.score)
        currentScore.value = lastScored?.score ?? null
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '模拟数据加载失败'
  }
}

onMounted(loadCase)
</script>
