<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Clock, Grid, MagicStick } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const activeIndex = computed(() =>
  route.path.startsWith('/interview') ? '/interview' : route.path,
)

async function onLogout() {
  await authStore.logout()
  await router.push('/login')
}
</script>

<template>
  <header class="header">
    <div class="header-inner">
      <div class="logo">AI Interview</div>
      <el-menu
        class="nav"
        mode="horizontal"
        router
        :ellipsis="false"
        :default-active="activeIndex"
      >
        <el-menu-item index="/home">
          <el-icon><Grid /></el-icon>
          <span>面试工作台</span>
        </el-menu-item>
        <el-menu-item index="/interview">
          <el-icon><MagicStick /></el-icon>
          <span>模拟面试</span>
        </el-menu-item>
        <el-menu-item index="/records">
          <el-icon><Clock /></el-icon>
          <span>面试记录</span>
        </el-menu-item>
      </el-menu>
      <el-dropdown>
        <el-avatar class="avatar">U</el-avatar>
        <template #dropdown>
          <el-dropdown-menu>
              <el-dropdown-item @click="onLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped>
.header {
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
}
.header-inner {
  max-width: 1080px;
  height: 60px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.logo {
  font-weight: 600;
  white-space: nowrap;
}
.nav {
  flex: 1;
  border-bottom: none;
}
.avatar {
  cursor: pointer;
}
</style>
