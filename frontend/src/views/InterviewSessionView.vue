<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  abandonInterviewSession,
  getInterviewSession,
  submitInterviewTurn,
  type InterviewSessionDetail,
} from '@/api/interview'
import { ApiError } from '@/api/http'
import AppHeader from '@/components/AppHeader.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const abandoning = ref(false)
const session = ref<InterviewSessionDetail | null>(null)
const answer = ref('')

const sessionId = computed(() => Number(route.params.id))
const inProgress = computed(() => session.value?.status === 'in_progress')
const difficultyLabel: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

async function loadSession() {
  if (!Number.isInteger(sessionId.value) || sessionId.value <= 0) {
    ElMessage.error('面试场次不存在')
    await router.replace('/interview')
    return
  }
  loading.value = true
  try {
    session.value = await getInterviewSession(sessionId.value)
  } catch (error) {
    session.value = null
    ElMessage.error(error instanceof ApiError ? error.message : '加载面试失败')
    if (error instanceof ApiError && error.status === 404) {
      await router.replace('/interview')
    }
  } finally {
    loading.value = false
  }
}

async function onSubmit() {
  const text = answer.value.trim()
  if (!text) {
    ElMessage.warning('请先填写回答')
    return
  }
  submitting.value = true
  try {
    const result = await submitInterviewTurn(sessionId.value, text)
    answer.value = ''
    await loadSession()
    if (result.status === 'completed') {
      ElMessage.success('本场面试已结束')
    }
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '提交回答失败')
  } finally {
    submitting.value = false
  }
}

async function onAbandon() {
  try {
    await ElMessageBox.confirm('中途退出后本场不能继续作答，也不会生成报告。', '结束本场面试', {
      type: 'warning',
      confirmButtonText: '结束面试',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  abandoning.value = true
  try {
    await abandonInterviewSession(sessionId.value)
    ElMessage.success('已结束本场面试')
    await router.push('/interview')
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '结束面试失败')
  } finally {
    abandoning.value = false
  }
}

onMounted(loadSession)
</script>

<template>
  <div class="layout">
    <AppHeader />

    <main v-loading="loading" class="main">
      <div v-if="session" class="content">
        <div class="intro">
          <div>
            <h1>{{ session.target_role }}</h1>
            <p>
              {{ difficultyLabel[session.difficulty] ?? session.difficulty }}
              ·
              {{ session.status === 'in_progress' ? '进行中' : session.status === 'completed' ? '已完成' : '已结束' }}
            </p>
          </div>
          <div class="intro-actions">
            <el-button @click="router.push('/interview')">返回设置</el-button>
            <el-button
              v-if="inProgress"
              :loading="abandoning"
              @click="onAbandon"
            >
              结束本场
            </el-button>
          </div>
        </div>

        <el-card
          v-for="turn in session.turns"
          :key="turn.seq"
          class="turn"
          shadow="never"
        >
          <div class="question">第 {{ turn.seq }} 问 · {{ turn.question }}</div>
          <div class="answer">{{ turn.answer }}</div>
        </el-card>

        <el-card v-if="inProgress && session.current_question" class="panel" shadow="never">
          <template #header>当前问题</template>
          <p class="current">{{ session.current_question }}</p>
          <el-input
            v-model="answer"
            type="textarea"
            :rows="6"
            maxlength="8000"
            show-word-limit
            :disabled="submitting"
            placeholder="结合简历和刚才的问题作答"
          />
          <el-button
            class="submit"
            type="primary"
            :loading="submitting"
            @click="onSubmit"
          >
            提交回答
          </el-button>
        </el-card>

        <el-card v-if="session.report" class="panel" shadow="never">
          <template #header>本场报告</template>
          <p class="score">总分 {{ session.report.score }}</p>
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
.intro-actions {
  display: flex;
  gap: 8px;
}
.panel,
.turn {
  margin-bottom: 16px;
  border-radius: 12px;
}
.question {
  font-weight: 600;
}
.answer {
  margin-top: 8px;
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
}
.current {
  margin: 0 0 16px;
  line-height: 1.6;
}
.submit {
  margin-top: 12px;
}
.score {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}
</style>
