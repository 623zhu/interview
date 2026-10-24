<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <main class="page">
    <p>面试记录页即将接入。</p>
    <el-button type="primary" @click="router.push('/home')">返回工作台</el-button>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: #eef2f6;
}
</style>
