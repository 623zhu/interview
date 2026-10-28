<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  listInterviewSessions,
  type InterviewSessionListItem,
  type SessionStatus,
} from '@/api/interview'
import { ApiError } from '@/api/http'
import AppHeader from '@/components/AppHeader.vue'
import { formatDateTime } from '@/utils/datetime'

const router = useRouter()
const loading = ref(false)
const sessions = ref<InterviewSessionListItem[]>([])
const statusFilter = ref<SessionStatus | 'all'>('all')

const difficultyLabel: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}
const statusLabel: Record<string, string> = {
  planned: '待开始',
  in_progress: '进行中',
  completed: '已完成',
  abandoned: '已放弃',
}
const statusType: Record<string, 'info' | 'warning' | 'success'> = {
  planned: 'info',
  in_progress: 'warning',
  completed: 'success',
  abandoned: 'info',
}

function formatTime(value: string) {
  return formatDateTime(value)
}

function openSession(row: InterviewSessionListItem) {
async function loadSessions() {
  loading.value = true
  try {
    sessions.value = await listInterviewSessions({
      status: statusFilter.value === 'all' ? undefined : statusFilter.value,
      limit: 100,
    })
  } catch (error) {
    sessions.value = []
    ElMessage.error(error instanceof ApiError ? error.message : '加载面试记录失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadSessions)
</script>

<template>
  <div class="layout">
    <AppHeader />

    <main v-loading="loading" class="main">
      <div class="content">
        <el-card class="panel" shadow="never">
          <div class="toolbar">
            <el-radio-group v-model="statusFilter" @change="loadSessions">
              <el-radio-button value="all">全部</el-radio-button>
              <el-radio-button value="in_progress">进行中</el-radio-button>
              <el-radio-button value="completed">已完成</el-radio-button>
              <el-radio-button value="abandoned">已放弃</el-radio-button>
            </el-radio-group>
            <el-button type="primary" @click="router.push('/interview')">开始新面试</el-button>
          </div>

          <el-table
            v-if="sessions.length"
            :data="sessions"
            empty-text="暂无记录"
            class="table"
            @row-click="openSession"
          >
            <el-table-column label="目标岗位" min-width="140">
              <template #default="{ row }">
                <span class="role-name">{{ row.target_role }}</span>
              </template>
            </el-table-column>
            <el-table-column label="难度" width="100">
              <template #default="{ row }">
                {{ difficultyLabel[row.difficulty] ?? row.difficulty }}
              </template>
            </el-table-column>
            <el-table-column label="面试时间" min-width="170">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="statusType[row.status] ?? 'info'" size="small">
                  {{ statusLabel[row.status] ?? row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="得分" width="110">
              <template #default="{ row }">
                <span v-if="row.score == null" class="score-empty">—</span>
                <span v-else class="score">
                  <strong>{{ row.score }}</strong><span>/100</span>
                </span>
              </template>
            </el-table-column>
            <el-table-column label="" width="120" align="right">
              <template #default="{ row }">
                <el-button link type="primary" @click.stop="openSession(row)">
                  {{ row.status === 'in_progress' ? '继续面试' : '查看详情' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-else description="还没有符合条件的面试记录">
            <el-button type="primary" @click="router.push('/interview')">去开始第一场</el-button>
          </el-empty>
        </el-card>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  background: #eef2f6;
}
.main {
  padding: 28px 24px 48px;
}
.content {
  max-width: 1080px;
  margin: 0 auto;
}
.panel {
  border-radius: 18px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.table {
  cursor: pointer;
  font-size: 14px;
  --el-table-header-text-color: var(--el-text-color-secondary);
}
.table :deep(th.el-table__cell) {
  font-size: 12px;
  font-weight: 500;
  background: transparent;
}
.table :deep(td.el-table__cell) {
  padding: 16px 0;
  color: var(--el-text-color-regular);
}
.role-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.score strong {
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}
.score span {
  margin-left: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.score-empty {
  color: var(--el-text-color-placeholder);
}
</style>
