import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginView from '@/views/LoginView.vue'
import HomeView from '@/views/HomeView.vue'
import SignUpView from '@/views/SignUpView.vue'
import ResetPasswordView from '@/views/ResetPasswordView.vue'
import InterviewView from '@/views/InterviewView.vue'
import InterviewSessionView from '@/views/InterviewSessionView.vue'
import RecordsView from '@/views/RecordsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginView, meta: { guest: true, title: '登录' } },
    { path: '/home', component: HomeView, meta: { requiresAuth: true, title: '面试工作台' } },
    { path: '/interview', component: InterviewView, meta: { requiresAuth: true, title: '模拟面试' } },
    { path: '/interview/:id', component: InterviewSessionView, meta: { requiresAuth: true, title: '面试中' } },
    { path: '/records', component: RecordsView, meta: { requiresAuth: true, title: '面试记录' } },
    { path: '/signup', component: SignUpView, meta: { guest: true, title: '注册' } },
    { path: '/reset-password', component: ResetPasswordView, meta: { guest: true, title: '重置密码' } },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.accessToken) {
    return '/login'
  }
  if (to.meta.guest && auth.accessToken) {
    return '/home'
  }
})

router.afterEach((to) => {
  const page = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = page ? `${page} · 智面` : '智面'
})

export default router
