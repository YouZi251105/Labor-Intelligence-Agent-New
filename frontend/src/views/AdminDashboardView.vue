<template>
  <section class="content-page admin-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">平台管理</span>
        <h1>管理后台</h1>
        <p>管理用户、律师、案件、规则、材料和审计记录。</p>
      </div>
      <button class="secondary-action" type="button" @click="loadAll">刷新数据</button>
    </header>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <div class="metric-grid">
      <article><span>用户</span><strong>{{ stats.users }}</strong></article>
      <article><span>案件</span><strong>{{ stats.cases }}</strong></article>
      <article><span>证据</span><strong>{{ stats.evidence }}</strong></article>
      <article><span>文书</span><strong>{{ stats.documents }}</strong></article>
    </div>

    <nav class="tab-bar" aria-label="管理功能">
      <button
        v-for="tab in tabs"
        :key="tab"
        type="button"
        :class="{ active: activeTab === tab }"
        @click="activeTab = tab"
      >
        {{ tab }}
      </button>
    </nav>

    <div v-if="activeTab === '总览'" class="admin-grid">
      <section class="detail-card">
        <div class="detail-section-heading">
          <div><span class="eyebrow">案件分配</span><h2>案件与律师</h2></div>
        </div>
        <div class="assignment-list">
          <article v-for="item in cases" :key="item.id">
            <div class="assignment-list__main">
              <strong>#{{ item.id }} {{ item.title }}</strong>
              <span>{{ item.summary || item.facts }}</span>
            </div>
            <div class="assignment-list__actions">
              <select v-model="assignmentSelections[item.id]">
                <option :value="null">选择律师</option>
                <option v-for="lawyerItem in lawyers" :key="lawyerItem.id" :value="lawyerItem.id">
                  {{ lawyerItem.display_name }} · {{ lawyerItem.specialties }}
                </option>
              </select>
              <button
                class="primary-action primary-action--compact"
                type="button"
                :disabled="!assignmentSelections[item.id] || assigningId === item.id"
                @click="assignCase(item.id)"
              >
                {{ assigningId === item.id ? '分配中...' : '分配' }}
              </button>
              <button class="secondary-action" type="button" @click="router.push(`/cases/${item.id}`)">
                查看
              </button>
            </div>
          </article>
        </div>
      </section>

      <section class="detail-card">
        <div class="detail-section-heading">
          <div><span class="eyebrow">用户管理</span><h2>{{ users.length }} 个账号</h2></div>
        </div>
        <div class="user-admin-list">
          <article v-for="userItem in users" :key="userItem.id">
            <div class="user-admin-list__avatar">{{ userItem.username.slice(0, 1).toUpperCase() }}</div>
            <div>
              <strong>{{ userItem.display_name || userItem.username }}</strong>
              <span>{{ userItem.username }} · {{ roleLabels[userItem.role] }}</span>
            </div>
            <button type="button" class="table-action" @click="resetPassword(userItem)">重置密码</button>
          </article>
        </div>
      </section>

      <section class="detail-card detail-card--wide">
        <span class="eyebrow">匿名话题</span>
        <h2>{{ topics.total }} 个案件主题</h2>
        <div class="topic-stats">
          <article v-for="topic in topics.topics" :key="topic.dispute_type">
            <span>{{ topic.label }}</span>
            <strong>{{ topic.count }}</strong>
          </article>
        </div>
        <small>仅展示聚合纠纷类型，不展示用户原始咨询。</small>
      </section>
    </div>

    <section v-else-if="activeTab === '律师'" class="detail-card">
      <span class="eyebrow">律师审核</span>
      <h2>律师状态</h2>
      <div class="admin-table">
        <article v-for="lawyerItem in lawyers" :key="lawyerItem.id">
          <div>
            <strong>{{ lawyerItem.display_name }}</strong>
            <span>{{ lawyerItem.license_no }} · {{ lawyerItem.specialties }}</span>
          </div>
          <select v-model="lawyerStatuses[lawyerItem.id]">
            <option value="pending">待审核</option>
            <option value="active">正常</option>
            <option value="suspended">暂停</option>
          </select>
          <button type="button" @click="updateLawyerStatus(lawyerItem.id)">保存</button>
        </article>
      </div>
    </section>

    <section v-else-if="activeTab === '规则'" class="rule-admin-grid">
      <article v-for="rule in rules" :key="rule.id" class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">{{ disputeLabels[rule.dispute_type] }}</span>
            <h2>{{ rule.name }}</h2>
          </div>
          <span class="status-tag">{{ rule.review_status }}</span>
        </div>
        <p>证据要求：{{ rule.evidence_requirements.join('、') }}</p>
        <p>{{ rule.source_note }}</p>
        <select v-model="ruleReviews[rule.id].status">
          <option value="pending_review">待复核</option>
          <option value="approved">已通过</option>
          <option value="rejected">需修订</option>
        </select>
        <textarea v-model="ruleReviews[rule.id].note" rows="2" placeholder="复核说明" />
        <button class="primary-action primary-action--compact" type="button" @click="updateRule(rule)">
          保存复核
        </button>
      </article>
    </section>

    <section v-else-if="activeTab === '材料'" class="detail-card">
      <span class="eyebrow">材料管理</span>
      <h2>{{ materials.length }} 份材料</h2>
      <div class="admin-table">
        <article v-for="item in materials" :key="item.id">
          <div>
            <strong>{{ item.filename }}</strong>
            <span>案件 #{{ item.case_id }} · {{ categoryLabels[item.category] || item.category }}</span>
          </div>
          <span class="status-tag">{{ item.extraction_status }}</span>
          <small>{{ formatFileSize(item.file_size) }}</small>
        </article>
      </div>
    </section>

    <section v-else-if="activeTab === '审计'" class="detail-card">
      <span class="eyebrow">审计日志</span>
      <h2>最近操作</h2>
      <div class="audit-list">
        <article v-for="item in auditLogs" :key="item.id">
          <strong>{{ auditLabels[item.action] || item.action }}</strong>
          <span>{{ item.object_type }} #{{ item.object_id }}</span>
          <small>{{ new Date(item.created_at).toLocaleString('zh-CN') }}</small>
        </article>
      </div>
    </section>

    <section v-else-if="activeTab === '收益'" class="detail-grid">
      <div class="detail-card">
        <span class="eyebrow">服务记录</span>
        <h2>{{ serviceRecords.length }} 条</h2>
        <div class="ledger-list">
          <article v-for="record in serviceRecords" :key="record.id">
            <div>
              <strong>案件 #{{ record.case_id }} · {{ record.service_type }}</strong>
              <span>{{ record.summary }}</span>
            </div>
            <span class="status-tag">{{ record.status }}</span>
          </article>
        </div>
      </div>
      <div class="detail-card">
        <span class="eyebrow">收益台账</span>
        <h2>{{ revenueEntries.length }} 条</h2>
        <div class="ledger-list">
          <article v-for="entry in revenueEntries" :key="entry.id">
            <div>
              <strong>¥{{ (entry.amount_cents / 100).toFixed(2) }}</strong>
              <span>{{ entry.entry_type }} · {{ entry.note }}</span>
            </div>
            <div class="ledger-list__actions">
              <span class="status-tag">{{ entry.status }}</span>
              <button v-if="nextRevenueStatus(entry.status)" type="button" @click="advanceRevenue(entry)">
                {{ nextRevenueStatus(entry.status) }}
              </button>
            </div>
          </article>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiRequest } from '../api/http'
import type {
  AuditLogItem,
  CaseItem,
  MaterialSummary,
  RevenueLedger,
  RuleConfigItem,
  ServiceRecord,
  TopicsResponse,
  User,
} from '../types/api'
import { formatFileSize } from '../utils/format'

interface LawyerSummary {
  id: number
  username: string
  display_name: string
  license_no: string
  specialties: string
  status: string
}

const router = useRouter()
const activeTab = ref('总览')
const users = ref<User[]>([])
const lawyers = ref<LawyerSummary[]>([])
const cases = ref<CaseItem[]>([])
const rules = ref<RuleConfigItem[]>([])
const materials = ref<MaterialSummary[]>([])
const auditLogs = ref<AuditLogItem[]>([])
const serviceRecords = ref<ServiceRecord[]>([])
const revenueEntries = ref<RevenueLedger[]>([])
const topics = reactive<TopicsResponse>({ topics: [], total: 0 })
const stats = reactive({ users: 0, cases: 0, evidence: 0, documents: 0 })
const assignmentSelections = reactive<Record<number, number | null>>({})
const lawyerStatuses = reactive<Record<number, string>>({})
const ruleReviews = reactive<Record<number, { status: string; note: string }>>({})
const assigningId = ref<number | null>(null)
const error = ref('')

const tabs = ['总览', '律师', '规则', '材料', '审计', '收益']
const roleLabels: Record<string, string> = { user: '劳动者', lawyer: '律师', admin: '管理员' }
const disputeLabels: Record<string, string> = {
  wage: '欠薪',
  termination: '违法解除',
  contract: '未签劳动合同',
  overtime: '加班费',
  injury: '工伤待遇',
  service_pay: '劳务报酬',
}
const categoryLabels: Record<string, string> = {
  contract: '合同',
  chat: '聊天记录',
  payroll: '工资记录',
  attendance: '考勤',
  medical: '医疗',
  social_insurance: '社保',
  settlement: '结算',
  other: '其他',
}
const auditLabels: Record<string, string> = {
  'admin.rule_reviewed': '规则复核',
  'admin.lawyer_status_changed': '律师状态变更',
  'admin.revenue_status_changed': '收益状态变更',
  'case.assigned': '案件分配',
  'user.password_reset': '密码重置',
}

function nextRevenueStatus(status: string) {
  if (status === 'pending') return 'confirmed'
  if (status === 'confirmed') return 'paid'
  return ''
}

async function loadAll() {
  error.value = ''
  try {
    const [
      statsData,
      userData,
      lawyerData,
      caseData,
      ruleData,
      materialData,
      auditData,
      serviceData,
      revenueData,
      topicData,
    ] = await Promise.all([
      apiRequest<typeof stats>('/admin/stats'),
      apiRequest<User[]>('/admin/users'),
      apiRequest<LawyerSummary[]>('/admin/lawyers'),
      apiRequest<CaseItem[]>('/admin/cases'),
      apiRequest<RuleConfigItem[]>('/admin/rules'),
      apiRequest<MaterialSummary[]>('/admin/materials'),
      apiRequest<AuditLogItem[]>('/admin/audit-logs?limit=30'),
      apiRequest<ServiceRecord[]>('/admin/service-records'),
      apiRequest<RevenueLedger[]>('/admin/revenue'),
      apiRequest<TopicsResponse>('/analytics/topics'),
    ])
    Object.assign(stats, statsData)
    users.value = userData
    lawyers.value = lawyerData
    cases.value = caseData
    rules.value = ruleData
    materials.value = materialData
    auditLogs.value = auditData
    serviceRecords.value = serviceData
    revenueEntries.value = revenueData
    Object.assign(topics, topicData)
    for (const item of caseData) {
      assignmentSelections[item.id] = item.assigned_lawyer_id
    }
    for (const lawyer of lawyerData) {
      lawyerStatuses[lawyer.id] = lawyer.status
    }
    for (const rule of ruleData) {
      ruleReviews[rule.id] = {
        status: rule.review_status,
        note: rule.source_note,
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '管理数据加载失败'
  }
}

async function assignCase(caseId: number) {
  const lawyerId = assignmentSelections[caseId]
  if (!lawyerId) return
  assigningId.value = caseId
  try {
    const updated = await apiRequest<CaseItem>(`/admin/cases/${caseId}/assign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lawyer_id: lawyerId }),
    })
    const index = cases.value.findIndex((item) => item.id === caseId)
    if (index >= 0) cases.value[index] = updated
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件分配失败'
  } finally {
    assigningId.value = null
  }
}

async function resetPassword(userItem: User) {
  const newPassword = window.prompt(`为 ${userItem.username} 设置新密码（至少 8 位）`)
  if (!newPassword) return
  try {
    await apiRequest(`/admin/users/${userItem.id}/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPassword }),
    })
    window.alert('密码已重置')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '密码重置失败'
  }
}

async function updateLawyerStatus(userId: number) {
  try {
    const updated = await apiRequest<LawyerSummary>(`/admin/lawyers/${userId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: lawyerStatuses[userId] }),
    })
    const index = lawyers.value.findIndex((item) => item.id === userId)
    if (index >= 0) lawyers.value[index] = updated
  } catch (err) {
    error.value = err instanceof Error ? err.message : '律师状态更新失败'
  }
}

async function updateRule(rule: RuleConfigItem) {
  try {
    const updated = await apiRequest<RuleConfigItem>(`/admin/rules/${rule.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        review_status: ruleReviews[rule.id].status,
        source_note: ruleReviews[rule.id].note,
      }),
    })
    const index = rules.value.findIndex((item) => item.id === rule.id)
    if (index >= 0) rules.value[index] = updated
  } catch (err) {
    error.value = err instanceof Error ? err.message : '规则复核失败'
  }
}

async function advanceRevenue(entry: RevenueLedger) {
  const status = nextRevenueStatus(entry.status)
  if (!status) return
  try {
    const updated = await apiRequest<RevenueLedger>(`/admin/revenue/${entry.id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    const index = revenueEntries.value.findIndex((item) => item.id === entry.id)
    if (index >= 0) revenueEntries.value[index] = updated
  } catch (err) {
    error.value = err instanceof Error ? err.message : '收益状态更新失败'
  }
}

onMounted(loadAll)
</script>
