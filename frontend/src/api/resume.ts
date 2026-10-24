import { request } from './http'

export interface ResumeListItem {
  id: number
  original_filename: string
  media_type: string
  status: string
  created_at: string
}

export interface ResumeUploadResponse extends ResumeListItem {
  raw_text: string | null
  profile: Record<string, unknown> | null
  error_detail: string | null
}

export function listResumes() {
  return request<ResumeListItem[]>('/api/v1/resumes')
}

export function uploadResume(file: File) {
  const body = new FormData()
  body.append('file', file)
  return request<ResumeUploadResponse>('/api/v1/resumes', {
    method: 'POST',
    body,
  })
}
