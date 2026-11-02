import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '../layouts/AppLayout.vue'
import { useAuthStore } from '../stores/auth'

const LoginView = () => import('../views/LoginView.vue')
const WorkspaceView = () => import('../views/WorkspaceView.vue')
const CasesView = () => import('../views/CasesView.vue')
const CaseDetailView = () => import('../views/CaseDetailView.vue')
const SimulationView = () => import('../views/SimulationView.vue')
const HelpCenterView = () => import('../views/HelpCenterView.vue')
const ProfileView = () => import('../views/ProfileView.vue')
const LawyerDashboardView = () => import('../views/LawyerDashboardView.vue')
const AdminDashboardView = () => import('../views/AdminDashboardView.vue')

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
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
          redirect: '/cases',
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
          path: 'profile',
          name: 'profile',
          component: ProfileView,
          meta: { title: '账户资料', roles: ['user'] },
        },
        {
          path: 'lawyer',
          name: 'lawyer',
          component: LawyerDashboardView,
          meta: { title: '律师工作台', roles: ['lawyer'] },
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
