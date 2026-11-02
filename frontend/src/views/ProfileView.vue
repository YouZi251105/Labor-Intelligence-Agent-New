<template>
  <section class="content-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">账户与核验</span>
        <h1>账户资料</h1>
        <p>实名资料仅用于咨询、材料提交和律师协助前的必要身份核验。</p>
      </div>
      <span v-if="profile" class="status-tag" :class="verificationClass">
        {{ verificationLabels[profile.verification_status] }}
      </span>
    </header>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <section v-if="required" class="detail-card profile-required-card">
      <div class="profile-required-icon"><ShieldCheck :size="24" /></div>
      <div>
        <span class="eyebrow">使用前确认</span>
        <h2>请先完善个人资料</h2>
        <p>完成以下信息后，才能创建案件、使用 AI 咨询、提交证据、生成文书或进入模拟训练。帮助中心仍可正常浏览。</p>
      </div>
    </section>

    <div class="detail-grid profile-page-grid">
      <section class="detail-card">
        <span class="eyebrow">登录账号</span>
        <h2>{{ auth.user?.display_name || auth.user?.username }}</h2>
        <dl class="profile-account-list">
          <div><dt>用户名</dt><dd>{{ auth.user?.username }}</dd></div>
          <div><dt>账号角色</dt><dd>劳动者</dd></div>
          <div><dt>绑定手机号</dt><dd>{{ profile?.phone || auth.user?.phone || '未填写' }}</dd></div>
          <div><dt>核验状态</dt><dd>{{ profile ? verificationLabels[profile.verification_status] : '尚未提交' }}</dd></div>
        </dl>
        <p class="muted-text">修改实名资料后会重新进入待审核状态，已产生的历史操作不会因此删除。</p>
      </section>

      <section class="detail-card">
        <div class="detail-section-heading">
          <div>
            <span class="eyebrow">实名资料</span>
            <h2>{{ profile ? '更新必要信息' : '补充必要信息' }}</h2>
          </div>
          <ShieldCheck :size="22" />
        </div>
        <form class="form-grid" @submit.prevent="saveProfile">
          <label class="form-grid__wide">
            <span>真实姓名</span>
            <input v-model.trim="profileForm.real_name" autocomplete="name" required />
          </label>
          <label class="form-grid__wide">
            <span>手机号</span>
            <input v-model.trim="profileForm.phone" inputmode="tel" autocomplete="tel" required />
          </label>
          <label class="form-grid__wide">
            <span>身份证号</span>
            <input
              v-model.trim="profileForm.id_number"
              autocomplete="off"
              maxlength="18"
              required
            />
          </label>
          <div class="form-grid__wide form-actions">
            <button class="primary-action primary-action--compact" type="submit" :disabled="saving">
              {{ saving ? '提交中...' : required ? '保存并继续使用' : '保存并提交核验' }}
            </button>
            <small>身份证号仅保存脱敏值、不可逆哈希和审核状态。</small>
          </div>
        </form>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ShieldCheck } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, apiRequest } from '../api/http'
import { useAuthStore } from '../stores/auth'
import type { UserProfileItem } from '../types/api'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const profile = ref<UserProfileItem | null>(null)
const saving = ref(false)
const error = ref('')
const profileForm = ref({
  real_name: '',
  phone: auth.user?.phone || '',
  id_number: '',
})

const verificationLabels: Record<UserProfileItem['verification_status'], string> = {
  unverified: '未提交',
  pending: '审核中',
  verified: '已核验',
  rejected: '需重新提交',
}
const verificationClass = computed(() => {
  if (profile.value?.verification_status === 'verified') return 'status-tag--success'
  if (profile.value?.verification_status === 'pending') return 'status-tag--warning'
  return ''
})
const required = computed(() => route.query.required === '1')

async function saveProfile() {
  saving.value = true
  error.value = ''
  try {
    profile.value = await apiRequest<UserProfileItem>('/users/me/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileForm.value),
    })
    profileForm.value.id_number = ''
    auth.markProfileCompleted()
    const redirect =
      typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
        ? route.query.redirect
        : '/'
    await router.push(redirect)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '个人资料提交失败'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    profile.value = await apiRequest<UserProfileItem>('/users/me/profile')
    profileForm.value = {
      real_name: profile.value.real_name,
      phone: profile.value.phone,
      id_number: '',
    }
  } catch (err) {
    if (!(err instanceof ApiError && err.status === 404)) {
      error.value = err instanceof Error ? err.message : '个人资料加载失败'
    }
  }
})
</script>
