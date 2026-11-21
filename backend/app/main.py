from contextlib import asynccontextmanager
from pathlib import Path
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import dashboard, glossary, projects, system
from app.core.config import settings
from app.models import entities  # Register model metadata.


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "audio").mkdir(parents=True, exist_ok=True)
    migration_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    migration_config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(migration_config, "head")
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(projects.router)
app.include_router(glossary.router)
app.include_router(system.router)
app.include_router(dashboard.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": {"code": "INTERNAL_ERROR", "message": "The request could not be completed."}})


@app.get("/api/health")
def health():
    return {"status": "ok", "name": settings.app_name}
