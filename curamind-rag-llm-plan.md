# CuraMind — RAG / LLM Assistant & Document Comparison: Full Implementation Plan

Paste this into your IDE's AI assistant as the task description. This covers Phase 3 (document
processing & comparison) and Phase 4 (RAG assistant) from the original roadmap, now that auth,
RBAC, workspace isolation, and the core clinical models are built and tested.

Work through the numbered sections **in order**. Each section ends with tests that must pass
before moving to the next — do not build the chat assistant before retrieval is permission-safe,
and do not build AI-assisted comparison before the deterministic comparison works.

---

## 0. Prerequisite decision: move to PostgreSQL + pgvector before building embeddings

Vector similarity search is not something SQLite does natively or efficiently. Before any
embedding work starts:

1. Stand up PostgreSQL (local Docker container for dev is fine) and install the `pgvector`
   extension.
2. Update `core/config.py` and the Alembic env to point at Postgres instead of SQLite. Run all
   existing migrations against it and confirm the full existing test suite still passes
   unchanged — this is a database swap, not a schema change, so nothing in `models/` should need
   to change for this step alone.
3. Add `pgvector`'s SQLAlchemy integration (`pgvector.sqlalchemy.Vector` column type) as a
   dependency.
4. Do not proceed to Section 2 until the existing test suite passes against Postgres.

This is worth doing now rather than prototyping embeddings on SQLite and migrating later —
retrieval quality and latency work very differently once the storage engine changes, and you'd
redo tuning work twice otherwise.

---

## 1. Document ingestion pipeline (text extraction, OCR, background processing)

Your `Document`/`ExtractedField` models already exist for structured field extraction. This
section adds the **full-text** pipeline needed for RAG, which is a separate concern from
structured field extraction (a document can have both: structured fields like "Diagnosis" *and*
full-text chunks for semantic search over the whole note).

### 1.1 Background job infrastructure

Document processing (OCR, chunking, embedding) must not block the HTTP request/response cycle.

1. Add a background task runner. For this stage, FastAPI's built-in `BackgroundTasks` is enough
   for Document OCR + embedding and does not need Celery/Redis yet — only introduce a real task
   queue if/when processing volume or multi-worker scaling requires it. Note that choice
   explicitly in your output rather than silently picking one.
2. Add a `processing_status` field to `Document` if not already granular enough (it currently has
   `processing / needs_review / processed`) — add `failed` as a status, and a
   `processing_error` (nullable text) field to record why, without exposing stack traces to the
   API response.

### 1.2 Text extraction service (`services/ingestion.py`)

1. For text-layer PDFs/DOCX: extract text directly (e.g. `pypdf`/`pdfplumber` for PDF,
   `python-docx` for DOCX).
2. For scanned/image documents with no text layer: run OCR (e.g. `pytesseract` wrapping Tesseract,
   or a cloud OCR provider if you prefer — keep the OCR call behind an interface so the provider
   can be swapped later without touching the rest of the pipeline).
3. Store the full extracted text on the `Document` row (new `full_text` column) or in object
   storage with a reference, depending on expected document size — plain text in Postgres is fine
   at this stage; don't over-engineer storage yet.
4. On extraction failure, set `processing_status = failed` with a reason, write an audit event,
   and leave the document queryable by structured fields (if any already exist) rather than
   disappearing from the UI.

### 1.3 Tests for this section
- Text-layer PDF extracts correctly
- Image-only PDF routes through OCR and extracts correctly
- A corrupted/unsupported file fails gracefully with `processing_status = failed`, not a 500
- Extraction runs in the background — the upload endpoint returns immediately, not after OCR
  completes

---

## 2. Chunking & embeddings

### 2.1 Chunking strategy (`services/ingestion.py`, extended)

1. Split `full_text` into overlapping chunks (e.g. ~500 tokens with ~50 token overlap — tune
   later, but start with a sane default rather than an arbitrary one).
2. Preserve page number per chunk where the source format supports it (PDF page boundaries) —
   this is required for citations later (Section 5). If page boundaries aren't available for a
   format, store a best-effort section/paragraph index instead and note the limitation.
3. New model, `DocumentChunk`:
   ```
   id, document_id (FK), workspace_id (FK), patient_id (FK), chunk_text,
   page_number (nullable), chunk_index, embedding (pgvector column),
   created_at
   ```
   Carrying `workspace_id` and `patient_id` directly on the chunk (denormalized from `Document`)
   is deliberate — it lets the retrieval query filter on the chunk table alone without an extra
   join on every search, which matters for query performance and makes the permission filter
   impossible to accidentally omit.

### 2.2 Embedding generation (`services/embeddings.py`)

1. Choose one embedding model and keep it behind an interface (`embed_text(text: str) -> list[float]`)
   so the provider can change later without touching ingestion/retrieval code.
2. Generate an embedding per chunk, store it on `DocumentChunk.embedding`.
3. Batch embedding calls where the provider supports it, rather than one call per chunk, to keep
   ingestion latency and cost reasonable for multi-page documents.
4. Add a migration for `DocumentChunk` via Alembic — do not skip this, per the existing project
   convention.

### 2.3 Tests for this section
- A document's chunks sum back to (approximately) its full text with no silent data loss
- Each chunk has a non-null embedding of the expected dimensionality
- Page numbers are correctly attached where the source format provides them
- Deleting a `Document` (soft-delete) also excludes its chunks from retrieval — verify this
  explicitly, it's an easy thing to miss

---

## 3. Retrieval service — permission-safe by construction

This is the most important section in this plan. Per the handoff doc's own stated requirement:
retrieval must filter by workspace, user permissions, and patient/document access rules **before**
retrieval, not after.

### 3.1 `services/retrieval.py`

```python
def search_chunks(
    query_embedding: list[float],
    workspace_id: UUID,
    user: User,
    patient_id: UUID | None = None,
    top_k: int = 8,
) -> list[DocumentChunk]:
    ...
```

1. The query **must** filter `DocumentChunk.workspace_id == workspace_id` as a non-optional,
   non-bypassable clause — not something the caller can forget to pass.
2. If `patient_id` is given, filter to that patient's chunks only — used when the assistant is
   scoped to one patient's chart (the common case: "what does this patient's chart say about X").
3. If no `patient_id` is given (a workspace-wide query), additionally filter by the requesting
   user's role/permissions: a `records` or `viewer` role should not retrieve chunks from clinical
   note documents even in a broad search, matching the same document-type/role rules already
   enforced on direct document access. Reuse `core/rbac.py` for this check — do not hand-roll a
   second permission system for retrieval.
4. Use pgvector's cosine similarity operator for the actual nearest-neighbor search.
5. Return chunks with their `document_id`, `page_number`, and parent `Document.name` attached
   (joined), since the caller needs this for citations — don't make the caller do a second
   round-trip per chunk.

### 3.2 Tests for this section (write these before building the chat assistant on top)
- A query scoped to Patient A never returns chunks from Patient B, even within the same workspace
- A query in Workspace 1 never returns chunks from Workspace 2
- A `viewer` searching workspace-wide does not get clinical-note chunks back
- A `clinician` searching within a patient they have access to gets relevant chunks back
- An empty/no-match query returns an empty list, not an error

---

## 4. Deterministic document comparison (build this before AI-assisted comparison)

Per the roadmap: build deterministic comparison first, AI comparison second. This also gives you
a non-LLM fallback and a way to sanity-check the AI version's output later.

### 4.1 `services/comparison.py`

1. Given two `Document` IDs (must belong to the same workspace — enforce this), retrieve their
   `full_text` (or their `ExtractedField` sets, if comparing structured fields specifically —
   support both modes, since your frontend's Compare Reports screen currently compares structured
   fields like "Chief complaint" / "Suggested ICD-10").
2. For structured-field comparison: diff matching `ExtractedField.label` values between the two
   documents, flagging where values differ (this maps directly to your existing `Compare.jsx`
   `COMPARE_ROWS` shape — formalize it as real output instead of mock rows).
3. For full-text comparison (optional, if needed beyond structured fields): use a standard text
   diff algorithm (e.g. `difflib`) to highlight added/removed/changed passages, with page
   references preserved where available.
4. New endpoint: `POST /patients/{id}/documents/compare` (or a workspace-level
   `POST /documents/compare` if comparing across patients should be supported — confirm which
   your product needs; the current frontend only compares within context of a patient's chart, so
   default to patient-scoped).

### 4.2 Tests for this section
- Comparing two documents with identical field values returns no differences flagged
- Comparing documents with a changed field value correctly flags it
- Comparing a document from Workspace A against one from Workspace B is rejected, not silently
  allowed
- A document missing a field the other has is handled explicitly (shown as "not present"), not
  dropped silently

---

## 5. RAG assistant — retrieval-augmented chat with citations

Only start this once Sections 3 and 4 are tested and passing.

### 5.1 `services/rag_assistant.py`

1. Embed the user's question using the same embedding function from Section 2.2.
2. Call `search_chunks` (Section 3) with the appropriate `workspace_id`, `user`, and optional
   `patient_id` scope.
3. Construct the LLM prompt with:
   - The retrieved chunks, each clearly labeled with its source document name and page number
   - An explicit system instruction: answer **only** from the provided chunks; if the answer
     isn't in them, say so explicitly rather than guessing; never present output as a diagnosis or
     autonomous treatment decision; flag when sources conflict rather than silently picking one
4. Call the LLM (keep the provider behind an interface, same principle as embeddings — this
   project already runs on Claude in other contexts, so using the Anthropic API here is a
   reasonable default, but don't hardcode assumptions that make swapping providers hard later).
5. Parse the response to extract which chunks were actually used, and return a citations array
   (`document_id`, `document_name`, `page_number`) alongside the answer text — this is what
   renders as the citation chips already built in `Ask.jsx`.
6. If retrieval returns zero relevant chunks, return an explicit "no relevant information found in
   this patient's indexed documents" response rather than letting the LLM answer from general
   knowledge — this is a hard requirement, not a nice-to-have, given the clinical context.

### 5.2 Conversation persistence

1. New models: `Conversation` (id, workspace_id, patient_id nullable, user_id, created_at) and
   `ConversationMessage` (id, conversation_id, role, content, citations as JSON, created_at).
2. New endpoints:
   ```
   GET  /patients/{id}/conversations
   POST /patients/{id}/conversations
   POST /conversations/{id}/messages
   GET  /conversations/{id}/messages
   ```
3. Every message write goes through the same workspace/permission checks as Section 3 — a
   conversation scoped to a patient inherits that patient's access rules.

### 5.3 Streaming (optional but recommended for UX)

1. If the LLM provider supports streaming, stream tokens back via Server-Sent Events or a
   WebSocket, so the frontend chat feels responsive rather than waiting for a full response.
2. If deferring this, say so explicitly and build the non-streaming version first — don't let
   streaming infrastructure block getting a working assistant shipped.

### 5.4 Tests for this section
- A question scoped to Patient A cannot surface information from Patient B's documents, even
  indirectly through the LLM's answer (test with documents that have distinctive content to make
  leakage detectable)
- A question with no relevant indexed content returns the explicit "not found" response, not a
  hallucinated answer
- Citations returned match chunks actually retrieved and used, not fabricated ones
- A `viewer` role gets appropriately scoped answers per the same document-type restrictions as
  direct retrieval

---

## 6. Evaluation, safety, and cost controls (do not skip this for a clinical product)

1. **Evaluation set**: build a small set of test questions with known expected answers and
   expected source documents, specific to your seeded test data. Run this set after any change to
   chunking, retrieval, or prompting, and track whether answers stay grounded and citations stay
   accurate. This doesn't need to be elaborate — even 15-20 question/answer pairs reviewed
   manually is far better than no evaluation at all.
2. **Faithfulness check**: periodically (manually, to start) verify that answers don't say
   anything the cited chunks don't actually support.
3. **Rate limiting**: add rate limiting on the chat/comparison endpoints specifically — LLM calls
   are the most expensive operation in the system, and both cost and abuse risk are real here.
4. **Token/cost ceiling**: cap the number of chunks retrieved per query and the max response
   length, with sane defaults, so a single query can't balloon into an expensive request.
5. **Disclaimer in every assistant response** (UI-level, not just a backend concern): the
   assistant's output is informational and requires clinician review — it does not diagnose or
   recommend treatment. This should be visible in the chat UI, not just in documentation.

---

## 7. Frontend wiring (only after backend sections above are tested)

1. `Ask.jsx` — replace the mock `INITIAL_MESSAGES` flow with real calls to the conversation
   endpoints from Section 5.2, rendering citations from the real response instead of hardcoded
   `cites` arrays.
2. `Compare.jsx` — replace mock `COMPARE_ROWS` with a real call to the comparison endpoint from
   Section 4, with a document picker (the UI already has `cmp-slot` placeholders for this).
3. Add loading and error states to both screens for the new async calls.
4. Keep any remaining mock content clearly labeled as such if parts of this aren't wired up yet —
   do not let real and mock data blend silently, consistent with the project's existing rule.

---

## 8. Updated deliverables checklist

- [ ] Postgres + pgvector running, all existing tests passing against it
- [ ] `DocumentChunk` model + migration
- [ ] Ingestion pipeline: text extraction, OCR fallback, background processing, failure handling
- [ ] Embedding generation behind a swappable interface
- [ ] `search_chunks` retrieval service with workspace + patient + role filtering, fully tested
      for isolation
- [ ] Deterministic comparison service + endpoint, tested
- [ ] RAG assistant service: grounded answers, explicit "not found" handling, real citations
- [ ] `Conversation`/`ConversationMessage` models + endpoints
- [ ] Rate limiting and token/cost ceilings on AI endpoints
- [ ] A small manual evaluation set, run and reviewed at least once
- [ ] Frontend `Ask.jsx` and `Compare.jsx` connected to real endpoints, with loading/error states
- [ ] `PROJECT_HANDOFF.md` updated to reflect what's actually built and tested, same standard as
      before — nothing marked done without a passing test behind it

---

## Final instruction to the IDE

> Work through Sections 0–7 above in order. Do not build the RAG assistant (Section 5) before the
> permission-safe retrieval service (Section 3) is fully tested — retrieval correctness is a
> patient-data-isolation concern, not just a relevance concern. Do not build AI-assisted
> comparison before the deterministic comparison (Section 4) works, since it's both a required
> precursor and a useful fallback. Keep embedding and LLM providers behind interfaces so they can
> be swapped later. Never let the assistant answer from outside the retrieved, permission-filtered
> context. After each section, run the full backend test suite and report actual pass/fail
> results before moving to the next section. Do not use real patient data at any point. Update
> `PROJECT_HANDOFF.md` at the end with what was actually built and verified.
