<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Bottom, DataAnalysis, Timer, Top, TrendCharts, Trophy } from '@element-plus/icons-vue'
import {
  TARGET_ROLES,
  listInterviewSessions,
  type InterviewSessionListItem,
  type ScoredStageKind,
  type TargetRole,
} from '@/api/interview'
import { ApiError } from '@/api/http'
import AppHeader from '@/components/AppHeader.vue'
import { formatRelativeDateTime, parseUtcDate } from '@/utils/datetime'

const DAY_MS = 24 * 60 * 60 * 1000
const RING_RADIUS = 52
const RING_LENGTH = 2 * Math.PI * RING_RADIUS

const router = useRouter()
const loading = ref(false)
const sessions = ref<InterviewSessionListItem[]>([])
const targetRole = ref<TargetRole>('Python 后端')

const stageMeta: { kind: ScoredStageKind; label: string; color: string; advice: string }[] = [
  {
    kind: 'project_probe',
    label: '项目深挖',
    color: '#6d5df6',
    advice: '项目深挖偏弱。讲清你负责的部分、关键取舍和量化结果。',
  },
  {
    kind: 'fundamentals',
    label: '基础',
    color: '#2bb39a',
    advice: '基础偏弱。原理要讲到机制和边界条件，别停在名词上。',
  },
  {
    kind: 'scenario',
    label: '场景',
    color: '#f59a5b',
    advice: '场景题偏弱。先说思路和取舍，再落到具体方案和兜底。',
  },
]

function startOfWeek(date: Date) {
  const start = new Date(date)
  const day = start.getDay()
  const offset = day === 0 ? 6 : day - 1
  start.setHours(0, 0, 0, 0)
  start.setDate(start.getDate() - offset)
  return start
}

function createdMs(item: InterviewSessionListItem) {
  return parseUtcDate(item.created_at).getTime()
}

function isScored(item: InterviewSessionListItem) {
  return item.status === 'completed' && item.score != null
}

function average(values: number[]) {
  if (!values.length) return null
  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length)
}

function averageScore(items: InterviewSessionListItem[]) {
  return average(items.filter(isScored).map((item) => item.score ?? 0))
}

const weekStartMs = computed(() => startOfWeek(new Date()).getTime())
const lastWeekStartMs = computed(() => weekStartMs.value - 7 * DAY_MS)

const weekSessions = computed(() =>
  sessions.value.filter((item) => createdMs(item) >= weekStartMs.value),
)
const lastWeekSessions = computed(() =>
  sessions.value.filter((item) => {
    const ms = createdMs(item)
    return ms >= lastWeekStartMs.value && ms < weekStartMs.value
  }),
)

const weekScore = computed(() => averageScore(weekSessions.value))
const weekScoreDelta = computed(() => {
  const last = averageScore(lastWeekSessions.value)
  if (weekScore.value == null || last == null) return null
  return weekScore.value - last
})
const ringOffset = computed(() => RING_LENGTH * (1 - (weekScore.value ?? 0) / 100))

const weekStages = computed(() =>
  stageMeta.map((meta) => {
    const values = weekSessions.value
      .filter(isScored)
      .flatMap((item) => item.stages.filter((stage) => stage.kind === meta.kind))
      .map((stage) => stage.score)
    return { ...meta, score: average(values) }
  }),
)

const advice = computed(() => {
  const scored = weekStages.value.filter((item) => item.score != null)
  if (!scored.length) return '完成一场面试后，这里会按项目深挖、基础、场景给出建议。'
  const weakest = scored.reduce((low, item) => ((item.score ?? 0) < (low.score ?? 0) ? item : low))
  if ((weakest.score ?? 0) >= 80) return '三项都比较稳，可以试试更高难度。'
  return weakest.advice
})

const weekCount = computed(() => weekSessions.value.length)
const weekCountDelta = computed(() => weekCount.value - lastWeekSessions.value.length)
const totalCount = computed(() => sessions.value.length)
const completedCount = computed(
  () => sessions.value.filter((item) => item.status === 'completed').length,
)

const improvement = computed(() => {
  const now = Date.now()
  const recent = sessions.value.filter((item) => createdMs(item) >= now - 30 * DAY_MS)
  const before = sessions.value.filter((item) => {
    const ms = createdMs(item)
    return ms >= now - 60 * DAY_MS && ms < now - 30 * DAY_MS
  })
  const recentAvg = averageScore(recent)
  const beforeAvg = averageScore(before)
  if (recentAvg == null || beforeAvg == null) return null
  return recentAvg - beforeAvg
})

const bestSession = computed(() =>
  sessions.value
    .filter(isScored)
    .reduce<InterviewSessionListItem | null>(
      (best, item) => (best == null || (item.score ?? 0) > (best.score ?? 0) ? item : best),
      null,
    ),
)

const activeSession = computed(
  () => sessions.value.find((item) => item.status === 'in_progress') ?? null,
)
const recentSessions = computed(() => sessions.value.slice(0, 3))

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

function signed(value: number) {
  return value > 0 ? `+${value}` : String(value)
}

function openSession(row: InterviewSessionListItem) {
  void router.push(`/interview/${row.id}`)
}

function startInterview() {
  void router.push({ path: '/interview', query: { role: targetRole.value } })
}

function formatTime(value: string) {
  return formatRelativeDateTime(value)
}

async function loadSessions() {
  loading.value = true
  try {
    sessions.value = await listInterviewSessions()
    const lastRole = TARGET_ROLES.find((role) => role === sessions.value[0]?.target_role)
    if (lastRole) targetRole.value = lastRole
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
        <section class="top">
          <div class="hero">
            <div class="hero-glow hero-glow-a" />
            <div class="hero-glow hero-glow-b" />

            <button
              v-if="activeSession"
              type="button"
              class="hero-chip hero-chip-action"
              @click="openSession(activeSession)"
            >
              <span class="dot dot-warning" />
              有 1 场面试未完成，点此继续
            </button>
            <div v-else class="hero-chip">
              <span class="dot" />
              AI 面试官已就绪
            </div>

            <h1>下一场面试，从更好的回答开始</h1>
            <p class="hero-desc">
              选择目标岗位，AI 会结合你的简历出题、追问，结束后按项目深挖、基础、场景给出评分。
            </p>

            <div class="hero-actions">
              <div class="role-select">
                <span class="role-label">目标岗位</span>
                <el-select v-model="targetRole" class="role-input" popper-class="role-popper">
                  <el-option v-for="role in TARGET_ROLES" :key="role" :label="role" :value="role" />
                </el-select>
              </div>
              <button type="button" class="start-btn" @click="startInterview">
                开始模拟面试
                <el-icon><ArrowRight /></el-icon>
              </button>
            </div>
          </div>

          <div class="perf">
            <div class="perf-header">
              <span class="perf-title">本周表现</span>
              <span
                v-if="weekScoreDelta != null"
                class="perf-badge"
                :class="{ down: weekScoreDelta < 0 }"
              >
                <el-icon><component :is="weekScoreDelta < 0 ? Bottom : Top" /></el-icon>
                {{ Math.abs(weekScoreDelta) }} 分
              </span>
            </div>

            <div class="perf-body">
              <div class="ring">
                <svg viewBox="0 0 120 120">
                  <circle class="ring-track" cx="60" cy="60" :r="RING_RADIUS" />
                  <circle
                    class="ring-bar"
                    cx="60"
                    cy="60"
                    :r="RING_RADIUS"
                    :stroke-dasharray="RING_LENGTH"
                    :stroke-dashoffset="ringOffset"
                  />
                </svg>
                <div class="ring-text">
                  <div class="ring-score">
                    {{ weekScore ?? '—' }}<span v-if="weekScore != null">分</span>
                  </div>
                  <div class="ring-label">综合表现</div>
                </div>
              </div>

              <div class="bars">
                <div v-for="item in weekStages" :key="item.kind" class="bar">
                  <div class="bar-head">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.score ?? '—' }}</strong>
                  </div>
                  <div class="bar-track">
                    <div
                      class="bar-fill"
                      :style="{ width: `${item.score ?? 0}%`, background: item.color }"
                    />
                  </div>
                </div>
              </div>
            </div>

            <p class="advice"><strong>建议：</strong>{{ advice }}</p>
          </div>
        </section>

        <section class="stats">
          <div class="stat">
            <div class="stat-icon icon-purple"><el-icon><Timer /></el-icon></div>
            <div class="stat-main">
              <div class="stat-label">本周练习</div>
              <div class="stat-value">{{ weekCount }} 场</div>
            </div>
            <div class="stat-hint">较上周 {{ signed(weekCountDelta) }}</div>
          </div>

          <div class="stat">
            <div class="stat-icon icon-green"><el-icon><DataAnalysis /></el-icon></div>
            <div class="stat-main">
              <div class="stat-label">累计面试</div>
              <div class="stat-value">{{ totalCount }} 场</div>
            </div>
            <div class="stat-hint">已完成 {{ completedCount }} 场</div>
          </div>

          <div class="stat">
            <div class="stat-icon icon-orange"><el-icon><TrendCharts /></el-icon></div>
            <div class="stat-main">
              <div class="stat-label">能力提升</div>
              <div class="stat-value">
                {{ improvement == null ? '—' : `${signed(improvement)} 分` }}
              </div>
            </div>
            <div class="stat-hint">近 30 天对比</div>
          </div>

          <div class="stat">
            <div class="stat-icon icon-blue"><el-icon><Trophy /></el-icon></div>
            <div class="stat-main">
              <div class="stat-label">最高得分</div>
              <div class="stat-value">{{ bestSession?.score ?? '—' }}<template v-if="bestSession"> 分</template></div>
            </div>
            <div class="stat-hint">{{ bestSession?.target_role ?? '暂无' }}</div>
          </div>
        </section>

        <el-card class="records" shadow="never">
          <template #header>
            <div class="records-header">
              <div>
                <div class="records-title">最近面试</div>
                <p>回顾表现，持续迭代你的回答</p>
              </div>
              <el-link
                class="records-more"
                type="primary"
                :underline="false"
                @click="router.push('/records')"
              >
                查看全部<el-icon><ArrowRight /></el-icon>
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

          <el-empty v-else description="还没有面试记录">
            <el-button type="primary" @click="startInterview">去开始第一场</el-button>
          </el-empty>
        </el-card>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  background: linear-gradient(180deg, #dff3f4 0%, #eef2f6 320px);
}
.main {
  padding: 28px 24px 48px;
}
.content {
  max-width: 1080px;
  margin: 0 auto;
}

.top {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(300px, 1fr);
  gap: 18px;
}

.hero {
  position: relative;
  overflow: hidden;
  padding: 28px 30px 32px;
  border-radius: 22px;
  color: #fff;
  background: linear-gradient(135deg, #17172a 0%, #23264a 100%);
}
.hero-glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}
.hero-glow-a {
  top: -90px;
  right: -60px;
  width: 280px;
  height: 280px;
  background: rgba(99, 102, 241, 0.22);
}
.hero-glow-b {
  bottom: -160px;
  right: 80px;
  width: 300px;
  height: 300px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.hero > *:not(.hero-glow) {
  position: relative;
}
.hero-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
}
.hero-chip-action {
  cursor: pointer;
  font-family: inherit;
}
.hero-chip-action:hover {
  background: rgba(255, 255, 255, 0.12);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #7ef0a8;
}
.dot-warning {
  background: #fbbf24;
}
.hero h1 {
  margin: 20px 0 0;
  font-size: 30px;
  line-height: 1.3;
}
.hero-desc {
  max-width: 420px;
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.68);
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 12px;
  margin-top: 28px;
}
.role-select {
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 176px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
}
.role-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
}
.role-input :deep(.el-select__wrapper) {
  padding: 0;
  min-height: 28px;
  background: transparent;
  box-shadow: none;
}
.role-input :deep(.el-select__selected-item) {
  font-size: 16px;
  color: #fff;
}
.role-input :deep(.el-select__caret) {
  color: rgba(255, 255, 255, 0.6);
}
.start-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 0 24px;
  min-height: 58px;
  font-family: inherit;
  font-size: 16px;
  font-weight: 600;
  color: #14261c;
  background: #7ef0a8;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.start-btn:hover {
  background: #9cf5bd;
}

.perf {
  display: flex;
  flex-direction: column;
  padding: 22px 22px 20px;
  background: #fff;
  border-radius: 22px;
  box-shadow: 0 8px 28px rgba(31, 42, 55, 0.06);
}
.perf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.perf-title {
  font-size: 16px;
  font-weight: 600;
}
.perf-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 600;
  color: #16a34a;
  background: #e8f8ee;
  border-radius: 8px;
}
.perf-badge.down {
  color: #dc2626;
  background: #fdecec;
}
.perf-body {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-top: 18px;
}
.ring {
  position: relative;
  flex: none;
  width: 116px;
  height: 116px;
}
.ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.ring-track,
.ring-bar {
  fill: none;
  stroke-width: 12;
}
.ring-track {
  stroke: #ecebfd;
}
.ring-bar {
  stroke: #6d5df6;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.6s ease;
}
.ring-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.ring-score {
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
}
.ring-score span {
  margin-left: 2px;
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}
.ring-label {
  margin-top: 4px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
}
.bars {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.bar-head {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.bar-track {
  height: 6px;
  margin-top: 6px;
  overflow: hidden;
  background: #f0f1f5;
  border-radius: 999px;
}
.bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.6s ease;
}
.advice {
  margin: 18px 0 0;
  padding-top: 14px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
  border-top: 1px solid #f0f1f5;
}
.advice strong {
  color: #6d5df6;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin: 18px 0;
}
.stat {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 6px 20px rgba(31, 42, 55, 0.05);
}
.stat-icon {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  font-size: 20px;
  border-radius: 12px;
}
.icon-purple {
  color: #6d5df6;
  background: #efedfe;
}
.icon-green {
  color: #2bb39a;
  background: #e4f6f2;
}
.icon-orange {
  color: #f08a4b;
  background: #fdefe5;
}
.icon-blue {
  color: #3b82f6;
  background: #e8f1fe;
}
.stat-main {
  flex: 1;
  min-width: 0;
}
.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.stat-value {
  margin-top: 4px;
  font-size: 22px;
  font-weight: 700;
  white-space: nowrap;
}
.stat-hint {
  align-self: flex-end;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.records {
  border-radius: 18px;
}
.records-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.records-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}
.records-header p {
  margin: 4px 0 0;
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}
.records-more {
  font-size: 14px;
  font-weight: 500;
}
.records-more .el-icon {
  margin-left: 2px;
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

@media (max-width: 960px) {
  .top {
    grid-template-columns: 1fr;
  }
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 560px) {
  .stats {
    grid-template-columns: 1fr;
  }
  .hero h1 {
    font-size: 24px;
  }
}
</style>
