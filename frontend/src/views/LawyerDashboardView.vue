<template>
  <section class="content-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">本站律师</span>
        <h1>律师工作台</h1>
        <p>这里只展示管理员已经分配给你的案件。材料查看会记录审计日志。</p>
      </div>
      <div class="metric-chip">
        <strong>{{ cases.length }}</strong>
        <span>待处理案件</span>
      </div>
    </header>

    <p v-if="error" class="inline-error">{{ error }}</p>
    <div v-if="loading" class="loading-block"><span class="spinner-dot" /> 正在加载案件...</div>
    <div v-else-if="cases.length" class="case-grid">
      <article v-for="item in cases" :key="item.id" class="case-card" @click="router.push(`/cases/${item.id}`)">
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
</template>

<script setup lang="ts">
import { ArrowRight, BriefcaseBusiness, Clock3, MapPin } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiRequest } from '../api/http'
import type { CaseItem } from '../types/api'

const router = useRouter()
const cases = ref<CaseItem[]>([])
const loading = ref(true)
const error = ref('')
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

onMounted(async () => {
  try {
    cases.value = await apiRequest<CaseItem[]>('/lawyer/cases')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案件加载失败'
  } finally {
    loading.value = false
  }
})
</script>
