<template>
  <section class="rule-package-center">
    <header class="rule-package-toolbar">
      <div>
        <span class="eyebrow">版本化内容管理</span>
        <h2>争议分类与字典</h2>
        <p>
          法律口径变化时在这里更新分类、关键词、证据要求和文书请求，发布后立即对全平台生效，无需修改代码。
        </p>
      </div>
      <div class="rule-package-toolbar__actions">
        <button type="button" class="secondary-action" @click="loadAll()">
          <RefreshCw :size="16" />
          刷新
        </button>
        <button
          type="button"
          class="primary-action primary-action--compact"
          :disabled="editor !== null"
          @click="startNewDraft"
        >
          新建草稿
        </button>
      </div>
    </header>

    <p v-if="error" class="inline-error">{{ error }}</p>
    <p v-if="success" class="form-success">{{ success }}</p>

    <div v-if="loading" class="admin-loading-skeleton" aria-label="字典版本加载中">
      <span />
      <span />
      <span />
    </div>

    <div v-else class="rule-package-layout">
      <aside class="rule-package-list" aria-label="字典版本列表">
        <div class="rule-package-list__heading">
          <strong>{{ versions.length }} 个版本</strong>
          <button type="button" class="icon-button" title="刷新字典版本" @click="loadAll()">
            <RefreshCw :size="16" />
          </button>
        </div>
        <button
          v-for="item in versions"
          :key="item.id"
          type="button"
          class="rule-package-list__item"
          :class="{ active: selected?.id === item.id }"
          @click="selectVersion(item)"
        >
          <span>
            <strong>字典 v{{ item.version }}</strong>
            <small>{{ formatDate(item.published_at || item.created_at) }}</small>
          </span>
          <span class="status-tag" :class="statusClass(item.status)">
            {{ statusLabel(item.status) }}
          </span>
        </button>
        <p v-if="!versions.length" class="muted-text">
          暂无字典版本，平台当前使用内置默认口径。
        </p>
      </aside>

      <div v-if="!editor" class="rule-package-editor dictionary-empty">
        <span class="eyebrow">当前生效</span>
        <h3>
          {{
            activePackage
              ? activePackage.source === 'published'
                ? `已发布字典 v${activePackage.version}`
                : '内置默认口径'
              : '加载中'
          }}
        </h3>
        <p class="muted-text">
          从左侧选择版本查看内容，或基于当前生效口径新建草稿。已发布版本不可修改，只能通过新版本迭代。
        </p>
      </div>

      <div v-else class="rule-package-editor">
        <div class="rule-package-editor__heading">
          <div>
            <span class="eyebrow">{{ editor.id ? `版本 #${editor.id}` : '新草稿' }}</span>
            <h3>{{ editor.id ? `字典 v${editor.version}` : '基于当前生效口径的草稿' }}</h3>
          </div>
          <div class="rule-package-editor__status">
            <span class="status-tag" :class="statusClass(editor.status)">
              {{ statusLabel(editor.status) }}
            </span>
          </div>
        </div>

        <p v-if="!editable" class="rule-package-readonly-note">
          该版本已{{ editor.status === 'published' ? '发布' : '停用' }}，内容仅供查看；如需调整请新建草稿。
        </p>

        <template v-if="editable">
          <section class="dictionary-section">
            <h4>纠纷分类（{{ rows.length }} 类）</h4>
            <p class="muted-text">
              关键词用于 AI 自动分类；必需/核心材料驱动证据缺口判断；请求事项用于文书生成。labor_other
              为兜底分类，必须保留。
            </p>
            <article
              v-for="(row, index) in rows"
              :key="index"
              class="dictionary-dispute-card"
            >
              <div class="dictionary-dispute-card__head">
                <label>
                  <span>标识 value</span>
                  <input
                    v-model.trim="row.value"
                    type="text"
                    placeholder="如 labor_pay"
                    :disabled="isExistingValue(row.value)"
                  />
                </label>
                <label>
                  <span>分组</span>
                  <select v-model="row.group">
                    <option value="labor">劳动争议</option>
                    <option value="service">劳务纠纷</option>
                  </select>
                </label>
                <button
                  v-if="!isExistingValue(row.value)"
                  type="button"
                  class="secondary-action primary-action--compact"
                  @click="rows.splice(index, 1)"
                >
                  移除
                </button>
              </div>
              <label class="dictionary-field">
                <span>分类名称</span>
                <input v-model.trim="row.label" type="text" placeholder="对外展示的分类名称" />
              </label>
              <div class="dictionary-dispute-grid">
                <label class="dictionary-field">
                  <span>识别关键词（逗号分隔）</span>
                  <input v-model.trim="row.keywordsText" type="text" placeholder="欠薪, 拖欠工资" />
                </label>
                <label class="dictionary-field">
                  <span>必需证据材料（逗号分隔）</span>
                  <input
                    v-model.trim="row.requiredText"
                    type="text"
                    placeholder="payroll, chat, contract"
                  />
                </label>
                <label class="dictionary-field">
                  <span>核心证据材料（逗号分隔）</span>
                  <input v-model.trim="row.coreText" type="text" placeholder="payroll, chat" />
                </label>
              </div>
              <label class="dictionary-field">
                <span>文书请求事项</span>
                <input
                  v-model.trim="row.claimText"
                  type="text"
                  placeholder="请求裁决被申请人支付……"
                />
              </label>
            </article>
            <button
              type="button"
              class="secondary-action"
              @click="addRow"
            >
              新增分类
            </button>
          </section>

          <section class="dictionary-section">
            <h4>案件阶段（JSON）</h4>
            <textarea
              v-model="stagesText"
              class="rule-package-editor__textarea"
              rows="6"
              spellcheck="false"
            />
          </section>

          <section class="dictionary-section">
            <h4>证据类别（JSON）</h4>
            <textarea
              v-model="categoriesText"
              class="rule-package-editor__textarea"
              rows="6"
              spellcheck="false"
            />
          </section>

          <section class="dictionary-section">
            <h4>历史值迁移映射（JSON）</h4>
            <p class="muted-text">旧枚举值到新枚举值的映射，用于历史案件兼容。</p>
            <textarea
              v-model="migrationsText"
              class="rule-package-editor__textarea"
              rows="4"
              spellcheck="false"
            />
          </section>

          <div class="dictionary-editor-actions">
            <button
              type="button"
              class="primary-action primary-action--compact"
              :disabled="saving"
              @click="saveDraft"
            >
              {{ saving ? '保存中...' : editor.id ? '保存草稿' : '创建草稿' }}
            </button>
            <button
              v-if="editor.id"
              type="button"
              class="primary-action primary-action--compact"
              :disabled="publishing"
              @click="publishDraft"
            >
              {{ publishing ? '发布中...' : '发布生效' }}
            </button>
            <button
              v-if="editor.id"
              type="button"
              class="secondary-action"
              :disabled="saving"
              @click="removeDraft"
            >
              删除草稿
            </button>
            <button type="button" class="secondary-action" @click="closeEditor">关闭</button>
          </div>
        </template>

        <template v-else>
          <section
            v-for="(row, index) in rows"
            :key="index"
            class="dictionary-dispute-card"
          >
            <div class="dictionary-dispute-card__head">
              <strong>{{ row.label }}</strong>
              <span class="status-tag">
                {{ row.group === 'labor' ? '劳动争议' : '劳务纠纷' }}
              </span>
            </div>
            <p class="muted-text">
              关键词：{{ row.keywordsText || '无' }} · 必需材料：{{ row.requiredText || '无' }} ·
              核心材料：{{ row.coreText || '无' }}
            </p>
            <p class="muted-text">文书请求：{{ row.claimText || '未配置' }}</p>
          </section>
        </template>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RefreshCw } from '@lucide/vue'

import { apiRequest } from '../api/http'
import { confirmAction, notifySuccess } from '../utils/dialogs'
import type {
  DictionaryActivePackage,
  DictionaryDisputeConfig,
  DictionaryPackageContent,
  DictionaryVersionDetail,
  DictionaryVersionSummary,
} from '../types/api'
import { useDictionaryStore } from '../stores/dictionary'

interface DisputeRow {
  value: string
  label: string
  group: 'labor' | 'service'
  keywordsText: string
  requiredText: string
  coreText: string
  claimText: string
}

interface EditorState {
  id: number | null
  version: number
  status: DictionaryVersionSummary['status']
  content: DictionaryPackageContent
}

const dictionaryStore = useDictionaryStore()
const versions = ref<DictionaryVersionSummary[]>([])
const activePackage = ref<DictionaryActivePackage | null>(null)
const selected = ref<DictionaryVersionSummary | null>(null)
const editor = ref<EditorState | null>(null)
const loading = ref(false)
const saving = ref(false)
const publishing = ref(false)
const error = ref('')
const success = ref('')
const stagesText = ref('')
const categoriesText = ref('')
const migrationsText = ref('')
const rows = reactive<DisputeRow[]>([])
const originalValues = ref<Set<string>>(new Set())

const editable = computed(() => editor.value?.status === 'draft')

const statusLabels: Record<string, string> = {
  draft: '草稿',
  published: '已发布',
  retired: '已停用',
}

function statusLabel(status: string) {
  return statusLabels[status] ?? status
}

function statusClass(status: string) {
  if (status === 'published') return 'status-tag--success'
  if (status === 'retired') return 'status-tag--warning'
  return ''
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function toRow(config: DictionaryDisputeConfig): DisputeRow {
  return {
    value: config.value,
    label: config.label,
    group: config.group,
    keywordsText: config.keywords.join(', '),
    requiredText: config.required_categories.join(', '),
    coreText: config.core_categories.join(', '),
    claimText: config.claim_text,
  }
}

function toConfig(row: DisputeRow): DictionaryDisputeConfig {
  const split = (text: string) =>
    text
      .split(/[,，]/)
      .map((item) => item.trim())
      .filter(Boolean)
  return {
    value: row.value,
    label: row.label,
    group: row.group,
    keywords: split(row.keywordsText),
    required_categories: split(row.requiredText),
    core_categories: split(row.coreText),
    claim_text: row.claimText,
  }
}

function isExistingValue(value: string) {
  return originalValues.value.has(value)
}

function openContent(
  id: number | null,
  version: number,
  status: DictionaryVersionSummary['status'],
  content: DictionaryPackageContent,
) {
  editor.value = { id, version, status, content }
  rows.splice(0, rows.length, ...content.disputes.map(toRow))
  stagesText.value = JSON.stringify(content.stages, null, 2)
  categoriesText.value = JSON.stringify(content.evidence_categories, null, 2)
  migrationsText.value = JSON.stringify(content.migrations, null, 2)
  originalValues.value = new Set(content.disputes.map((item) => item.value))
}

function closeEditor() {
  editor.value = null
  selected.value = null
}

function addRow() {
  rows.push({
    value: '',
    label: '',
    group: 'labor',
    keywordsText: '',
    requiredText: '',
    coreText: '',
    claimText: '',
  })
}

async function loadAll() {
  error.value = ''
  success.value = ''
  loading.value = true
  try {
    const [versionList, active] = await Promise.all([
      apiRequest<DictionaryVersionSummary[]>('/admin/dictionary/versions'),
      apiRequest<DictionaryActivePackage>('/admin/dictionary/active'),
    ])
    versions.value = versionList
    activePackage.value = active
    if (
      editor.value &&
      editor.value.id &&
      !versionList.some((item) => item.id === editor.value?.id)
    ) {
      closeEditor()
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '字典版本加载失败'
  } finally {
    loading.value = false
  }
}

async function startNewDraft() {
  error.value = ''
  selected.value = null
  if (!activePackage.value) {
    await loadAll()
  }
  if (!activePackage.value) return
  openContent(
    null,
    0,
    'draft',
    JSON.parse(JSON.stringify(activePackage.value.content)) as DictionaryPackageContent,
  )
}

async function selectVersion(item: DictionaryVersionSummary) {
  error.value = ''
  selected.value = item
  try {
    const detail = await apiRequest<DictionaryVersionDetail>(
      `/admin/dictionary/versions/${item.id}`,
    )
    openContent(detail.id, detail.version, detail.status, detail.content)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '字典版本详情加载失败'
  }
}

function buildContent(): DictionaryPackageContent | null {
  if (!editor.value) return null
  try {
    return {
      disputes: rows.map(toConfig),
      stages: JSON.parse(stagesText.value),
      evidence_categories: JSON.parse(categoriesText.value),
      migrations: JSON.parse(migrationsText.value) as Record<string, string>,
    }
  } catch {
    error.value = '案件阶段、证据类别或迁移映射不是有效的 JSON'
    return null
  }
}

async function saveDraft() {
  if (!editor.value) return
  const content = buildContent()
  if (!content) return
  saving.value = true
  error.value = ''
  try {
    if (editor.value.id) {
      const updated = await apiRequest<DictionaryVersionDetail>(
        `/admin/dictionary/versions/${editor.value.id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content }),
        },
      )
      editor.value.content = updated.content
      success.value = `字典 v${updated.version} 草稿已保存`
    } else {
      const created = await apiRequest<DictionaryVersionDetail>(
        '/admin/dictionary/versions',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content }),
        },
      )
      editor.value.id = created.id
      editor.value.version = created.version
      editor.value.content = created.content
      success.value = `字典 v${created.version} 草稿已创建，确认内容后发布`
    }
    await loadAll()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '字典草稿保存失败'
  } finally {
    saving.value = false
  }
}

async function publishDraft() {
  if (!editor.value?.id) return
  const confirmed = await confirmAction(
    '发布后新口径立即对全平台生效，且该版本不可再修改。确认发布吗？',
    { title: '发布字典版本', confirmText: '发布' },
  )
  if (!confirmed) return
  publishing.value = true
  error.value = ''
  try {
    const published = await apiRequest<DictionaryVersionDetail>(
      `/admin/dictionary/versions/${editor.value.id}/publish`,
      { method: 'POST' },
    )
    editor.value.status = published.status
    success.value = `字典 v${published.version} 已发布并生效`
    notifySuccess('字典已发布')
    // 让前端各页面的下拉与标签立即使用新字典。
    dictionaryStore.loaded = false
    await dictionaryStore.load()
    await loadAll()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '字典发布失败'
  } finally {
    publishing.value = false
  }
}

async function removeDraft() {
  if (!editor.value?.id) return
  const confirmed = await confirmAction('确认删除该草稿吗？删除后不可恢复。', {
    title: '删除字典草稿',
    confirmText: '删除',
    danger: true,
  })
  if (!confirmed) return
  saving.value = true
  error.value = ''
  try {
    await apiRequest(`/admin/dictionary/versions/${editor.value.id}`, {
      method: 'DELETE',
    })
    success.value = '草稿已删除'
    closeEditor()
    await loadAll()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '字典草稿删除失败'
  } finally {
    saving.value = false
  }
}

void loadAll()
</script>
