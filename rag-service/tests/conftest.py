import os
import sys
from pathlib import Path

# Add rag-service to sys.path
rag_service_dir = str(Path(__file__).resolve().parent.parent)
if rag_service_dir not in sys.path:
    sys.path.insert(0, rag_service_dir)

import jwt
import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.db.memory_fallback import in_memory_store
from app.main import app


def make_token(user_id: str, workspace_id: str, role: str, email: str = "test@example.com") -> str:
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "workspace_id": workspace_id,
        "role": role,
        "email": email,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_db_store():
    orig_llm = settings.LLM_PROVIDER
    orig_emb = settings.EMBEDDING_PROVIDER
    settings.LLM_PROVIDER = "mock"
    settings.EMBEDDING_PROVIDER = "mock"
    in_memory_store.reset()
    yield
    in_memory_store.reset()
    settings.LLM_PROVIDER = orig_llm
    settings.EMBEDDING_PROVIDER = orig_emb


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
