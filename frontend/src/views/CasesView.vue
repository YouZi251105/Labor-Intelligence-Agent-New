<template>
  <section class="content-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">案件工作台</span>
        <h1>我的案件</h1>
        <p>案件会保存咨询上下文、证据材料、文书草稿和律师协助记录。</p>
      </div>
      <button class="primary-action primary-action--compact" type="button" @click="showCreate = !showCreate">
        <Plus :size="17" />
        新建案件
      </button>
    </header>

    <form v-if="showCreate" class="inline-form-card" @submit.prevent="createCase">
      <div class="form-grid">
        <label>
          <span>案件名称</span>
          <input v-model="form.title" required maxlength="160" />
        </label>
        <label>
          <span>纠纷类型</span>
          <select v-model="form.dispute_type">
            <option v-for="item in dictionary.disputes" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </label>
        <label>
          <span>用工所在地</span>
          <input v-model="form.location" placeholder="例如：上海市浦东新区" />
        </label>
        <label class="form-grid__wide">
          <span>基本情况</span>
          <textarea v-model="form.facts" rows="4" placeholder="描述工作时间、工资、合同和目前遇到的问题" />
        </label>
      </div>
      <div class="form-actions">
        <button class="primary-action primary-action--compact" type="submit" :disabled="creating">
          {{ creating ? '创建中...' : '创建案件' }}
        </button>
        <button class="secondary-action" type="button" @click="showCreate = false">取消</button>
      </div>
    </form>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <div class="case-toolbar">
      <div class="case-tabs" role="tablist">
        <button type="button" :class="{ active: filterStatus === 'active' }" @click="setStatus('active')">
          进行中
        </button>
        <button type="button" :class="{ active: filterStatus === 'archived' }" @click="setStatus('archived')">
          已归档
        </button>
      </div>
      <div class="case-filters">
        <select v-model="disputeFilter" aria-label="按纠纷类型筛选" @change="loadCases">
          <option value="">全部类型</option>
          <option v-for="item in dictionary.disputes" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <input v-model="query" type="search" placeholder="搜索案件标题或内容" @input="onSearch" />
      </div>
    </div>

    <div v-if="loading" class="loading-block"><span class="spinner-dot" /> 正在加载案件...</div>
    <div v-else-if="cases.length" class="case-list">
      <article v-for="item in cases" :key="item.id" class="case-row" @click="openCase(item.id)">
        <div class="case-row__main">
          <span class="status-tag">{{ dictionary.disputeLabels[item.dispute_type] || '待识别' }}</span>
          <div class="case-row__text">
            <h2>{{ item.title }}</h2>
            <p>{{ item.summary || item.facts || '暂无案件摘要' }}</p>
          </div>
        </div>
        <div class="case-row__meta">
          <span><Clock3 :size="14" />{{ dictionary.stageLabels[item.stage] || item.stage }}</span>
          <span>{{ new Date(item.updated_at).toLocaleDateString('zh-CN') }}</span>
        </div>
        <div class="case-row__actions" @click.stop>
          <button type="button" class="text-action" @click="toggleArchive(item)">
            {{ item.archived ? '取消归档' : '归档' }}
          </button>
          <button type="button" class="text-action text-action--danger" @click="removeCase(item)">
            删除
          </button>
          <ArrowRight :size="16" class="case-row__arrow" />
        </div>
      </article>
    </div>
    <div v-else class="empty-state">
      <FolderKanban :size="38" />
      <h2>{{ filterStatus === 'archived' ? '没有已归档案件' : '还没有案件' }}</h2>
      <p>
        {{ filterStatus === 'archived' ? '归档的案件会显示在这里，可随时取消归档。' : '创建第一个案件，之后可以在同一案件内持续咨询和整理材料。' }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ArrowRight, Clock3, FolderKanban, Plus } from '@lucide/vue'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiRequest } from '../api/http'
import { useDictionaryStore } from '../stores/dictionary'
import { confirmAction, notifySuccess } from '../utils/dialogs'
import type { CaseItem } from '../types/api'

const router = useRouter()
const cases = ref<CaseItem[]>([])
const loading = ref(true)
const creating = ref(false)
const showCreate = ref(false)
const error = ref('')
const filterStatus = ref<'active' | 'archived'>('active')
const disputeFilter = ref('')
const query = ref('')
let searchTimer: ReturnType<typeof setTimeout> | undefined

const form = reactive({
  title: '',
  dispute_type: 'general',
  location: '',
  facts: '',
})

const dictionary = useDictionaryStore()

function buildParams() {
  const params = new URLSearchParams()
  params.set('status', filterStatus.value)
  if (disputeFilter.value) params.set('dispute_type', disputeFilter.value)
  if (query.value.trim()) params.set('q', query.value.trim())
  return params.toString()
}

async function loadCases() {
  loading.value = true
  try {
    cases.value = await apiRequest<CaseItem[]>(`/cases?${buildParams()}`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件加载失败'
  } finally {
    loading.value = false
  }
}

function setStatus(status: 'active' | 'archived') {
  filterStatus.value = status
  void loadCases()
}

function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    void loadCases()
  }, 300)
}

async function toggleArchive(item: CaseItem) {
  error.value = ''
  try {
    await apiRequest<CaseItem>(`/cases/${item.id}/archive`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ archived: !item.archived }),
    })
    await loadCases()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
  }
}

async function removeCase(item: CaseItem) {
  error.value = ''
  const confirmed = await confirmAction(
    `确定删除案件“${item.title}”？删除后不可恢复。`,
    {
      title: '删除案件',
      confirmText: '删除',
      danger: true,
    },
  )
  if (!confirmed) return
  try {
    await apiRequest<void>(`/cases/${item.id}`, { method: 'DELETE' })
    await loadCases()
    notifySuccess('案件已删除')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除失败'
  }
}

async function createCase() {
  creating.value = true
  error.value = ''
  try {
    const created = await apiRequest<CaseItem>('/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
    await router.push(`/cases/${created.id}`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建案件失败'
  } finally {
    creating.value = false
  }
}

function openCase(id: number) {
  void router.push(`/cases/${id}`)
}

onMounted(async () => {
  await dictionary.load()
  await loadCases()
})
</script>
