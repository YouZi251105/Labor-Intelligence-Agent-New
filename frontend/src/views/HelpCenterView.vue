<template>
  <section class="content-page help-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">服务支持</span>
        <h1>维权帮助</h1>
        <p>集中查看仲裁、法院、法律援助和本站律师入口，关键事项仍以当地官方要求为准。</p>
      </div>
      <RouterLink v-if="isWorker" to="/cases" class="primary-action primary-action--compact">
        <MessageCircleMore :size="17" />
        申请人工协助
      </RouterLink>
    </header>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <section class="detail-card">
      <div class="detail-section-heading">
        <div>
          <span class="eyebrow">官方与公共入口</span>
          <h2>办事渠道</h2>
        </div>
        <ExternalLink :size="22" />
      </div>
      <div class="help-resource-grid">
        <article v-for="resource in resources" :key="resource.id" class="help-resource-card">
          <div class="help-resource-card__top">
            <span class="status-tag">{{ resourceTypeLabels[resource.resource_type] || resource.resource_type }}</span>
            <span>{{ resource.region || '全国' }}</span>
          </div>
          <h3>{{ resource.name }}</h3>
          <p>{{ resource.description }}</p>
          <dl>
            <div v-if="resource.phone"><dt>电话</dt><dd>{{ resource.phone }}</dd></div>
            <div v-if="resource.address"><dt>地址</dt><dd>{{ resource.address }}</dd></div>
          </dl>
          <a
            v-if="resource.website"
            :href="resource.website"
            class="text-link"
            target="_blank"
            rel="noreferrer"
          >
            打开官方入口
            <ExternalLink :size="15" />
          </a>
        </article>
        <p v-if="!resources.length" class="muted-text">暂时没有可展示的帮助入口。</p>
      </div>
    </section>

    <div v-if="isWorker" class="detail-grid">
      <section class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">本站律师</span>
            <h2>人工复核</h2>
          </div>
          <ShieldCheck :size="22" />
        </div>
        <div class="site-lawyer-list">
          <article v-for="lawyer in lawyers" :key="lawyer.id">
            <div class="site-lawyer-list__avatar">{{ lawyer.display_name.slice(0, 1) }}</div>
            <div>
              <strong>{{ lawyer.display_name }}</strong>
              <span>{{ lawyer.specialties }}</span>
              <p>{{ lawyer.bio }}</p>
            </div>
            <RouterLink to="/cases" class="secondary-action">申请协助</RouterLink>
          </article>
          <p v-if="!lawyers.length" class="muted-text">当前没有可接单的本站律师。</p>
        </div>
      </section>

      <section class="detail-card help-guidance">
        <span class="eyebrow">准备材料</span>
        <h2>人工协助前建议准备</h2>
        <ul>
          <li>身份信息和可联系手机号。</li>
          <li>工资、考勤、聊天记录或合同等材料目录。</li>
          <li>争议时间、金额和目前已经沟通的结果。</li>
        </ul>
        <p>平台不会代替律师作正式法律判断，复杂事项由已授权律师复核。</p>
        <RouterLink to="/cases" class="text-link">
          选择案件并发起协助
          <ArrowRight :size="15" />
        </RouterLink>
      </section>
    </div>

    <section v-else class="detail-card">
      <div class="detail-section-heading">
        <div>
          <span class="eyebrow">{{ isAdmin ? '平台管理' : '律师服务' }}</span>
          <h2>{{ isAdmin ? '平台资源维护' : '律师服务支持' }}</h2>
        </div>
        <ShieldCheck :size="22" />
      </div>
      <p v-if="isAdmin" class="muted-text">
        官方办事入口由平台统一维护。用户实名资料、劳动者协助申请和律师分配分别在独立管理页面处理。
      </p>
      <p v-else class="muted-text">
        你只能查看已分配给自己的案件。案件事实由劳动者维护，律师意见、服务记录和收益记录请在律师工作台提交。
      </p>
      <RouterLink :to="isAdmin ? '/admin?section=overview' : '/lawyer'" class="text-link">
        返回{{ isAdmin ? '管理总览' : '律师工作台' }}
        <ArrowRight :size="15" />
      </RouterLink>
    </section>
  </section>
</template>

<script setup lang="ts">
import {
  ArrowRight,
  ExternalLink,
  MessageCircleMore,
  ShieldCheck,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { apiRequest } from '../api/http'
import { useAuthStore } from '../stores/auth'
import type { HelpResource, SiteLawyer } from '../types/api'

const auth = useAuthStore()
const resources = ref<HelpResource[]>([])
const lawyers = ref<SiteLawyer[]>([])
const error = ref('')
const isWorker = computed(() => auth.user?.role === 'user')
const isAdmin = computed(() => auth.user?.role === 'admin')

const resourceTypeLabels: Record<string, string> = {
  arbitration: '劳动仲裁',
  court: '法院诉讼',
  legal_aid: '法律援助',
  site_lawyer: '本站律师',
  other: '其他入口',
}
onMounted(async () => {
  try {
    const resourceData = await apiRequest<HelpResource[]>('/help/resources')
    resources.value = resourceData
    if (isWorker.value) {
      lawyers.value = await apiRequest<SiteLawyer[]>('/help/site-lawyers')
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '帮助数据加载失败'
  }
})
</script>
