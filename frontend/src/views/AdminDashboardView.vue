<template>
  <section class="content-page admin-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">平台管理</span>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageDescription }}</p>
      </div>
      <button class="secondary-action" type="button" @click="loadCurrentSection">刷新数据</button>
    </header>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <div v-if="loading" class="admin-loading-skeleton" aria-label="管理数据加载中">
      <span />
      <span />
      <span />
    </div>

    <template v-else>
    <div v-if="activeTab === '总览'" class="dashboard-screen">
      <div class="metric-grid dashboard-metrics">
        <article>
          <span>平台用户</span>
          <strong>{{ stats.users }}</strong>
          <small>{{ stats.profile_completed_users }} 人已完善资料</small>
        </article>
        <article>
          <span>案件总量</span>
          <strong>{{ stats.cases }}</strong>
          <small>{{ stats.unassigned_cases }} 个待分配</small>
        </article>
        <article>
          <span>证据材料</span>
          <strong>{{ stats.evidence }}</strong>
          <small>材料访问全程留痕</small>
        </article>
        <article>
          <span>法律文书</span>
          <strong>{{ stats.documents }}</strong>
          <small>草稿与版本独立保存</small>
        </article>
        <article>
          <span>实名待核验</span>
          <strong>{{ stats.pending_verifications }}</strong>
          <small>进入用户管理处理</small>
        </article>
        <article>
          <span>律师待审核</span>
          <strong>{{ stats.pending_lawyers }}</strong>
          <small>{{ stats.lawyers }} 位律师已入驻</small>
        </article>
      </div>

      <AdminDashboardCharts v-if="dashboardData" :data="dashboardData" />

      <div class="dashboard-bottom-grid">
        <section class="detail-card">
          <div class="dashboard-card-heading">
            <div>
              <span class="eyebrow">运行提醒</span>
              <h2>待处理事项</h2>
            </div>
          </div>
          <div class="dashboard-alert-list">
            <article>
              <strong>{{ stats.pending_verifications }}</strong>
              <span>位劳动者的实名资料待核验</span>
              <RouterLink to="/admin/users">前往用户管理</RouterLink>
            </article>
            <article>
              <strong>{{ stats.pending_lawyers }}</strong>
              <span>位律师账号待审核</span>
              <RouterLink to="/admin/lawyers">前往律师管理</RouterLink>
            </article>
            <article>
              <strong>{{ stats.unassigned_cases }}</strong>
              <span>个案件尚未分配承办律师</span>
              <RouterLink to="/admin/cases">前往案件分配</RouterLink>
            </article>
          </div>
        </section>

        <section class="detail-card">
          <div class="dashboard-card-heading">
            <div>
              <span class="eyebrow">实时审计</span>
              <h2>最近操作</h2>
            </div>
            <RouterLink to="/admin/audit" class="text-link">查看全部</RouterLink>
          </div>
          <div class="audit-list dashboard-audit-list">
            <article v-for="item in dashboardData?.recent_actions ?? []" :key="item.id">
              <strong>{{ auditLabels[item.action] || item.action }}</strong>
              <span>{{ item.object_type }} #{{ item.object_id }}</span>
              <small>{{ new Date(item.created_at).toLocaleString('zh-CN') }}</small>
            </article>
            <p v-if="!dashboardData?.recent_actions?.length" class="muted-text">暂无操作记录。</p>
          </div>
        </section>
      </div>
    </div>

    <section v-else-if="activeTab === '用户'" class="detail-card">
      <div class="detail-section-heading">
        <div><span class="eyebrow">账号与权限</span><h2>用户管理</h2></div>
        <span class="status-tag">{{ userPage.total }} 个账号</span>
      </div>
      <div class="admin-filter-bar">
        <input
          v-model.trim="userSearch"
          type="search"
          placeholder="搜索用户名、姓名或手机号"
          @input="queueUserSearch"
        />
        <select v-model="userRoleFilter" @change="applyUserFilters">
          <option value="all">全部角色</option>
          <option value="user">劳动者</option>
          <option value="lawyer">律师</option>
          <option value="admin">管理员</option>
        </select>
        <select v-model="userStatusFilter" @change="applyUserFilters">
          <option value="all">全部状态</option>
          <option value="active">正常</option>
          <option value="inactive">已停用</option>
        </select>
      </div>
      <div class="admin-table user-management-table">
        <article v-for="userItem in users" :key="userItem.id" class="user-management-row">
          <div class="user-admin-list__avatar">{{ userItem.username.slice(0, 1).toUpperCase() }}</div>
          <div class="user-management-table__identity">
            <strong>{{ userItem.display_name || userItem.username }}</strong>
            <span>{{ userItem.username }} · {{ roleLabels[userItem.role] }}</span>
            <small>
              {{ userItem.phone || '未填写手机号' }} ·
              {{ verificationLabels[userItem.verification_status] }} ·
              {{ new Date(userItem.created_at).toLocaleDateString('zh-CN') }}
            </small>
          </div>
          <div class="user-management-table__status">
            <span class="status-tag" :class="{ 'status-tag--warning': !userItem.is_active }">
              {{ userItem.is_active ? '正常' : '已停用' }}
            </span>
            <span
              class="status-tag"
              :class="{ 'status-tag--success': userItem.verification_status === 'verified' }"
            >
              {{ verificationLabels[userItem.verification_status] }}
            </span>
          </div>
          <div class="user-management-table__actions">
            <button type="button" class="table-action" @click="toggleUserDetail(userItem)">
              {{ selectedUser?.id === userItem.id ? '收起' : '查看详情' }}
            </button>
            <button type="button" class="table-action" @click="resetPassword(userItem)">重置密码</button>
            <button
              type="button"
              class="table-action"
              :disabled="userItem.role === 'admin'"
              @click="updateUserStatus(userItem)"
            >
              {{ userItem.is_active ? '停用账号' : '恢复账号' }}
            </button>
          </div>
          <div v-if="selectedUser?.id === userItem.id" class="user-management-detail">
            <dl>
              <div><dt>用户编号</dt><dd>#{{ userItem.id }}</dd></div>
              <div><dt>实名姓名</dt><dd>{{ userItem.real_name || '未填写' }}</dd></div>
              <div><dt>手机号</dt><dd>{{ userItem.phone || '未填写' }}</dd></div>
              <div><dt>身份证号</dt><dd>{{ userItem.id_number_masked || '未提交' }}</dd></div>
            </dl>
            <div v-if="userItem.role === 'user'" class="verification-actions">
              <select v-model="verificationSelections[userItem.id]">
                <option value="unverified">未提交</option>
                <option value="pending">待核验</option>
                <option value="verified">已核验</option>
                <option value="rejected">需重新提交</option>
              </select>
              <button type="button" class="primary-action primary-action--compact" @click="updateVerification(userItem)">
                保存核验状态
              </button>
            </div>
          </div>
        </article>
        <p v-if="!users.length" class="muted-text">没有符合筛选条件的账号。</p>
      </div>
      <div class="pagination-bar">
        <button
          type="button"
          class="secondary-action primary-action--compact"
          :disabled="userPage.page <= 1 || usersLoading"
          @click="changeUserPage(userPage.page - 1)"
        >
          上一页
        </button>
        <span>第 {{ userPage.page }} 页 · 共 {{ userPage.total }} 个账号</span>
        <button
          type="button"
          class="secondary-action primary-action--compact"
          :disabled="!hasNextUserPage || usersLoading"
          @click="changeUserPage(userPage.page + 1)"
        >
          下一页
        </button>
      </div>
    </section>

    <section v-else-if="activeTab === '案件'" class="detail-card">
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

    <section v-else-if="activeTab === '律师'" class="detail-card">
      <div class="detail-section-heading">
        <div>
          <span class="eyebrow">律师审核</span>
          <h2>律师状态</h2>
        </div>
        <button
          type="button"
          class="primary-action primary-action--compact"
          @click="openLawyerCreate"
        >
          <UserPlus :size="16" />
          新增律师
        </button>
      </div>
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
        <p v-if="!lawyers.length" class="muted-text">还没有律师账号。</p>
      </div>

      <div
        v-if="lawyerCreateOpen"
        class="review-modal"
        @click.self="closeLawyerCreate"
      >
        <section
          class="review-modal__card lawyer-create-modal__card"
          role="dialog"
          aria-modal="true"
          aria-labelledby="lawyer-create-title"
        >
          <header class="review-modal__head">
            <div>
              <span class="eyebrow">平台律师入驻</span>
              <h3 id="lawyer-create-title">新增律师账号</h3>
            </div>
            <button
              type="button"
              class="icon-button"
              title="关闭"
              aria-label="关闭新增律师窗口"
              :disabled="lawyerCreating"
              @click="closeLawyerCreate"
            >
              <X :size="18" />
            </button>
          </header>
          <form class="lawyer-create-form" @submit.prevent="createLawyer">
            <div class="review-modal__body">
              <p v-if="lawyerCreateError" class="inline-error">{{ lawyerCreateError }}</p>
              <div class="form-grid lawyer-create-form__grid">
                <label>
                  <span>登录用户名</span>
                  <input
                    v-model.trim="lawyerCreateForm.username"
                    autocomplete="off"
                    minlength="3"
                    maxlength="64"
                    required
                  />
                </label>
                <label>
                  <span>初始密码</span>
                  <input
                    v-model="lawyerCreateForm.password"
                    type="password"
                    autocomplete="new-password"
                    minlength="8"
                    maxlength="128"
                    required
                  />
                </label>
                <label>
                  <span>律师姓名</span>
                  <input
                    v-model.trim="lawyerCreateForm.display_name"
                    autocomplete="name"
                    minlength="2"
                    maxlength="80"
                    required
                  />
                </label>
                <label>
                  <span>手机号</span>
                  <input
                    v-model.trim="lawyerCreateForm.phone"
                    inputmode="tel"
                    autocomplete="tel"
                    maxlength="32"
                  />
                </label>
                <label>
                  <span>执业证号</span>
                  <input
                    v-model.trim="lawyerCreateForm.license_no"
                    maxlength="80"
                    required
                  />
                </label>
                <label>
                  <span>专业方向</span>
                  <input
                    v-model.trim="lawyerCreateForm.specialties"
                    maxlength="500"
                    required
                  />
                </label>
                <label class="form-grid__wide">
                  <span>律师简介</span>
                  <textarea
                    v-model.trim="lawyerCreateForm.bio"
                    rows="3"
                    maxlength="2000"
                    placeholder="例如：擅长欠薪、违法解除和工伤待遇争议。"
                  />
                </label>
                <label>
                  <span>初始状态</span>
                  <select v-model="lawyerCreateForm.status">
                    <option value="active">正常</option>
                    <option value="pending">待审核</option>
                  </select>
                </label>
              </div>
              <p class="muted-text">
                初始密码只用于首次登录，请通过安全渠道交给律师。账号创建后可在列表中调整状态或重置密码。
              </p>
            </div>
            <footer class="review-modal__foot">
              <div class="form-actions lawyer-create-actions">
                <button
                  type="button"
                  class="secondary-action"
                  :disabled="lawyerCreating"
                  @click="closeLawyerCreate"
                >
                  取消
                </button>
                <button
                  type="submit"
                  class="primary-action primary-action--compact"
                  :disabled="lawyerCreating"
                >
                  <Plus :size="16" />
                  {{ lawyerCreating ? '创建中...' : '创建律师账号' }}
                </button>
              </div>
            </footer>
          </form>
        </section>
      </div>
    </section>

    <section v-else-if="activeTab === '规则'" class="rule-admin-grid">
      <article v-for="rule in rules" :key="rule.id" class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">{{ dictionary.disputeLabels[rule.dispute_type] }}</span>
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

    <RulePackageCenter v-else-if="activeTab === '规则包'" />

    <DictionaryAdminPanel v-else-if="activeTab === '字典'" />

    <section v-else-if="activeTab === '材料'" class="detail-card">
      <span class="eyebrow">材料管理</span>
      <h2>{{ materials.length }} 份材料</h2>
      <div class="admin-table">
        <article v-for="item in materials" :key="item.id">
          <div>
            <strong>{{ item.filename }}</strong>
            <span>案件 #{{ item.case_id }} · {{ dictionary.categoryLabels[item.category] || item.category }}</span>
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
    </template>
  </section>
</template>

<script setup lang="ts">
import { Plus, UserPlus, X } from '@lucide/vue'
import {
  computed,
  defineAsyncComponent,
  onBeforeUnmount,
  reactive,
  ref,
  watch,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { apiRequest } from '../api/http'
import { useDictionaryStore } from '../stores/dictionary'
import {
  confirmAction,
  notifySuccess,
  promptForPassword,
} from '../utils/dialogs'
import RulePackageCenter from '../components/RulePackageCenter.vue'
import DictionaryAdminPanel from '../components/DictionaryAdminPanel.vue'
import type {
  AdminDashboardData,
  AdminUserPage,
  AdminUserSummary,
  AuditLogItem,
  CaseItem,
  MaterialSummary,
  RevenueLedger,
  RuleConfigItem,
  ServiceRecord,
  User,
} from '../types/api'
import { formatFileSize } from '../utils/format'

const AdminDashboardCharts = defineAsyncComponent(
  () => import('../components/AdminDashboardCharts.vue'),
)

interface LawyerSummary {
  id: number
  username: string
  display_name: string
  license_no: string
  specialties: string
  status: string
}

interface CreateLawyerPayload {
  username: string
  password: string
  display_name: string
  phone: string
  license_no: string
  specialties: string
  bio: string
  status: 'pending' | 'active'
}

const route = useRoute()
const router = useRouter()
const sectionTabs: Record<string, string> = {
  overview: '总览',
  users: '用户',
  lawyers: '律师',
  cases: '案件',
  rules: '规则',
  packages: '规则包',
  dictionary: '字典',
  materials: '材料',
  audit: '审计',
  revenue: '收益',
}
const sectionTitles: Record<string, string> = {
  overview: '运营数据大屏',
  users: '用户管理',
  lawyers: '律师管理',
  cases: '案件分配',
  rules: '规则复核',
  packages: '规则包中心',
  dictionary: '字典管理',
  materials: '材料管理',
  audit: '审计日志',
  revenue: '收益管理',
}
const sectionDescriptions: Record<string, string> = {
  overview: '实时查看用户、案件、材料、文书和待办事项的整体运行情况。',
  users: '检索账号、核验实名资料并管理账号状态。',
  lawyers: '审核律师状态和平台服务能力。',
  cases: '查看待分配案件并指定承办律师。',
  rules: '复核证据规则和法律内容版本。',
  packages: '导入、编辑、校验、审核和发布版本化规则包。',
  dictionary: '维护纠纷分类、识别关键词、证据要求和文书请求，发布后立即全平台生效。',
  materials: '查看材料元数据和提取状态，不展示材料正文。',
  audit: '追踪平台关键操作和敏感数据访问。',
  revenue: '核对律师服务记录和收益流转。',
}
const activeTab = computed(
  () => sectionTabs[activeSection.value] ?? '总览',
)
const pageTitle = computed(() => sectionTitles[activeSection.value] ?? '运营数据大屏')
const pageDescription = computed(
  () => sectionDescriptions[activeSection.value] ?? sectionDescriptions.overview,
)
const activeSection = computed(() => {
  const value = String(route.params.section ?? 'overview')
  return value in sectionTabs ? value : 'overview'
})
const users = ref<AdminUserSummary[]>([])
const lawyers = ref<LawyerSummary[]>([])
const cases = ref<CaseItem[]>([])
const rules = ref<RuleConfigItem[]>([])
const materials = ref<MaterialSummary[]>([])
const auditLogs = ref<AuditLogItem[]>([])
const serviceRecords = ref<ServiceRecord[]>([])
const revenueEntries = ref<RevenueLedger[]>([])
const dashboardData = ref<AdminDashboardData | null>(null)
const stats = reactive({
  users: 0,
  cases: 0,
  evidence: 0,
  documents: 0,
  lawyers: 0,
  pending_lawyers: 0,
  unassigned_cases: 0,
  pending_verifications: 0,
  profile_completed_users: 0,
})
const userPage = reactive<AdminUserPage>({
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
})
const assignmentSelections = reactive<Record<number, number | null>>({})
const lawyerStatuses = reactive<Record<number, string>>({})
const ruleReviews = reactive<Record<number, { status: string; note: string }>>({})
const assigningId = ref<number | null>(null)
const error = ref('')
const loading = ref(false)
const usersLoading = ref(false)
const userSearch = ref('')
const userRoleFilter = ref('all')
const userStatusFilter = ref('all')
const selectedUser = ref<AdminUserSummary | null>(null)
const verificationSelections = reactive<Record<number, string>>({})
const lawyerCreateOpen = ref(false)
const lawyerCreating = ref(false)
const lawyerCreateError = ref('')
const lawyerCreateForm = reactive<CreateLawyerPayload>({
  username: '',
  password: '',
  display_name: '',
  phone: '',
  license_no: '',
  specialties: '劳动纠纷',
  bio: '',
  status: 'active',
})
let userSearchTimer: ReturnType<typeof setTimeout> | null = null

const roleLabels: Record<string, string> = { user: '劳动者', lawyer: '律师', admin: '管理员' }
const verificationLabels: Record<string, string> = {
  unverified: '未提交',
  pending: '待核验',
  verified: '已核验',
  rejected: '需重新提交',
}
const dictionary = useDictionaryStore()
void dictionary.load()
const auditLabels: Record<string, string> = {
  'admin.rule_reviewed': '规则复核',
  'admin.rule_package_imported': '规则包导入',
  'admin.rule_package_updated': '规则包编辑',
  'admin.rule_package_submitted': '规则包送审',
  'admin.rule_package_reviewed': '规则包审核',
  'admin.rule_package_published': '规则包发布',
  'admin.rule_package_retired': '规则包停用',
  'admin.dictionary_version_created': '字典草稿创建',
  'admin.dictionary_version_updated': '字典草稿编辑',
  'admin.dictionary_version_published': '字典版本发布',
  'admin.dictionary_version_deleted': '字典草稿删除',
  'admin.lawyer_created': '律师账号创建',
  'admin.lawyer_status_changed': '律师状态变更',
  'admin.revenue_status_changed': '收益状态变更',
  'admin.user_status_changed': '账号状态变更',
  'case.assigned': '案件分配',
  'user.password_reset': '密码重置',
}

const hasNextUserPage = computed(
  () => userPage.page * userPage.page_size < userPage.total,
)

function nextRevenueStatus(status: string) {
  if (status === 'pending') return 'confirmed'
  if (status === 'confirmed') return 'paid'
  return ''
}

async function loadLawyers() {
  lawyers.value = await apiRequest<LawyerSummary[]>('/admin/lawyers')
  for (const lawyer of lawyers.value) {
    lawyerStatuses[lawyer.id] = lawyer.status
  }
}

async function loadCases() {
  const [caseData] = await Promise.all([
    apiRequest<CaseItem[]>('/admin/cases'),
    loadLawyers(),
  ])
  cases.value = caseData
  for (const item of caseData) {
    assignmentSelections[item.id] = item.assigned_lawyer_id
  }
}

async function loadRules() {
  rules.value = await apiRequest<RuleConfigItem[]>('/admin/rules')
  for (const rule of rules.value) {
    ruleReviews[rule.id] = {
      status: rule.review_status,
      note: rule.source_note,
    }
  }
}

async function loadRevenue() {
  const [serviceData, revenueData] = await Promise.all([
    apiRequest<ServiceRecord[]>('/admin/service-records'),
    apiRequest<RevenueLedger[]>('/admin/revenue'),
  ])
  serviceRecords.value = serviceData
  revenueEntries.value = revenueData
}

async function loadSection(section: string) {
  error.value = ''
  try {
    if (section === 'overview') {
      const data = await apiRequest<AdminDashboardData>('/admin/dashboard')
      dashboardData.value = data
      Object.assign(stats, data.totals)
      return
    }
    if (section === 'users') {
      await fetchUsers()
      return
    }
    if (section === 'lawyers') {
      await loadLawyers()
      return
    }
    if (section === 'cases') {
      await loadCases()
      return
    }
    if (section === 'rules') {
      await loadRules()
      return
    }
    if (section === 'packages') {
      return
    }
    if (section === 'materials') {
      materials.value = await apiRequest<MaterialSummary[]>('/admin/materials')
      return
    }
    if (section === 'audit') {
      auditLogs.value = await apiRequest<AuditLogItem[]>(
        '/admin/audit-logs?limit=30',
      )
      return
    }
    if (section === 'revenue') {
      await loadRevenue()
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '管理数据加载失败'
  }
}

async function loadCurrentSection() {
  loading.value = true
  try {
    await loadSection(activeSection.value)
  } finally {
    loading.value = false
  }
}

async function fetchUsers() {
  usersLoading.value = true
  try {
    const params = new URLSearchParams({
      page: String(userPage.page),
      page_size: String(userPage.page_size),
    })
    if (userSearch.value) params.set('q', userSearch.value)
    if (userRoleFilter.value !== 'all') params.set('role', userRoleFilter.value)
    if (userStatusFilter.value !== 'all') {
      params.set('status', userStatusFilter.value)
    }
    const response = await apiRequest<AdminUserPage>(
      `/admin/users/manage?${params.toString()}`,
    )
    users.value = response.items
    Object.assign(userPage, response)
    for (const userItem of response.items) {
      verificationSelections[userItem.id] = userItem.verification_status
    }
    if (
      selectedUser.value &&
      !response.items.some((item) => item.id === selectedUser.value?.id)
    ) {
      selectedUser.value = null
    }
  } finally {
    usersLoading.value = false
  }
}

function queueUserSearch() {
  if (userSearchTimer) clearTimeout(userSearchTimer)
  userSearchTimer = setTimeout(() => {
    userPage.page = 1
    void fetchUsers().catch((err: unknown) => {
      error.value = err instanceof Error ? err.message : '用户搜索失败'
    })
  }, 300)
}

function applyUserFilters() {
  userPage.page = 1
  void fetchUsers().catch((err: unknown) => {
    error.value = err instanceof Error ? err.message : '用户筛选失败'
  })
}

function changeUserPage(page: number) {
  userPage.page = page
  void fetchUsers().catch((err: unknown) => {
    error.value = err instanceof Error ? err.message : '用户分页加载失败'
  })
}

function toggleUserDetail(userItem: AdminUserSummary) {
  selectedUser.value = selectedUser.value?.id === userItem.id ? null : userItem
  verificationSelections[userItem.id] = userItem.verification_status
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

async function resetPassword(userItem: AdminUserSummary) {
  const newPassword = await promptForPassword(
    `为 ${userItem.username} 设置新密码`,
  )
  if (!newPassword) return
  try {
    await apiRequest(`/admin/users/${userItem.id}/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPassword }),
    })
    notifySuccess('密码已重置')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '密码重置失败'
  }
}

async function updateUserStatus(userItem: AdminUserSummary) {
  const nextStatus = !userItem.is_active
  const actionLabel = nextStatus ? '恢复' : '停用'
  const confirmed = await confirmAction(
    `确认${actionLabel}账号 ${userItem.username} 吗？`,
    {
      title: `${actionLabel}账号`,
      confirmText: actionLabel,
      danger: !nextStatus,
    },
  )
  if (!confirmed) return
  try {
    const updated = await apiRequest<User>(`/admin/users/${userItem.id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: nextStatus }),
    })
    userItem.is_active = updated.is_active
    notifySuccess(`账号已${actionLabel}`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '账号状态更新失败'
  }
}

async function updateVerification(userItem: AdminUserSummary) {
  try {
    const status = verificationSelections[userItem.id]
    const updated = await apiRequest<{ verification_status: AdminUserSummary['verification_status'] }>(
      `/admin/users/${userItem.id}/verification`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verification_status: status }),
      },
    )
    userItem.verification_status = updated.verification_status
    verificationSelections[userItem.id] = updated.verification_status
    if (selectedUser.value?.id === userItem.id) {
      selectedUser.value = userItem
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '实名核验状态更新失败'
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

function openLawyerCreate() {
  lawyerCreateError.value = ''
  Object.assign(lawyerCreateForm, {
    username: '',
    password: '',
    display_name: '',
    phone: '',
    license_no: '',
    specialties: '劳动纠纷',
    bio: '',
    status: 'active',
  })
  lawyerCreateOpen.value = true
}

function closeLawyerCreate() {
  if (lawyerCreating.value) return
  lawyerCreateOpen.value = false
  lawyerCreateError.value = ''
}

async function createLawyer() {
  lawyerCreating.value = true
  lawyerCreateError.value = ''
  try {
    const created = await apiRequest<LawyerSummary>('/admin/lawyers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lawyerCreateForm),
    })
    lawyerCreateOpen.value = false
    lawyerCreateForm.password = ''
    await loadLawyers()
    notifySuccess(`律师账号 ${created.username} 已创建`)
  } catch (err) {
    lawyerCreateError.value =
      err instanceof Error ? err.message : '律师账号创建失败'
  } finally {
    lawyerCreating.value = false
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

watch(
  activeSection,
  () => {
    void loadCurrentSection()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (userSearchTimer) clearTimeout(userSearchTimer)
})
</script>
