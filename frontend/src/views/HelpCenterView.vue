<template>
  <section class="content-page help-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">服务支持</span>
        <h1>维权帮助</h1>
        <p>集中查看仲裁、法院、法律援助和本站律师入口，关键事项仍以当地官方要求为准。</p>
      </div>
      <RouterLink to="/cases" class="primary-action primary-action--compact">
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

    <section class="detail-card profile-card">
      <div class="detail-section-heading">
        <div>
          <span class="eyebrow">账户资料</span>
          <h2>{{ profile ? '实名资料已提交' : '补充必要资料' }}</h2>
        </div>
        <span v-if="profile" class="status-tag">{{ verificationLabels[profile.verification_status] }}</span>
      </div>
      <p v-if="profile" class="profile-summary">
        {{ profile.real_name }} · {{ profile.id_number_masked }} · {{ profile.phone }}
      </p>
      <form v-else class="form-grid" @submit.prevent="saveProfile">
        <label>
          <span>真实姓名</span>
          <input v-model="profileForm.real_name" required />
        </label>
        <label>
          <span>手机号</span>
          <input v-model="profileForm.phone" inputmode="tel" required />
        </label>
        <label class="form-grid__wide">
          <span>身份证号</span>
          <input v-model="profileForm.id_number" required />
        </label>
        <div class="form-grid__wide form-actions">
          <button class="primary-action primary-action--compact" type="submit" :disabled="savingProfile">
            {{ savingProfile ? '提交中...' : '提交实名资料' }}
          </button>
          <small>身份证号只保存脱敏值、哈希和审核状态。</small>
        </div>
      </form>
    </section>

    <div class="detail-grid">
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
  </section>
</template>

<script setup lang="ts">
import {
  ArrowRight,
  ExternalLink,
  MessageCircleMore,
  ShieldCheck,
} from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { apiRequest } from '../api/http'
import type { HelpResource, SiteLawyer, UserProfileItem } from '../types/api'

const resources = ref<HelpResource[]>([])
const lawyers = ref<SiteLawyer[]>([])
const profile = ref<UserProfileItem | null>(null)
const savingProfile = ref(false)
const error = ref('')
const profileForm = ref({
  real_name: '',
  phone: '',
  id_number: '',
})

const resourceTypeLabels: Record<string, string> = {
  arbitration: '劳动仲裁',
  court: '法院诉讼',
  legal_aid: '法律援助',
  site_lawyer: '本站律师',
  other: '其他入口',
}
const verificationLabels: Record<string, string> = {
  unverified: '未提交',
  pending: '审核中',
  verified: '已核验',
  rejected: '需重新提交',
}

async function saveProfile() {
  savingProfile.value = true
  error.value = ''
  try {
    profile.value = await apiRequest<UserProfileItem>('/users/me/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileForm.value),
    })
    profileForm.value.id_number = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '个人资料提交失败'
  } finally {
    savingProfile.value = false
  }
}

onMounted(async () => {
  try {
    const [resourceData, lawyerData] = await Promise.all([
      apiRequest<HelpResource[]>('/help/resources'),
      apiRequest<SiteLawyer[]>('/help/site-lawyers'),
    ])
    resources.value = resourceData
    lawyers.value = lawyerData
    profile.value = await apiRequest<UserProfileItem>('/users/me/profile').catch(() => null)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '帮助数据加载失败'
  }
})
</script>
