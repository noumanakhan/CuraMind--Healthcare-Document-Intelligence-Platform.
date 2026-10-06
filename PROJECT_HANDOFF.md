# CuraMind Project Handoff

## Overview
CuraMind is an enterprise clinical document intelligence workspace featuring multi-role access control, secure authentication, workspace-scoped clinical records, and a standalone **RAG / LLM Assistant & Deterministic Document Comparison Service** built with pure PostgreSQL + pgvector.

---

## Architecture & Services

The application consists of two decoupled backend services and a React frontend:

### 1. Core Clinical Backend (`backend/app/`)
- **Framework & DB**: FastAPI + SQLAlchemy + Alembic migrations.
- **`core/`**: JWT auth (`security.py`), RBAC authorization (`rbac.py`).
- **`models/`**: Clinical database models (`Patient`, `Document`, `Medication`, `LabTest`, `Appointment`, `DischargeDraft`, `Immunization`, `Vitals`, `AuditEvent`).
- **`controllers/`**: Endpoints under `/api/v1` for patient CRUD, charts, discharge summaries, and dashboard stats.

### 2. Standalone RAG & Comparison Service (`rag-service/app/`)
*Built in a dedicated directory separate from `backend/`, using **pure PostgreSQL** without SQLAlchemy:*
- **Database (`app/db/`)**:
  - `schema.sql`: Pure PostgreSQL DDL with `pgvector` extension (`vector(1536)`).
  - `postgres.py`: Connection pool (`asyncpg` / `psycopg3`) executing parameterized raw SQL queries (`$1, $2`).
  - `memory_fallback.py`: In-memory PostgreSQL relational store with vector cosine similarity for test/offline execution.
- **Ingestion Pipeline (`app/services/ingestion.py`, `ocr.py`)**:
  - LangChain Community loaders for PDF, DOCX, and text, with page-preserving metadata and the existing pypdf fallback.
  - Scanned PDF pages are rendered before real OCR; mock OCR returns no text so it cannot invent clinical facts.
  - LangChain page-preserving chunking (~500 chars with ~50 overlap).
  - Background asynchronous task runner with non-blocking HTTP 202 uploads and granular error states (`processing`, `processed`, `failed`).
- **Embeddings & Retrieval (`app/services/embeddings.py`, `retrieval.py`)**:
  - Swappable LangChain embedding adapters (`OpenAI`, `Gemini`, `DeterministicMock`); explicit provider failures do not silently mix in mock vectors.
  - Permission-safe vector search pre-filtered by `workspace_id`, `patient_id`, and user role (viewer/records restricted from clinical notes).
  - Native LangChain `BaseRetriever` wraps the existing authorized SQL; configured semantic relevance filtering runs before chunks enter the model.
  - Nearest neighbor search via pgvector cosine distance operator `<=>`.
  - Parent document metadata and page numbers joined directly in retrieval output for real-time citations.
- **Deterministic Document Comparison (`app/services/comparison.py`)**:
  - Structured field diffing (labels, matched/differ/missing status).
  - Full-text line diffing via `difflib.SequenceMatcher`.
  - Strict workspace boundaries (cross-workspace comparisons rejected).
- **Clinical RAG Assistant (`app/services/rag_assistant.py`, `llm.py`)**:
  - LCEL retriever → prompt → configured LangChain chat model / explicit mock runnable → output parser pipeline (`Gemini`, `Anthropic/Claude`, `OpenAI`/APInex, `MockLLM`).
  - Grounded prompt engineering: answers strictly from retrieved chunks, clinical disclaimers, explicit refusal on questions with no matching records.
  - Generates verified citation objects (`document_id`, `document_name`, `page_number`, `snippet`).
  - Multi-turn conversation persistence (`conversations`, `conversation_messages`).
- **Evaluation & Cost Controls (`app/services/evaluation.py`, `rate_limiter.py`)**:
  - Sliding-window rate limiter per user/workspace on AI endpoints.
  - 16-case clinical benchmark test suite measuring accuracy, groundedness, citations, and refusal behaviors.

### 3. Frontend Application (`frontend/`)
- **`Ask.jsx`**: Wired to conversation & RAG assistant endpoints with real citation chips, loading states, and clinical notice banners.
- **`Compare.jsx`**: Wired to deterministic document comparison with dual document pickers, structured diff highlighting, and difference counters.

---

## API Endpoints Summary

### Core Backend (`http://localhost:8000/api/v1`)
- `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `GET /auth/permissions`
- `GET /users`, `PATCH /users/{id}/role`, `PATCH /users/{id}/status`
- `GET /patients`, `POST /patients`, `GET /patients/{id}`, `PATCH /patients/{id}`
- `GET/POST /patients/{id}/documents`, `PATCH /documents/{id}/fields/{id}/confirm`
- `GET /patients/{id}/medications`, `PATCH /medications/{id}/review`
- `GET /patients/{id}/labs`, `POST /patients/{id}/labs/{test_id}/points`
- `GET/POST /patients/{id}/appointments`
- `GET /patients/{id}/discharge`, `POST /patients/{id}/discharge/sign`
- `GET /patients/{id}/immunizations`, `GET/POST /patients/{id}/vitals`
- `GET /patients/{id}/audit`, `GET /dashboard/stats`

### RAG & Comparison Service (`http://localhost:8001/api/v1`)
- `POST /documents/upload` (multipart background ingestion)
- `POST /documents`, `GET /documents`, `GET /documents/{id}`, `DELETE /documents/{id}`
- `POST /retrieval/search` (vector similarity search)
- `POST /patients/{id}/documents/compare`, `POST /documents/compare`
- `GET/POST /patients/{id}/conversations`, `GET/POST /conversations`
- `GET /conversations/{id}/messages`, `POST /conversations/{id}/messages`
- `POST /evaluation/run` (16-case benchmark evaluation)

---

## Test Verification Suite

- **Core Backend**: `10/10 passed` (`pytest backend/tests/`)
- **RAG & Comparison Service**: `23/23 passed` (`pytest rag-service/tests/`)
  - `test_ingestion.py`: PDF, DOCX, OCR fallback, background task, error handling.
  - `test_chunking_embeddings.py`: Chunking fidelity, page numbers, 1536-dim embeddings, soft-delete exclusion.
  - `test_retrieval_isolation.py`: Cross-workspace isolation, cross-patient isolation, RBAC role filtering.
  - `test_comparison.py`: Structured & text diffs, cross-workspace rejection.
  - `test_rag_assistant.py`: Grounded answers, refusal when not found, citation extraction, patient isolation.
  - `test_conversations.py`: Multi-turn chat persistence and history.
  - `test_evaluation.py`: 16-case clinical benchmark test execution.
- **Frontend Build**: `npm run build` completed cleanly with zero errors.
