<template>
  <section class="content-page admin-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">平台管理</span>
        <h1>管理后台</h1>
        <p>管理用户、律师和案件分配，查看演示业务数据。</p>
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

    <div class="admin-grid">
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
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiRequest } from '../api/http'
import type { CaseItem, User } from '../types/api'

interface LawyerSummary {
  id: number
  username: string
  display_name: string
  license_no: string
  specialties: string
  status: string
}

const router = useRouter()
const users = ref<User[]>([])
const lawyers = ref<LawyerSummary[]>([])
const cases = ref<CaseItem[]>([])
const stats = reactive({ users: 0, cases: 0, evidence: 0, documents: 0 })
const assignmentSelections = reactive<Record<number, number | null>>({})
const assigningId = ref<number | null>(null)
const error = ref('')
const roleLabels: Record<string, string> = {
  user: '劳动者',
  lawyer: '律师',
  admin: '管理员',
}

async function loadAll() {
  error.value = ''
  try {
    const [statsData, userData, lawyerData, caseData] = await Promise.all([
      apiRequest<typeof stats>('/admin/stats'),
      apiRequest<User[]>('/admin/users'),
      apiRequest<LawyerSummary[]>('/admin/lawyers'),
      apiRequest<CaseItem[]>('/admin/cases'),
    ])
    Object.assign(stats, statsData)
    users.value = userData
    lawyers.value = lawyerData
    cases.value = caseData
    for (const item of caseData) {
      assignmentSelections[item.id] = item.assigned_lawyer_id
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

onMounted(loadAll)
</script>
