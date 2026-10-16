import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import HomeView from '@/views/HomeView.vue'
import SignUpView from '@/views/SignUpView.vue'
import ResetPasswordView from '@/views/ResetPasswordView.vue'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {path:'/',redirect:'/login'},
    {path:'/login',component:LoginView},
    {path:'/home',component:HomeView},
    { path: '/signup', component: SignUpView },
  { path: '/reset-password', component: ResetPasswordView },
  ],
})

export default router
