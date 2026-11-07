<template>
  <section class="content-page lawyer-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">本站律师</span>
        <h1>律师工作台</h1>
        <p>这里只展示管理员已经分配给你的案件。材料查看和业务操作会记录审计日志。</p>
      </div>
      <div class="metric-chip">
        <strong>{{ cases.length }}</strong>
        <span>待处理案件</span>
      </div>
    </header>

    <nav class="tab-bar" aria-label="律师工作台功能">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <component :is="tab.icon" :size="17" />
        {{ tab.label }}
      </button>
    </nav>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <section v-if="activeTab === 'cases'">
      <div v-if="cases.length" class="case-grid">
        <article
          v-for="item in cases"
          :key="item.id"
          class="case-card"
          @click="router.push(`/cases/${item.id}`)"
        >
          <div class="case-card__top">
            <span class="status-tag status-tag--wrap">{{ dictionary.disputeLabels[item.dispute_type] || '待识别' }}</span>
            <span class="case-card__id">#{{ item.id }}</span>
          </div>
          <h2>{{ item.title }}</h2>
          <p>{{ item.summary || item.facts }}</p>
          <div class="case-card__meta">
            <span><MapPin :size="14" />{{ item.location || '地点待补充' }}</span>
            <span><Clock3 :size="14" />{{ dictionary.stageLabels[item.stage] || item.stage }}</span>
          </div>
          <div class="case-card__footer">
            <span>{{ new Date(item.updated_at).toLocaleString('zh-CN') }}</span>
            <span class="text-link">查看材料 <ArrowRight :size="15" /></span>
          </div>
        </article>
      </div>
      <div v-else class="empty-state">
        <BriefcaseBusiness :size="38" />
        <h2>暂时没有分配案件</h2>
        <p>管理员分配案件后，案件会出现在这里。</p>
      </div>
    </section>

    <section v-else-if="activeTab === 'services'" class="detail-grid">
      <form class="detail-card" @submit.prevent="createServiceRecord">
        <span class="eyebrow">服务记录</span>
        <h2>登记本次服务</h2>
        <div class="form-grid">
          <label>
            <span>关联案件</span>
            <select v-model.number="serviceForm.case_id" required>
              <option :value="0">选择案件</option>
              <option v-for="item in cases" :key="item.id" :value="item.id">
                #{{ item.id }} {{ item.title }}
              </option>
            </select>
          </label>
          <label>
            <span>服务类型</span>
            <select v-model="serviceForm.service_type">
              <option value="consultation">咨询</option>
              <option value="evidence">证据整理</option>
              <option value="document">文书协助</option>
              <option value="hearing">出庭或仲裁</option>
              <option value="other">其他</option>
            </select>
          </label>
          <label class="form-grid__wide">
            <span>服务摘要</span>
            <textarea v-model="serviceForm.summary" rows="3" required />
          </label>
          <label>
            <span>时长（分钟）</span>
            <input v-model.number="serviceForm.duration_minutes" type="number" min="0" max="1440" />
          </label>
        </div>
        <div class="form-actions">
          <button class="primary-action primary-action--compact" type="submit" :disabled="saving">
            {{ saving ? '保存中...' : '保存服务记录' }}
          </button>
        </div>
      </form>

      <div class="detail-card">
        <span class="eyebrow">服务台账</span>
        <h2>{{ serviceRecords.length }} 条记录</h2>
        <div class="ledger-list">
          <article v-for="record in serviceRecords" :key="record.id">
            <div>
              <strong>#{{ record.case_id }} · {{ serviceLabels[record.service_type] }}</strong>
              <span>{{ record.summary }}</span>
              <small>{{ record.duration_minutes }} 分钟 · {{ new Date(record.created_at).toLocaleString('zh-CN') }}</small>
            </div>
            <div class="ledger-list__actions">
              <span class="status-tag">{{ statusLabels[record.status] }}</span>
              <button
                v-if="nextServiceStatus(record.status)"
                type="button"
                @click="advanceServiceRecord(record)"
              >
                {{ statusLabels[nextServiceStatus(record.status) as string] }}
              </button>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'revenue'" class="detail-grid">
      <form class="detail-card" @submit.prevent="createRevenue">
        <span class="eyebrow">收益台账</span>
        <h2>登记服务收入</h2>
        <div class="form-grid">
          <label>
            <span>关联案件</span>
            <select v-model.number="revenueForm.case_id">
              <option :value="null">不关联案件</option>
              <option v-for="item in cases" :key="item.id" :value="item.id">
                #{{ item.id }} {{ item.title }}
              </option>
            </select>
          </label>
          <label>
            <span>金额（元）</span>
            <input v-model.number="revenueAmountYuan" type="number" min="0" step="0.01" />
          </label>
          <label>
            <span>收入类型</span>
            <input v-model="revenueForm.entry_type" placeholder="consultation" />
          </label>
          <label class="form-grid__wide">
            <span>备注</span>
            <textarea v-model="revenueForm.note" rows="2" />
          </label>
        </div>
        <div class="form-actions">
          <button class="primary-action primary-action--compact" type="submit" :disabled="saving">
            创建待确认记录
          </button>
        </div>
      </form>
      <div class="detail-card">
        <span class="eyebrow">收益记录</span>
        <h2>{{ revenueEntries.length }} 条</h2>
        <div class="ledger-list">
          <article v-for="entry in revenueEntries" :key="entry.id">
            <div>
              <strong>¥{{ (entry.amount_cents / 100).toFixed(2) }}</strong>
              <span>{{ entry.entry_type }} · {{ entry.note || '无备注' }}</span>
              <small>{{ new Date(entry.created_at).toLocaleString('zh-CN') }}</small>
            </div>
            <span class="status-tag">{{ revenueStatusLabels[entry.status] }}</span>
          </article>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'todos'" class="detail-grid">
      <div class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">待受理预约</span>
            <h2>{{ todoRequests.length }} 条待处理</h2>
          </div>
        </div>
        <div class="ledger-list">
          <article v-for="request in todoRequests" :key="request.id">
            <div>
              <strong>
                #{{ request.case_id }} · {{ todoCaseTitle(request.case_id) }}
                <span v-if="request.priority === 'urgent'" class="status-tag status-tag--warning">加急</span>
                <span
                  v-if="request.preferred_date && request.preferred_date < todayIso"
                  class="status-tag status-tag--warning"
                >已过期</span>
              </strong>
              <span class="pre-line">{{ request.reason }}</span>
              <small>
                期望时间：{{ todoSlotText(request) }} · 已等待 {{ waitingHours(request.created_at) }} ·
                {{ new Date(request.created_at).toLocaleString('zh-CN') }}
              </small>
            </div>
            <div class="ledger-list__actions">
              <button
                type="button"
                :disabled="actingRequestId === request.id"
                @click="actTodoRequest(request, true)"
              >
                {{ actingRequestId === request.id ? '处理中...' : '受理并开始对话' }}
              </button>
              <button
                type="button"
                :disabled="actingRequestId === request.id"
                @click="actTodoRequest(request, false)"
              >
                拒绝
              </button>
            </div>
          </article>
          <p v-if="!todoRequests.length" class="muted-text">暂无待受理预约。</p>
        </div>
      </div>

      <div class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">待复核案件</span>
            <h2>{{ todoReviews.length }} 件待复核</h2>
          </div>
        </div>
        <div class="ledger-list">
          <article v-for="review in todoReviews" :key="review.id">
            <div>
              <strong>#{{ review.case_id }} · {{ todoCaseTitle(review.case_id) }}</strong>
              <small>申请于 {{ new Date(review.created_at).toLocaleString('zh-CN') }}</small>
            </div>
            <div class="ledger-list__actions">
              <button
                class="secondary-action"
                type="button"
                @click="openReviewModal(review.id)"
              >
                查看材料并复核
              </button>
            </div>
          </article>
          <p v-if="!todoReviews.length" class="muted-text">暂无待复核案件。</p>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'sessions'" class="detail-grid detail-grid--sessions">
      <div class="detail-card sessions-list-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">咨询会话</span>
            <h2>{{ sessions.length }} 个会话</h2>
          </div>
        </div>
        <div class="ledger-list">
          <article
            v-for="item in sessions"
            :key="item.id"
            class="session-item"
            :class="{ 'session-item--active': activeSessionId === item.id }"
            @click="activeSessionId = item.id"
          >
            <div class="session-item__main">
              <strong
                class="session-item__title"
                :title="`#${item.case_id} · ${sessionCaseTitle(item)}`"
              >
                #{{ item.case_id }} · {{ sessionCaseTitle(item) }}
              </strong>
              <small class="session-item__time">
                {{ new Date(item.created_at).toLocaleString('zh-CN') }}
              </small>
            </div>
            <span
              class="status-tag status-tag--compact"
              :class="{ 'status-tag--success': item.status === 'active' }"
            >
              {{ item.status === 'active' ? '进行中' : '已结束' }}
            </span>
          </article>
          <p v-if="!sessions.length" class="muted-text">
            暂无咨询会话，受理预约后会自动创建。
          </p>
        </div>
      </div>
      <div class="detail-card sessions-chat-card">
        <template v-if="activeSession">
          <div class="detail-section-heading">
            <div>
              <span class="eyebrow">对话窗口</span>
              <h2>#{{ activeSession.case_id }} · {{ sessionCaseTitle(activeSession) }}</h2>
            </div>
          </div>
          <ConsultationChat
            :key="activeSession.id"
            :session="activeSession"
            sender-role="lawyer"
            @closed="onSessionClosed"
          />
        </template>
        <div v-else class="sessions-chat-empty">
          <MessageCircle :size="32" />
          <p class="muted-text">
            {{ sessions.length ? '从左侧选择一个会话开始对话' : '暂无会话可选择' }}
          </p>
        </div>
      </div>
    </section>

    <div v-if="modalReview" class="review-modal" @click.self="closeReviewModal">
      <div class="review-modal__card">
        <div class="review-modal__head">
          <div>
            <span class="eyebrow">立案前复核</span>
            <h3>#{{ modalReview.case_id }} · {{ todoCaseTitle(modalReview.case_id) }}</h3>
          </div>
          <button class="secondary-action" type="button" @click="closeReviewModal">关闭</button>
        </div>
        <div class="review-modal__body">
          <p v-if="briefLoadingId === modalReview.id" class="muted-text">正在加载案件材料…</p>
          <div v-else-if="reviewBriefs[modalReview.id]" class="review-brief">
            <div class="review-brief__section">
              <span class="review-brief__title">案件概要</span>
              <div class="review-brief__meta">
                <span class="status-tag status-tag--wrap">
                  {{ dictionary.disputeLabels[reviewBriefs[modalReview.id]!.case.dispute_type] || '待识别' }}
                </span>
                <span class="status-tag">
                  {{ dictionary.stageLabels[reviewBriefs[modalReview.id]!.case.stage] || reviewBriefs[modalReview.id]!.case.stage }}
                </span>
                <small>{{ reviewBriefs[modalReview.id]!.case.location || '地点未填写' }}</small>
              </div>
              <p class="pre-line">{{ reviewBriefs[modalReview.id]!.case.facts }}</p>
              <p v-if="reviewBriefs[modalReview.id]!.case.summary" class="review-brief__summary">
                {{ reviewBriefs[modalReview.id]!.case.summary }}
              </p>
            </div>
            <div class="review-brief__section">
              <span class="review-brief__title">
                证据材料（{{ reviewBriefs[modalReview.id]!.evidence.items.length }} 件）
              </span>
              <p v-if="!reviewBriefs[modalReview.id]!.evidence.items.length" class="review-brief__gap">
                该案件暂无证据材料，复核时请重点确认。
              </p>
              <ul v-else class="review-brief__list">
                <li v-for="ev in reviewBriefs[modalReview.id]!.evidence.items" :key="ev.id">
                  <strong>{{ ev.filename }}</strong>
                  <span>{{ evidenceCategoryLabel(ev.category) }}</span>
                  <small>{{ screeningLabels[ev.screening_status] || ev.screening_status }}</small>
                </li>
              </ul>
              <p
                v-if="reviewBriefs[modalReview.id]!.evidence.assessment.missing_labels.length"
                class="review-brief__gap"
              >
                材料缺口：{{ reviewBriefs[modalReview.id]!.evidence.assessment.missing_labels.join('、') }}
              </p>
            </div>
            <div class="review-brief__section">
              <span class="review-brief__title">
                法律文书（{{ reviewBriefs[modalReview.id]!.documents.length }} 份）
              </span>
              <p v-if="!reviewBriefs[modalReview.id]!.documents.length" class="muted-text">
                尚无法律文书。
              </p>
              <ul v-else class="review-brief__list">
                <li v-for="doc in reviewBriefs[modalReview.id]!.documents" :key="doc.id">
                  <strong>{{ docTypeLabels[doc.doc_type] || doc.doc_type }}</strong>
                  <span>{{ doc.title }}</span>
                  <small>{{ doc.status === 'draft' ? '草稿' : doc.status }}</small>
                </li>
              </ul>
            </div>
          </div>
          <div class="review-item__field">
            <span>复核结论</span>
            <div class="lawyer-slot-picker__options">
              <button
                v-for="option in reviewConclusionOptions"
                :key="option.value"
                type="button"
                class="lawyer-slot-chip"
                :class="{ 'lawyer-slot-chip--active': reviewForm(modalReview.id).conclusion === option.value }"
                @click="reviewForm(modalReview.id).conclusion = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>
          <div class="review-item__field">
            <span>复核意见</span>
            <textarea
              v-model="reviewForm(modalReview.id).comment"
              rows="4"
              placeholder="向用户说明结论依据和下一步建议。"
            />
          </div>
        </div>
        <div class="review-modal__foot">
          <button
            class="primary-action primary-action--compact"
            type="button"
            :disabled="submittingReviewId === modalReview.id || !reviewForm(modalReview.id).conclusion"
            @click="submitReview(modalReview)"
          >
            {{ submittingReviewId === modalReview.id ? '提交中...' : '提交复核结论' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  ArrowRight,
  BellRing,
  BriefcaseBusiness,
  Clock3,
  FileText,
  MapPin,
  MessageCircle,
  MessagesSquare,
  WalletCards,
} from '@lucide/vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiRequest } from '../api/http'
import ConsultationChat from '../components/ConsultationChat.vue'
import { useDictionaryStore } from '../stores/dictionary'
import { notifySuccess, promptForText } from '../utils/dialogs'
import type {
  CaseItem,
  CaseReviewItem,
  ConsultationSessionItem,
  LawyerRequestItem,
  LawyerTodoCase,
  LawyerTodosResponse,
  RevenueLedger,
  ReviewCaseBrief,
  ServiceRecord,
} from '../types/api'

const docTypeLabels: Record<string, string> = {
  settlement: '和解协议',
  arbitration: '仲裁申请书',
  complaint: '民事起诉状',
}
const screeningLabels: Record<string, string> = {
  accepted: '已受理',
  quarantined: '待复核',
  needs_review: '待复核',
}

const slotLabels: Record<string, string> = {
  morning: '上午 09:00-12:00',
  afternoon: '下午 14:00-18:00',
  evening: '晚间 18:00-21:00',
}
const todayIso = new Date().toISOString().slice(0, 10)

const router = useRouter()
const activeTab = ref('cases')
const cases = ref<CaseItem[]>([])
const serviceRecords = ref<ServiceRecord[]>([])
const revenueEntries = ref<RevenueLedger[]>([])
const error = ref('')
const saving = ref(false)
const revenueAmountYuan = ref(0)

const serviceForm = reactive({
  case_id: 0,
  service_type: 'consultation',
  summary: '',
  duration_minutes: 30,
})
const revenueForm = reactive({
  case_id: null as number | null,
  entry_type: 'consultation',
  note: '',
})

const todoRequests = ref<LawyerRequestItem[]>([])
const todoReviews = ref<CaseReviewItem[]>([])
const todoCases = ref<Record<string, LawyerTodoCase>>({})
const sessions = ref<ConsultationSessionItem[]>([])
const sessionTitles = ref<Record<number, string>>({})
const activeSessionId = ref(0)
const actingRequestId = ref<number | null>(null)
const submittingReviewId = ref<number | null>(null)
const reviewModalId = ref<number | null>(null)
const reviewForms = reactive<Record<number, { conclusion: string; comment: string }>>({})
const reviewBriefs = reactive<Record<number, ReviewCaseBrief | null>>({})
const briefLoadingId = ref<number | null>(null)

const modalReview = computed(
  () => todoReviews.value.find((review) => review.id === reviewModalId.value) ?? null,
)

function openReviewModal(reviewId: number) {
  reviewModalId.value = reviewId
  if (!reviewBriefs[reviewId]) void loadReviewBrief(reviewId)
}

function closeReviewModal() {
  reviewModalId.value = null
}

async function loadReviewBrief(reviewId: number) {
  briefLoadingId.value = reviewId
  try {
    reviewBriefs[reviewId] = await apiRequest<ReviewCaseBrief>(
      `/lawyer-service/reviews/${reviewId}/case-brief`,
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件材料加载失败'
  } finally {
    briefLoadingId.value = null
  }
}

function evidenceCategoryLabel(category: string) {
  return dictionary.categoryLabels[category] || category
}

const reviewConclusionOptions = [
  { value: 'ready_to_file', label: '材料齐备，可以立案' },
  { value: 'need_more', label: '需要补充材料后再立案' },
  { value: 'not_recommended', label: '暂不建议立案' },
]

const activeSession = computed(
  () => sessions.value.find((item) => item.id === activeSessionId.value) ?? null,
)

function todoCaseTitle(caseId: number) {
  return todoCases.value[String(caseId)]?.title ?? `案件 ${caseId}`
}

function sessionCaseTitle(item: ConsultationSessionItem) {
  return sessionTitles.value[item.case_id] ?? `案件 ${item.case_id}`
}

function reviewForm(reviewId: number) {
  let form = reviewForms[reviewId]
  if (!form) {
    form = { conclusion: 'ready_to_file', comment: '' }
    reviewForms[reviewId] = form
  }
  return form
}

async function loadSessionCaseTitles() {
  const ids = [...new Set(sessions.value.map((item) => item.case_id))]
  await Promise.all(
    ids.map(async (id) => {
      if (sessionTitles.value[id]) return
      try {
        const item = await apiRequest<CaseItem>(`/cases/${id}`)
        sessionTitles.value[id] = item.title
      } catch {
        sessionTitles.value[id] = `案件 ${id}`
      }
    }),
  )
}

async function refreshLawyerService() {
  const [todoData, sessionData] = await Promise.all([
    apiRequest<LawyerTodosResponse>('/lawyer-service/todos'),
    apiRequest<ConsultationSessionItem[]>('/lawyer-service/sessions'),
  ])
  todoRequests.value = todoData.requests
  todoReviews.value = todoData.reviews
  todoCases.value = todoData.cases
  sessions.value = sessionData
  if (!activeSessionId.value && sessions.value.length) {
    activeSessionId.value = sessions.value[0].id
  }
  await loadSessionCaseTitles()
}

async function actTodoRequest(request: LawyerRequestItem, accept: boolean) {
  let rejectReason = ''
  if (!accept) {
    const reason = await promptForText('拒绝预约时需要向用户说明理由（会展示给用户）：', {
      title: '拒绝预约',
      placeholder: '例如：近期时段已排满，请改约其他时间',
      requiredMessage: '请填写拒绝理由',
      multiline: true,
    })
    if (reason === null) return
    rejectReason = reason
  }
  actingRequestId.value = request.id
  error.value = ''
  try {
    await apiRequest<LawyerRequestItem>(`/lawyer-service/requests/${request.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accept, reject_reason: rejectReason }),
    })
    notifySuccess(accept ? '已受理，可在咨询会话中回复' : '已拒绝该预约')
    await refreshLawyerService()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '预约处理失败'
  } finally {
    actingRequestId.value = null
  }
}

function todoSlotText(request: LawyerRequestItem) {
  if (request.preferred_date && request.preferred_slot) {
    const monthDay = request.preferred_date.slice(5).replace('-', '月')
    return `${monthDay}日 · ${slotLabels[request.preferred_slot]}`
  }
  return request.preferred_time || '不限'
}

function waitingHours(createdAt: string) {
  const hours = Math.max(0, Math.floor((Date.now() - new Date(createdAt).getTime()) / 3_600_000))
  if (hours < 1) return '不足 1 小时'
  if (hours >= 24) return `${Math.floor(hours / 24)} 天 ${hours % 24} 小时`
  return `${hours} 小时`
}

async function submitReview(review: CaseReviewItem) {
  const form = reviewForm(review.id)
  submittingReviewId.value = review.id
  error.value = ''
  try {
    await apiRequest<CaseReviewItem>(`/lawyer-service/reviews/${review.id}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conclusion: form.conclusion, comment: form.comment.trim() }),
    })
    notifySuccess('复核结论已提交')
    reviewModalId.value = null
    reviewBriefs[review.id] = null
    await refreshLawyerService()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '复核提交失败'
  } finally {
    submittingReviewId.value = null
  }
}

function onSessionClosed(closed: ConsultationSessionItem) {
  const index = sessions.value.findIndex((item) => item.id === closed.id)
  if (index >= 0) sessions.value[index] = closed
  void refreshLawyerService()
}

const tabs = [
  { key: 'cases', label: '案件', icon: BriefcaseBusiness },
  { key: 'todos', label: '待办', icon: BellRing },
  { key: 'sessions', label: '咨询会话', icon: MessagesSquare },
  { key: 'services', label: '服务记录', icon: FileText },
  { key: 'revenue', label: '收益台账', icon: WalletCards },
]

const dictionary = useDictionaryStore()
const serviceLabels: Record<string, string> = {
  consultation: '咨询',
  evidence: '证据整理',
  document: '文书协助',
  hearing: '出庭或仲裁',
  other: '其他',
}
const statusLabels: Record<string, string> = {
  pending: '待开始',
  in_progress: '进行中',
  completed: '已完成',
}
const revenueStatusLabels: Record<string, string> = {
  pending: '待确认',
  confirmed: '已确认',
  paid: '已结算',
}

function nextServiceStatus(status: string) {
  if (status === 'pending') return 'in_progress'
  if (status === 'in_progress') return 'completed'
  return ''
}

async function loadAll() {
  error.value = ''
  try {
    const [caseData, serviceData, revenueData] = await Promise.all([
      apiRequest<CaseItem[]>('/lawyer/cases'),
      apiRequest<ServiceRecord[]>('/lawyer/service-records'),
      apiRequest<RevenueLedger[]>('/lawyer/revenue'),
    ])
    cases.value = caseData
    serviceRecords.value = serviceData
    revenueEntries.value = revenueData
    if (!serviceForm.case_id && caseData.length) {
      serviceForm.case_id = caseData[0].id
    }
    await refreshLawyerService()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '律师数据加载失败'
  }
}

async function createServiceRecord() {
  if (!serviceForm.case_id) return
  saving.value = true
  try {
    const record = await apiRequest<ServiceRecord>('/lawyer/service-records', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(serviceForm),
    })
    serviceRecords.value.unshift(record)
    serviceForm.summary = ''
    serviceForm.duration_minutes = 30
  } catch (err) {
    error.value = err instanceof Error ? err.message : '服务记录保存失败'
  } finally {
    saving.value = false
  }
}

async function advanceServiceRecord(record: ServiceRecord) {
  const status = nextServiceStatus(record.status)
  if (!status) return
  try {
    const updated = await apiRequest<ServiceRecord>(
      `/lawyer/service-records/${record.id}/status`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      },
    )
    const index = serviceRecords.value.findIndex((item) => item.id === record.id)
    if (index >= 0) serviceRecords.value[index] = updated
  } catch (err) {
    error.value = err instanceof Error ? err.message : '服务状态更新失败'
  }
}

async function createRevenue() {
  if (revenueAmountYuan.value <= 0) return
  saving.value = true
  try {
    const entry = await apiRequest<RevenueLedger>('/lawyer/revenue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_id: revenueForm.case_id,
        amount_cents: Math.round(revenueAmountYuan.value * 100),
        entry_type: revenueForm.entry_type,
        note: revenueForm.note,
      }),
    })
    revenueEntries.value.unshift(entry)
    revenueAmountYuan.value = 0
    revenueForm.note = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '收益记录创建失败'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await dictionary.load()
  await loadAll()
})
</script>
