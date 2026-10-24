import { request } from './http'

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

export function listInterviewSessions() {
  return request<InterviewSessionListItem[]>('/api/v1/interview-sessions?limit=100')
}
