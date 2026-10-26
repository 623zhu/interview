<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  abandonInterviewSession,
  consumeSessionTypewriter,
  getInterviewSession,
  submitInterviewTurnStream,
  type InterviewSessionDetail,
  type InterviewTurnSubmitResponse,
} from '@/api/interview'
import { ApiError } from '@/api/http'
import AppHeader from '@/components/AppHeader.vue'

type ChatRole = 'interviewer' | 'user'

interface ChatMessage {
  id: string
  role: ChatRole
  text: string
  streaming?: boolean
  score?: number | null
  comment?: string | null
}

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const abandoning = ref(false)
const thinking = ref(false)
const typingIntro = ref(false)
const session = ref<InterviewSessionDetail | null>(null)
const messages = ref<ChatMessage[]>([])
const answer = ref('')
const threadRef = ref<HTMLElement | null>(null)

const sessionId = computed(() => Number(route.params.id))
const inProgress = computed(() => session.value?.status === 'in_progress')
const canSend = computed(
  () =>
    inProgress.value &&
    !submitting.value &&
    !thinking.value &&
    !typingIntro.value &&
    Boolean(answer.value.trim()),
)
const difficultyLabel: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}
const stageLabel: Record<string, string> = {
  intro: '开场',
  project_probe: '项目深挖',
  fundamentals: '基础',
  scenario: '场景',
  closing: '收尾',
}

let abortStream: AbortController | null = null
let typewriterToken = 0
let dripGen = 0
let dripBuffer = ''
let dripping = false

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function scrollToBottom() {
  await nextTick()
  const el = threadRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

function messagesFromSession(detail: InterviewSessionDetail): ChatMessage[] {
  const items: ChatMessage[] = []
  for (const turn of detail.turns) {
    items.push({
      id: `q-${turn.seq}`,
      role: 'interviewer',
      text: turn.question,
    })
    if (turn.answer) {
      items.push({
        id: `a-${turn.seq}`,
        role: 'user',
        text: turn.answer,
        score: turn.score,
        comment: turn.comment,
      })
    }
  }
  if (detail.current_question) {
    items.push({
      id: 'pending',
      role: 'interviewer',
      text: detail.current_question,
    })
  }
  return items
}

function nextUserSeq() {
  return messages.value.filter((item) => item.role === 'user').length + 1
}

function liveMessage() {
  return messages.value.find((item) => item.id === 'live')
}

function ensureLiveMessage() {
  if (!liveMessage()) {
    messages.value.push({
      id: 'live',
      role: 'interviewer',
      text: '',
      streaming: true,
    })
  }
}

function enqueueDrip(text: string, gen: number) {
  if (!text || gen !== dripGen) return
  thinking.value = false
  dripBuffer += text
  ensureLiveMessage()
  if (!dripping) {
    dripping = true
    void runDrip(gen)
  }
}

async function runDrip(gen: number) {
  try {
    while (dripBuffer.length && gen === dripGen) {
      const chunk = dripBuffer.slice(0, 1)
      dripBuffer = dripBuffer.slice(1)
      const live = liveMessage()
      if (live) {
        live.text += chunk
      }
      await scrollToBottom()
      await sleep(18)
    }
  } finally {
    if (gen === dripGen) {
      dripping = false
      if (dripBuffer.length) {
        dripping = true
        void runDrip(gen)
      }
    }
  }
}

async function finishDrip(gen: number, finalText?: string | null) {
  const live = liveMessage()
  if (finalText) {
    const current = live?.text ?? ''
    if (!current) {
      enqueueDrip(finalText, gen)
    } else if (finalText.startsWith(current) && finalText.length > current.length) {
      enqueueDrip(finalText.slice(current.length), gen)
    }
  }
  while (gen === dripGen && (dripping || dripBuffer.length)) {
    await sleep(16)
  }
  const done = liveMessage()
  if (done && gen === dripGen) {
    if (finalText) {
      done.text = finalText
    }
    done.streaming = false
  }
}

async function playTypewriter(full: string) {
  const token = ++typewriterToken
  const pending = messages.value.find((item) => item.id === 'pending')
  if (!pending) return
  pending.text = ''
  pending.streaming = true
  await scrollToBottom()
  for (const char of full) {
    if (token !== typewriterToken) return
    pending.text += char
    await scrollToBottom()
    await sleep(24)
  }
  if (token === typewriterToken) {
    pending.streaming = false
  }
}

async function loadSession() {
  if (!Number.isInteger(sessionId.value) || sessionId.value <= 0) {
    ElMessage.error('面试场次不存在')
    await router.replace('/interview')
    return
  }
  loading.value = true
  try {
    const detail = await getInterviewSession(sessionId.value)
    session.value = detail
    loading.value = false
    const shouldType = consumeSessionTypewriter(detail.id) && Boolean(detail.current_question)
    if (shouldType && detail.current_question) {
      typingIntro.value = true
      messages.value = messagesFromSession({ ...detail, current_question: '' })
      messages.value.push({
        id: 'pending',
        role: 'interviewer',
        text: '',
        streaming: true,
      })
      try {
        await playTypewriter(detail.current_question)
      } finally {
        typingIntro.value = false
      }
    } else {
      messages.value = messagesFromSession(detail)
      await scrollToBottom()
    }
  } catch (error) {
    session.value = null
    messages.value = []
    ElMessage.error(error instanceof ApiError ? error.message : '加载面试失败')
    if (error instanceof ApiError && error.status === 404) {
      await router.replace('/interview')
    }
  } finally {
    loading.value = false
  }
}

function applyDone(result: InterviewTurnSubmitResponse) {
  if (!session.value) return
  session.value = {
    ...session.value,
    status: result.status,
    current_question: result.current_turn?.question ?? null,
    report: result.report,
  }
  const live = liveMessage()
  if (live) {
    live.id = result.current_turn ? `q-${result.current_turn.seq}` : live.id
    live.streaming = false
  }
}

async function onSubmit() {
  const text = answer.value.trim()
  if (!text || !session.value || submitting.value) return

  const seq = nextUserSeq()
  messages.value.push({
    id: `a-${seq}`,
    role: 'user',
    text,
  })
  answer.value = ''
  submitting.value = true
  thinking.value = true
  dripGen += 1
  const gen = dripGen
  dripBuffer = ''
  dripping = false
  await scrollToBottom()

  abortStream?.abort()
  abortStream = new AbortController()
  let completed = false

  try {
    await submitInterviewTurnStream(
      sessionId.value,
      text,
      async (event, data) => {
        if (event === 'status') {
          thinking.value = true
          return
        }
        if (event === 'delta') {
          const piece = typeof data === 'object' && data && 'text' in data ? String((data as { text: string }).text) : ''
          enqueueDrip(piece, gen)
          return
        }
        if (event === 'done') {
          thinking.value = false
          const result = data as InterviewTurnSubmitResponse
          await finishDrip(gen, result.current_turn?.question)
          applyDone(result)
          completed = result.status === 'completed'
          return
        }
        if (event === 'error') {
          const detail =
            typeof data === 'object' && data && 'detail' in data
              ? String((data as { detail: string }).detail)
              : '处理本轮回答失败'
          throw new ApiError(500, detail)
        }
      },
      abortStream.signal,
    )
    if (completed) {
      ElMessage.success('本场面试已结束')
      await loadSession()
    } else {
      await scrollToBottom()
    }
  } catch (error) {
    if ((error as { name?: string }).name === 'AbortError') return
    thinking.value = false
    ElMessage.error(error instanceof ApiError ? error.message : '提交回答失败')
    await loadSession()
  } finally {
    submitting.value = false
    thinking.value = false
    abortStream = null
  }
}

function onComposerKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void onSubmit()
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
    abortStream?.abort()
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
onUnmounted(() => {
  typewriterToken += 1
  dripGen += 1
  abortStream?.abort()
})
</script>

<template>
  <div class="layout">
    <AppHeader />

    <main v-loading="loading" class="main">
      <div v-if="session" class="stage">
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
            <el-button @click="router.push(inProgress ? '/interview' : '/records')">
              {{ inProgress ? '返回设置' : '返回记录' }}
            </el-button>
            <el-button
              v-if="inProgress"
              :loading="abandoning"
              @click="onAbandon"
            >
              结束本场
            </el-button>
          </div>
        </div>

        <div ref="threadRef" class="thread">
          <div
            v-for="item in messages"
            :key="item.id"
            class="row"
            :class="item.role"
          >
            <div class="avatar">{{ item.role === 'interviewer' ? '面' : '我' }}</div>
            <div class="col">
              <div class="bubble" :class="{ streaming: item.streaming }">
                {{ item.text }}<span v-if="item.streaming" class="caret" />
              </div>
              <p v-if="item.comment" class="meta">{{ item.comment }}</p>
            </div>
          </div>

          <div v-if="thinking" class="row interviewer">
            <div class="avatar">面</div>
            <div class="bubble thinking">
              <span class="dot" />
              <span class="dot" />
              <span class="dot" />
            </div>
          </div>

          <div v-if="session.report" class="report">
            <div class="report-title">本场报告</div>
            <p class="score">总分 {{ session.report.score }}</p>
            <div v-if="session.report.stages.length" class="stages">
              <span v-for="item in session.report.stages" :key="item.kind" class="stage">
                {{ stageLabel[item.kind] ?? item.kind }} {{ item.score }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="inProgress" class="composer">
          <el-input
            v-model="answer"
            type="textarea"
            :rows="3"
            maxlength="8000"
            show-word-limit
            resize="none"
            :disabled="submitting || typingIntro"
            placeholder="结合简历和刚才的问题作答，Enter 发送，Shift+Enter 换行"
            @keydown="onComposerKeydown"
          />
          <el-button
            type="primary"
            :loading="submitting"
            :disabled="!canSend"
            @click="onSubmit"
          >
            发送
          </el-button>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #eef2f6;
}
.main {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.stage {
  flex: 1;
  min-height: 0;
  width: min(100%, 860px);
  margin: 0 auto;
  padding: 20px 24px 24px;
  display: flex;
  flex-direction: column;
}
.intro {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.intro h1 {
  margin: 0;
  font-size: 22px;
}
.intro p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
}
.intro-actions {
  display: flex;
  gap: 8px;
}
.thread {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px 4px 24px;
}
.row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  max-width: 100%;
}
.row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  background: #dbe4ee;
  color: #334155;
}
.row.user .avatar {
  background: #1677ff;
  color: #fff;
}
.col {
  max-width: min(72%, 560px);
}
.bubble {
  padding: 10px 14px;
  border-radius: 18px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}
.row.user .bubble {
  background: #1677ff;
  color: #fff;
  border-bottom-right-radius: 6px;
}
.row.interviewer .bubble {
  border-bottom-left-radius: 6px;
}
.bubble.thinking {
  display: flex;
  gap: 5px;
  align-items: center;
  min-height: 22px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #94a3b8;
  animation: pulse 1s infinite ease-in-out;
}
.dot:nth-child(2) {
  animation-delay: 0.15s;
}
.dot:nth-child(3) {
  animation-delay: 0.3s;
}
.caret {
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  background: currentColor;
  vertical-align: -2px;
  animation: blink 1s step-end infinite;
}
.meta {
  margin: 6px 2px 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}
.report {
  margin: 8px 0 16px;
  padding: 16px 18px;
  background: #fff;
  border-radius: 12px;
}
.report-title {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.score {
  margin: 8px 0 0;
  font-size: 22px;
  font-weight: 600;
}
.stages {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.stage {
  padding: 4px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.composer {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding: 12px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}
.composer :deep(.el-textarea) {
  flex: 1;
}
.composer :deep(.el-textarea__inner) {
  box-shadow: none;
  background: #f8fafc;
}
@keyframes pulse {
  0%,
  80%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-2px);
  }
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>
