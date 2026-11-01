<template>
  <section class="placeholder">
    <span class="eyebrow">{{ eyebrow }}</span>
    <h1>{{ title }}</h1>
    <p>{{ description }}</p>

    <div class="placeholder__grid">
      <article v-for="item in capabilities" :key="item">
        <span class="placeholder__bullet" />
        <strong>{{ item }}</strong>
        <p>该能力已纳入产品与技术设计，将在后续迭代中实现。</p>
      </article>
    </div>

    <RouterLink to="/" class="back-link">
      <ArrowLeft :size="17" />
      返回 AI 法律咨询
    </RouterLink>
  </section>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@lucide/vue'
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const title = computed(() => String(route.meta.title ?? '功能建设中'))
const eyebrow = computed(() => String(route.meta.eyebrow ?? '后续模块'))
const description = computed(() => String(route.meta.description ?? '该模块正在规划中。'))

const moduleCapabilities: Record<string, string[]> = {
  cases: ['案件阶段进度', '证据缺口清单', '文书与律师记录'],
  evidence: ['材料分类与筛查', '合法性关联性评估', '权限隔离与审计'],
  simulation: ['角色场景训练', '表达维度评分', '针对性改进建议'],
  help: ['仲裁与法院入口', '办理材料指南', '本站律师人工协助'],
}

const capabilities = computed(() => moduleCapabilities[String(route.name)] ?? [])
</script>
