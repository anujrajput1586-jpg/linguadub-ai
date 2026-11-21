export type ProjectStatus = 'uploaded' | 'extracting_audio' | 'transcribing' | 'awaiting_review' | 'translating' | 'dubbing' | 'mixing' | 'lipsync' | 'exporting' | 'completed' | 'failed' | 'cancelled'

export interface Segment {
  id: number
  start: number
  end: number
  original_text: string
  translated_text: string | null
  speaker: string | null
  audio_path?: string | null
}

export interface Project {
  id: number
  title: string
  source_language: string
  detected_language: string | null
  target_language: string
  duration_seconds: number
  file_size: number
  status: ProjectStatus
  progress: number
  current_step: string
  error_message: string | null
  created_at: string
  segments: Segment[]
}

export interface Language {
  code: string
  name: string
}

export interface GlossaryTerm {
  id: number
  source_term: string
  target_term: string
  source_language: string
  target_language: string
}

export interface DashboardStats {
  total_videos: number
  translated_minutes: number
  available_languages: number
  recent_projects: Array<Pick<Project, 'id' | 'title' | 'status' | 'progress' | 'created_at'>>
}

export interface Capabilities {
  ffmpeg: boolean
  ffprobe: boolean
  gpu: boolean
  stt_provider: string
  translation_provider: string
  tts_provider: string
  lipsync_available: boolean
  lipsync_reason: string
}
