import { ApiError, request } from './http'
import { readSseStream } from './sse'
import { useAuthStore } from '@/stores/auth'

export const TYPEWRITER_SESSION_KEY = 'ai-interview-typewriter'

export type Difficulty = 'easy' | 'medium' | 'hard'
export type TargetRole = 'Java 后端' | 'Python 后端' | 'AI Agent'
export type SessionStatus = 'planned' | 'in_progress' | 'completed' | 'abandoned'

export const TARGET_ROLES: TargetRole[] = ['Java 后端', 'Python 后端', 'AI Agent']

export type ScoredStageKind = 'project_probe' | 'fundamentals' | 'scenario'

export interface StageScore {
  kind: string
  score: number
}

export interface InterviewSessionListItem {
  id: number
  resume_id: number
  target_role: string
  difficulty: string
  status: string
  created_at: string
  score: number | null
  stages: StageScore[]
  current_question: string | null
}

export interface CurrentTurn {
  seq: number
  action: string
  question: string
}

export interface InterviewSessionCreateResponse {
  id: number
  resume_id: number
  target_role: string
  difficulty: string
  status: string
  created_at: string
  current_turn: CurrentTurn
}

export interface InterviewTurnPublic {
  seq: number
  question: string
  answer: string
  score: number | null
  comment: string | null
}

export interface InterviewReport {
  score: number
  stages: StageScore[]
  covered: string[]
  missing: string[]
  said_dont_know_count: number
}

export interface InterviewSessionDetail {
  id: number
  resume_id: number
  target_role: string
  difficulty: string
  status: string
  created_at: string
  turns: InterviewTurnPublic[]
  current_question: string | null
  report: InterviewReport | null
}

export interface InterviewTurnSubmitResponse {
  id: number
  status: SessionStatus
  current_turn: CurrentTurn | null
  report: InterviewReport | null
}

export function listInterviewSessions(params?: { status?: SessionStatus; limit?: number }) {
  const query = new URLSearchParams()
  if (params?.status) query.set('status', params.status)
  query.set('limit', String(params?.limit ?? 100))
  return request<InterviewSessionListItem[]>(`/api/v1/interview-sessions?${query}`)
}

export function createInterviewSession(body: {
  resume_id: number
  target_role: TargetRole
  difficulty: Difficulty
}) {
  return request<InterviewSessionCreateResponse>('/api/v1/interview-sessions', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getInterviewSession(id: number) {
  return request<InterviewSessionDetail>(`/api/v1/interview-sessions/${id}`)
}

export function submitInterviewTurn(id: number, answer: string) {
  return request<InterviewTurnSubmitResponse>(`/api/v1/interview-sessions/${id}/turns`, {
    method: 'POST',
    body: JSON.stringify({ answer }),
  })
}

export async function submitInterviewTurnStream(
  id: number,
  answer: string,
  onEvent: (event: string, data: unknown) => void,
  signal?: AbortSignal,
) {
  const accessToken = useAuthStore().accessToken
  const headers = new Headers({
    Accept: 'text/event-stream',
    'Content-Type': 'application/json',
  })
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  const response = await fetch(`/api/api/v1/interview-sessions/${id}/turns`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ answer }),
    cache: 'no-store',
    signal,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message =
      typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((item: { msg?: string }) => item.msg ?? '').join(';') : '请求失败'
    throw new ApiError(response.status, message)
  }
  await readSseStream(response, onEvent)
}

export function markSessionTypewriter(id: number) {
  sessionStorage.setItem(`${TYPEWRITER_SESSION_KEY}:${id}`, '1')
}

export function consumeSessionTypewriter(id: number) {
  const key = `${TYPEWRITER_SESSION_KEY}:${id}`
  const enabled = sessionStorage.getItem(key) === '1'
  if (enabled) {
    sessionStorage.removeItem(key)
  }
  return enabled
}

export function abandonInterviewSession(id: number) {
  return request<InterviewSessionListItem>(`/api/v1/interview-sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'abandoned' }),
  })
}
