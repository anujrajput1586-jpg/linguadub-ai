import { useEffect, useState, type ChangeEvent, type DragEvent } from 'react'
import {
  Activity, ArrowDownToLine, ArrowLeft, AudioLines, BookOpen, Check, ChevronDown,
  CircleHelp, Clock3, FileAudio, FileVideo2, Globe2, HardDrive, History, Languages,
  LoaderCircle, Menu, Mic2, MoreHorizontal, Play, Plus, Search, Settings2, ShieldCheck,
  Sparkles, Subtitles, Trash2, Upload, Volume2, WandSparkles, X,
} from 'lucide-react'
import { api, downloadUrl, previewAudio } from './api/client'
import type { Capabilities, DashboardStats, GlossaryTerm, Language, Project, Segment } from './types'
import './lip-sync.css'
import './styles.css'

type Page = 'dashboard' | 'projects' | 'glossary' | 'voices' | 'history' | 'settings'

const activeStatuses = new Set(['extracting_audio', 'transcribing', 'translating', 'dubbing', 'mixing', 'lipsync', 'exporting'])
const statusNames: Record<string, string> = {
  uploaded: 'Ready to transcribe', extracting_audio: 'Extracting audio', transcribing: 'Transcribing',
  awaiting_review: 'Review needed', translating: 'Translating', dubbing: 'Generating voices',
  mixing: 'Mixing audio', lipsync: 'Lip sync', exporting: 'Exporting', completed: 'Completed',
  failed: 'Failed', cancelled: 'Cancelled',
}

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
}

function formatBytes(bytes: number) {
  return bytes >= 1024 ** 3 ? `${(bytes / 1024 ** 3).toFixed(1)} GB` : `${(bytes / 1024 ** 2).toFixed(1)} MB`
}

function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [projects, setProjects] = useState<Project[]>([])
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [languages, setLanguages] = useState<{ source: Language[]; target: Language[] }>({ source: [], target: [] })
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [glossary, setGlossary] = useState<GlossaryTerm[]>([])
  const [project, setProject] = useState<Project | null>(null)
  const [loadError, setLoadError] = useState('')
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState('')
  const [search, setSearch] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [sourceLanguage, setSourceLanguage] = useState('auto')
  const [targetLanguage, setTargetLanguage] = useState('hi')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [termSource, setTermSource] = useState('')
  const [termTarget, setTermTarget] = useState('')
  const [previewUrl, setPreviewUrl] = useState('')

  async function loadWorkspace() {
    try {
      const [projectList, dashboard, languageList, caps] = await Promise.all([
        api.projects(), api.stats(), api.languages(), api.capabilities(),
      ])
      setLoadError('')
      setProjects(projectList)
      setStats(dashboard)
      setLanguages(languageList)
      setCapabilities(caps)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Could not load the workspace.')
    }
  }

  async function loadGlossary() {
    try { setGlossary(await api.glossary()) }
    catch (error) { notify(error instanceof Error ? error.message : 'Could not load glossary.') }
  }

  useEffect(() => {
    let active = true
    void Promise.all([api.projects(), api.stats(), api.languages(), api.capabilities()]).then(([projectList, dashboard, languageList, caps]) => {
      if (!active) return
      setProjects(projectList)
      setStats(dashboard)
      setLanguages(languageList)
      setCapabilities(caps)
      setLoadError('')
    }).catch((error: unknown) => {
      if (active) setLoadError(error instanceof Error ? error.message : 'Could not load the workspace.')
    })
    void api.glossary().then((terms) => { if (active) setGlossary(terms) }).catch((error: unknown) => {
      if (active) notify(error instanceof Error ? error.message : 'Could not load glossary.')
    })
    return () => { active = false }
  }, [])
  useEffect(() => {
    const projectId = project?.id
    if (!projectId || !project || !activeStatuses.has(project.status)) return
    const timer = window.setInterval(() => {
      void api.project(projectId).then((updated) => {
        setProject(updated)
        setProjects((current) => current.map((item) => item.id === updated.id ? updated : item))
        if (!activeStatuses.has(updated.status)) void loadWorkspace()
      }).catch(() => undefined)
    }, 3000)
    return () => window.clearInterval(timer)
  }, [project])
  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(''), 3600)
    return () => window.clearTimeout(timer)
  }, [toast])
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl) }, [previewUrl])

  function notify(message: string) { setToast(message) }
  async function openProject(id: number) {
    try { setProject(await api.project(id)); setPage('projects') }
    catch (error) { notify(error instanceof Error ? error.message : 'Could not open project.') }
  }
  function chooseFile(file?: File) {
    if (!file) return
    if (file.size > 500 * 1024 * 1024) { notify('Maximum upload size is 500 MB.'); return }
    if (!['video/mp4', 'video/quicktime', 'video/x-msvideo', 'application/octet-stream'].includes(file.type) && !/\.(mp4|mov|avi)$/i.test(file.name)) {
      notify('Choose an MP4, MOV, or AVI video.'); return
    }
    setUploadFile(file)
  }
  async function submitUpload() {
    if (!uploadFile) return
    setBusy(true)
    try {
      const created = await api.upload(uploadFile, sourceLanguage, targetLanguage, setUploadProgress)
      setProject(created)
      setProjects((current) => [created, ...current])
      setUploadOpen(false)
      setUploadFile(null)
      setUploadProgress(0)
      await api.transcribe(created.id)
      const updated = await api.project(created.id)
      setProject(updated)
      notify('Upload complete. Transcription started.')
    } catch (error) { notify(error instanceof Error ? error.message : 'Upload failed.') }
    finally { setBusy(false); void loadWorkspace() }
  }
  async function runAction(action: () => Promise<unknown>, message: string) {
    if (!project) return
    setBusy(true)
    try {
      await action()
      setProject(await api.project(project.id))
      void loadWorkspace()
      notify(message)
    } catch (error) { notify(error instanceof Error ? error.message : 'Action failed.') }
    finally { setBusy(false) }
  }
  function patchSegment(id: number, patch: Partial<Segment>) {
    setProject((current) => current ? { ...current, segments: current.segments.map((segment) => segment.id === id ? { ...segment, ...patch } : segment) } : current)
  }
  async function saveSegment(segment: Segment) {
    if (!project) return
    try { await api.saveSegment(project.id, segment); notify('Segment saved.') }
    catch (error) { notify(error instanceof Error ? error.message : 'Could not save segment.') }
  }
  async function playSegment(segmentId: number) {
    if (!project) return
    try {
      const url = await previewAudio(project.id, segmentId)
      setPreviewUrl((current) => { if (current) URL.revokeObjectURL(current); return url })
      window.setTimeout(() => { const player = document.querySelector<HTMLAudioElement>('#segment-audio'); void player?.play() }, 50)
    } catch (error) { notify(error instanceof Error ? error.message : 'Voice preview failed.') }
  }
  async function deleteProject(id: number) {
    try {
      await api.deleteProject(id)
      setProjects((current) => current.filter((item) => item.id !== id))
      if (project?.id === id) setProject(null)
      notify('Project deleted.')
      void loadWorkspace()
    } catch (error) { notify(error instanceof Error ? error.message : 'Could not delete project.') }
  }
  async function duplicateProject(id: number) {
    try {
      const clone = await api.duplicateProject(id)
      setProjects((current) => [clone, ...current])
      notify('Project duplicated.')
    } catch (error) { notify(error instanceof Error ? error.message : 'Could not duplicate project.') }
  }
  async function addGlossaryTerm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      await api.addGlossary({ source_term: termSource, target_term: termTarget, source_language: 'auto', target_language: targetLanguage })
      setTermSource(''); setTermTarget(''); await loadGlossary(); notify('Glossary term saved.')
    } catch (error) { notify(error instanceof Error ? error.message : 'Could not save term.') }
  }

  const navItems = [
    { key: 'dashboard' as const, label: 'Dashboard', icon: Activity },
    { key: 'projects' as const, label: 'My projects', icon: FileVideo2 },
    { key: 'voices' as const, label: 'Voice settings', icon: AudioLines },
    { key: 'glossary' as const, label: 'Glossary', icon: BookOpen },
    { key: 'history' as const, label: 'History', icon: History },
    { key: 'settings' as const, label: 'Settings', icon: Settings2 },
  ]
  const filteredProjects = projects.filter((item) => item.title.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" onClick={() => { setProject(null); setPage('dashboard') }} aria-label="LinguaDub dashboard">
          <span className="brand-mark"><AudioLines size={19} /></span><span>lingua<span>dub</span><small>STUDIO</small></span>
        </button>
        <button className="workspace-switch"><span className="workspace-avatar">L</span><span className="workspace-name">Workshop team<small>Personal workspace</small></span><ChevronDown size={15} /></button>
        <div className="nav-caption">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navItems.map(({ key, label, icon: Icon }) => <button key={key} className={`nav-link ${page === key && !project ? 'active' : ''}`} onClick={() => { setProject(null); setPage(key) }}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{key === 'projects' && projects.length > 0 && <small>{projects.length}</small>}</button>)}
        </nav>
        <div className="sidebar-spacer" />
        <div className="usage-block"><div className="usage-head"><span>Monthly processing</span><span>{stats?.translated_minutes ?? 0} / 120 min</span></div><div className="usage-track"><i style={{ width: `${Math.min(100, ((stats?.translated_minutes ?? 0) / 120) * 100)}%` }} /></div><button onClick={() => setPage('settings')}><CircleHelp size={14} /> Usage & plan</button></div>
        <div className="user-profile"><div className="profile-avatar">AD</div><div><strong>Alex Duarte</strong><small>Studio member</small></div><MoreHorizontal size={18} /></div>
      </aside>

      <main className="main-shell">
        <header className="topbar"><div className="breadcrumb"><span>LinguaDub</span><span>/</span><strong>{project ? project.title : navItems.find((item) => item.key === page)?.label}</strong></div><div className="top-actions"><span className={`service-indicator ${capabilities?.ffmpeg ? 'online' : 'warning'}`}><i />{capabilities?.ffmpeg ? 'Media engine ready' : 'Media engine unavailable'}</span><button className="icon-button mobile-menu" aria-label="Open menu"><Menu size={19} /></button><div className="profile-avatar small">AD</div></div></header>
        {loadError && <div className="error-banner"><ShieldCheck size={16} /><span>{loadError}</span><button onClick={() => void loadWorkspace()}>Retry</button></div>}
        <div className="content-area">
          {project ? <ProjectWorkspace project={project} languages={languages.target} caps={capabilities} busy={busy} previewUrl={previewUrl} onTranscribe={() => void runAction(() => api.transcribe(project.id), 'Transcription started.')} onRetry={() => void runAction(() => api.retry(project.id), 'Retry queued.')} onCancel={() => void runAction(() => api.cancel(project.id), 'Job cancelled.')} onBack={() => { setProject(null); setPage('projects') }} onPatch={patchSegment} onSave={saveSegment} onTranslate={() => void runAction(() => api.translate(project.id, project.target_language), 'Translation ready for review.')} onRetranslate={(id) => void runAction(() => api.retranslate(project.id, id), 'Segment translated.')} onDub={(lipsync) => void runAction(() => api.dub(project.id, project.target_language, undefined, lipsync), 'Voice generation started.')} onExport={() => void runAction(() => api.export(project.id), 'Export started.')} onPreview={playSegment} /> : page === 'dashboard' ? <Dashboard stats={stats} onNew={() => setUploadOpen(true)} onOpen={openProject} onPage={setPage} /> : page === 'projects' ? <ProjectsPage projects={filteredProjects} search={search} setSearch={setSearch} onOpen={openProject} onDelete={deleteProject} onDuplicate={duplicateProject} onNew={() => setUploadOpen(true)} /> : page === 'glossary' ? <GlossaryPage glossary={glossary} languages={languages.target} source={termSource} target={termTarget} setSource={setTermSource} setTarget={setTermTarget} onAdd={addGlossaryTerm} onDelete={async (id) => { try { await api.deleteGlossary(id); await loadGlossary(); notify('Glossary term removed.') } catch (error) { notify(error instanceof Error ? error.message : 'Could not remove term.') } }} /> : page === 'voices' ? <VoicePage languages={languages.target} caps={capabilities} /> : page === 'history' ? <HistoryPage projects={projects} onOpen={openProject} /> : <SettingsPage caps={capabilities} />}
        </div>
      </main>

      {uploadOpen && <UploadDialog languages={languages} file={uploadFile} progress={uploadProgress} busy={busy} dragging={dragging} source={sourceLanguage} target={targetLanguage} setSource={setSourceLanguage} setTarget={setTargetLanguage} onFile={chooseFile} onSubmit={() => void submitUpload()} onClose={() => { setUploadOpen(false); setUploadFile(null); setUploadProgress(0) }} onDrag={(value) => setDragging(value)} />}
      {previewUrl && <audio id="segment-audio" src={previewUrl} hidden onEnded={() => URL.revokeObjectURL(previewUrl)} />}
      {toast && <div className="toast"><Check size={16} /><span>{toast}</span><button aria-label="Dismiss" onClick={() => setToast('')}><X size={15} /></button></div>}
    </div>
  )
}

function Dashboard({ stats, onNew, onOpen, onPage }: { stats: DashboardStats | null; onNew: () => void; onOpen: (id: number) => void; onPage: (page: Page) => void }) {
  const recent = stats?.recent_projects ?? []
  return <>
    <div className="page-heading dashboard-heading"><div><div className="eyebrow"><span /> MULTILINGUAL VIDEO WORKSPACE</div><h1>Good morning, Alex<span>.</span></h1><p>Your translation studio is ready when you are.</p></div><button className="primary-button" onClick={onNew}><Plus size={17} /> New translation</button></div>
    <section className="metrics-grid">
      <Metric icon={FileVideo2} label="Videos processed" value={String(stats?.total_videos ?? 0).padStart(2, '0')} detail="Across your workspace" tone="blue" />
      <Metric icon={Clock3} label="Translated minutes" value={String(stats?.translated_minutes ?? 0)} detail="Completed project runtime" tone="lime" />
      <Metric icon={Globe2} label="Target languages" value={String(stats?.available_languages ?? 10).padStart(2, '0')} detail="Ready for translation" tone="coral" />
    </section>
    <section className="home-grid">
      <div className="section-panel recent-panel"><div className="section-title"><div><span className="section-kicker">YOUR WORKSPACE</span><h2>Recent projects</h2></div><button className="text-button" onClick={() => onPage('projects')}>All projects <ArrowDownToLine size={14} className="turn-icon" /></button></div>
        {recent.length ? <div className="project-list">{recent.slice(0, 5).map((item) => <button className="project-row" key={item.id} onClick={() => onOpen(item.id)}><div className="project-thumb"><FileVideo2 size={18} /></div><div className="project-info"><strong>{item.title}</strong><span>{new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span></div><div className="row-status"><i className={`status-dot ${item.status}`} />{statusNames[item.status] ?? item.status}</div><div className="row-progress"><div><i style={{ width: `${item.progress}%` }} /></div><span>{item.progress}%</span></div><ChevronDown className="row-chevron" size={15} /></button>)}</div> : <EmptyState icon={FileVideo2} title="No translations yet" text="Upload a short clip to start your first multilingual project." action="Create a project" onAction={onNew} />}
      </div>
      <div className="section-panel start-panel"><div className="section-title"><div><span className="section-kicker">QUICK START</span><h2>Start translating</h2></div><span className="sparkle-mark"><Sparkles size={16} /></span></div><div className="pipeline-illustration"><div className="pipeline-orbit orbit-a"/><div className="pipeline-orbit orbit-b"/><div className="pipeline-center"><AudioLines size={28} /></div><div className="pipeline-node node-a"><FileVideo2 size={15} /></div><div className="pipeline-node node-b"><Languages size={15} /></div><div className="pipeline-node node-c"><Volume2 size={15} /></div></div><p>From source video to translated voice, subtitles, and a finished export.</p><div className="start-meta"><span><i /> No paid API keys</span><span>MP4 · MOV · AVI</span></div><button className="secondary-button full-width" onClick={onNew}><Upload size={15} /> Upload a video</button></div>
    </section>
    <section className="pipeline-strip"><div className="pipeline-label"><span className="section-kicker">THE WORKFLOW</span><span>Four steps, one finished video</span></div>{[{ n: '01', title: 'Transcribe', icon: AudioLines }, { n: '02', title: 'Translate', icon: Languages }, { n: '03', title: 'Dub', icon: Mic2 }, { n: '04', title: 'Export', icon: FileVideo2 }].map(({ n, title, icon: Icon }) => <div className="workflow-step" key={n}><span>{n}</span><Icon size={16} /><strong>{title}</strong></div>)}</section>
  </>
}

function Metric({ icon: Icon, label, value, detail, tone }: { icon: typeof Activity; label: string; value: string; detail: string; tone: string }) {
  return <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={18} /></div><span className="metric-label">{label}</span><strong>{value}</strong><small>{detail}</small><div className={`metric-accent ${tone}`} /></div>
}

function ProjectsPage({ projects, search, setSearch, onOpen, onDelete, onDuplicate, onNew }: { projects: Project[]; search: string; setSearch: (value: string) => void; onOpen: (id: number) => void; onDelete: (id: number) => void; onDuplicate: (id: number) => void; onNew: () => void }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span /> LIBRARY</div><h1>My projects<span>.</span></h1><p>Manage translations and pick up where you left off.</p></div><button className="primary-button" onClick={onNew}><Plus size={17} /> New translation</button></div><div className="toolbar"><label className="search-box"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search projects" /></label><span className="toolbar-count">{projects.length} {projects.length === 1 ? 'project' : 'projects'}</span></div>{projects.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>PROJECT</th><th>LANGUAGE PAIR</th><th>RUNTIME</th><th>STATUS</th><th>CREATED</th><th /></tr></thead><tbody>{projects.map((item) => <tr key={item.id}><td><button className="table-project" onClick={() => onOpen(item.id)}><span className="project-thumb"><FileVideo2 size={17} /></span><span><strong>{item.title}</strong><small>{formatBytes(item.file_size)}</small></span></button></td><td><span className="language-pair">{item.detected_language ?? item.source_language}<i>→</i>{item.target_language}</span></td><td className="mono-cell">{formatDuration(item.duration_seconds)}</td><td><span className="status-label"><i className={`status-dot ${item.status}`} />{statusNames[item.status] ?? item.status}</span></td><td>{new Date(item.created_at).toLocaleDateString()}</td><td><button className="icon-button" title="Duplicate project" onClick={() => onDuplicate(item.id)}><Plus size={15} /></button><button className="icon-button danger-hover" title="Delete project" onClick={() => onDelete(item.id)}><Trash2 size={15} /></button></td></tr>)}</tbody></table></div> : <div className="section-panel empty-page"><EmptyState icon={FileVideo2} title="Your project library is clear" text="Uploaded videos and their translated exports will appear here." action="Create a project" onAction={onNew} /></div>}</>
}

function ProjectWorkspace({ project, languages, caps, busy, previewUrl, onTranscribe, onRetry, onCancel, onBack, onPatch, onSave, onTranslate, onRetranslate, onDub, onExport, onPreview }: { project: Project; languages: Language[]; caps: Capabilities | null; busy: boolean; previewUrl: string; onTranscribe: () => void; onRetry: () => void; onCancel: () => void; onBack: () => void; onPatch: (id: number, patch: Partial<Segment>) => void; onSave: (segment: Segment) => void; onTranslate: () => void; onRetranslate: (id: number) => void; onDub: (lipsync: boolean) => void; onExport: () => void; onPreview: (id: number) => void }) {
  const languageName = languages.find((item) => item.code === project.target_language)?.name ?? project.target_language.toUpperCase()
  const [lipSync, setLipSync] = useState(false)

  return <div className="workspace-view">
    <button className="back-link" onClick={onBack}><ArrowLeft size={15} /> All projects</button>
    <div className="project-heading">
      <div>
        <div className="eyebrow"><span /> PROJECT {String(project.id).padStart(4, '0')}</div>
        <h1>{project.title}<span>.</span></h1>
        <div className="project-subtitle"><span className="language-chip">{project.detected_language ?? project.source_language} <i>→</i> {languageName}</span><span>{formatDuration(project.duration_seconds)}</span><span>{formatBytes(project.file_size)}</span><span className={`status-label ${project.status}`}><i className={`status-dot ${project.status}`} />{statusNames[project.status]}</span></div>
      </div>
      <div className="project-actions">
        {project.status === 'uploaded' && <button className="secondary-button" onClick={onTranscribe} disabled={busy}><AudioLines size={15} /> Transcribe</button>}
        {activeStatuses.has(project.status) && <button className="icon-button" title="Cancel job" onClick={onCancel}><X size={15} /></button>}
        {project.status === 'failed' && <button className="secondary-button" onClick={onRetry} disabled={busy}><Activity size={15} /> Retry failed step</button>}
        <button className="secondary-button" onClick={onTranslate} disabled={busy || !project.segments.length}><Languages size={15} /> Translate</button>
        <button className="secondary-button" onClick={() => onDub(lipSync)} disabled={busy || !project.segments.some((item) => item.translated_text)}><Mic2 size={15} /> Generate voice</button>
        <button className="primary-button" onClick={onExport} disabled={busy || !project.segments.some((item) => item.audio_path)}><ArrowDownToLine size={15} /> Export video</button>
      </div>
    </div>
    <div className="lip-sync-row"><label className="lip-sync-toggle"><input type="checkbox" checked={lipSync} disabled={!caps?.lipsync_available} onChange={(event) => setLipSync(event.target.checked)} /><span>Lip sync</span></label><span>{caps?.lipsync_available ? 'Slow, optimized for short clips' : caps?.lipsync_reason ?? 'GPU provider unavailable'}</span></div>
    {(project.status !== 'awaiting_review' && project.status !== 'completed' && project.status !== 'failed') && <div className="job-progress"><div className="job-progress-top"><span><LoaderCircle size={15} className="spin" /> {project.current_step}</span><span>{project.progress}%</span></div><div className="progress-track"><i style={{ width: `${project.progress}%` }} /></div></div>}
    {project.status === 'failed' && <div className="error-banner project-error"><X size={16} /><span>{project.error_message ?? 'This job failed.'}</span></div>}
    <div className="editor-layout"><div className="editor-main"><section className="section-panel source-panel"><div className="section-title"><div><span className="section-kicker">SOURCE VIDEO</span><h2>Original recording</h2></div><span className="small-chip"><FileVideo2 size={13} /> {project.title.split('.').pop()?.toUpperCase() ?? 'VIDEO'}</span></div><div className="video-surface"><video controls preload="metadata" src={downloadUrl(project.id, 'source')} /><div className="video-caption"><span><Play size={13} /> Original audio</span><span>{formatDuration(project.duration_seconds)}</span></div></div></section>
      <section className="section-panel transcript-panel"><div className="section-title"><div><span className="section-kicker">TRANSCRIPT & DUB</span><h2>Segment review <span className="count-badge">{project.segments.length}</span></h2></div><div className="editor-tools">{previewUrl && <span className="preview-indicator"><i /> Preview ready</span>}<button className="icon-button" title="Refresh project" onClick={() => window.location.reload()}><Activity size={16} /></button></div></div>
        {project.segments.length ? <div className="segment-list">{project.segments.map((segment, index) => <article className="segment-row" key={segment.id}><div className="segment-index">{String(index + 1).padStart(2, '0')}</div><div className="segment-content"><div className="segment-timing"><label><input aria-label="Segment start" type="number" min="0" step="0.1" value={segment.start} onChange={(event) => onPatch(segment.id, { start: Number(event.target.value) })} onBlur={() => onSave(segment)} /></label><span>to</span><label><input aria-label="Segment end" type="number" min="0" step="0.1" value={segment.end} onChange={(event) => onPatch(segment.id, { end: Number(event.target.value) })} onBlur={() => onSave(segment)} /></label><span className="segment-duration">{formatDuration(segment.end - segment.start)}</span><button className="icon-button segment-play" title="Preview translated voice" onClick={() => onPreview(segment.id)}><Play size={14} /></button><button className="icon-button segment-refresh" title="Re-translate segment" onClick={() => onRetranslate(segment.id)}><WandSparkles size={14} /></button></div><div className="segment-text-grid"><div><span className="field-caption">ORIGINAL</span><textarea value={segment.original_text} onChange={(event) => onPatch(segment.id, { original_text: event.target.value })} onBlur={() => onSave(segment)} rows={2} /></div><div><span className="field-caption target-caption">{languageName.toUpperCase()}</span><textarea value={segment.translated_text ?? ''} placeholder="Translation will appear here" onChange={(event) => onPatch(segment.id, { translated_text: event.target.value })} onBlur={() => onSave(segment)} rows={2} /></div></div></div></article>)}</div> : <EmptyState icon={AudioLines} title="No transcript yet" text={project.status === 'uploaded' ? 'Start transcription to prepare editable segments.' : 'Segments appear here after speech recognition finishes.'} action={project.status === 'uploaded' ? 'Start transcription' : undefined} onAction={undefined} />}
      </section></div>
      <aside className="editor-aside"><section className="section-panel workflow-panel"><div className="section-title"><div><span className="section-kicker">PRODUCTION</span><h2>Workflow</h2></div><span className="workflow-status-mark"><Activity size={15} /></span></div><ol className="workflow-list">{[{ name: 'Upload', state: 'complete' }, { name: 'Transcribe', state: project.segments.length ? 'complete' : project.status === 'transcribing' ? 'current' : 'pending' }, { name: 'Review transcript', state: project.status === 'awaiting_review' ? 'current' : project.segments.length ? 'complete' : 'pending' }, { name: 'Translate', state: project.segments.some((item) => item.translated_text) ? 'complete' : 'pending' }, { name: 'Voice generation', state: project.segments.some((item) => item.audio_path) ? 'complete' : 'pending' }, { name: 'Export', state: project.status === 'completed' ? 'complete' : 'pending' }].map((step, index) => <li className={step.state} key={step.name}><span className="step-marker">{step.state === 'complete' ? <Check size={12} /> : index + 1}</span><span>{step.name}</span>{step.state === 'current' && <i />}</li>)}</ol><button className="full-width primary-button workflow-cta" onClick={project.status === 'uploaded' ? () => undefined : onTranslate} disabled={busy || !project.segments.length}><WandSparkles size={15} /> {project.status === 'uploaded' ? 'Waiting for transcription' : 'Continue workflow'}</button><p className="workflow-note">You can review and adjust every segment before export.</p></section>
        <section className="section-panel delivery-panel"><div className="section-title"><div><span className="section-kicker">DELIVERABLES</span><h2>Downloads</h2></div><ArrowDownToLine size={16} className="muted-icon" /></div>{project.status === 'completed' ? <div className="download-list">{[['video', 'Final video', FileVideo2], ['audio', 'Dubbed audio', FileAudio], ['target-srt', 'Translated subtitles', Subtitles], ['original-srt', 'Original subtitles', Subtitles], ['transcript-json', 'Transcript JSON', FileAudio]].map(([kind, label, Icon]) => <a className="download-row" key={String(kind)} href={downloadUrl(project.id, String(kind))} download><Icon size={15} /><span>{String(label)}</span><ArrowDownToLine size={14} /></a>)}</div> : <div className="deliverable-empty"><div><FileVideo2 size={16} /><Subtitles size={16} /><FileAudio size={16} /></div><span>Video, audio and subtitle files will be available after export.</span></div>}</section>
        <section className="system-note"><span><HardDrive size={14} /></span><p><strong>Media engine</strong>{' '}{capabilityText(project.status)}</p></section>
      </aside></div>
  </div>
}

function capabilityText(status: string) { return status === 'failed' ? 'Check the error above, then retry after fixing the provider or media requirement.' : 'Processing runs locally. FFmpeg and ffprobe are required for video operations.' }

function GlossaryPage({ glossary, languages, source, target, setSource, setTarget, onAdd, onDelete }: { glossary: GlossaryTerm[]; languages: Language[]; source: string; target: string; setSource: (value: string) => void; setTarget: (value: string) => void; onAdd: (event: React.FormEvent<HTMLFormElement>) => void; onDelete: (id: number) => void }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span /> TRANSLATION QUALITY</div><h1>Technical glossary<span>.</span></h1><p>Keep machine names, parts, and repair terms consistent across every project.</p></div><span className="glossary-count">{glossary.length} TERMS</span></div><div className="glossary-layout"><section className="section-panel glossary-form-panel"><div className="section-title"><div><span className="section-kicker">ADD A MAPPING</span><h2>New glossary term</h2></div><BookOpen size={17} className="muted-icon" /></div><form className="glossary-form" onSubmit={onAdd}><label>Source term<input value={source} onChange={(event) => setSource(event.target.value)} placeholder="e.g. 主轴" required /></label><label>Preferred translation<input value={target} onChange={(event) => setTarget(event.target.value)} placeholder="e.g. spindle / स्पिंडल" required /></label><div className="form-language"><label>Apply to target<select defaultValue="hi">{languages.map((language) => <option value={language.code} key={language.code}>{language.name}</option>)}</select></label><span>Exact term protection</span></div><button className="primary-button" type="submit"><Plus size={16} /> Add term</button></form></section><section className="section-panel glossary-table-panel"><div className="section-title"><div><span className="section-kicker">YOUR VOCABULARY</span><h2>Saved terms</h2></div><span className="small-chip"><ShieldCheck size={13} /> Enforced</span></div>{glossary.length ? <div className="glossary-terms">{glossary.map((term) => <div className="glossary-term" key={term.id}><div className="term-source"><strong>{term.source_term}</strong><small>{term.source_language.toUpperCase()}</small></div><span className="term-arrow">→</span><div className="term-target"><strong>{term.target_term}</strong><small>{term.target_language.toUpperCase()}</small></div><button className="icon-button danger-hover" title="Remove term" onClick={() => onDelete(term.id)}><Trash2 size={15} /></button></div>)}</div> : <EmptyState icon={BookOpen} title="No terms added" text="Add critical part names and technical phrases to protect them during translation." />}</section></div></>
}

function VoicePage({ languages, caps }: { languages: Language[]; caps: Capabilities | null }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span /> SPEECH OUTPUT</div><h1>Voice settings<span>.</span></h1><p>Natural neural voices are selected automatically for each target language.</p></div><span className="small-chip provider-chip"><AudioLines size={14} /> EDGE TTS</span></div><div className="section-panel voice-list-panel"><div className="section-title"><div><span className="section-kicker">AVAILABLE VOICES</span><h2>Language presets</h2></div><span className="small-chip"><i className="online-dot" /> Free provider</span></div><div className="voice-grid">{languages.map((language, index) => <div className="voice-row" key={language.code}><div className={`voice-avatar avatar-${index % 4}`}><Volume2 size={17} /></div><div><strong>{language.name}</strong><small>{language.code.toUpperCase()} · Neural voice</small></div><button className="icon-button" title="Preview voice" onClick={() => window.open('https://speech.microsoft.com/portal/voicegallery', '_blank', 'noopener,noreferrer')}><Play size={14} /></button></div>)}</div></div><div className="notice-row"><ShieldCheck size={17} /><span>Voice generation uses the Edge TTS service. Network access is required; no API key is needed.</span><span>{caps?.tts_provider ?? 'edge'}</span></div></>
}

function HistoryPage({ projects, onOpen }: { projects: Project[]; onOpen: (id: number) => void }) {
  const sorted = [...projects].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  return <><div className="page-heading"><div><div className="eyebrow"><span /> ACTIVITY LOG</div><h1>History<span>.</span></h1><p>A chronological record of your video translation work.</p></div><span className="small-chip"><History size={14} /> {projects.length} events</span></div>{sorted.length ? <div className="section-panel history-panel"><div className="timeline">{sorted.map((item) => <button className="timeline-row" key={item.id} onClick={() => onOpen(item.id)}><span className="timeline-mark"><FileVideo2 size={15} /></span><span className="timeline-text"><strong>{item.title}</strong><small>{statusNames[item.status] ?? item.status} · {formatDuration(item.duration_seconds)} · {item.target_language.toUpperCase()}</small></span><span className="timeline-date">{new Date(item.created_at).toLocaleString()}</span><ChevronDown size={15} className="row-chevron" /></button>)}</div></div> : <div className="section-panel empty-page"><EmptyState icon={History} title="History starts here" text="Your translation activity will be recorded as you work." /></div>}</>
}

function SettingsPage({ caps }: { caps: Capabilities | null }) {
  return <><div className="page-heading"><div><div className="eyebrow"><span /> WORKSPACE CONFIGURATION</div><h1>Settings<span>.</span></h1><p>Runtime configuration and local service health.</p></div></div><div className="settings-grid"><section className="section-panel settings-panel"><div className="section-title"><div><span className="section-kicker">SYSTEM HEALTH</span><h2>Connected services</h2></div><Activity size={17} className="muted-icon" /></div>{[['FFmpeg', caps?.ffmpeg], ['ffprobe', caps?.ffprobe], ['GPU / CUDA', caps?.gpu], ['Lip-sync provider', caps?.lipsync_available]].map(([name, ready]) => <div className="service-row" key={String(name)}><span><i className={`health-dot ${ready ? 'good' : 'missing'}`} />{String(name)}</span><strong className={ready ? 'health-good' : 'health-missing'}>{ready ? 'Available' : 'Not detected'}</strong></div>)}<p className="settings-footnote">Install FFmpeg and ensure both ffmpeg and ffprobe are on PATH to enable upload validation and media processing.</p></section><section className="section-panel settings-panel"><div className="section-title"><div><span className="section-kicker">PROVIDERS</span><h2>Active defaults</h2></div><Settings2 size={17} className="muted-icon" /></div>{[['Speech recognition', caps?.stt_provider], ['Translation', caps?.translation_provider], ['Voice synthesis', caps?.tts_provider]].map(([name, value]) => <div className="service-row" key={String(name)}><span>{String(name)}</span><strong className="provider-value">{String(value ?? 'Loading…')}</strong></div>)}<p className="settings-footnote">Optional provider keys belong in the backend environment file. They are never exposed to the browser.</p></section></div></>
}

function UploadDialog({ languages, file, progress, busy, dragging, source, target, setSource, setTarget, onFile, onSubmit, onClose, onDrag }: { languages: { source: Language[]; target: Language[] }; file: File | null; progress: number; busy: boolean; dragging: boolean; source: string; target: string; setSource: (value: string) => void; setTarget: (value: string) => void; onFile: (file?: File) => void; onSubmit: () => void; onClose: () => void; onDrag: (value: boolean) => void }) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) { const selected = event.target.files?.[0]; onFile(selected) }
  function handleDrop(event: DragEvent<HTMLLabelElement>) { event.preventDefault(); onDrag(false); onFile(event.dataTransfer.files[0]) }
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="upload-modal" role="dialog" aria-modal="true" aria-labelledby="upload-title"><header><div><div className="eyebrow"><span /> NEW PROJECT</div><h2 id="upload-title">Bring a video to life.</h2><p>Upload a source recording to begin.</p></div><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={18} /></button></header><label className={`drop-zone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`} onDragOver={(event) => { event.preventDefault(); onDrag(true) }} onDragLeave={() => onDrag(false)} onDrop={handleDrop}><input type="file" accept="video/mp4,video/quicktime,video/x-msvideo,.mp4,.mov,.avi" onChange={handleChange} />{file ? <div className="uploaded-file"><div className="file-preview">{<FilePreview file={file} />}</div><span><strong>{file.name}</strong><small>{formatBytes(file.size)} · Preview loaded</small></span><button type="button" className="icon-button" aria-label="Remove file" onClick={(event) => { event.preventDefault(); onFile(undefined) }}><X size={16} /></button></div> : <><span className="upload-symbol"><Upload size={20} /></span><strong>Drop your video here, or <em>browse files</em></strong><small>MP4, MOV, AVI · Up to 500 MB · 10 minutes</small></>}</label><div className="upload-language-row"><label>Source language<select value={source} onChange={(event) => setSource(event.target.value)}>{languages.source.map((item) => <option value={item.code} key={item.code}>{item.name}</option>)}</select></label><span className="language-arrow">→</span><label>Translate to<select value={target} onChange={(event) => setTarget(event.target.value)}>{languages.target.map((item) => <option value={item.code} key={item.code}>{item.name}</option>)}</select></label></div>{progress > 0 && <div className="upload-progress"><span>Uploading video</span><span>{progress}%</span><div className="progress-track"><i style={{ width: `${progress}%` }} /></div></div>}<div className="modal-footer"><span><ShieldCheck size={14} /> Files stay in your workspace</span><button className="primary-button" disabled={!file || busy} onClick={onSubmit}>{busy ? <><LoaderCircle size={16} className="spin" /> Processing</> : <><Sparkles size={16} /> Start translation</>}</button></div></section></div>
}

function FilePreview({ file }: { file: File }) {
  const [url] = useState(() => URL.createObjectURL(file))
  useEffect(() => () => URL.revokeObjectURL(url), [url])
  return <video src={url} muted />
}

function EmptyState({ icon: Icon, title, text, action, onAction }: { icon: typeof Activity; title: string; text: string; action?: string; onAction?: () => void }) {
  return <div className="empty-state"><span className="empty-icon"><Icon size={21} /></span><strong>{title}</strong><p>{text}</p>{action && onAction && <button className="secondary-button" onClick={onAction}><Plus size={15} /> {action}</button>}</div>
}

export default App
