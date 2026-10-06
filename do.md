I have an existing healthcare RAG application called CuraMind.

IMPORTANT:
Read PROJECT_HANDOFF.md first and inspect the existing rag-service code before making any changes.

CuraMind currently has two decoupled backend services:

1. Core Clinical Backend
   - FastAPI
   - SQLAlchemy
   - Alembic
   - JWT authentication
   - RBAC
   - Clinical database models
   - Patient/document/medication/lab/appointment/etc. APIs

2. Standalone RAG & Comparison Service
   - FastAPI
   - Pure PostgreSQL
   - pgvector
   - asyncpg / psycopg3
   - PDF/DOCX extraction
   - OCR fallback
   - page-preserving chunking
   - embeddings
   - permission-safe vector retrieval
   - grounded RAG assistant
   - citations
   - multi-turn conversations
   - deterministic document comparison
   - rate limiting
   - clinical evaluation benchmark

The existing implementation is already working and has tests.

DO NOT rewrite the project from scratch.

The objective is:

INTRODUCE LANGCHAIN ONLY WHERE IT PROVIDES A REAL BENEFIT FOR THE RAG/LLM PIPELINE.

Do NOT replace normal application/backend functionality with LangChain.

==================================================
1. KEEP THESE PARTS WITHOUT LANGCHAIN
==================================================

These should remain normal FastAPI/Python/PostgreSQL code:

- FastAPI routes
- Authentication
- JWT handling
- RBAC
- User permissions
- Workspace authorization
- Patient authorization
- Workspace isolation
- Patient isolation
- Database schema
- PostgreSQL connection pooling
- Raw SQL queries
- Database transactions
- Clinical CRUD operations
- Audit logging
- Rate limiting
- API validation
- File upload endpoints
- Background task management
- Document deletion/soft deletion
- Deterministic document comparison
- Structured field comparison
- difflib text comparison
- Cross-workspace comparison rejection
- Conversation persistence in PostgreSQL
- Frontend API contracts
- Existing API response schemas
- Existing authentication/authorization middleware
- Existing business logic

DO NOT introduce LangChain into these areas merely for abstraction.

==================================================
2. USE LANGCHAIN FOR THE LLM LAYER
==================================================

Replace the custom LLM orchestration where appropriate with LangChain's LLM abstraction.

Current architecture has:

app/services/llm.py
app/services/rag_assistant.py

Use LangChain for:

- LLM client abstraction
- model invocation
- streaming if currently supported/needed
- message formatting
- system/user messages
- structured output where useful

The LLM provider must remain swappable.

The configuration should support:

- APInex/OpenAI-compatible API
- OpenAI
- Anthropic
- Mock LLM for tests

Do NOT hardcode the provider.

Use environment variables for:

LLM_API_KEY
LLM_BASE_URL
LLM_MODEL

The APInex provider should be configurable through an OpenAI-compatible endpoint.

==================================================
3. USE LANGCHAIN FOR PROMPT TEMPLATES
==================================================

Replace manually constructed prompt strings with LangChain prompt templates.

Create a clean prompt structure for CuraMind:

System instructions
+
Clinical safety instructions
+
Retrieved context
+
Conversation history where appropriate
+
User question

The existing behavior MUST remain:

- Answer only from retrieved clinical records.
- Do not invent patient information.
- Refuse when relevant records are not available.
- Include appropriate clinical disclaimer behavior.
- Preserve citation information.
- Do not expose unauthorized information.

Do not weaken the existing grounding rules.

==================================================
4. USE LANGCHAIN FOR DOCUMENT LOADING
==================================================

Review the existing ingestion pipeline:

app/services/ingestion.py
app/services/ocr.py

Use LangChain document loaders where they provide value for:

- PDF
- DOCX
- text documents

However:

DO NOT remove existing OCR support.

The existing pytesseract/mock OCR behavior must continue working.

Preserve document metadata:

- document_id
- document_name
- workspace_id
- patient_id
- page_number
- source
- document_type
- timestamps
- authorization-related metadata

The metadata must survive:

document loading
→ splitting
→ embedding
→ vector storage
→ retrieval
→ LLM context
→ citation generation

==================================================
5. USE LANGCHAIN TEXT SPLITTERS
==================================================

Current implementation uses approximately:

chunk size = 500 characters
overlap = 50 characters

Review this implementation and replace the custom chunking logic with an appropriate LangChain text splitter where beneficial.

Do NOT blindly change the existing chunking behavior.

Preserve:

- page numbers
- document IDs
- patient IDs
- workspace IDs
- chunk ordering
- metadata

The existing chunking tests must continue to pass or be updated only when behavior intentionally changes.

==================================================
6. USE LANGCHAIN EMBEDDING ABSTRACTIONS
==================================================

Current project already has:

app/services/embeddings.py

with a swappable embedding provider:

- OpenAI
- Claude
- DeterministicMock

Use LangChain's embedding interface where appropriate.

The embedding provider must remain swappable.

Keep the current vector dimensionality requirement:

1536 dimensions

unless the existing codebase/provider configuration requires a deliberate change.

IMPORTANT:

Do NOT blindly recreate or re-embed the entire database.

Do not change the existing pgvector schema unless absolutely necessary.

==================================================
7. KEEP POSTGRESQL + PGVECTOR
==================================================

This is VERY IMPORTANT.

Do NOT replace PostgreSQL/pgvector with:

- Chroma
- Pinecone
- Weaviate
- FAISS
- Qdrant
- another vector database

The existing architecture intentionally uses:

PostgreSQL + pgvector.

LangChain should integrate with the existing vector database rather than forcing a new vector database.

If LangChain's vector-store abstraction is useful, use it carefully.

If using the abstraction would cause us to lose existing security filtering or metadata behavior, keep the existing SQL retrieval implementation and only use LangChain above it.

The database remains PostgreSQL + pgvector.

==================================================
8. DO NOT MOVE AUTHORIZATION INTO LANGCHAIN
==================================================

THIS IS A CRITICAL SECURITY REQUIREMENT.

The current retrieval implementation performs permission-safe vector search using:

- workspace_id
- patient_id
- user role

and restricts clinical notes for unauthorized roles.

Preserve this behavior exactly.

Authorization MUST happen BEFORE data is given to the LLM.

Correct:

Authenticated User
↓
RBAC / authorization
↓
workspace filter
↓
patient filter
↓
vector retrieval
↓
authorized chunks
↓
LangChain
↓
LLM

NOT:

User
↓
LangChain
↓
retrieve everything
↓
LLM
↓
try to hide unauthorized data

Never allow LangChain or the LLM to bypass PostgreSQL authorization filters.

==================================================
9. USE LANGCHAIN FOR RETRIEVAL ORCHESTRATION
==================================================

Review:

app/services/retrieval.py

If appropriate, create a LangChain-compatible retriever around the existing PostgreSQL/pgvector retrieval implementation.

The retriever should accept authorization context such as:

- user_id
- workspace_id
- patient_id
- role

The retriever must return only authorized documents.

Do not expose unrestricted vector search to the LLM.

Preserve:

- cosine similarity
- pgvector <=> operator
- metadata
- page numbers
- parent document information
- citation data

==================================================
10. USE LANGCHAIN FOR THE RAG PIPELINE
==================================================

Refactor:

app/services/rag_assistant.py

so LangChain handles the orchestration:

User question
↓
authorized retriever
↓
relevant chunks
↓
prompt template
↓
LLM
↓
structured answer/citations
↓
API response

Use modern LangChain APIs.

Do NOT use deprecated Chain classes if modern LangChain Runnable/LangChain Expression Language APIs are appropriate.

Keep the pipeline modular.

Prefer something conceptually similar to:

retriever
→ prompt
→ llm
→ parser

rather than creating unnecessary agent complexity.

==================================================
11. CITATIONS MUST REMAIN FIRST-CLASS
==================================================

The existing system generates verified citation objects:

- document_id
- document_name
- page_number
- snippet

Do NOT remove this behavior.

The final response must still provide citations based on actual retrieved chunks.

Never allow the LLM to invent citation metadata.

Ideally:

Retriever
↓
Documents + metadata
↓
LLM
↓
Answer
↓
Application verifies/constructs citations from retrieved metadata

The database/application remains the source of truth for citations.

==================================================
12. KEEP CONVERSATION STORAGE OUTSIDE LANGCHAIN
==================================================

The existing system stores:

conversations
conversation_messages

in PostgreSQL.

Keep this.

LangChain can be used for:

- message representations
- conversation context formatting
- history-aware retrieval if beneficial

But PostgreSQL remains the source of truth.

Do not replace the existing conversation database with LangChain memory.

==================================================
13. USE LANGCHAIN HISTORY-AWARE RETRIEVAL ONLY IF NEEDED
==================================================

Review the existing multi-turn conversation implementation.

If useful, implement:

conversation history
→ contextualized question
→ authorized retrieval
→ RAG answer

But do NOT automatically send the entire conversation history to the LLM.

Keep context controlled and efficient.

==================================================
14. DO NOT TURN CURAMIND INTO AN AGENT BY DEFAULT
==================================================

This is a RAG assistant, not an unrestricted autonomous agent.

Do NOT introduce agents simply because LangChain supports them.

Normal questions should use:

Retriever → Prompt → LLM

Only use LangChain tools/agents if there is an actual requirement such as:

- searching medications
- retrieving lab results
- retrieving appointments
- querying patient records
- performing multi-step operations

Even then:

Every tool must enforce authorization.

The LLM must never directly access the database.

==================================================
15. KEEP DETERMINISTIC DOCUMENT COMPARISON WITHOUT LANGCHAIN
==================================================

Do NOT modify:

app/services/comparison.py

for LangChain.

The comparison system is deterministic and should remain deterministic.

Keep:

- structured field diffing
- SequenceMatcher
- workspace boundary validation
- difference status
- missing/matched/different fields

LangChain provides no meaningful benefit here.

==================================================
16. PRESERVE RATE LIMITING
==================================================

Keep:

app/services/rate_limiter.py

outside LangChain.

Rate limiting must happen at the application/service/API layer.

Do not rely on LangChain for security or quota enforcement.

==================================================
17. PRESERVE THE EXISTING EVALUATION SYSTEM
==================================================

The existing system has a 16-case clinical benchmark covering:

- accuracy
- groundedness
- citations
- refusal behavior
- patient isolation

DO NOT remove this.

After the LangChain migration:

Run all existing tests.

Expected:

Core Backend:
10/10 tests passing

RAG Service:
13/13 tests passing

The existing tests include:

- ingestion
- chunking
- embeddings
- retrieval isolation
- comparison
- RAG assistant
- conversations
- evaluation

Any changed tests must have a clear reason.

==================================================
18. TARGET ARCHITECTURE
==================================================

The desired architecture should be:

FastAPI
│
├── Authentication / RBAC
│
├── API Routes
│
├── PostgreSQL
│
└── RAG Service
      │
      ├── Document Ingestion
      │     ├── PDF/DOCX extraction
      │     ├── OCR
      │     └── LangChain Document Loaders
      │
      ├── Chunking
      │     └── LangChain Text Splitters
      │
      ├── Embeddings
      │     └── LangChain Embedding Interface
      │
      ├── PostgreSQL + pgvector
      │     └── Existing database
      │
      ├── Authorized Retriever
      │     └── Existing permission-safe SQL retrieval
      │
      ├── LangChain RAG Pipeline
      │     ├── Retriever
      │     ├── Prompt Template
      │     ├── Conversation Context
      │     ├── LLM
      │     └── Output Parser
      │
      ├── Citation Verification
      │
      ├── Conversation Persistence
      │     └── PostgreSQL
      │
      ├── Rate Limiter
      │
      └── Evaluation

==================================================
19. CREATE A MIGRATION PLAN BEFORE CODING
==================================================

Before changing anything, inspect the entire repository.

Then provide:

A. Current architecture

B. Current components that should remain unchanged

C. Current components that should use LangChain

D. Exact files that need modification

E. Exact LangChain packages required

F. Migration risks

G. Security risks

H. Backward compatibility considerations

Then implement the changes.

==================================================
20. IMPORTANT: MINIMAL MIGRATION
==================================================

Do not rewrite working code simply to increase LangChain usage.

The goal is:

CURRENT WORKING CURAMIND
+
SELECTIVE LANGCHAIN INTEGRATION
=
BETTER RAG/LLM ORCHESTRATION

NOT:

CURRENT CURAMIND
→ complete rewrite using LangChain

Preserve existing APIs and frontend behavior.

==================================================
21. FINAL REPORT
==================================================

After implementation, provide:

1. Files changed
2. Files intentionally left unchanged
3. LangChain components introduced
4. Why each LangChain component was introduced
5. APInex/OpenAI-compatible LLM configuration
6. RAG flow
7. Authorization flow
8. Citation flow
9. Conversation flow
10. Packages installed
11. Environment variables
12. Tests executed
13. Test results
14. Any remaining limitations

Most importantly:

Clearly separate:

"LANGCHAIN RESPONSIBILITIES"

from:

"CURAMIND APPLICATION RESPONSIBILITIES"

The final implementation must preserve CuraMind's existing security, workspace isolation, patient isolation, citations, deterministic comparison, conversations, rate limiting, and evaluation behavior.