import type { Capabilities, DashboardStats, GlossaryTerm, Language, Project, Segment } from '../types'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: { message?: string } } | null
    throw new Error(body?.detail?.message ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  projects: () => request<Project[]>('/api/projects'),
  project: (id: number) => request<Project>(`/api/projects/${id}`),
  stats: () => request<DashboardStats>('/api/dashboard/stats'),
  languages: () => request<{ source: Language[]; target: Language[] }>('/api/languages'),
  capabilities: () => request<Capabilities>('/api/system/capabilities'),
  glossary: () => request<GlossaryTerm[]>('/api/glossary'),
  deleteProject: (id: number) => request<{ deleted: boolean }>(`/api/projects/${id}`, { method: 'DELETE' }),
  duplicateProject: (id: number) => request<Project>(`/api/projects/${id}/duplicate`, { method: 'POST' }),
  saveSegment: (projectId: number, segment: Segment) => request<Segment>(`/api/projects/${projectId}/segments/${segment.id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(segment),
  }),
  transcribe: (id: number) => request<{ job_id: number }>(`/api/projects/${id}/transcribe`, { method: 'POST' }),
  translate: (id: number, target_language: string) => request<Project>(`/api/projects/${id}/translate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_language }),
  }),
  retranslate: (id: number, segmentId: number) => request<Project>(`/api/projects/${id}/segments/${segmentId}/translate`, { method: 'POST' }),
  dub: (id: number, target_language: string, voice?: string, lipsync = false) => request<{ job_id: number; lipsync_warning?: string }>(`/api/projects/${id}/dub`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_language, voice, keep_background: true, speed: 1, lipsync }),
  }),
  export: (id: number, subtitle_mode: 'off' | 'soft' | 'burn' = 'soft') => request<{ job_id: number }>(`/api/projects/${id}/export`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ subtitle_mode }),
  }),
  retry: (id: number) => request<{ job_id: number }>(`/api/projects/${id}/retry`, { method: 'POST' }),
  cancel: (id: number) => request<{ status: string }>(`/api/projects/${id}/cancel`, { method: 'POST' }),
  status: (id: number) => request<Pick<Project, 'id' | 'status' | 'progress' | 'current_step' | 'error_message'>>(`/api/projects/${id}/status`),
  addGlossary: (term: Omit<GlossaryTerm, 'id'>) => request<GlossaryTerm>('/api/glossary', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(term),
  }),
  deleteGlossary: (id: number) => request<{ deleted: boolean }>(`/api/glossary/${id}`, { method: 'DELETE' }),
  upload(file: File, sourceLanguage: string, targetLanguage: string, onProgress: (progress: number) => void): Promise<Project> {
    return new Promise((resolve, reject) => {
      const form = new FormData()
      form.append('file', file)
      form.append('source_language', sourceLanguage)
      form.append('target_language', targetLanguage)
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${API_BASE}/api/projects/upload`)
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
      }
      xhr.onerror = () => reject(new Error('Could not reach the LinguaDub API.'))
      xhr.onload = () => {
        const body = JSON.parse(xhr.responseText || '{}') as Project & { detail?: { message?: string } }
        if (xhr.status >= 200 && xhr.status < 300) resolve(body)
        else reject(new Error(body.detail?.message ?? `Upload failed (${xhr.status})`))
      }
      xhr.send(form)
    })
  },
}

export function downloadUrl(projectId: number, kind: string): string {
  return `${API_BASE}/api/projects/${projectId}/download/${kind}`
}

export async function previewAudio(projectId: number, segmentId: number): Promise<string> {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/segments/${segmentId}/preview-audio`, { method: 'POST' })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: { message?: string } } | null
    throw new Error(body?.detail?.message ?? 'Voice preview failed.')
  }
  return URL.createObjectURL(await response.blob())
}
