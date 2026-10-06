from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.controllers import (
    comparison_api,
    conversations_api,
    evaluation_api,
    ingestion_api,
    retrieval_api,
    summarise_api,
)
from pathlib import Path
from app.db.postgres import init_db
from app.db.postgres import is_postgres_active
from scripts.ingest_clinical_files import ingest_files


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize pure PostgreSQL schema
    await init_db()
    # Ingest clinical PDF files from files/ directory if present
    files_dir = Path(__file__).resolve().parent.parent.parent / "files"
    if files_dir.exists():
        ws_ids = {"default-workspace"}
        # Attempt to discover workspaces from backend sqlite db if present
        backend_db = Path(__file__).resolve().parent.parent.parent / "backend" / "curamind.db"
        if backend_db.exists():
            try:
                import sqlite3
                con = sqlite3.connect(str(backend_db))
                cur = con.cursor()
                cur.execute("SELECT id FROM workspaces")
                for (wid,) in cur.fetchall():
                    if wid:
                        ws_ids.add(str(wid))
                con.close()
            except Exception:
                pass

        for wid in ws_ids:
            try:
                await ingest_files(files_dir=files_dir, workspace_id=wid)
            except Exception as e:
                print(f"Warning: Auto-ingest of clinical files for {wid} encountered: {e}")
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    description="CuraMind RAG / LLM Assistant & Document Comparison Service (Pure PostgreSQL)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(ingestion_api.router, prefix="/api/v1")
app.include_router(retrieval_api.router, prefix="/api/v1")
app.include_router(comparison_api.router, prefix="/api/v1")
app.include_router(conversations_api.router, prefix="/api/v1")
app.include_router(evaluation_api.router, prefix="/api/v1")
app.include_router(summarise_api.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    postgres_active = await is_postgres_active()
    return {
        "status": "ok",
        "service": "CuraMind RAG Service",
        "db": "PostgreSQL + pgvector" if postgres_active else "in-memory fallback (non-persistent)",
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
    }
