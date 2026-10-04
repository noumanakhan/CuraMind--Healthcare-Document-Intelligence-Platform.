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
)
from app.db.postgres import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize pure PostgreSQL schema
    await init_db()
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
    allow_origins=["*"],
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


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "CuraMind RAG Service",
        "db": "PostgreSQL",
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
    }
