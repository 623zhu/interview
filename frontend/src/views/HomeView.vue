<script setup lang="ts">
import {
  Monitor,
  VideoCamera,
  Document,
  DataAnalysis,
  Collection,
  Setting,
} from '@element-plus/icons-vue'
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">AI Interview</div>
      <el-menu default-active="home">
        <el-menu-item index="home">
          <el-icon><Monitor /></el-icon>
          <span>工作台</span>
        </el-menu-item>
        <el-menu-item index="interview">
          <el-icon><VideoCamera /></el-icon>
          <span>AI 模拟面试</span>
        </el-menu-item>
        <el-menu-item index="records">
          <el-icon><Document /></el-icon>
          <span>面试记录</span>
        </el-menu-item>
        <el-menu-item index="analysis">
          <el-icon><DataAnalysis /></el-icon>
          <span>能力分析</span>
        </el-menu-item>
        <el-menu-item index="questions">
          <el-icon><Collection /></el-icon>
          <span>面试题库</span>
        </el-menu-item>
        <el-menu-item index="settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span>面试工作台</span>
        <el-avatar>U</el-avatar>
      </el-header>

      <el-main class="main">
        <el-row :gutter="16">
          <el-col :span="16">
            <el-card shadow="never">开始面试</el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never">本周表现</el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16" class="metrics">
          <el-col :span="8">
            <el-card shadow="never">本周练习</el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never">累计面试</el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never">能力提升</el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  border-right: 1px solid var(--el-border-color-light);
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-weight: 600;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-light);
}
.main {
  background: #f5f7fa;
}
.metrics {
  margin-top: 16px;
}
</style>