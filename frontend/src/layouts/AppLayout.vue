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
        <template v-for="item in navigation" :key="item.name">
          <RouterLink
            :to="item.to"
            class="nav__item"
            :class="{ 'nav__item--active': isNavActive(item.to) }"
            @click="sidebarOpen = false"
          >
            <component :is="item.icon" :size="19" :stroke-width="1.8" />
            <span>{{ item.label }}</span>
          </RouterLink>
          <div v-if="item.children" class="nav__children">
            <RouterLink
              v-for="child in item.children"
              :key="child.name"
              :to="child.to"
              class="nav__child"
              :class="{ 'nav__child--active': isNavActive(child.to) }"
              @click="sidebarOpen = false"
            >
              <span>{{ child.label }}</span>
            </RouterLink>
          </div>
        </template>
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

      <main class="page" :class="{ 'page--workspace': route.name === 'workspace' }">
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
  ShieldCheck,
  ShieldPlus,
  UserRound,
  UsersRound,
} from '@lucide/vue'
import { computed, ref, type Component } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import BrandMark from '../components/BrandMark.vue'
import { useAuthStore } from '../stores/auth'
import { getInitial } from '../utils/format'

const sidebarOpen = ref(false)
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

interface NavChild {
  name: string
  label: string
  to: string
}

interface NavItem {
  name: string
  label: string
  to: string
  icon: Component
  children?: NavChild[]
}

const userNavigation: NavItem[] = [
  { name: 'workspace', label: 'AI 法律咨询', to: '/', icon: MessageSquareText },
  { name: 'cases', label: '我的案件', to: '/cases', icon: FolderKanban },
  { name: 'simulation', label: '模拟对话', to: '/simulation', icon: Drama },
  { name: 'help', label: '维权帮助', to: '/help', icon: BookOpenText },
  { name: 'profile', label: '账户资料', to: '/profile', icon: UserRound },
]

const lawyerNavigation: NavItem[] = [
  { name: 'lawyer', label: '律师工作台', to: '/lawyer', icon: ShieldPlus },
  { name: 'help', label: '维权帮助', to: '/help', icon: BookOpenText },
]

const adminNavigation: NavItem[] = [
  {
    name: 'admin',
    label: '管理后台',
    to: '/admin?section=overview',
    icon: UsersRound,
    children: [
      { name: 'admin-overview', label: '管理总览', to: '/admin?section=overview' },
      { name: 'admin-users', label: '用户管理', to: '/admin?section=users' },
      { name: 'admin-lawyers', label: '律师管理', to: '/admin?section=lawyers' },
      { name: 'admin-cases', label: '案件分配', to: '/admin?section=cases' },
      { name: 'admin-rules', label: '规则复核', to: '/admin?section=rules' },
      { name: 'admin-materials', label: '材料管理', to: '/admin?section=materials' },
      { name: 'admin-audit', label: '审计日志', to: '/admin?section=audit' },
      { name: 'admin-revenue', label: '收益管理', to: '/admin?section=revenue' },
    ],
  },
  { name: 'admin-help', label: '平台资源', to: '/help', icon: BookOpenText },
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
  auth.user?.role === 'lawyer'
    ? '只查看已分配案件'
    : auth.user?.role === 'admin'
      ? '平台配置与审计'
      : '人工协助随时可接入',
)
const supportDescription = computed(() =>
  auth.user?.role === 'lawyer'
    ? '案件材料访问会记录审计日志。'
    : auth.user?.role === 'admin'
      ? '权限变更、材料访问和账号操作均留痕。'
      : '复杂问题可申请本站律师复核。',
)

function isNavActive(to: string) {
  const target = router.resolve(to)
  if (route.path !== target.path) return false
  const section = target.query.section
  return typeof section !== 'string' || route.query.section === section
}

function logout() {
  auth.logout()
  void router.push('/login')
}
</script>
