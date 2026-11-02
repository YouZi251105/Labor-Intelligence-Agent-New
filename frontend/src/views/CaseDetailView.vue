<template>
  <section v-if="caseItem" class="content-page case-detail-page">
    <header class="case-detail-header">
      <button class="back-button" type="button" @click="router.push('/cases')">
        <ArrowLeft :size="18" />
      </button>
      <div class="case-detail-header__main">
        <span class="eyebrow">案件 #{{ caseItem.id }}</span>
        <h1>{{ caseItem.title }}</h1>
        <div class="tag-row">
          <span class="status-tag">{{ disputeLabels[caseItem.dispute_type] || '待识别' }}</span>
          <span class="status-tag">{{ stageLabels[caseItem.stage] || caseItem.stage }}</span>
          <span class="status-tag">
            {{ caseItem.legal_relationship === 'service' ? '劳务关系' : '劳动关系' }}
          </span>
          <span v-if="caseItem.assigned_lawyer_id" class="status-tag status-tag--success">
            已分配律师
          </span>
        </div>
      </div>
      <button class="secondary-action" type="button" @click="router.push('/')">继续 AI 咨询</button>
    </header>

    <nav class="tab-bar" aria-label="案件功能">
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

    <section v-if="activeTab === 'overview'">
      <div v-if="workflow" class="detail-card workflow-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">案件流程</span>
            <h2>{{ workflowLabel }}</h2>
          </div>
          <span
            class="status-tag"
            :class="{ 'status-tag--warning': workflow.rule_package.review_status === 'pending_review' }"
          >
            {{ workflowReviewLabel }}
          </span>
        </div>
        <ol class="workflow-steps">
          <li
            v-for="stage in workflow.stages"
            :key="stage.stage"
            :class="`workflow-step workflow-step--${stage.status}`"
          >
            <span class="workflow-step__dot" />
            <div class="workflow-step__body">
              <strong>{{ stage.label }}</strong>
              <small v-if="stage.required_actions.length">
                待办：{{ stage.required_actions.join('、') }}
              </small>
            </div>
          </li>
        </ol>
        <div v-if="workflow.options.length" class="workflow-options">
          <article
            v-for="option in workflow.options"
            :key="option.id"
            class="workflow-option"
            :class="{ 'workflow-option--blocked': !option.enabled }"
          >
            <div class="workflow-option__heading">
              <strong>{{ option.label }}</strong>
              <span v-if="option.deadlines.some((item) => item.review_status === 'pending_review')">
                含待复核期限
              </span>
            </div>
            <p>{{ option.description }}</p>
            <dl class="workflow-option__details">
              <div>
                <dt>选择后</dt>
                <dd>{{ option.outcome }}</dd>
              </div>
              <div>
                <dt>下一步</dt>
                <dd>{{ option.next_step }}</dd>
              </div>
            </dl>
            <div v-if="option.deadlines.length" class="workflow-deadlines">
              <article v-for="deadline in option.deadlines" :key="deadline.id">
                <strong>{{ deadline.title }}</strong>
                <p>{{ deadline.description }}</p>
                <small v-if="deadline.due_at">
                  建议截止：{{ new Date(deadline.due_at).toLocaleDateString('zh-CN') }}
                </small>
                <small v-else>期限规则{{ reviewStatusLabel(deadline.review_status) }}</small>
              </article>
            </div>
            <p
              v-if="!option.enabled"
              class="workflow-option__reason workflow-option__reason--blocked"
            >
              {{ option.blocked_reasons.join('；') }}
            </p>
            <button
              class="secondary-action workflow-option__action"
              type="button"
              :disabled="!option.enabled || transitioningTarget === option.id"
              @click="transitionTo(option)"
            >
              {{ transitioningTarget === option.id ? '处理中...' : option.label }}
            </button>
          </article>
        </div>
        <small class="workflow-disclaimer">{{ workflow.rule_package.disclaimer }}</small>
      </div>

      <div class="detail-grid">
        <div class="detail-card">
          <span class="eyebrow">案件事实</span>
          <p class="pre-line">{{ caseItem.facts || '暂无案件事实' }}</p>
        </div>
        <div class="detail-card">
          <span class="eyebrow">当前建议</span>
          <p>{{ suggestedNextStep || '继续补充咨询信息，系统会更新案件建议。' }}</p>
          <dl class="meta-list">
            <div><dt>用工地点</dt><dd>{{ caseItem.location || '待补充' }}</dd></div>
            <div><dt>更新时间</dt><dd>{{ new Date(caseItem.updated_at).toLocaleString('zh-CN') }}</dd></div>
            <div><dt>承办律师</dt><dd>{{ caseItem.assigned_lawyer_id ? '已分配' : '尚未分配' }}</dd></div>
          </dl>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'chat'" class="detail-card detail-card--wide">
      <div class="detail-section-heading">
        <div>
          <span class="eyebrow">咨询记录</span>
          <h2>多轮案件咨询</h2>
        </div>
        <span class="status-tag">{{ messages.length }} 条消息</span>
      </div>
      <div class="case-chat-list">
        <article
          v-for="message in messages"
          :key="message.id"
          class="chat-message"
          :class="`chat-message--${message.role}`"
        >
          <span class="chat-message__role">{{ message.role === 'user' ? '你' : '劳务通' }}</span>
          <SafeMarkdown :content="message.content" />
        </article>
        <p v-if="!messages.length" class="muted-text">还没有咨询记录。</p>
      </div>
      <form class="chat-compose-inline" @submit.prevent="sendChat">
        <textarea v-model="chatInput" rows="3" placeholder="继续补充事实，系统会带上当前案件上下文。" />
        <button class="primary-action primary-action--compact" type="submit" :disabled="chatSending">
          {{ chatSending ? '发送中...' : '发送' }}
        </button>
      </form>
    </section>

    <section v-else-if="activeTab === 'evidence'" class="detail-grid">
      <div class="detail-card">
        <span class="eyebrow">材料上传</span>
        <h2>证据整理</h2>
        <p>演示版支持图片、PDF、TXT、DOC 和 DOCX，单文件不超过 20MB。</p>
        <label class="upload-zone">
          <Upload :size="24" />
          <strong>{{ uploading ? '正在上传...' : '选择证据材料' }}</strong>
          <span>上传后会自动分类并生成材料缺口提示</span>
          <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf,.txt,.doc,.docx" @change="uploadEvidence" />
        </label>

        <div v-if="evidenceRulesAssessment" class="rules-assessment">
          <div class="detail-section-heading">
            <div>
              <span class="eyebrow">证据四性评估</span>
              <h2>材料评估</h2>
            </div>
          </div>
          <div
            class="dimension-card"
            :class="`dimension--${evidenceRulesAssessment.completeness.status === 'ready' ? 'ok' : 'warning'}`"
          >
            <strong>完整性</strong>
            <span>
              {{ evidenceRulesAssessment.completeness.status === 'ready' ? '材料类别已覆盖' : '仍有缺口' }}
            </span>
            <p v-if="evidenceRulesAssessment.completeness.missing_labels.length">
              缺少：{{ evidenceRulesAssessment.completeness.missing_labels.join('、') }}
            </p>
            <p v-if="evidenceRulesAssessment.completeness.present_categories.length">
              已有：{{
                evidenceRulesAssessment.completeness.present_categories
                  .map((item) => categoryLabels[item] || item)
                  .join('、')
              }}
            </p>
          </div>
          <div
            v-for="dim in dimensions"
            :key="dim.key"
            class="dimension-card"
            :class="`dimension--${dim.status}`"
          >
            <strong>{{ dim.label }}</strong>
            <span>{{ dimStatusLabel(dim.status) }}</span>
            <p v-for="finding in dim.findings" :key="finding.message">{{ finding.message }}</p>
          </div>
          <small class="muted-text">{{ evidenceRulesAssessment.disclaimer }}</small>
        </div>
      </div>
      <div class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">材料列表</span>
            <h2>{{ evidenceItems.length }} 份材料</h2>
          </div>
        </div>
        <div class="evidence-list">
          <article v-for="item in evidenceItems" :key="item.id">
            <FileText :size="19" />
            <div class="evidence-list__main">
              <strong>{{ item.filename }}</strong>
              <span>{{ categoryLabels[item.category] || item.category }} · {{ formatFileSize(item.file_size) }}</span>
              <small class="evidence-list__time">上传于 {{ new Date(item.created_at).toLocaleString('zh-CN') }}</small>
              <small v-if="item.text_preview" class="evidence-list__preview">{{ item.text_preview }}</small>
            </div>
            <div class="evidence-list__side">
              <span class="status-tag" :class="`extract-${item.extraction_status}`">
                {{ extractionStatusLabels[item.extraction_status] || item.extraction_status }}
              </span>
              <div class="row-actions">
                <button type="button" @click="previewEvidence(item)">查看</button>
                <button type="button" :disabled="extractingId === item.id" @click="extractEvidence(item)">
                  {{ extractingId === item.id ? '提取中...' : '重新提取' }}
                </button>
                <button type="button" @click="downloadEvidence(item)">下载</button>
                <button
                  type="button"
                  class="row-actions__danger"
                  :disabled="deletingId === item.id"
                  @click="deleteEvidence(item)"
                >
                  {{ deletingId === item.id ? '删除中...' : '删除' }}
                </button>
              </div>
            </div>
          </article>
          <p v-if="!evidenceItems.length" class="muted-text">还没有上传材料。</p>
        </div>
      </div>

      <div v-if="preview" class="preview-modal" @click.self="closePreview">
        <div class="preview-modal__body">
          <img v-if="preview.isImage" :src="preview.url" :alt="preview.filename" />
          <pre v-else class="preview-modal__text">{{ preview.text }}</pre>
          <button type="button" class="preview-modal__close" @click="closePreview">关闭</button>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'contract'" class="detail-grid">
      <div class="detail-card">
        <span class="eyebrow">合同审查</span>
        <h2>粘贴合同内容</h2>
        <p>演示版基于文本规则识别明显风险，不构成合同真实性或法律效力结论。</p>
        <textarea
          v-model="contractText"
          class="large-textarea"
          rows="10"
          placeholder="粘贴合同条款，例如工资、工作时间、解除条件和社会保险约定……"
        />
        <button class="primary-action primary-action--compact" type="button" :disabled="reviewing" @click="reviewContract">
          {{ reviewing ? '审查中...' : '开始审查' }}
        </button>
        <div v-if="contractReview" class="review-result">
          <span class="status-tag" :class="`risk-${contractReview.risk_level}`">
            风险等级：{{ riskLabels[contractReview.risk_level] }}
          </span>
          <article v-for="finding in contractReview.findings" :key="finding.title">
            <strong>{{ finding.title }}</strong>
            <p>{{ finding.detail }}</p>
          </article>
          <p v-if="contractReview.missing_items.length">
            建议补充：{{ contractReview.missing_items.join('、') }}
          </p>
          <small>{{ contractReview.disclaimer }}</small>
        </div>
      </div>
      <div class="detail-card">
        <span class="eyebrow">文件审查</span>
        <h2>上传合同文件</h2>
        <p>支持 TXT、PDF、DOCX 和图片，系统会先提取文本再审查。</p>
        <label class="upload-zone">
          <Upload :size="24" />
          <strong>{{ reviewingFile ? '正在审查...' : '选择合同文件' }}</strong>
          <span>上传后自动提取文本并做风险提示</span>
          <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf,.txt,.doc,.docx" @change="reviewContractFile" />
        </label>
        <div v-if="contractFileReview" class="review-result">
          <span class="status-tag" :class="`extract-${contractFileReview.extraction_status}`">
            {{ extractionStatusLabels[contractFileReview.extraction_status] || contractFileReview.extraction_status }}
          </span>
          <span class="status-tag" :class="`risk-${contractFileReview.review.risk_level}`">
            风险等级：{{ riskLabels[contractFileReview.review.risk_level] }}
          </span>
          <article v-for="finding in contractFileReview.review.findings" :key="finding.title">
            <strong>{{ finding.title }}</strong>
            <p>{{ finding.detail }}</p>
          </article>
          <p v-if="contractFileReview.review.missing_items.length">
            建议补充：{{ contractFileReview.review.missing_items.join('、') }}
          </p>
          <small>{{ contractFileReview.review.disclaimer }}</small>
        </div>
        <div class="manual-review-entry">
          <ShieldCheck :size="16" />
          <span>风险判断需要专业复核？</span>
          <RouterLink to="/help" class="text-link">申请人工复核</RouterLink>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'documents'" class="detail-grid">
      <div class="detail-card">
        <span class="eyebrow">文书生成</span>
        <h2>生成案件草稿</h2>
        <p>系统会根据已确认的案件事实和证据目录生成文本草稿。</p>
        <div class="document-actions">
          <button
            v-for="option in documentOptions"
            :key="option.type"
            class="secondary-action"
            type="button"
            :disabled="generatingDocument === option.type"
            @click="generateDocument(option.type)"
          >
            <FilePlus2 :size="17" />
            {{ option.label }}
          </button>
        </div>
      </div>
      <div class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">草稿列表</span>
            <h2>{{ documents.length }} 份文书</h2>
          </div>
        </div>
        <div class="document-list">
          <article v-for="document in documents" :key="document.id">
            <div>
              <strong>{{ document.title }}</strong>
              <span>版本 {{ document.version }} · {{ new Date(document.created_at).toLocaleString('zh-CN') }}</span>
              <small v-if="document.evidence.length">引用 {{ document.evidence.length }} 份证据</small>
            </div>
            <div class="row-actions">
              <button type="button" @click="selectedDocument = document">预览</button>
              <button type="button" @click="startEditDocument(document)">编辑</button>
              <button type="button" :disabled="exportingFormat !== ''" @click="exportDocument(document, 'docx')">DOCX</button>
              <button type="button" :disabled="exportingFormat !== ''" @click="exportDocument(document, 'pdf')">PDF</button>
              <button type="button" @click="downloadDocument(document)">TXT</button>
            </div>
          </article>
          <p v-if="!documents.length" class="muted-text">还没有生成文书。</p>
        </div>
      </div>
      <div v-if="editingDocument" class="detail-card detail-card--wide">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">编辑文书</span>
            <h2>保存为新版本</h2>
          </div>
        </div>
        <div class="form-grid">
          <div class="form-grid__wide">
            <label>
              标题
              <input v-model="editTitle" />
            </label>
          </div>
          <div class="form-grid__wide">
            <label>
              内容
              <textarea v-model="editContent" rows="12" />
            </label>
          </div>
        </div>
        <div class="form-actions">
          <button class="primary-action primary-action--compact" type="button" :disabled="savingRevision" @click="saveRevision">
            {{ savingRevision ? '保存中...' : '保存为新版本' }}
          </button>
          <button class="secondary-action" type="button" @click="editingDocument = null">取消</button>
        </div>
      </div>
      <div v-if="selectedDocument" class="detail-card detail-card--wide">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">文书预览</span>
            <h2>{{ selectedDocument.title }}</h2>
          </div>
          <button class="secondary-action" type="button" @click="selectedDocument = null">关闭</button>
        </div>
        <SafeMarkdown class="document-preview" :content="selectedDocument.content" />
      </div>
    </section>
  </section>

  <div v-else class="loading-block"><span class="spinner-dot" /> 正在加载案件...</div>
</template>

<script setup lang="ts">
import {
  ArrowLeft,
  Clock3,
  FilePlus2,
  FileText,
  MessageSquareText,
  Scale,
  ShieldCheck,
  Upload,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { API_BASE_URL, apiRequest, TOKEN_KEY } from '../api/http'
import SafeMarkdown from '../components/SafeMarkdown.vue'
import type {
  CaseItem,
  ConsultationResponse,
  ContractFileReviewResponse,
  ContractReviewResponse,
  DocumentItem,
  EvidenceAssessmentResponse,
  EvidenceExtractionResponse,
  EvidenceItem,
  EvidenceResponse,
  MessageItem,
  WorkflowOption,
  WorkflowResponse,
} from '../types/api'
import { formatFileSize } from '../utils/format'

const route = useRoute()
const router = useRouter()
const caseId = Number(route.params.id)
const caseItem = ref<CaseItem | null>(null)
const messages = ref<MessageItem[]>([])
const evidenceItems = ref<EvidenceItem[]>([])
const evidenceAssessment = ref<EvidenceResponse['assessment'] | null>(null)
const documents = ref<DocumentItem[]>([])
const activeTab = ref('overview')
const error = ref('')
const suggestedNextStep = ref('')
const chatInput = ref('')
const chatSending = ref(false)
const uploading = ref(false)
const contractText = ref('')
const reviewing = ref(false)
const contractReview = ref<ContractReviewResponse | null>(null)
const generatingDocument = ref('')
const selectedDocument = ref<DocumentItem | null>(null)
const workflow = ref<WorkflowResponse | null>(null)
const transitioningTarget = ref('')
const evidenceRulesAssessment = ref<EvidenceAssessmentResponse | null>(null)
const extractingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)
const preview = ref<{ filename: string; isImage: boolean; url: string; text: string } | null>(null)
const contractFileReview = ref<ContractFileReviewResponse | null>(null)
const reviewingFile = ref(false)
const editingDocument = ref<DocumentItem | null>(null)
const editTitle = ref('')
const editContent = ref('')
const savingRevision = ref(false)
const exportingFormat = ref('')

const tabs = [
  { key: 'overview', label: '案件概览', icon: Scale },
  { key: 'chat', label: '咨询记录', icon: MessageSquareText },
  { key: 'evidence', label: '证据材料', icon: Upload },
  { key: 'contract', label: '合同审查', icon: FileText },
  { key: 'documents', label: '法律文书', icon: FilePlus2 },
]
const disputeLabels: Record<string, string> = {
  wage: '欠薪',
  termination: '违法解除',
  contract: '劳动合同',
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
const categoryLabels: Record<string, string> = {
  contract: '合同',
  chat: '聊天记录',
  payroll: '工资记录',
  attendance: '考勤',
  medical: '医疗材料',
  social_insurance: '社保材料',
  settlement: '结算单',
  other: '其他',
}
const documentOptions = [
  { type: 'settlement', label: '协商和解协议' },
  { type: 'arbitration', label: '劳动仲裁申请书' },
  { type: 'complaint', label: '民事起诉状' },
] as const
const riskLabels = { low: '低', medium: '中', high: '高' }

const extractionStatusLabels: Record<string, string> = {
  pending: '待提取',
  extracted: '已提取',
  ocr_required: '待 OCR',
  unsupported: '不支持',
  failed: '提取失败',
}

function dimStatusLabel(status: string) {
  if (status === 'ok') return '正常'
  if (status === 'warning') return '需关注'
  if (status === 'issue') return '需复核'
  return status
}

const latestClassification = computed(() => caseItem.value?.classification ?? {})

const dimensions = computed(() => {
  const rules = evidenceRulesAssessment.value
  if (!rules) return []
  return [
    {
      key: 'legality',
      label: '合法性（形式）',
      status: rules.legality.status,
      findings: rules.legality.findings,
    },
    {
      key: 'relevance',
      label: '关联性',
      status: rules.relevance.status,
      findings: rules.relevance.findings,
    },
    {
      key: 'sufficiency',
      label: '充分性',
      status: rules.sufficiency.status,
      findings: rules.sufficiency.findings,
    },
  ]
})

const workflowLabel = computed(() => {
  if (!workflow.value) return '案件流程'
  const current = workflow.value.stages.find(
    (item) => item.stage === workflow.value?.current_stage,
  )
  return current?.label ?? '案件流程'
})

const workflowReviewLabel = computed(() => {
  const status = workflow.value?.rule_package.review_status
  return status === 'pending_review' ? '规则待复核' : reviewStatusLabel(status ?? '')
})

function reviewStatusLabel(status: string) {
  const labels: Record<string, string> = {
    draft: '草稿',
    pending_review: '待复核',
    approved: '已批准',
    published: '已发布',
    retired: '已停用',
    rejected: '已驳回',
  }
  return labels[status] ?? status
}

async function loadAll() {
  try {
    const [caseData, messageData, evidenceData, documentData, workflowData, rulesAssessment] =
      await Promise.all([
        apiRequest<CaseItem>(`/cases/${caseId}`),
        apiRequest<MessageItem[]>(`/cases/${caseId}/messages`),
        apiRequest<EvidenceResponse>(`/cases/${caseId}/evidence`),
        apiRequest<DocumentItem[]>(`/cases/${caseId}/documents`),
        apiRequest<WorkflowResponse>(`/cases/${caseId}/workflow`),
        apiRequest<EvidenceAssessmentResponse>(`/cases/${caseId}/evidence-assessment`),
      ])
    caseItem.value = caseData
    messages.value = messageData
    evidenceItems.value = evidenceData.items
    evidenceAssessment.value = evidenceData.assessment
    documents.value = documentData
    workflow.value = workflowData
    evidenceRulesAssessment.value = rulesAssessment
    suggestedNextStep.value = String(
      messageData.at(-1)?.metadata_json?.suggested_next_step ??
        caseItem.value.classification.suggested_next_step ??
        '',
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件加载失败'
  }
}

async function transitionTo(option: WorkflowOption) {
  if (!caseItem.value) return
  transitioningTarget.value = option.id
  error.value = ''
  try {
    workflow.value = await apiRequest<WorkflowResponse>(`/cases/${caseId}/transitions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ option_id: option.id }),
    })
    caseItem.value = {
      ...caseItem.value,
      stage: workflow.value.current_stage,
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件阶段推进失败'
  } finally {
    transitioningTarget.value = ''
  }
}

async function sendChat() {
  const text = chatInput.value.trim()
  if (!text) return
  chatSending.value = true
  try {
    const response = await apiRequest<ConsultationResponse>(`/cases/${caseId}/consultations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    })
    messages.value.push(response.user_message, response.assistant_message)
    caseItem.value = response.case
    suggestedNextStep.value = response.suggested_next_step
    workflow.value = await apiRequest<WorkflowResponse>(`/cases/${caseId}/workflow`)
    chatInput.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发送失败'
  } finally {
    chatSending.value = false
  }
}

async function uploadEvidence(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    await apiRequest<EvidenceItem>(`/cases/${caseId}/evidence`, {
      method: 'POST',
      body,
    })
    const evidenceData = await apiRequest<EvidenceResponse>(`/cases/${caseId}/evidence`)
    evidenceItems.value = evidenceData.items
    evidenceAssessment.value = evidenceData.assessment
    evidenceRulesAssessment.value = await apiRequest<EvidenceAssessmentResponse>(
      `/cases/${caseId}/evidence-assessment`,
    )
    workflow.value = await apiRequest<WorkflowResponse>(`/cases/${caseId}/workflow`)
    input.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

async function reviewContract() {
  if (!contractText.value.trim()) return
  reviewing.value = true
  try {
    contractReview.value = await apiRequest<ContractReviewResponse>(
      `/cases/${caseId}/contract-review`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: contractText.value }),
      },
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : '合同审查失败'
  } finally {
    reviewing.value = false
  }
}

async function generateDocument(type: 'settlement' | 'arbitration' | 'complaint') {
  generatingDocument.value = type
  try {
    const document = await apiRequest<DocumentItem>(`/cases/${caseId}/documents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_type: type }),
    })
    documents.value.unshift(document)
    selectedDocument.value = document
  } catch (err) {
    error.value = err instanceof Error ? err.message : '文书生成失败'
  } finally {
    generatingDocument.value = ''
  }
}

async function downloadDocument(documentItem: DocumentItem) {
  const response = await fetch(
    `${API_BASE_URL}/cases/${caseId}/documents/${documentItem.id}/download`,
    {
      headers: {
        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}`,
      },
    },
  )
  if (!response.ok) {
    error.value = '文书下载失败'
    return
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${documentItem.title}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

async function extractEvidence(item: EvidenceItem) {
  extractingId.value = item.id
  error.value = ''
  try {
    await apiRequest<EvidenceExtractionResponse>(
      `/cases/${caseId}/evidence/${item.id}/extract`,
      { method: 'POST' },
    )
    const evidenceData = await apiRequest<EvidenceResponse>(`/cases/${caseId}/evidence`)
    evidenceItems.value = evidenceData.items
    evidenceAssessment.value = evidenceData.assessment
  } catch (err) {
    error.value = err instanceof Error ? err.message : '重新提取失败'
  } finally {
    extractingId.value = null
  }
}

async function downloadEvidence(item: EvidenceItem) {
  const response = await fetch(
    `${API_BASE_URL}/cases/${caseId}/evidence/${item.id}/download`,
    {
      headers: {
        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}`,
      },
    },
  )
  if (!response.ok) {
    error.value = '材料下载失败'
    return
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = item.filename
  link.click()
  URL.revokeObjectURL(url)
}

async function deleteEvidence(item: EvidenceItem) {
  deletingId.value = item.id
  error.value = ''
  try {
    await apiRequest(`/cases/${caseId}/evidence/${item.id}`, { method: 'DELETE' })
    const evidenceData = await apiRequest<EvidenceResponse>(`/cases/${caseId}/evidence`)
    evidenceItems.value = evidenceData.items
    evidenceAssessment.value = evidenceData.assessment
    evidenceRulesAssessment.value = await apiRequest<EvidenceAssessmentResponse>(
      `/cases/${caseId}/evidence-assessment`,
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    deletingId.value = null
  }
}

async function previewEvidence(item: EvidenceItem) {
  const isImage = item.content_type.startsWith('image/')
  if (isImage) {
    const response = await fetch(
      `${API_BASE_URL}/cases/${caseId}/evidence/${item.id}/download`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}`,
        },
      },
    )
    if (!response.ok) {
      error.value = '预览加载失败'
      return
    }
    const blob = await response.blob()
    preview.value = {
      filename: item.filename,
      isImage: true,
      url: URL.createObjectURL(blob),
      text: '',
    }
  } else {
    preview.value = {
      filename: item.filename,
      isImage: false,
      url: '',
      text: item.text_preview || '该类型暂不支持在线预览，请点击「下载」查看。',
    }
  }
}

function closePreview() {
  if (preview.value?.url) URL.revokeObjectURL(preview.value.url)
  preview.value = null
}

async function reviewContractFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  reviewingFile.value = true
  error.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    contractFileReview.value = await apiRequest<ContractFileReviewResponse>(
      `/cases/${caseId}/contract-review/file`,
      { method: 'POST', body },
    )
    input.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '合同文件审查失败'
  } finally {
    reviewingFile.value = false
  }
}

function startEditDocument(documentItem: DocumentItem) {
  editingDocument.value = documentItem
  editTitle.value = documentItem.title
  editContent.value = documentItem.content
}

async function saveRevision() {
  if (!editingDocument.value) return
  savingRevision.value = true
  error.value = ''
  try {
    const revision = await apiRequest<DocumentItem>(
      `/cases/${caseId}/documents/${editingDocument.value.id}/revisions`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editTitle.value.trim(),
          content: editContent.value,
        }),
      },
    )
    documents.value = await apiRequest<DocumentItem[]>(`/cases/${caseId}/documents`)
    selectedDocument.value = revision
    editingDocument.value = null
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存版本失败'
  } finally {
    savingRevision.value = false
  }
}

async function exportDocument(documentItem: DocumentItem, format: 'docx' | 'pdf') {
  exportingFormat.value = format
  error.value = ''
  try {
    const response = await fetch(
      `${API_BASE_URL}/cases/${caseId}/documents/${documentItem.id}/export?format=${format}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY) ?? ''}`,
        },
      },
    )
    if (!response.ok) {
      error.value = '导出失败'
      return
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${documentItem.title}.${format}`
    link.click()
    URL.revokeObjectURL(url)
  } finally {
    exportingFormat.value = ''
  }
}

onMounted(loadAll)
</script>
