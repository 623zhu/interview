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
  void router.push(`/interview/${row.id}`)
}

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
        <div class="intro">
          <div>
            <h1>面试记录</h1>
            <p>查看自己的场次、分数和问答详情。进行中的可以继续作答。</p>
          </div>
          <el-button type="primary" @click="router.push('/interview')">开始新面试</el-button>
        </div>

        <el-card class="panel" shadow="never">
          <div class="toolbar">
            <el-radio-group v-model="statusFilter" @change="loadSessions">
              <el-radio-button value="all">全部</el-radio-button>
              <el-radio-button value="in_progress">进行中</el-radio-button>
              <el-radio-button value="completed">已完成</el-radio-button>
              <el-radio-button value="abandoned">已放弃</el-radio-button>
            </el-radio-group>
          </div>

          <el-table
            v-if="sessions.length"
            :data="sessions"
            empty-text="暂无记录"
            class="table"
            @row-click="openSession"
          >
            <el-table-column prop="target_role" label="目标岗位" min-width="140" />
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
            <el-table-column label="得分" width="90">
              <template #default="{ row }">
                {{ row.score == null ? '—' : row.score }}
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
.intro {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.intro h1 {
  margin: 0;
  font-size: 26px;
}
.intro p {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
}
.panel {
  border-radius: 12px;
}
.toolbar {
  margin-bottom: 16px;
}
.table {
  cursor: pointer;
}
</style>
