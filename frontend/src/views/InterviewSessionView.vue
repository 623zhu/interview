<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  abandonInterviewSession,
  consumeSessionTypewriter,
  getInterviewSession,
  submitInterviewTurn,
  submitInterviewTurnStream,
  type InterviewSessionDetail,
  type InterviewTurnSubmitResponse,
} from '@/api/interview'
import { ApiError } from '@/api/http'
import AppHeader from '@/components/AppHeader.vue'

type ChatRole = 'interviewer' | 'user'

interface ChatMessage {
  uid: string
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
const holdingClose = ref(false)
const session = ref<InterviewSessionDetail | null>(null)
const messages = ref<ChatMessage[]>([])
const answer = ref('')
const threadRef = ref<HTMLElement | null>(null)

const sessionId = computed(() => Number(route.params.id))
const inProgress = computed(() => session.value?.status === 'in_progress')
const canSend = computed(
  () =>
    inProgress.value &&
    !holdingClose.value &&
    !submitting.value &&
    !thinking.value &&
    !typingIntro.value &&
    Boolean(answer.value.trim()),
)
const CLOSING_QUESTION = '今天的面试先到这里，你有想问我的吗？'
const CLOSING_HOLD_MS = 3000
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

const DRIP_MS = 24

let abortStream: AbortController | null = null
let typewriterToken = 0
let dripGen = 0
let dripBuffer = ''
let dripping = false
let messageUid = 0
let closingHoldToken = 0

function isClosingQuestion(text: string | null | undefined) {
  return (text ?? '').trim() === CLOSING_QUESTION
}

function nextMessageUid(prefix: string) {
  messageUid += 1
  return `${prefix}-${messageUid}`
}

function noteBody(comment: string | null | undefined) {
  return (comment ?? '').trim().replace(/^本轮\s*\d+\s*分[。.]?\s*/, '')
}

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
      uid: `q-${turn.seq}`,
      id: `q-${turn.seq}`,
      role: 'interviewer',
      text: turn.question,
    })
    if (turn.answer) {
      items.push({
        uid: `a-${turn.seq}`,
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
      uid: 'pending',
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
      uid: nextMessageUid('live'),
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
      await sleep(DRIP_MS)
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

async function waitDrip(gen: number) {
  while (gen === dripGen && (dripping || dripBuffer.length)) {
    await sleep(16)
  }
}

async function finishDrip(gen: number, finalText?: string | null) {
  await waitDrip(gen)
  const live = liveMessage()
  const current = live?.text ?? ''
  if (finalText && !current) {
    enqueueDrip(finalText, gen)
    await waitDrip(gen)
  }
  const done = liveMessage()
  if (done && gen === dripGen) {
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
        uid: 'pending',
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
      if (detail.status === 'in_progress' && isClosingQuestion(detail.current_question)) {
        void autoEndClosing()
      }
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

async function revealEnded(result?: InterviewTurnSubmitResponse) {
  const token = ++closingHoldToken
  holdingClose.value = true
  await sleep(CLOSING_HOLD_MS)
  if (token !== closingHoldToken) return
  if (result) {
    applyDone(result)
  }
  ElMessage.success('本场面试已结束')
  await loadSession()
  holdingClose.value = false
}

async function autoEndClosing() {
  const token = ++closingHoldToken
  holdingClose.value = true
  await sleep(CLOSING_HOLD_MS)
  if (token !== closingHoldToken) return
  submitting.value = true
  try {
    const result = await submitInterviewTurn(sessionId.value, '')
    applyDone(result)
    ElMessage.success('本场面试已结束')
    await loadSession()
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '结束面试失败')
  } finally {
    submitting.value = false
    if (token === closingHoldToken) {
      holdingClose.value = false
    }
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
    uid: `a-${seq}`,
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
  let doneResult: InterviewTurnSubmitResponse | null = null

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
        if (event === 'error') {
          const detail =
            typeof data === 'object' && data && 'detail' in data
              ? String((data as { detail: string }).detail)
              : '处理本轮回答失败'
          throw new ApiError(500, detail)
        }
        if (event !== 'done') return
        thinking.value = false
        const result = data as InterviewTurnSubmitResponse
        await finishDrip(gen, result.current_turn?.question)
        doneResult = result
        const closing =
          isClosingQuestion(result.current_turn?.question) ||
          isClosingQuestion(liveMessage()?.text)
        if (closing) {
          holdingClose.value = true
        } else {
          applyDone(result)
        }
      },
      abortStream.signal,
    )
    const closing =
      isClosingQuestion(doneResult?.current_turn?.question) ||
      isClosingQuestion(liveMessage()?.text)
    if (closing && doneResult) {
      await revealEnded(doneResult)
    } else if (doneResult?.status === 'completed') {
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
  closingHoldToken += 1
  abortStream?.abort()
})
</script>

<template>
  <div class="layout">
    <AppHeader />

    <main v-loading="loading" class="main">
      <div v-if="session" class="session">
        <div class="board" :class="{ ended: !inProgress }">
          <div class="panel-bg" />

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
                v-if="inProgress && !holdingClose"
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
              :key="item.uid"
              class="row"
              :class="item.role"
            >
              <div class="turn">
                <div class="avatar">{{ item.role === 'interviewer' ? '面' : '我' }}</div>
                <div class="col">
                  <div class="bubble" :class="{ streaming: item.streaming }">
                    {{ item.text }}<span v-if="item.streaming" class="caret" />
                  </div>
                </div>
              </div>
              <aside v-if="item.comment" class="note">
                <div class="note-head">
                  <span class="note-label">评估</span>
                  <strong v-if="item.score != null">{{ item.score }} 分</strong>
                </div>
                <p v-if="noteBody(item.comment)" class="note-body">{{ noteBody(item.comment) }}</p>
              </aside>
            </div>

            <div v-if="thinking" class="row interviewer">
              <div class="turn">
                <div class="avatar">面</div>
                <div class="bubble thinking">
                  <span class="dot" />
                  <span class="dot" />
                  <span class="dot" />
                </div>
              </div>
            </div>

            <div v-if="session.report" class="report">
              <div class="report-title">本场报告</div>
              <p class="score">总分 {{ session.report.score }}</p>
              <div v-if="session.report.stages.length" class="stages">
                <span v-for="item in session.report.stages" :key="item.kind" class="chip">
                  {{ stageLabel[item.kind] ?? item.kind }} {{ item.score }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="inProgress && !holdingClose" class="composer">
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
.session {
  flex: 1;
  min-height: 0;
  width: min(100%, 1240px);
  margin: 0 auto;
  padding: 20px 24px 24px;
  display: flex;
  flex-direction: column;
}
.board {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr) auto;
  position: relative;
}
.board.ended {
  grid-template-columns: minmax(0, 1fr) 260px;
  column-gap: 16px;
}
.panel-bg {
  grid-column: 1;
  grid-row: 1 / -1;
  background: #fff;
  border-radius: 22px;
  box-shadow: 0 8px 28px rgba(31, 42, 55, 0.06);
  pointer-events: none;
}
.intro {
  grid-column: 1;
  grid-row: 1;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
  padding: 18px 22px 16px;
  border-bottom: 1px solid #eef2f6;
}
.intro h1 {
  margin: 0;
  font-size: 20px;
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
  grid-column: 1 / -1;
  grid-row: 2;
  z-index: 1;
  min-height: 0;
  overflow: auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-auto-rows: max-content;
  align-content: start;
  column-gap: 16px;
  padding: 20px 0 12px;
}
.board.ended .thread {
  grid-template-columns: minmax(0, 1fr) 260px;
  padding-bottom: 24px;
}
.row {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  column-gap: 16px;
  margin-bottom: 18px;
}
.board.ended .row {
  grid-template-columns: minmax(0, 1fr) 260px;
}
.turn {
  display: flex;
  gap: 10px;
  min-width: 0;
  grid-column: 1;
  padding: 0 22px;
}
.row.user .turn {
  flex-direction: row-reverse;
}
.row.interviewer .col {
  max-width: min(72%, 560px);
}
.row.user .col {
  max-width: min(72%, 520px);
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
.bubble {
  padding: 10px 14px;
  border-radius: 18px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f4f7fb;
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
.note {
  grid-column: 2;
  grid-row: 1;
  align-self: start;
  min-width: 0;
  padding: 10px 12px 12px;
  background: #fffdf7;
  border: 1px solid #f1e4c3;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(120, 80, 20, 0.05);
}
.note-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.note-label {
  font-size: 12px;
  font-weight: 600;
  color: #b45309;
}
.note-head strong {
  font-size: 13px;
  font-weight: 700;
  color: #92400e;
}
.note-body {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: #57534e;
  white-space: pre-wrap;
  word-break: break-word;
}
.report {
  grid-column: 1;
  margin: 8px 22px 8px;
  padding: 16px 18px;
  background: #f8fafc;
  border-radius: 14px;
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
.chip {
  padding: 4px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.composer {
  grid-column: 1;
  grid-row: 3;
  z-index: 1;
  display: flex;
  flex-shrink: 0;
  gap: 12px;
  align-items: flex-end;
  margin: 8px 16px 16px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e8edf3;
  border-radius: 16px;
}
.composer :deep(.el-textarea) {
  flex: 1;
}
.composer :deep(.el-textarea__inner) {
  box-shadow: none;
  background: transparent;
}
.composer :deep(.el-button) {
  height: 40px;
}
@media (max-width: 840px) {
  .session {
    padding: 12px 12px 16px;
  }
  .intro {
    flex-direction: column;
    align-items: flex-start;
  }
  .board.ended {
    grid-template-columns: minmax(0, 1fr);
  }
  .board.ended .thread,
  .board.ended .row {
    grid-template-columns: minmax(0, 1fr);
  }
  .row.interviewer .col,
  .row.user .col {
    max-width: min(86%, 560px);
  }
  .note {
    grid-column: 1;
    grid-row: auto;
    margin: 0 22px 0 48px;
  }
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
