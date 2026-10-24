<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
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
        :default-active="$route.path"
      >
        <el-menu-item index="/home">面试工作台</el-menu-item>
        <el-menu-item index="/interview">模拟面试</el-menu-item>
        <el-menu-item index="/records">面试记录</el-menu-item>
      </el-menu>
      <el-dropdown>
        <el-avatar class="avatar">U</el-avatar>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="router.push('/login')">退出登录</el-dropdown-item>
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
