<template>
  <div class="app-shell">
    <button
      v-if="sidebarOpen"
      class="sidebar-backdrop"
      aria-label="关闭导航"
      @click="sidebarOpen = false"
    />

    <aside class="sidebar" :class="{ 'sidebar--open': sidebarOpen }">
      <div class="brand">
        <BrandMark />
        <div>
          <strong>劳务通</strong>
          <span>劳动法律服务工作台</span>
        </div>
      </div>

      <nav class="nav" aria-label="主导航">
        <RouterLink
          v-for="item in navigation"
          :key="item.name"
          :to="item.to"
          class="nav__item"
          active-class="nav__item--active"
          @click="sidebarOpen = false"
        >
          <component :is="item.icon" :size="19" :stroke-width="1.8" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar__support">
        <ShieldCheck :size="20" />
        <div>
          <strong>{{ supportTitle }}</strong>
          <p>{{ supportDescription }}</p>
        </div>
      </div>

      <div class="account">
        <div class="account__avatar">{{ getInitial(auth.user?.display_name || auth.user?.username) }}</div>
        <div class="account__meta">
          <strong>{{ auth.user?.display_name || auth.user?.username }}</strong>
          <span>{{ roleLabel }}</span>
        </div>
        <button class="icon-button" title="退出登录" @click="logout">
          <LogOut :size="18" />
        </button>
      </div>
    </aside>

    <div class="main-shell">
      <header class="mobile-header">
        <button class="icon-button" aria-label="打开导航" @click="sidebarOpen = true">
          <Menu :size="22" />
        </button>
        <strong>劳务通</strong>
        <span class="mobile-header__status">法律服务</span>
      </header>

      <main class="page">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  BookOpenText,
  Drama,
  FolderKanban,
  LogOut,
  Menu,
  MessageSquareText,
  Paperclip,
  ShieldCheck,
  ShieldPlus,
  UsersRound,
} from '@lucide/vue'
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import BrandMark from '../components/BrandMark.vue'
import { useAuthStore } from '../stores/auth'
import { getInitial } from '../utils/format'

const sidebarOpen = ref(false)
const auth = useAuthStore()
const router = useRouter()

const userNavigation = [
  { name: 'workspace', label: 'AI 法律咨询', to: '/', icon: MessageSquareText },
  { name: 'cases', label: '我的案件', to: '/cases', icon: FolderKanban },
  { name: 'evidence', label: '证据整理', to: '/evidence', icon: Paperclip },
  { name: 'simulation', label: '模拟对话', to: '/simulation', icon: Drama },
  { name: 'help', label: '维权帮助', to: '/help', icon: BookOpenText },
]

const lawyerNavigation = [
  { name: 'lawyer', label: '律师工作台', to: '/lawyer', icon: ShieldPlus },
  { name: 'help', label: '维权帮助', to: '/help', icon: BookOpenText },
]

const adminNavigation = [
  { name: 'admin', label: '管理后台', to: '/admin', icon: UsersRound },
  { name: 'help', label: '帮助中心', to: '/help', icon: BookOpenText },
]

const navigation = computed(() => {
  if (auth.user?.role === 'admin') return adminNavigation
  if (auth.user?.role === 'lawyer') return lawyerNavigation
  return userNavigation
})

const roleLabel = computed(() => {
  if (auth.user?.role === 'admin') return '平台管理员'
  if (auth.user?.role === 'lawyer') return '本站律师'
  return '劳动者用户'
})

const supportTitle = computed(() =>
  auth.user?.role === 'lawyer' ? '只查看已分配案件' : '人工协助随时可接入',
)
const supportDescription = computed(() =>
  auth.user?.role === 'lawyer'
    ? '案件材料访问会记录审计日志。'
    : '复杂问题可申请本站律师复核。',
)

function logout() {
  auth.logout()
  void router.push('/login')
}
</script>
