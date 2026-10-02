# CuraMind Backend Design Requirements

## 1. Purpose and scope

This document translates the current CuraMind frontend into a backend design brief. It is intended to guide the design and implementation of the API, database, file storage, background processing, search/RAG, authorization, and audit services.

The app is a clinical document intelligence workspace. It combines a patient roster and chart with document ingestion and AI-assisted extraction, lab trends, medication safety flags, appointments, discharge summaries, a clinical assistant with citations, document comparison, and workspace settings.

> **Important scope note:** The current frontend is a demo, not a functioning EHR or clinical decision system. Most data is seeded mock data held in React context and browser `localStorage`. No real file is uploaded, parsed, searched, or sent to an AI service. Backend behavior described as a requirement below is a design target, not a claim that it already exists. This is not a compliance certification or a substitute for clinical, legal, privacy, and security review.

## 2. Frontend inventory and current behavior

| Area | Current frontend behavior | Backend capability needed |
|---|---|---|
| Dashboard | Computes patient census, discharge-pending patients, flagged extracted fields, medication flags, upcoming appointments, and recent chart activity from shared client state. Links to patient charts and work queue. | Authorized dashboard aggregates, review-item feed, appointments, activity feed, and pagination/time filtering. |
| Work queue | Derives medication, document-field, discharge, and abnormal-lab items locally. Offers category filters and text search across title, summary, patient name, and MRN. | Persisted/recomputable review work items, filters/search, assignment/priority/status lifecycle, and audit events. Do not rely on the client to determine clinical flags. |
| Patients | Lists active patients filtered by admission status; archive filter is visible to roles with archive permission. Supports create, demographic edit, archive/restore, and opening a chart. | Patient search/list/detail/create/update/archive/restore with server-side validation, duplicate detection, and role enforcement. |
| Patient overview | Shows demographics, contact/emergency contact, insurance, care team, latest vitals snapshot, and immunizations. | Patient and related resource read APIs; structured, time-stamped observations and immunization history. |
| Patient documents | Shows documents and extracted fields with confidence and flagged status; a reviewer can confirm fields; users with document-create permission can add a document. | Document metadata and file storage, ingestion state, extraction results/versioning, reviewer decisions, and source provenance. |
| Lab trends | Plots one or more series of dated numeric values against a reference range, highlighting out-of-range values. | Structured observations/lab results, units, reference ranges, timestamps, and result interpretation flags. |
| Medications | Displays medication name, dose, safety flag category (`interaction` or `dosage`), note, and a “Mark reviewed” button. That button is currently presentational and does not change shared state. | Medication orders/reconciliation and medication safety review lifecycle; persist reviewer and decision. |
| Appointments | Shows upcoming and past appointments and lets authorized users schedule one with type, provider, date, and time. | Appointment create/list/update/cancel/status APIs and server-side date/time validation. |
| Discharge summary | Displays an AI draft as paragraphs with source-document citations and lets a clinician approve/sign it. Signing updates patient status to `discharge-pending` in the current demo. | Draft generation/versioning, paragraph-level provenance, explicit clinician sign-off, signature identity/time, immutable signed version, and a correctly modeled discharge workflow. |
| Audit log | Displays a patient-scoped list of who/action/when. Current timestamps are human-readable strings, and many events are generated client-side. | Server-generated, append-only, time-stamped and attributable audit trail for reads and writes, with protected access and retention. |
| Document Vault | Facility-wide list with status filters, details, metadata editing, archive/restore. Fields include filename, type, patient, date, size, status. | Searchable document catalog, file access controls, metadata CRUD, retention/archive policy, and processing status. |
| Upload | UI claims PDF, DOCX and scanned-image support up to 25 MB and selection of patient. Current form accepts a filename/type only; it does not contain a file input or transmit bytes. Simulated extraction creates placeholder fields. | Multipart upload, file validation, private object storage, asynchronous OCR/extraction/indexing, status polling/events, failure/retry, and patient association. |
| Clinical Assistant | Displays hardcoded sample messages and citations. New prompt locally appends a generic placeholder answer. There is no model/API call or patient/document scope selector. | Authenticated RAG query endpoint with access-filtered retrieval, grounded answer generation, citations, safety boundaries, conversation persistence, and feedback/telemetry controls. |
| Compare Reports | Shows fixed document pair and fixed comparison rows. There is no picker or comparison call. | Authorized document selection, comparison job/service, structured differences and citations, and comparison history if needed. |
| Settings | Theme persists in browser storage. Role selector is a demo preview. Preference toggles update component state only and are not persisted. | User/workspace preference APIs; theme can remain client-only. Production identity and role assignments must be server-controlled, not selected by the user in this screen. |
| Global top-bar search | Displays a search affordance only; no input/search interaction is implemented. | Optional global authorized search across documents/patients, if retained as a functional feature. |

Navigation is implemented as a client-side view switch, not a URL router. Patient chart tabs are overview, documents, labs, medications, appointments, discharge, and audit. The PHI toggle only masks a name and date of birth in the UI; it is not an authorization or data-redaction control.

## 3. Current persistence and demo constraints

- Patient and clinical seed data comes from `frontend/src/data/patientMock.js`; facility-wide document metadata, static assistant messages, dashboard content, and settings defaults come from `frontend/src/data/mock.js`.
- `frontend/src/context/PatientContext.jsx` holds patients, chart documents, vault documents, lab trends, medications, discharge drafts, audit entries, immunizations, vitals, and appointments in one state object persisted to `localStorage`.
- The selected demo role is also stored in browser storage. The roles in `frontend/src/data/roles.js` are frontend-only permission previews and must not be trusted by an API.
- IDs and timestamps are generated on the client or represented as strings such as `Just now`, `2 hours ago`, or locale-formatted dates. Replace these with server-generated IDs and ISO-8601 timestamps.
- Document ingestion uses a delay and randomized confidence values. Placeholder extracted values say “pending clinician review”; no OCR, parsing, validation, or embedding occurs.
- In-memory sample field names are not a finalized clinical data standard. Normalize them, define units and time zones, and validate them against clinical/operational requirements before production.

## 4. Actors and authorization model

The UI demonstrates four roles. These are a starting point for requirements, not a complete production policy:

| Demo role | Intended capabilities in current UI |
|---|---|
| Workspace admin | View/create/edit/archive patients; view/create/edit/archive documents; manage appointments and workspace settings. |
| Clinician | View patients/documents; upload documents; verify extracted fields; sign clinical workflows; manage appointments. |
| Records staff | View/create/edit patient demographics; view/create/edit document metadata; manage appointments. No clinical sign-off. |
| Read-only | View patient charts and documents only. |

The permission identifiers currently implied by the frontend are:

- `patients:view`, `patients:create`, `patients:edit`, `patients:archive`
- `documents:view`, `documents:create`, `documents:edit`, `documents:archive`
- `clinical:review`, `appointments:manage`, `settings:manage`

### Production authorization requirements

1. Authenticate every request. Obtain the actor, organization/workspace, and role from a trusted server-side identity provider or session/token validation.
2. Enforce permissions on every endpoint and every referenced object. UI hiding/disabling controls is only a convenience.
3. Enforce tenant/workspace isolation and patient/document access policy in database queries and file-download paths.
4. Define whether patient access is organization-wide or constrained by assignment, care team, ward, purpose of use, or encounter. This cannot be inferred from the demo and must be decided before implementation.
5. Add fine-grained permissions for medication review, appointment management, discharge drafting/sign-off, assistant use, comparison, export/download, and audit access as policy requires.
6. Record actor ID, role/context, organization, request correlation ID, timestamp, action, and affected resource in audit records. Do not accept `who`, `confirmedBy`, or `signedBy` from the client as authoritative identity.
7. The “preview as role” control must be disabled or restricted to an explicitly non-production test environment. It must never grant real privileges.
8. Consider field-level access/redaction for direct identifiers and sensitive fields. The current PHI hide/show control is visual only.

## 5. Proposed domain model

Use relational persistence for records and relationships, private object storage for source files, and a search/vector index for retrieval. Exact database and infrastructure choices remain open. IDs should be opaque stable identifiers (UUID/ULID), and all persisted times should be UTC ISO-8601 timestamps with explicit display-time-zone conversion.

### 5.1 Workspace and identity

**Workspace**
- `id`, `name`, `status`, `created_at`, `updated_at`
- Workspace-level preferences and retention/configuration references.

**User**
- `id`, `workspace_id`, identity-provider subject, `display_name`, `email`, `status`, `created_at`, `updated_at`
- Avoid storing credentials when an external identity provider is used.

**RoleAssignment**
- `id`, `workspace_id`, `user_id`, role or permission set, optional scope (department/ward), `created_by`, `created_at`, `revoked_at`
- Role assignment and permission policy are server-controlled.

### 5.2 Patient and care resources

**Patient** (demographic/administrative record)
- `id`, `workspace_id`, `mrn` (unique within configured scope), `given_name`, `family_name`, optional display name, `date_of_birth`, `administrative_sex` or appropriately defined sex/gender fields, `blood_type`
- Contact fields: phone, email, address
- Emergency contact should preferably be a related record with name, relationship, phone, and optional contact preference.
- Coverage fields: insurance provider, policy/member number; consider a separate coverage table for multiple policies and effective periods.
- Care assignment: attending/provider reference, department/ward, bed/location reference where applicable.
- `status`: define allowed transitions (current UI has `admitted`, `discharge-pending`, `discharged`); `archived_at`, `archived_by`, `created_at`, `updated_at`.
- Allergy/intolerance data should be a structured resource, not a comma-separated string or `None recorded` sentinel. Include substance, reaction, severity, status, source, and verification state as appropriate.
- `reason` submitted by the add-patient form currently has no persisted handling in the context; decide whether this becomes an encounter reason/note and who may author it.

**Encounter / Admission** (recommended rather than overloading Patient status)
- `id`, `patient_id`, encounter class/type, status, start/end time, reason, location/ward, attending/provider, discharge fields, created/updated metadata.
- Separating patient identity from admissions allows repeat visits and historical episodes.

**VitalObservation**
- `id`, `patient_id`, optionally `encounter_id`, code/name, numeric or coded value, unit, measured time, source, reference range where applicable, entered/verified by.
- The UI shows blood pressure, heart rate, temperature, SpO2, weight. Store normalized values rather than strings such as `118/76` or `92 bpm`; provide formatted strings at the API/UI boundary if needed.

**Immunization**
- `id`, `patient_id`, vaccine, administration date, status, source, optional lot/provider metadata.

**LabResult / Observation**
- `id`, `patient_id`, optional encounter/document/source reference, test code/name, value, numeric/coded type, unit, reference low/high, abnormal interpretation, collected/observed/reported timestamps, status, performing organization.
- Keep observations as individual time-stamped results. Trend series can be assembled by query; do not store only a precomputed chart array.

**MedicationOrder / MedicationStatement**
- `id`, `patient_id`, optional encounter, medication identifier/name, strength, dose, route, frequency, start/end, status, prescriber, source, created/updated metadata.
- Distinguish an order from a medication the patient reports taking; the demo conflates these concepts.

**MedicationSafetyReview**
- `id`, `patient_id`, related medication(s), flag type (e.g. allergy conflict, dose check, interaction), evidence/rationale, severity/priority, status (`open`, `acknowledged`, `resolved`, `dismissed` as approved by workflow), generated time, reviewer, review time, resolution.
- Safety recommendations must be clinically validated and must not be represented as definitive solely because a model generated them.

**Appointment**
- `id`, `workspace_id`, `patient_id`, encounter/provider references where applicable, type, provider, start/end timestamps, time zone, status (`upcoming`, `completed`, plus cancelled/no-show as needed), location, created/updated metadata.
- Current form collects type, free-text provider, date, and time; production should validate against scheduling rules and use a timezone-aware timestamp.

### 5.3 Documents and AI processing

**Document**
- `id`, `workspace_id`, `patient_id`, optional `encounter_id`, original filename, content type, byte size, cryptographic checksum, private object-storage key, document type, document/service date, upload time, uploader, source, status, archive/retention fields.
- Keep `processing_status` separate from document lifecycle/archive status. Suggested processing statuses: `uploaded`, `queued`, `extracting`, `needs_review`, `processed`, `failed`; define retry and terminal-state rules.
- Keep a secure access-controlled download mechanism; never expose permanent public object-store URLs.

**DocumentProcessingJob / ProcessingEvent**
- `id`, `document_id`, pipeline version, current stage, status, attempt count, started/finished timestamps, error code (safe for client), retryability, worker/job correlation ID.
- Stages implied by the UI/project notes: upload, text extraction, OCR, clean/normalize, classify, extract fields, PHI scan, validate, embed, index. Persist stage events for operational visibility and troubleshooting.
- Processing should be asynchronous and idempotent. Enforce size, extension, MIME/content signature, malware scanning, and safe parsing controls. The UI advertises PDF, DOCX, and scanned images, max 25 MB; confirm final supported formats and limits.

**ExtractedField**
- `id`, `document_id`, schema/key, label, value (typed JSON or normalized resource link), confidence score in `[0,1]`, flagged/review-required indicator, page and bounding/source locator, extraction model/version, status, created time.
- A field confirmation must be a separate immutable review event/decision with reviewer ID, time, decision, optional correction, and rationale. Do not merely clear a boolean without history.
- Document status should be derived from all required processing/review states under clearly documented rules. In the demo, `needs-review` and `processed` are document statuses while individual fields also have flags.

**DocumentSourceReference**
- `id`, document ID, page number, text span/locator, optional bounding box, quoted/source text reference.
- Citation references returned from AI must resolve to authorized document pages/snippets; UI examples use `filename · Page N`.

**DischargeSummaryDraft**
- `id`, patient/encounter ID, version, status (`draft`, `pending_review`, `signed`, `superseded`), generated timestamp, generator/model/prompt version, authoring actor/system, content, source document IDs.
- **DraftParagraph / Citation**: paragraph order, text, one or more document/page/snippet references, generated provenance.
- **Signature event**: signer user ID, signed timestamp, version/hash, optional attestation; immutable once signed. Corrections should produce a new version/addendum according to policy.
- The demo's `signDischarge` currently sets status to `signed` and sets patient status to `discharge-pending`, which is semantically questionable. Define an explicit discharge/encounter transition model and correct UI behavior before implementing this transition.

### 5.4 Work queue and audit

**WorkItem** (can be persisted or generated from source records with a stable query projection)
- `id`, workspace/patient/encounter references, kind/category (`safety`, `documents`, `discharge`, `labs`), title, description, priority, source resource, status, assigned user/team, due time, created/updated/resolved metadata.
- The current work queue derives items from medication flags, flagged extracted fields, discharge-pending status, and the latest lab value outside the reference range. Server-side rules should be versioned and auditable. Recompute or update work items when their source/review state changes.

**AuditEvent**
- `id`, workspace, actor user/system identity, action, resource type/id, event timestamp, request/correlation ID, outcome, relevant metadata, optional before/after diff subject to privacy rules.
- Append-only to application roles. Include sensitive reads (patient/document access) if policy requires. Protect audit access, integrity, retention, and export.
- Use real event timestamps, not relative strings. Do not log unnecessary PHI, raw document text, access tokens, or secrets.

### 5.5 Assistant, comparison, and preferences

**Conversation / Message**
- Conversation: ID, workspace, owner, optional patient/encounter scope, created/updated time.
- Message: ID, conversation, role, content, timestamp, processing status, model/prompt version, safety metadata.
- **MessageCitation**: message ID, document ID, page/snippet/source locator, relevance metadata, and retrieval reference.
- Apply the same patient/document access checks during retrieval as for direct reads. Store only information needed for the feature and according to retention policy.

**DocumentComparison**
- ID, selected document IDs, requesting user, status, created/completed time, structured field differences, source citations, algorithm/model version, error state.
- The frontend comparison rows are static and currently do not establish which fields must be compared. Define supported document types, comparison schema, and clinical review disclaimer.

**WorkspacePreference**
- Workspace-scoped settings for email notifications, auto-OCR, hybrid search, clinician sign-off requirements, and model-evaluation data sharing. Each preference has explicit default, permissions, audit, and effective value.
- Theme can remain local user preference (`light`, `dark`, `system`) unless cross-device sync is desired.
- Model-evaluation sharing should default conservatively and require explicit governance, privacy review, and consent/policy decisions; do not treat the current toggle as sufficient consent.

## 6. Suggested REST API surface

Prefix all endpoints with `/api/v1`. Use JSON for metadata and `multipart/form-data` or a secure upload-session flow for files. Exact endpoint conventions can change; the listed behaviors are the contract needs. All list endpoints should support bounded pagination and deterministic ordering. Use a consistent error envelope and request/correlation IDs.

### Authentication and session

Authentication is not implemented in the UI. Integrate the organization's selected identity provider. Example server API needs, if the chosen auth model requires them:

- `GET /api/v1/me` — current user, workspace membership, effective roles/permissions.
- Login, refresh, logout, password, MFA, and SSO endpoints should be provided by the selected identity system rather than invented without a product decision.

### Patients and related records

- `GET /api/v1/patients?status=&archived=&q=&ward=&cursor=&limit=` — authorized roster/search.
- `POST /api/v1/patients` — create patient, optional initial encounter, allergies and reason handled according to finalized model.
- `GET /api/v1/patients/{patient_id}` — authorized demographics/chart summary.
- `PATCH /api/v1/patients/{patient_id}` — partial demographic/admin update with optimistic concurrency.
- `POST /api/v1/patients/{patient_id}/archive` and `/restore` — soft archive/restore; never hard-delete through the UI workflow.
- `GET /api/v1/patients/{patient_id}/overview` — optional aggregated overview (latest vitals, care assignment, immunization summary).
- `GET /api/v1/patients/{patient_id}/encounters` and `POST /api/v1/patients/{patient_id}/encounters` — recommended if encounters are included in first release.
- `GET /api/v1/patients/{patient_id}/allergies`, `GET /api/v1/patients/{patient_id}/vitals`, `GET /api/v1/patients/{patient_id}/immunizations`.

### Documents and ingestion

- `GET /api/v1/documents?patient_id=&status=&type=&archived=&q=&cursor=&limit=` — vault list and search.
- `POST /api/v1/documents` — create an upload session or multipart upload associated with a patient (and optionally encounter); validate permissions and file.
- `GET /api/v1/documents/{document_id}` — metadata, processing state, extracted fields, and applicable review state.
- `GET /api/v1/patients/{patient_id}/documents` — patient-scoped documents.
- `GET /api/v1/documents/{document_id}/content` — short-lived authorized download/view URL or streaming response.
- `PATCH /api/v1/documents/{document_id}` — editable metadata such as name/type, with audit and version checks.
- `POST /api/v1/documents/{document_id}/archive` and `/restore` — soft archive/restore under retention rules.
- `GET /api/v1/documents/{document_id}/processing` — current job status/stages; optionally use SSE/WebSocket notifications for live progress.
- `POST /api/v1/documents/{document_id}/retry` — permitted retry of retryable failures.
- `GET /api/v1/documents/{document_id}/fields` — extracted fields and source locators.
- `POST /api/v1/documents/{document_id}/fields/{field_id}/review` — confirm, correct, or reject with authenticated reviewer and optional rationale. Keep review history.

Recommended upload lifecycle:
1. Client submits patient/encounter and file metadata; server checks permission and constraints.
2. File is stored in private object storage and a document/job record is transactionally created.
3. Worker processes extraction/OCR and records stage events; failures have safe user-facing state and detailed restricted operational logs.
4. Extracted values, confidence, source locations, clinical flags, and indexing metadata are saved with model/pipeline version.
5. Review-required fields create or update work items; no clinical field becomes verified solely from model confidence.
6. Authorized staff review/confirm/correct; the review decision is audited and downstream records/indexes are updated as policy allows.

### Labs, medications, and work queue

- `GET /api/v1/patients/{patient_id}/lab-results?test=&from=&to=` — observations suitable for trend charts.
- `POST /api/v1/patients/{patient_id}/lab-results` — if manual entry is in scope; document extraction may also create linked results after validation/review.
- `GET /api/v1/patients/{patient_id}/medications?status=` — medication list/orders/statements.
- `POST /api/v1/patients/{patient_id}/medication-reviews/{review_id}/resolve` — backend action for the currently nonfunctional “Mark reviewed” control; require reviewer, outcome, and optional note.
- `GET /api/v1/work-items?category=&priority=&status=&assigned_to=&patient_id=&q=&cursor=&limit=` — prioritized queue.
- `GET /api/v1/work-items/{work_item_id}` — work item and authorized source context.
- `PATCH /api/v1/work-items/{work_item_id}` — assignment/status/due date if supported. Closing a work item must not silently alter its clinical source record.

### Appointments

- `GET /api/v1/patients/{patient_id}/appointments?status=&from=&to=`
- `POST /api/v1/patients/{patient_id}/appointments` — schedule with ISO timestamp/time zone and validation.
- `PATCH /api/v1/appointments/{appointment_id}` — reschedule or update.
- `POST /api/v1/appointments/{appointment_id}/cancel` and `/complete` as appropriate.

### Discharge workflow

- `GET /api/v1/patients/{patient_id}/discharge-summary` — current draft/signed version and citations.
- `POST /api/v1/patients/{patient_id}/discharge-summary/drafts` — request generation; return job/draft status.
- `PATCH /api/v1/discharge-summaries/{draft_id}` — clinician edits before signing, with version check and provenance behavior defined.
- `POST /api/v1/discharge-summaries/{draft_id}/sign` — server verifies permission, required review, encounter state, and version; records signer/time/attestation and advances the explicitly defined discharge workflow.
- `GET /api/v1/patients/{patient_id}/discharge-summary/versions` — version history and signed record access.

### Clinical Assistant (RAG)

- `POST /api/v1/assistant/conversations` — create a conversation with optional patient/encounter scope.
- `GET /api/v1/assistant/conversations?cursor=&limit=` — list caller's authorized conversations.
- `GET /api/v1/assistant/conversations/{conversation_id}/messages?cursor=&limit=`
- `POST /api/v1/assistant/conversations/{conversation_id}/messages` — submit a question; asynchronous status or streamed response; return answer and citations.
- `POST /api/v1/assistant/messages/{message_id}/feedback` — optional helpfulness/correction feedback.

RAG requirements:
- Filter retrieval by workspace, user permissions, patient/encounter scope, document lifecycle, and current authorization at query time.
- Cite every material clinical statement with resolvable document/page/snippet references; return “not found in available records” rather than inventing facts.
- Preserve source links and provenance; do not treat generated text as a verified clinical record.
- Define retention, prompt-injection handling, PHI handling, model/vendor data-use limits, safety messaging, rate limits, and model/prompt version logging.
- Avoid broad cross-patient retrieval by default. Require explicit scope and policy for cross-patient aggregate questions.

### Compare, settings, and audit

- `POST /api/v1/document-comparisons` — document IDs and comparison mode; returns job/result.
- `GET /api/v1/document-comparisons/{comparison_id}` — structured comparison and citations.
- `GET /api/v1/workspace/settings` and `PATCH /api/v1/workspace/settings` — authenticated settings access, admin-only mutations, audit changes.
- `GET /api/v1/audit-events?patient_id=&resource_type=&actor_id=&action=&from=&to=&cursor=&limit=` — strict authorization and audit access rules.
- `GET /api/v1/dashboard/summary` — aggregate cards and recent review items/activity; alternatively compose from existing APIs if simplicity is preferred.

## 7. API contract and data handling conventions

- Use ISO-8601 UTC timestamps (e.g. `2026-10-02T09:30:00Z`) in API responses. Keep dates such as DOB as date-only (`YYYY-MM-DD`). Preserve the relevant local time zone for appointments.
- Use numeric values with explicit units for observations and confidence. Define whether confidence is calibrated and how it is displayed; it is not a clinical truth score.
- Standardize enums for patient/encounter, document, processing, appointment, work-item, field-review, medication-review, and draft lifecycle states.
- Use server-assigned immutable IDs; MRN uniqueness should be scoped and protected from accidental disclosure.
- Use `201 Created` for synchronous creates, `202 Accepted` for asynchronous jobs, `400/422` for invalid input, `401` for unauthenticated, `403` or policy-safe `404` for forbidden resources, `404` for missing resources, `409` for state/version conflicts, and `429` for rate limits.
- Use optimistic concurrency (`ETag`/`If-Match` or explicit version) for patient/document/draft edits and sign-off to avoid overwriting concurrent changes.
- Paginate large lists and bound user-controlled query/filter sizes. Return stable sort order.
- Define a consistent error shape, for example `{ "error": { "code": "VALIDATION_ERROR", "message": "...", "request_id": "...", "details": [] } }`; never return stack traces, secrets, raw model prompts, or unrestricted clinical data in error details.
- Use idempotency keys for uploads, scheduling, draft/signing actions, and other operations where retries could duplicate work.
- Validate every resource relationship server-side (patient belongs to workspace, document belongs to patient, actor may access both).

## 8. Security, privacy, and clinical safety requirements

1. **Transport and storage:** TLS in transit; encryption at rest for databases, object storage, backups, and queues as appropriate; managed keys and rotation.
2. **Access control:** Server-side authentication/authorization, least privilege, tenant isolation, short-lived file access, session controls, and protection against IDOR/BOLA attacks.
3. **PHI minimization:** Collect and expose only necessary fields. Masking in the UI is not a substitute for API access control. Avoid PHI in URLs, analytics, telemetry, exception traces, and model-provider logs.
4. **File safety:** Enforce size/type/signature limits, malware scanning, safe parser isolation, decompression/resource limits, private storage, retention/deletion policy, and safe download headers.
5. **Auditability:** Append-only protected audit events for sensitive access and mutations, with trustworthy server time, actor attribution, retention/export policies, and monitoring for anomalous access.
6. **AI governance:** Record model/pipeline versions, sources, review decisions, and failure states. Require clinician review for clinical decisions and discharge sign-off. Provide confidence/provenance without implying certainty. Do not silently overwrite source clinical records.
7. **RAG safety:** Authorization-aware retrieval, citation verification, prompt-injection defenses, input/output handling policy, no unsupported claims, and a clear distinction between assistant output and chart data.
8. **Backups and recovery:** Define RPO/RTO, encrypted backups, restore tests, job replay/retry procedures, and recovery behavior for database/object-store inconsistency.
9. **Operational controls:** Rate limits, abuse monitoring, dependency patching, secrets management, environment separation, security review, and incident response.
10. **Compliance:** Determine applicable jurisdiction, health-data regulations, organizational contracts, retention/consent rules, and required certifications with qualified counsel/security professionals. Do not label the application compliant based on these recommendations alone.

## 9. Backend architecture options

A modular monolith is a practical first implementation unless scale, team structure, or operational requirements justify service separation:

- **API application:** Authentication integration, request validation, authorization, domain services, and versioned REST endpoints.
- **Relational database:** Patients, encounters, resource metadata, document records, review events, appointments, preferences, audit references, and workflow state.
- **Private object storage:** Original documents, derived text, page images, and export artifacts with per-request authorization.
- **Job queue and workers:** OCR, extraction, validation, PHI scan, embeddings/indexing, assistant generation, and comparison/discharge drafting.
- **Search/index layer:** Keyword and vector retrieval; index only authorized document content and support deletion/archive propagation. The authoritative record remains the relational store/object store.
- **External integrations:** Identity provider, OCR/parser, LLM/embedding provider, email/notification, and possibly terminology/medication services. Use adapters, timeouts, retries, vendor data-use review, and fallback behavior.
- **Observability:** Structured logs with PHI minimization, metrics for processing latency/failure, tracing with request/job IDs, queue monitoring, and operational alerts.

The existing frontend README mentions a FastAPI backend as an expected direction, but the backend directory is currently empty and no framework or language has been implemented. FastAPI is therefore an option, not an existing backend constraint.

## 10. Frontend integration plan

1. Replace `PatientContext` seed/localStorage reads and mutations with an API client and server queries/mutations. Do not store the full clinical record in browser storage.
2. Keep a small client cache for usability only; handle loading, empty, stale, offline, validation, permission, and server-error states.
3. Introduce a shared API client that attaches authentication, request IDs, handles refresh/error mapping, and avoids logging request/response PHI.
4. Use server-side filtering, pagination, dashboard aggregates, and work-item generation instead of duplicating clinical rules in pages.
5. Replace `AddDocumentForm` filename simulation with actual file selection, multipart upload, processing status subscription/polling, and retry/error UI. The current “Drag files in, or browse” region is not wired to a file input.
6. Replace client-provided `confirmedBy`/`signedBy` with authenticated server actor identity. Refresh/revalidate data after confirmation/sign-off and display the server audit time.
7. Implement “Mark reviewed” to resolve a real medication safety review, or remove/disable the control until a backend workflow exists.
8. Implement real document selection/comparison and assistant interactions, with citations linked to authorized source documents.
9. Decide whether theme remains local-only. Persist workspace settings and role assignment only through server-authorized APIs.
10. Add URL routing for durable deep links to patient charts/tabs and resource IDs if required; current navigation loses URL-level state.

## 11. Testing and acceptance criteria

### API/domain tests
- Patient CRUD, status transitions, duplicate MRN handling, soft archive/restore, and workspace isolation.
- Role/permission matrix for every read/write endpoint, including attempts to access another workspace's patient, file, audit entry, or conversation.
- File validation, size limits, MIME/signature mismatch, parser failures, malware rejection, duplicate/idempotent uploads, retries, and archive behavior.
- Ingestion pipeline state transitions, field confidence bounds, field-to-source provenance, and field-review history.
- Appointment date/time validation, concurrency, cancellation, and status transitions.
- Medication review resolution and correct work-item updates.
- Discharge draft version conflicts, authorized signing, immutable signature event, and valid encounter transition.
- Assistant access-scoped retrieval, citation validity, empty retrieval behavior, prompt-injection cases, and no cross-patient leakage.
- Audit completeness for sensitive reads and all protected mutations; ensure logs do not leak PHI/secrets.

### End-to-end acceptance
- Creating a patient returns a server ID and chart records can be fetched after a fresh login/browser session.
- Uploading a real supported file stores it privately and exposes processing progress and a retrievable failure/success state.
- Extracted fields show page/source citations, confidence, and a durable clinician review decision.
- Dashboard/work queue values agree with authoritative server data and update after review or workflow changes.
- Users cannot access or mutate data beyond their role and authorized patient scope by changing IDs or calling endpoints directly.
- Assistant responses include working source citations and never retrieve documents the user cannot access.
- Signed discharge summaries preserve the signed version, signer, timestamp, sources, and expected encounter status.

## 12. Suggested delivery phases

### Phase 0 — decisions and threat model
- Confirm deployment jurisdiction, data controller/processor roles, identity provider, tenant model, patient-access rules, retention, supported document types/size, clinical responsibility, and external AI/vendor constraints.
- Agree on encounter and discharge lifecycle semantics, medication/lab source-of-truth strategy, and whether this product is an EHR integration or standalone record store.

### Phase 1 — secure application foundation
- Establish backend project, migrations, authentication, workspace isolation, server-side RBAC, API conventions, error handling, audit foundation, configuration/secrets, and CI tests.
- Implement patient, encounter (if adopted), roster, demographics, archive, overview, and audit APIs.

### Phase 2 — document management and ingestion
- Implement upload/storage/catalog/detail/download, asynchronous processing jobs, OCR/text extraction, field extraction/provenance, review/confirmation, and processing status.
- Integrate dashboard document counts and patient document review.

### Phase 3 — operational clinical data
- Implement observations/labs, medication records and review lifecycle, appointments, work items, dashboard aggregates, and explicit discharge workflow/signature/versioning.

### Phase 4 — AI features
- Implement authorization-aware search/indexing, assistant conversations with validated citations, document comparison, and discharge draft generation behind appropriate feature flags and clinical governance.

### Phase 5 — production readiness
- Load/security testing, backup/restore and incident exercises, monitoring/alerts, accessibility, retention/export workflows, vendor/privacy review, penetration testing, and operational runbooks.

## 13. Open product/design decisions

- What backend framework, database, object storage, queue, and deployment target are preferred? Current backend folder is empty; FastAPI is mentioned only in the frontend README.
- Is this a standalone chart, a prototype, or an integration layer over an existing EHR? Which interoperability standards/terminologies are required?
- What defines workspace/tenant boundaries, MRN uniqueness, user provisioning, care-team membership, and permitted cross-patient access?
- Which exact patient statuses and encounter/discharge transitions are valid? In particular, should signing a discharge summary move an encounter toward discharged rather than mark it `discharge-pending`?
- Which document types and formats are truly supported, and what are the final upload size/retention limits?
- Which extracted fields map to canonical resources (allergy, lab, medication, diagnosis, appointment) versus remaining document-only annotations?
- Can clinicians edit extracted values? What requires a second reviewer, reason, or addendum?
- What is the clinical source of truth for medication interaction/dose alerts and lab reference ranges? Which licensed/validated services or clinical rules are approved?
- Does the assistant operate on one patient at a time, selected documents, or broader authorized workspace scope? How are citations displayed/opened?
- Are assistant conversations retained, exportable, or deleted on a schedule?
- Should document compare support arbitrary documents or only templates/types with common fields?
- Which workspace preferences must persist, who may manage them, and what does model-evaluation sharing mean operationally?
- What audit events, retention period, exports, and access monitoring are required?
- Which jurisdictions and regulatory obligations apply? Complete a formal privacy/security and clinical safety review before handling real patient information.

## 14. Frontend source map used for this assessment

- Application view selection and patient-chart navigation: `frontend/src/App.jsx`
- Shared client state, local persistence, demo mutations, role checks: `frontend/src/context/PatientContext.jsx`
- Main navigation, titles, demo vault documents, sample assistant/compare/settings data: `frontend/src/data/mock.js`
- Patient, document, lab, medication, discharge, audit, vitals, immunization, appointment seed shapes: `frontend/src/data/patientMock.js`
- Demo permission matrix: `frontend/src/data/roles.js`
- Patient forms: `frontend/src/components/AddPatientForm.jsx`
- Simulated document extraction: `frontend/src/components/AddDocumentForm.jsx`
- Main feature pages: `frontend/src/pages/Dashboard.jsx`, `frontend/src/pages/WorkQueue.jsx`, `frontend/src/pages/Patients.jsx`, `frontend/src/pages/PatientDetail.jsx`, `frontend/src/pages/Documents.jsx`, `frontend/src/pages/Upload.jsx`, `frontend/src/pages/Ask.jsx`, `frontend/src/pages/Compare.jsx`, `frontend/src/pages/Settings.jsx`
- Patient chart tabs: `frontend/src/pages/patient/Overview.jsx`, `frontend/src/pages/patient/DocumentReview.jsx`, `frontend/src/pages/patient/LabTrends.jsx`, `frontend/src/pages/patient/Medications.jsx`, `frontend/src/pages/patient/Appointments.jsx`, `frontend/src/pages/patient/DischargeSummary.jsx`, `frontend/src/pages/patient/AuditLog.jsx`
- Frontend setup and backend integration notes: `frontend/README.md`

---

This brief describes backend needs implied by the current prototype. Validate it with the product owner, clinicians, privacy/security stakeholders, and the chosen integration partners before implementation.
