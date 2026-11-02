<template>
  <div class="auth-page">
    <section class="auth-brand">
      <div class="auth-brand__content">
        <BrandMark size="large" />
        <span class="eyebrow">Labor Intelligence Agent</span>
        <h1>让劳动维权<br />从第一步就清楚</h1>
        <p>
          从问题识别、证据整理到文书草稿和律师协助，用清晰流程帮助基层劳动者完成每一步。
        </p>
        <div class="auth-brand__points">
          <span><ShieldCheck :size="17" /> 材料权限隔离</span>
          <span><Scale :size="17" /> 法律规则校验</span>
          <span><UserRoundCheck :size="17" /> 人工律师兜底</span>
        </div>
      </div>
    </section>

    <section class="auth-form-wrap">
      <div class="auth-card">
        <span class="eyebrow">{{ isRegister ? '创建账号' : '账号登录' }}</span>
        <h2>{{ isRegister ? '开始使用劳务通' : '欢迎回来' }}</h2>
        <p class="auth-card__intro">
          {{ isRegister ? '注册后即可创建案件和保存咨询上下文。' : '登录后继续处理你的案件和材料。' }}
        </p>

        <form class="auth-form" @submit.prevent="submit">
          <label>
            <span>用户名</span>
            <ElInput v-model="form.username" size="large" autocomplete="username" />
          </label>
          <label v-if="isRegister">
            <span>显示名称</span>
            <ElInput v-model="form.displayName" size="large" placeholder="例如：张师傅" />
          </label>
          <label>
            <span>密码</span>
            <ElInput
              v-model="form.password"
              type="password"
              size="large"
              show-password
              autocomplete="current-password"
              @keydown.enter="submit"
            />
          </label>

          <p v-if="error" class="form-error">{{ error }}</p>
          <button class="primary-action" type="submit" :disabled="loading">
            {{ loading ? '正在处理...' : isRegister ? '注册并进入' : '登录' }}
            <ArrowRight :size="18" />
          </button>
        </form>

        <button class="auth-switch" type="button" @click="toggleMode">
          {{ isRegister ? '已有账号，直接登录' : '没有账号，立即注册' }}
        </button>

      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElInput } from 'element-plus'
import { ArrowRight, Scale, ShieldCheck, UserRoundCheck } from '@lucide/vue'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BrandMark from '../components/BrandMark.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const isRegister = ref(false)
const loading = ref(false)
const error = ref('')
const form = reactive({
  username: '',
  password: '',
  displayName: '',
})

function toggleMode() {
  isRegister.value = !isRegister.value
  error.value = ''
}

async function submit() {
  if (!form.username.trim() || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  error.value = ''
  try {
    const user = isRegister.value
      ? await auth.register(form.username.trim(), form.password, form.displayName.trim())
      : await auth.login(form.username.trim(), form.password)

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    if (user.role === 'admin') await router.push('/admin')
    else if (user.role === 'lawyer') await router.push('/lawyer')
    else await router.push(redirect)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
  } finally {
    loading.value = false
  }
}
</script>
