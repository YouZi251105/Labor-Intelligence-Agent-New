<template>
  <section class="rule-package-center">
    <header class="rule-package-toolbar">
      <div>
        <span class="eyebrow">版本化内容管理</span>
        <h2>版本与发布</h2>
        <p>管理决策树内容、版本状态和发布流程。</p>
      </div>
      <div class="rule-package-toolbar__actions">
        <button
          type="button"
          class="primary-action primary-action--compact"
          @click="downloadExcelTemplate"
        >
          <FileSpreadsheet :size="16" />
          下载 Excel 模板
        </button>
        <label class="secondary-action rule-package-upload">
          <Upload :size="16" />
          导入 Excel
          <input
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            @change="importExcel"
          />
        </label>
        <button
          v-if="selectedPackage"
          type="button"
          class="secondary-action"
          @click="exportSelectedExcel"
        >
          <Download :size="16" />
          导出当前 Excel
        </button>
        <button type="button" class="secondary-action" @click="loadTemplate">
          <FilePlus2 :size="16" />
          载入模板
        </button>
        <button type="button" class="secondary-action" @click="downloadTemplate">
          <Download :size="16" />
          下载 JSON 模板
        </button>
        <label class="primary-action primary-action--compact rule-package-upload">
          <Upload :size="16" />
          导入 JSON
          <input type="file" accept=".json,application/json" @change="importFile" />
        </label>
      </div>
    </header>

    <p v-if="error" class="inline-error">{{ error }}</p>
    <p v-if="success" class="form-success">{{ success }}</p>

    <div v-if="loading" class="admin-loading-skeleton" aria-label="规则包加载中">
      <span />
      <span />
      <span />
    </div>

    <div v-else class="rule-package-layout">
      <aside class="rule-package-list" aria-label="规则包版本列表">
        <div class="rule-package-list__heading">
          <strong>{{ packages.length }} 个版本</strong>
          <button type="button" class="icon-button" title="刷新规则包" @click="loadPackages()">
            <RefreshCw :size="16" />
          </button>
        </div>
        <button
          v-for="item in packages"
          :key="item.id"
          type="button"
          class="rule-package-list__item"
          :class="{ active: selectedPackage?.id === item.id }"
          @click="selectPackage(item)"
        >
          <span>
            <strong>{{ item.package_id }}</strong>
            <small>{{ item.version }}</small>
          </span>
          <span class="status-tag" :class="statusClass(item.status)">
            {{ statusLabel(item.status) }}
          </span>
        </button>
        <p v-if="!packages.length" class="muted-text">还没有规则包版本。</p>
      </aside>

      <div class="rule-package-editor">
        <div class="rule-package-editor__heading">
          <div>
            <span class="eyebrow">{{ selectedPackage ? `#${selectedPackage.id}` : '新草稿' }}</span>
            <h3>{{ selectedPackage?.version || '从模板或编辑器创建' }}</h3>
          </div>
          <div class="rule-package-editor__status">
            <span v-if="selectedPackage" class="status-tag" :class="statusClass(selectedPackage.status)">
              {{ statusLabel(selectedPackage.status) }}
            </span>
            <small v-if="selectedPackage">
              更新于 {{ new Date(selectedPackage.updated_at).toLocaleString('zh-CN') }}
            </small>
          </div>
        </div>

        <div class="rule-package-view-switch" role="group" aria-label="编辑模式">
          <button
            type="button"
            :class="{ active: viewMode === 'visual' }"
            @click="setViewMode('visual')"
          >
            可视化
          </button>
          <button
            type="button"
            :class="{ active: viewMode === 'json' }"
            @click="setViewMode('json')"
          >
            JSON
          </button>
        </div>

        <WorkflowBlockDesigner
          v-if="viewMode === 'visual' && visualContent"
          :model-value="visualContent"
          @update:model-value="updateFromDesigner"
        />
        <textarea
          v-else
          v-model="editorContent"
          class="rule-package-editor__textarea"
          spellcheck="false"
          aria-label="规则包 JSON 内容"
          :readonly="Boolean(selectedPackage && !isEditable)"
        />

        <div class="rule-package-actions">
          <button type="button" class="secondary-action" :disabled="busy" @click="validateEditor">
            <CheckCircle2 :size="16" />
            校验内容
          </button>
          <button
            v-if="selectedPackage && isEditable"
            type="button"
            class="secondary-action"
            :disabled="busy"
            @click="saveDraft"
          >
            <Save :size="16" />
            保存草稿
          </button>
          <button
            v-if="!selectedPackage || selectedPackage.status === 'published'"
            type="button"
            class="secondary-action"
            :disabled="busy"
            @click="createDraft"
          >
            <GitBranch :size="16" />
            导入为新草稿
          </button>
          <button type="button" class="secondary-action" :disabled="busy" @click="downloadEditor">
            <Download :size="16" />
            下载当前内容
          </button>
          <button
            v-if="selectedPackage && ['draft', 'rejected'].includes(selectedPackage.status)"
            type="button"
            class="primary-action primary-action--compact"
            :disabled="busy"
            @click="submitForReview"
          >
            <Send :size="16" />
            提交复核
          </button>
          <button
            v-if="selectedPackage?.status === 'pending_review'"
            type="button"
            class="primary-action primary-action--compact"
            :disabled="busy"
            @click="reviewPackage('approved')"
          >
            <BadgeCheck :size="16" />
            批准
          </button>
          <button
            v-if="selectedPackage?.status === 'pending_review'"
            type="button"
            class="secondary-action"
            :disabled="busy"
            @click="reviewPackage('rejected')"
          >
            <XCircle :size="16" />
            驳回
          </button>
          <button
            v-if="selectedPackage?.status === 'approved'"
            type="button"
            class="primary-action primary-action--compact"
            :disabled="busy"
            @click="publishPackage"
          >
            <Rocket :size="16" />
            发布
          </button>
          <button
            v-if="selectedPackage?.status === 'published'"
            type="button"
            class="secondary-action"
            :disabled="busy"
            @click="retirePackage"
          >
            <Archive :size="16" />
            停用
          </button>
        </div>

        <div v-if="validation" class="rule-package-validation">
          <div class="rule-package-validation__state" :class="{ invalid: !validation.valid }">
            <CheckCircle2 v-if="validation.valid" :size="18" />
            <XCircle v-else :size="18" />
            <strong>{{ validation.valid ? '结构校验通过' : '结构校验未通过' }}</strong>
          </div>
          <ul v-if="validation.errors.length">
            <li v-for="item in validation.errors" :key="item">{{ item }}</li>
          </ul>
          <div v-if="validation.summary" class="rule-package-summary">
            <span>包标识 <strong>{{ validation.summary.package_id }}</strong></span>
            <span>版本 <strong>{{ validation.summary.version }}</strong></span>
            <span>阶段 <strong>{{ validation.summary.stage_count }}</strong></span>
            <span>节点 <strong>{{ validation.summary.node_count }}</strong></span>
            <span>路径 <strong>{{ validation.summary.option_count }}</strong></span>
            <span>积木 <strong>{{ validation.summary.block_count }}</strong></span>
            <span>复核状态 <strong>{{ statusLabel(validation.summary.review_status) }}</strong></span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  Archive,
  BadgeCheck,
  CheckCircle2,
  Download,
  FilePlus2,
  FileSpreadsheet,
  GitBranch,
  RefreshCw,
  Rocket,
  Save,
  Send,
  Upload,
  XCircle,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'

import { apiFile, apiRequest } from '../api/http'
import WorkflowBlockDesigner from './WorkflowBlockDesigner.vue'
import type {
  RulePackageDetail,
  RulePackageStatus,
  RulePackageSummary,
  RulePackageValidationResponse,
} from '../types/api'

const packages = ref<RulePackageSummary[]>([])
const selectedPackage = ref<RulePackageDetail | null>(null)
const editorContent = ref('')
const validation = ref<RulePackageValidationResponse | null>(null)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const success = ref('')
const viewMode = ref<'visual' | 'json'>('visual')
const visualContent = ref<Record<string, unknown> | null>(null)

const isEditable = computed(
  () =>
    selectedPackage.value?.status === 'draft' ||
    selectedPackage.value?.status === 'rejected',
)

onMounted(() => {
  void loadPackages()
})

async function loadPackages(preferredId?: number) {
  loading.value = true
  error.value = ''
  try {
    packages.value = await apiRequest<RulePackageSummary[]>('/admin/rule-packages')
    const targetId = preferredId ?? selectedPackage.value?.id ?? packages.value[0]?.id
    if (targetId) {
      const item = packages.value.find((entry) => entry.id === targetId)
      if (item) await selectPackage(item)
    } else {
      selectedPackage.value = null
      editorContent.value = ''
      validation.value = null
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '规则包加载失败'
  } finally {
    loading.value = false
  }
}

async function selectPackage(item: RulePackageSummary) {
  error.value = ''
  success.value = ''
  try {
    selectedPackage.value = await apiRequest<RulePackageDetail>(
      `/admin/rule-packages/${item.id}`,
    )
    editorContent.value = JSON.stringify(selectedPackage.value.content, null, 2)
    visualContent.value = cloneContent(selectedPackage.value.content)
    viewMode.value = isEditable.value ? 'visual' : 'json'
    validation.value = null
  } catch (err) {
    error.value = err instanceof Error ? err.message : '规则包详情加载失败'
  }
}

async function loadTemplate() {
  error.value = ''
  success.value = ''
  try {
    const template = await apiRequest<Record<string, unknown>>(
      '/admin/rule-packages/template',
    )
    editorContent.value = JSON.stringify(template, null, 2)
    visualContent.value = cloneContent(template)
    selectedPackage.value = null
    viewMode.value = 'visual'
    validation.value = null
    success.value = '模板已载入编辑器，修改版本号后可导入为新草稿。'
  } catch (err) {
    error.value = err instanceof Error ? err.message : '模板加载失败'
  }
}

async function downloadTemplate() {
  try {
    const template = await apiRequest<Record<string, unknown>>(
      '/admin/rule-packages/template',
    )
    downloadJson('workflow-rule-package-template.json', template)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '模板下载失败'
  }
}

async function downloadExcelTemplate() {
  error.value = ''
  success.value = ''
  try {
    const blob = await apiFile('/admin/rule-packages/template.xlsx')
    saveBlob('workflow-rule-package-template.xlsx', blob)
    success.value = 'Excel 模板已下载。'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Excel 模板下载失败'
  }
}

async function exportSelectedExcel() {
  if (!selectedPackage.value) return
  error.value = ''
  success.value = ''
  try {
    const blob = await apiFile(
      `/admin/rule-packages/${selectedPackage.value.id}/export.xlsx`,
    )
    saveBlob(
      `workflow-rule-package-${selectedPackage.value.version}.xlsx`,
      blob,
    )
    success.value = '当前规则包已导出为 Excel。'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Excel 导出失败'
  }
}

function downloadEditor() {
  const content = parseEditor()
  if (!content) return
  downloadJson('workflow-rule-package.json', content)
}

function downloadJson(filename: string, content: unknown) {
  const blob = new Blob([JSON.stringify(content, null, 2)], {
    type: 'application/json;charset=utf-8',
  })
  saveBlob(filename, blob)
}

function saveBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

async function importExcel(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    error.value = '请选择 .xlsx 格式的规则包文件'
    input.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    error.value = 'Excel 文件不能超过 5 MiB'
    input.value = ''
    return
  }
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file, file.name)
    const response = await apiRequest<RulePackageDetail>(
      '/admin/rule-packages/import-excel',
      {
        method: 'POST',
        body: formData,
      },
    )
    await loadPackages(response.id)
    success.value = `已导入 Excel 草稿 ${response.package_id} · ${response.version}`
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Excel 规则包导入失败'
  } finally {
    busy.value = false
    input.value = ''
  }
}

async function importFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const content = parseJsonObject(await file.text())
    const response = await apiRequest<RulePackageDetail>(
      '/admin/rule-packages/import',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      },
    )
    await loadPackages(response.id)
    success.value = `已导入草稿 ${response.package_id} · ${response.version}`
  } catch (err) {
    error.value = err instanceof Error ? err.message : '规则包导入失败'
  } finally {
    input.value = ''
  }
}

async function validateEditor() {
  const content = parseEditor()
  if (!content) return false
  busy.value = true
  error.value = ''
  try {
    validation.value = await apiRequest<RulePackageValidationResponse>(
      '/admin/rule-packages/validate',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      },
    )
    return validation.value.valid
  } catch (err) {
    error.value = err instanceof Error ? err.message : '规则包校验失败'
    return false
  } finally {
    busy.value = false
  }
}

async function saveDraft() {
  if (!selectedPackage.value || !isEditable.value) return
  const content = parseEditor()
  if (!content) return
  busy.value = true
  error.value = ''
  try {
    const response = await apiRequest<RulePackageDetail>(
      `/admin/rule-packages/${selectedPackage.value.id}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      },
    )
    await loadPackages(response.id)
    success.value = '草稿已保存。'
  } catch (err) {
    error.value = err instanceof Error ? err.message : '草稿保存失败'
  } finally {
    busy.value = false
  }
}

async function createDraft() {
  const content = parseEditor()
  if (!content) return
  busy.value = true
  error.value = ''
  try {
    const response = await apiRequest<RulePackageDetail>(
      '/admin/rule-packages/import',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      },
    )
    await loadPackages(response.id)
    success.value = '新草稿已创建。'
  } catch (err) {
    error.value = err instanceof Error ? err.message : '新草稿创建失败'
  } finally {
    busy.value = false
  }
}

async function submitForReview() {
  await runPackageAction('submit', '规则包已提交复核。')
}

async function reviewPackage(decision: 'approved' | 'rejected') {
  await runPackageAction('review', decision === 'approved' ? '规则包已批准。' : '规则包已驳回。', {
    decision,
  })
}

async function publishPackage() {
  await runPackageAction('publish', '规则包已发布，运行时将使用该版本。')
}

async function retirePackage() {
  if (!window.confirm('确认停用当前规则包版本？')) return
  await runPackageAction('retire', '规则包已停用。')
}

async function runPackageAction(
  action: string,
  message: string,
  payload?: Record<string, unknown>,
) {
  if (!selectedPackage.value) return
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    const response = await apiRequest<RulePackageDetail>(
      `/admin/rule-packages/${selectedPackage.value.id}/${action}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload ? JSON.stringify(payload) : undefined,
      },
    )
    await loadPackages(response.id)
    success.value = message
  } catch (err) {
    error.value = err instanceof Error ? err.message : '规则包操作失败'
  } finally {
    busy.value = false
  }
}

function parseEditor(): Record<string, unknown> | null {
  try {
    return parseJsonObject(editorContent.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'JSON 格式无效'
    validation.value = null
    return null
  }
}

function setViewMode(mode: 'visual' | 'json') {
  if (mode === 'visual') {
    if (selectedPackage.value && !isEditable.value) {
      error.value = '当前版本不可编辑，只能查看 JSON。'
      return
    }
    const parsed = parseEditor()
    if (!parsed) return
    visualContent.value = cloneContent(parsed)
  }
  viewMode.value = mode
}

function updateFromDesigner(value: Record<string, unknown>) {
  visualContent.value = cloneContent(value)
  editorContent.value = JSON.stringify(value, null, 2)
  validation.value = null
}

function cloneContent(value: Record<string, unknown>) {
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>
}

function parseJsonObject(value: string): Record<string, unknown> {
  const parsed: unknown = JSON.parse(value)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('规则包内容必须是 JSON 对象')
  }
  return parsed as Record<string, unknown>
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    draft: '草稿',
    pending_review: '待复核',
    approved: '已批准',
    rejected: '已驳回',
    published: '已发布',
    retired: '已停用',
  }
  return labels[status] ?? status
}

function statusClass(status: RulePackageStatus | string) {
  if (status === 'published' || status === 'approved') return 'status-tag--success'
  if (status === 'pending_review' || status === 'draft') return 'status-tag--warning'
  if (status === 'rejected') return 'status-tag--danger'
  return ''
}
</script>
