# LinguaDub AI

LinguaDub AI is a local-first multilingual video translation workspace. It combines FastAPI, SQLAlchemy/Alembic, React/Vite, faster-whisper, Google Translate, Edge TTS, and FFmpeg behind provider adapters. Paid-provider keys are optional.

## Run locally

Requirements: Python 3.11 or newer, Node.js 20.19+ (or 22.12+), and FFmpeg with `ffmpeg` and `ffprobe` on `PATH`. Noto fonts are recommended for Hindi, Arabic, and CJK subtitle rendering. Whisper downloads its selected model on first transcription. CPU works, but transcription is slower than CUDA.

1. Copy `.env.example` to `.env` and adjust the documented limits/providers if needed.
2. In one terminal:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

3. In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. FastAPI OpenAPI docs are at <http://localhost:8000/docs>.

To run with Docker, use `docker compose up --build`. The compose file installs FFmpeg/Noto fonts in the backend image and persists media/database files under `storage/`.

## Demo flow

1. Use a short MP4/MOV/AVI with an audio track (the configured maximum defaults to 10 minutes and 500 MB).
2. Upload and choose the source and target languages. The upload is checked by signature and ffprobe before it is saved as a project.
3. Review the Whisper transcript and adjust text/timings. Add machine terms in **Glossary** (for example `主轴` → `स्पिंडल`).
4. Translate, review/edit translated segments, then generate voice. Segment previews are available from the play icon.
5. Export the MP4 with soft or burned subtitles. Download the dubbed WAV, original/translated SRT/VTT, and transcript JSON/TXT.

For a generated 12-second real-media integration test (requires FFmpeg, faster-whisper, model download, and free-provider network access):

```powershell
cd backend
$env:RUN_MEDIA_INTEGRATION = "1"
python -m pytest -m integration -q
```

## Providers and configuration

The zero-paid-key defaults are `STT_PROVIDER=faster-whisper`, `TRANSLATION_PROVIDER=google`, and `TTS_PROVIDER=edge`. Translation and TTS require network access. Set `STT_PROVIDER=openai` with `OPENAI_API_KEY`, `TRANSLATION_PROVIDER=gemini` with `GEMINI_API_KEY`, or `TTS_PROVIDER=elevenlabs` with `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` to use optional providers. Secrets are read only by the backend and must not be put in frontend variables.

`WHISPER_MODEL` controls the local model (`tiny`, `base`, `small`, etc.); `WHISPER_DEVICE` is `cpu` by default. `MAX_UPLOAD_MB` and `MAX_VIDEO_MINUTES` set upload limits. `DATABASE_URL` can be changed to a PostgreSQL SQLAlchemy URL; migrations are managed with Alembic. Storage paths are configured via `STORAGE_DIR`.

Lip sync is off by default. To enable the local adapter, install a compatible CUDA-enabled PyTorch setup, configure `WAV2LIP_REPO` to a local Wav2Lip checkout and `WAV2LIP_CHECKPOINT` to its checkpoint. The UI disables the toggle unless CUDA, inference script, and weights are detected. Failed lip-sync inference falls back to the dubbed FFmpeg export.

## API overview

Core endpoints include upload/list/detail/delete/duplicate, transcription, segment editing, translation and per-segment retranslation, dub and segment preview, export and artifact download, glossary CRUD, status/retry/cancel, voice/language/capability metadata, and dashboard stats. Every route is documented in OpenAPI. Processing jobs use FastAPI `BackgroundTasks` and persist job records in SQLAlchemy tables.

## Tests

```powershell
cd backend
python -m pytest -q
```

```powershell
cd frontend
npm run build
npm run lint
```

The normal backend suite does not require FFmpeg or model downloads. The end-to-end media test is opt-in and reports a skip unless its prerequisites are available.

## Known limitations

- This is a hackathon-scale single-user workspace; authentication, tenant isolation, and production quotas are not included.
- Local speech transcription requires downloading the selected Whisper model and may be slow on CPU. The real-media integration test was not run in environments without FFmpeg/ffprobe and faster-whisper.
- The default Google Translate adapter is free but network-dependent and may rate-limit; technical accuracy should be reviewed, especially for uncommon Chinese machine terms. Glossary mappings are protected during translation.
- Edge TTS is network-dependent. Output timing is fitted with FFmpeg atempo up to 1.25x; overly long phrases are shortened by a simple character-ratio rule, so review is recommended.
- Demucs is optional. When unavailable, FFmpeg sidechain compression ducks the original audio under the dubbed track; it does not perfectly isolate machine sounds or music.
- Lip sync requires a compatible CUDA setup, local Wav2Lip repository, and weights. CPU-only setups export without lip sync.
- Subtitle burn-in requires compatible FFmpeg subtitle filters and fonts. Soft subtitles are embedded as MP4 `mov_text`; SRT/VTT sidecars are also generated.
- Speaker diarization, pause-aware long-audio chunk merging, detailed edit operations for splitting/merging transcript segments, and durable distributed job execution (Celery/Redis) are not implemented. Jobs run in the API process.
- PostgreSQL configuration is supported through SQLAlchemy, but only SQLite startup has been exercised here.
