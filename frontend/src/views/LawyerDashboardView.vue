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
            <span class="status-tag">{{ disputeLabels[item.dispute_type] || '待识别' }}</span>
            <span class="case-card__id">#{{ item.id }}</span>
          </div>
          <h2>{{ item.title }}</h2>
          <p>{{ item.summary || item.facts }}</p>
          <div class="case-card__meta">
            <span><MapPin :size="14" />{{ item.location || '地点待补充' }}</span>
            <span><Clock3 :size="14" />{{ stageLabels[item.stage] || item.stage }}</span>
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

    <section v-else-if="activeTab === 'opinions'" class="detail-grid">
      <form class="detail-card" @submit.prevent="createOpinion">
        <span class="eyebrow">律师意见</span>
        <h2>提交案件意见</h2>
        <label>
          <span>关联案件</span>
          <select v-model.number="opinionCaseId" required>
            <option :value="0">选择案件</option>
            <option v-for="item in cases" :key="item.id" :value="item.id">
              #{{ item.id }} {{ item.title }}
            </option>
          </select>
        </label>
        <label>
          <span>意见内容</span>
          <textarea v-model="opinionContent" rows="8" required />
        </label>
        <div class="form-actions">
          <button class="primary-action primary-action--compact" type="submit" :disabled="saving">
            提交意见
          </button>
        </div>
      </form>
      <div class="detail-card">
        <span class="eyebrow">已提交意见</span>
        <h2>{{ opinions.length }} 条</h2>
        <div class="ledger-list">
          <article v-for="opinion in opinions" :key="opinion.id">
            <div>
              <strong>案件 #{{ opinion.case_id }}</strong>
              <SafeMarkdown :content="opinion.content" />
              <small>{{ new Date(opinion.created_at).toLocaleString('zh-CN') }}</small>
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
  </section>
</template>

<script setup lang="ts">
import {
  ArrowRight,
  BriefcaseBusiness,
  Clock3,
  FileText,
  MapPin,
  MessageSquareText,
  WalletCards,
} from '@lucide/vue'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiRequest } from '../api/http'
import SafeMarkdown from '../components/SafeMarkdown.vue'
import type {
  CaseItem,
  LawyerOpinion,
  RevenueLedger,
  ServiceRecord,
} from '../types/api'

const router = useRouter()
const activeTab = ref('cases')
const cases = ref<CaseItem[]>([])
const serviceRecords = ref<ServiceRecord[]>([])
const opinions = ref<LawyerOpinion[]>([])
const revenueEntries = ref<RevenueLedger[]>([])
const error = ref('')
const saving = ref(false)
const opinionCaseId = ref(0)
const opinionContent = ref('')
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

const tabs = [
  { key: 'cases', label: '案件', icon: BriefcaseBusiness },
  { key: 'services', label: '服务记录', icon: FileText },
  { key: 'opinions', label: '律师意见', icon: MessageSquareText },
  { key: 'revenue', label: '收益台账', icon: WalletCards },
]

const disputeLabels: Record<string, string> = {
  wage: '欠薪',
  termination: '违法解除',
  contract: '未签劳动合同',
  overtime: '加班费',
  injury: '工伤待遇',
  service_pay: '劳务报酬',
  general: '待识别',
}
const stageLabels: Record<string, string> = {
  intake: '问题识别',
  evidence: '证据整理',
  procedure: '协商或程序',
  document: '文书准备',
  lawyer_help: '律师协助',
}
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
    const [caseData, serviceData, opinionData, revenueData] = await Promise.all([
      apiRequest<CaseItem[]>('/lawyer/cases'),
      apiRequest<ServiceRecord[]>('/lawyer/service-records'),
      apiRequest<LawyerOpinion[]>('/lawyer/opinions'),
      apiRequest<RevenueLedger[]>('/lawyer/revenue'),
    ])
    cases.value = caseData
    serviceRecords.value = serviceData
    opinions.value = opinionData
    revenueEntries.value = revenueData
    if (!serviceForm.case_id && caseData.length) {
      serviceForm.case_id = caseData[0].id
      opinionCaseId.value = caseData[0].id
    }
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

async function createOpinion() {
  if (!opinionCaseId.value || !opinionContent.value.trim()) return
  saving.value = true
  try {
    const opinion = await apiRequest<LawyerOpinion>(
      `/lawyer/cases/${opinionCaseId.value}/opinions`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: opinionContent.value.trim() }),
      },
    )
    opinions.value.unshift(opinion)
    opinionContent.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '律师意见提交失败'
  } finally {
    saving.value = false
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

onMounted(loadAll)
</script>
