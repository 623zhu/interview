import { request } from './http'

export type Difficulty = 'easy' | 'medium' | 'hard'
export type SessionStatus = 'planned' | 'in_progress' | 'completed' | 'abandoned'

export interface InterviewSessionListItem {
  id: number
  resume_id: number
  target_role: string
  difficulty: string
  status: string
  created_at: string
  score: number | null
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
  stages: { kind: string; score: number }[]
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
  target_role: string
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

export function abandonInterviewSession(id: number) {
  return request<InterviewSessionListItem>(`/api/v1/interview-sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'abandoned' }),
  })
}
