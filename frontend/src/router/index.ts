import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '../layouts/AppLayout.vue'
import { useAuthStore } from '../stores/auth'
import AdminDashboardView from '../views/AdminDashboardView.vue'
import CaseDetailView from '../views/CaseDetailView.vue'
import CasesView from '../views/CasesView.vue'
import HelpCenterView from '../views/HelpCenterView.vue'
import LawyerDashboardView from '../views/LawyerDashboardView.vue'
import LoginView from '../views/LoginView.vue'
import ModulePlaceholderView from '../views/ModulePlaceholderView.vue'
import SimulationView from '../views/SimulationView.vue'
import WorkspaceView from '../views/WorkspaceView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { title: '登录' },
    },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'workspace',
          component: WorkspaceView,
          meta: { title: 'AI 法律咨询' },
        },
        {
          path: 'cases',
          name: 'cases',
          component: CasesView,
          meta: { title: '我的案件' },
        },
        {
          path: 'cases/:id',
          name: 'case-detail',
          component: CaseDetailView,
          meta: { title: '案件工作台' },
        },
        {
          path: 'evidence',
          name: 'evidence',
          component: ModulePlaceholderView,
          meta: {
            title: '证据整理',
            eyebrow: '材料中心',
            description: '后续将支持聊天记录、合同、工资流水等材料上传、筛查和评估。',
          },
        },
        {
          path: 'simulation',
          name: 'simulation',
          component: SimulationView,
          meta: { title: '模拟对话' },
        },
        {
          path: 'help',
          name: 'help',
          component: HelpCenterView,
          meta: { title: '维权帮助' },
        },
        {
          path: 'lawyer',
          name: 'lawyer',
          component: LawyerDashboardView,
          meta: { title: '律师工作台', roles: ['lawyer', 'admin'] },
        },
        {
          path: 'admin',
          name: 'admin',
          component: AdminDashboardView,
          meta: { title: '管理后台', roles: ['admin'] },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.token) {
    return { name: 'workspace' }
  }
  const roles = to.meta.roles
  if (Array.isArray(roles) && auth.user && !roles.includes(auth.user.role)) {
    return { name: 'workspace' }
  }
  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : '劳动法律服务工作台'
  document.title = `${title} · 劳务通`
})

export default router
