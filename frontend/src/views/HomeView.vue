<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { listInterviewSessions, type InterviewSessionListItem } from '@/api/interview'
import { ApiError } from '@/api/http'
import AppHeader from '@/components/AppHeader.vue'
import { formatRelativeDateTime, parseUtcDate } from '@/utils/datetime'

const router = useRouter()
const loading = ref(false)
const sessions = ref<InterviewSessionListItem[]>([])

const weekdayLabels = ['日', '一', '二', '三', '四', '五', '六']
const todayLabel = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 · 星期${weekdayLabels[now.getDay()]}`
})

function startOfWeek(date: Date) {
  const start = new Date(date)
  const day = start.getDay()
  const offset = day === 0 ? 6 : day - 1
  start.setHours(0, 0, 0, 0)
  start.setDate(start.getDate() - offset)
  return start
}

const weekSessions = computed(() => {
  const weekStart = startOfWeek(new Date()).getTime()
  return sessions.value.filter((item) => parseUtcDate(item.created_at).getTime() >= weekStart)
})

const weekCount = computed(() => weekSessions.value.length)
const totalCount = computed(() => sessions.value.length)
const inProgressCount = computed(
  () => sessions.value.filter((item) => item.status === 'in_progress').length,
)
const weekScore = computed(() => {
  const scored = weekSessions.value.filter(
    (item) => item.status === 'completed' && item.score != null,
  )
  if (!scored.length) return null
  const sum = scored.reduce((total, item) => total + (item.score ?? 0), 0)
  return Math.round(sum / scored.length)
})
const recentSessions = computed(() => sessions.value.slice(0, 5))

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

function openSession(row: InterviewSessionListItem) {
  void router.push(`/interview/${row.id}`)
}

function formatTime(value: string) {
  return formatRelativeDateTime(value)
}

async function loadSessions() {
  loading.value = true
  try {
    sessions.value = await listInterviewSessions()
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
        <p class="date">{{ todayLabel }}</p>
        <div class="intro">
          <div>
            <h1>面试工作台</h1>
            <p>用每一次练习，看清自己离目标岗位还有多远。</p>
          </div>
          <el-button type="primary" :icon="ArrowRight" @click="router.push('/interview')">
            快速开始面试
          </el-button>
        </div>

        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="metric" shadow="never">
              <div class="metric-label">本周面试</div>
              <div class="metric-value">{{ weekCount }}<span>场</span></div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="metric" shadow="never">
              <div class="metric-label">累计面试</div>
              <div class="metric-value">{{ totalCount }}<span>场</span></div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="metric" shadow="never">
              <div class="metric-label">本周表现</div>
              <div class="metric-value">{{ weekScore ?? '—' }}<span v-if="weekScore != null">分</span></div>
              <p class="metric-hint">本周已完成场次的平均分</p>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="metric" shadow="never">
              <div class="metric-label">进行中</div>
              <div class="metric-value">{{ inProgressCount }}<span>场</span></div>
            </el-card>
          </el-col>
        </el-row>

        <el-card class="records" shadow="never">
          <template #header>
            <div class="records-header">
              <div>
                <div>最近面试</div>
                <p>查看最近几场练习，完整列表在面试记录里。</p>
              </div>
              <el-link type="primary" :underline="false" @click="router.push('/records')">
                查看全部
              </el-link>
            </div>
          </template>

          <el-table
            v-if="recentSessions.length"
            class="table"
            :data="recentSessions"
            empty-text="暂无记录"
            @row-click="openSession"
          >
            <el-table-column prop="target_role" label="目标岗位" min-width="140" />
            <el-table-column label="难度" width="100">
              <template #default="{ row }">
                {{ difficultyLabel[row.difficulty] ?? row.difficulty }}
              </template>
            </el-table-column>
            <el-table-column label="面试时间" min-width="140">
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
                <el-button
                  link
                  type="primary"
                  @click.stop="openSession(row)"
                >
                  {{ row.status === 'in_progress' ? '继续面试' : '查看详情' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-else description="还没有面试记录">
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
.date {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
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
.metric {
  margin-bottom: 16px;
  border-radius: 12px;
  min-height: 120px;
}
.metric-label {
  color: var(--el-text-color-secondary);
}
.metric-value {
  margin-top: 8px;
  font-size: 32px;
  font-weight: 600;
  line-height: 1.2;
}
.metric-value span {
  margin-left: 4px;
  font-size: 14px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}
.metric-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.records {
  border-radius: 12px;
}
.records-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.records-header p {
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}
.table {
  cursor: pointer;
}
</style>
