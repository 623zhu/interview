import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginView from '@/views/LoginView.vue'
import HomeView from '@/views/HomeView.vue'
import SignUpView from '@/views/SignUpView.vue'
import ResetPasswordView from '@/views/ResetPasswordView.vue'
import InterviewView from '@/views/InterviewView.vue'
import RecordsView from '@/views/RecordsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginView, meta: { guest: true } },
    { path: '/home', component: HomeView, meta: { requiresAuth: true } },
    { path: '/interview', component: InterviewView, meta: { requiresAuth: true } },
    { path: '/records', component: RecordsView, meta: { requiresAuth: true } },
    { path: '/signup', component: SignUpView, meta: { guest: true } },
    { path: '/reset-password', component: ResetPasswordView, meta: { guest: true } },
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

export default router
