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
            <option v-for="item in disputeTypes" :key="item.value" :value="item.value">
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

    <div v-if="loading" class="loading-block"><span class="spinner-dot" /> 正在加载案件...</div>
    <div v-else-if="cases.length" class="case-grid">
      <article v-for="item in cases" :key="item.id" class="case-card" @click="openCase(item.id)">
        <div class="case-card__top">
          <span class="status-tag">{{ disputeLabels[item.dispute_type] || '待识别' }}</span>
          <span class="case-card__id">#{{ item.id }}</span>
        </div>
        <h2>{{ item.title }}</h2>
        <p>{{ item.summary || item.facts || '暂无案件摘要' }}</p>
        <div class="case-card__meta">
          <span><MapPin :size="14" />{{ item.location || '地点待补充' }}</span>
          <span><Clock3 :size="14" />{{ stageLabels[item.stage] || item.stage }}</span>
        </div>
        <div class="case-card__footer">
          <span>{{ new Date(item.updated_at).toLocaleString('zh-CN') }}</span>
          <span class="text-link">进入案件 <ArrowRight :size="15" /></span>
        </div>
      </article>
    </div>
    <div v-else class="empty-state">
      <FolderKanban :size="38" />
      <h2>还没有案件</h2>
      <p>创建第一个案件，之后可以在同一案件内持续咨询和整理材料。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ArrowRight, Clock3, FolderKanban, MapPin, Plus } from '@lucide/vue'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiRequest } from '../api/http'
import type { CaseItem } from '../types/api'

const router = useRouter()
const cases = ref<CaseItem[]>([])
const loading = ref(true)
const creating = ref(false)
const showCreate = ref(false)
const error = ref('')
const form = reactive({
  title: '',
  dispute_type: 'general',
  location: '',
  facts: '',
})

const disputeTypes = [
  { value: 'general', label: '待进一步识别' },
  { value: 'wage', label: '欠薪' },
  { value: 'termination', label: '违法解除' },
  { value: 'contract', label: '未签劳动合同' },
  { value: 'overtime', label: '加班费' },
  { value: 'injury', label: '工伤待遇' },
  { value: 'service_pay', label: '劳务报酬' },
]
const disputeLabels = Object.fromEntries(disputeTypes.map((item) => [item.value, item.label]))
const stageLabels: Record<string, string> = {
  intake: '问题识别',
  evidence: '证据整理',
  procedure: '协商或程序',
  document: '文书准备',
  lawyer_help: '律师协助',
}

async function loadCases() {
  loading.value = true
  try {
    cases.value = await apiRequest<CaseItem[]>('/cases')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件加载失败'
  } finally {
    loading.value = false
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

onMounted(loadCases)
</script>
