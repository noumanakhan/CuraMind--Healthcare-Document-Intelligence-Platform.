# CuraMind — Next Phase Build Prompt (Security Fix + Clinical Data Foundation)

Paste this into your IDE's AI assistant as the task description. Work through the steps **in
order** — Step 0 is a hard blocker and must be verified complete before anything else begins.

This prompt is written against the **actual existing structure** in `PROJECT_HANDOFF.md`:
`backend/app/api`, `controllers`, `services`, `models`, `schemas`, `core`, `db`, with the
existing `Workspace`, `User`, `RefreshSession`, `AuditEvent` models and the four existing roles
(`admin`, `clinician`, `records`, `viewer`). Do not introduce a parallel structure or rename
existing modules.

---


## Step 1 — Add Alembic before adding any new tables

Every subsequent step adds new tables. Retrofitting migrations after the fact is painful — set
this up now, against the current schema, before Step 2.

1. Add `alembic` to backend dependencies if not already present.
2. Initialize Alembic in `backend/`, configured to read the DB URL from the existing
   `core/config.py` settings rather than a hardcoded URL in `alembic.ini`.
3. Generate and apply an initial migration capturing the current schema
   (`Workspace`, `User`, `RefreshSession`, `AuditEvent`) exactly as it exists today — this
   migration should be a no-op in effect (the tables already exist via
   `Base.metadata.create_all()`), it just establishes the migration baseline going forward.
4. From this point on, every new model in this prompt gets its own migration — do not fall back
   to `create_all()` for new tables.
5. Confirm `alembic upgrade head` runs cleanly on a fresh empty SQLite file.

---

## Step 2 — Design clinical models as workspace-scoped from the start

Every clinical table below **must** include a `workspace_id` foreign key and every query **must**
filter by the authenticated user's workspace. This is the most important architectural rule in
this phase — a workspace-isolation bug here is a patient-data leak between hospitals/tenants, not
a cosmetic bug. Add a workspace-isolation test for every new table before considering it done
(see Step 7).

Build these as SQLAlchemy models under `models/`, one file per entity as the existing structure
does, with UUID primary keys:

### Patient
```
id, workspace_id (FK), mrn (unique within workspace, server-generated),
name, dob, sex, blood_type, phone, email, address, emergency_contact,
insurance_provider, policy_number, attending_physician_id (FK -> User, nullable),
ward, status (enum: admitted / discharge_pending / discharged),
is_deleted (bool, default false — soft delete only, never hard-delete a patient),
created_by_id (FK -> User), created_at, updated_at
```

### Allergy
```
id, patient_id (FK), allergen, noted_by_id (FK -> User), noted_at
```
Structured table, not a comma-joined string — allergies need to be queried programmatically
against medications later.

### Document + ExtractedField
```
Document: id, patient_id (FK), workspace_id (FK), name, type (enum: lab_report /
  clinical_note / intake_form / referral_letter / insurance_claim / prescription /
  discharge_summary), status (enum: processing / needs_review / processed),
  uploaded_by_id (FK -> User), uploaded_at, source_file_url (nullable),
  is_deleted (bool, default false)

ExtractedField: id, document_id (FK), label, value, confidence (float), flagged (bool),
  confirmed_by_id (FK -> User, nullable), confirmed_at (nullable)
```

### Medication
```
id, patient_id (FK), workspace_id (FK), name, dose, flag (enum: none / interaction /
  dosage, nullable), flag_note (text, nullable), reviewed_by_id (FK -> User, nullable),
  reviewed_at (nullable), prescribed_at
```

### LabTest + LabResultPoint
```
LabTest: id, patient_id (FK), workspace_id (FK), test_name, unit, reference_low,
  reference_high

LabResultPoint: id, lab_test_id (FK), value (float), recorded_at
```

### Appointment
```
id, patient_id (FK), workspace_id (FK), type, with_provider_id (FK -> User, nullable),
with_provider_name, date, time, status (enum: upcoming / completed / cancelled),
scheduled_by_id (FK -> User), scheduled_at
```

### DischargeDraft + DischargeParagraph
```
DischargeDraft: id, patient_id (FK, one-to-one), workspace_id (FK),
  status (enum: draft / signed), generated_at, signed_by_id (FK -> User, nullable),
  signed_at (nullable)

DischargeParagraph: id, discharge_draft_id (FK), text, source_citation, order_index
```

### Immunization
```
id, patient_id (FK), workspace_id (FK), vaccine_name, administered_date,
recorded_by_id (FK -> User)
```

### Vitals
```
id, patient_id (FK), workspace_id (FK), bp, hr, temp, spo2, weight, recorded_at,
recorded_by_id (FK -> User)
```
Store every entry, not just latest — needed for trending later even though only "latest" is
shown today.

Write an Alembic migration for each table (can be grouped into one migration per logical group —
e.g. Patient+Allergy together, Document+ExtractedField together — your judgment on grouping, but
every table must exist in a migration, not just `create_all()`).

---

## Step 3 — Schemas, services, controllers (match existing layering exactly)

For each entity above, following the **same three-layer pattern already used for auth/users**:

- **`schemas/`** — Pydantic request/response models. Split `Create`, `Update`, and `Out` variants
  where the shape differs (e.g. `PatientCreate` doesn't include `id`/`mrn`, `PatientOut` does).
- **`services/`** — business logic: creating a patient (generates the MRN, enforces workspace
  scoping, writes the audit event), confirming a field (sets `confirmed_by_id`/`confirmed_at`,
  writes audit event), signing a discharge (enforces `clinician` or `admin` role, sets
  `signed_by_id`/`signed_at`, writes audit event). Controllers should stay thin and call services,
  not contain business logic directly — match the existing `services/` pattern used for
  auth-audit and default-workspace operations.
- **`controllers/`** — route definitions, one file per resource, registered in
  `api/v1/router.py` alongside the existing auth/users routes. All routes live under `/api/v1`.

### Role mapping for the four existing roles

| Action | Allowed roles |
|---|---|
| Create patient | `records`, `admin` |
| View patient list (workspace-scoped) | `clinician`, `records`, `viewer`, `admin` |
| View full clinical chart (notes, discharge content) | `clinician`, `admin` |
| Add/upload a clinical document | `clinician`, `records`, `admin` |
| Confirm an extracted field | `clinician`, `admin` |
| Sign a discharge summary | `clinician`, `admin` |
| Schedule an appointment | `records`, `admin` |
| Record vitals / immunizations | `clinician`, `admin` |
| Mark a medication reviewed | `clinician`, `admin` |
| View audit log for a patient | `admin` (reuse the existing `GET /admin/auth-audit` pattern, extended to clinical audit events) |

Use the existing `api/dependencies.py` permission-enforcement pattern (`core/rbac.py`) to gate
these — do not write a second, parallel authorization mechanism. If `core/rbac.py`'s policy
structure doesn't yet support resource-level permissions (e.g. "confirm field" as a distinct
permission from "view patient"), extend it there, in one place, rather than hand-rolling checks
in each controller.

### Endpoints to add (all under `/api/v1`)

```
GET    /patients                              (paginated, ?status=, workspace-scoped)
POST   /patients
GET    /patients/{id}
PATCH  /patients/{id}

GET    /patients/{id}/documents
POST   /patients/{id}/documents
PATCH  /documents/{doc_id}/fields/{field_id}/confirm

GET    /patients/{id}/medications
PATCH  /medications/{id}/review

GET    /patients/{id}/labs
POST   /patients/{id}/labs/{test_id}/points

GET    /patients/{id}/appointments
POST   /patients/{id}/appointments

GET    /patients/{id}/discharge
POST   /patients/{id}/discharge/sign

GET    /patients/{id}/immunizations
GET    /patients/{id}/vitals/latest
POST   /patients/{id}/vitals

GET    /patients/{id}/audit                   (admin only)
GET    /dashboard/stats                        (workspace-scoped live counts)
```

---

## Step 4 — Audit events for every clinical mutation

The existing `AuditEvent` model and audit-write service already handle auth events — extend the
**same** service/table for clinical actions rather than building a second audit system. Every
`POST`/`PATCH` above that mutates data must write an audit event recording: `user_id`,
`workspace_id`, `patient_id` (when applicable), a human-readable action description, timestamp.

---

## Step 5 — Reconcile the frontend role-permission duplication

`frontend/src/data/roles.js` currently duplicates role/permission logic for UI rendering, which
the handoff notes flags as a risk. Fix this:

1. On login/session restore, have the frontend call `GET /auth/permissions` (already implemented)
   and store the **returned** permission set as the single source of truth for what UI elements
   to show/hide.
2. Remove or significantly shrink `frontend/src/data/roles.js` so it no longer independently
   defines what each role can do — it should, at most, map a permission string to a UI label, not
   decide access.
3. Every UI gate (e.g. "only show Sign Discharge button if clinician") should check the
   permissions returned from the backend, not a locally duplicated role table. Make clear in code
   comments that this is a UX convenience only — the backend remains the actual authorization
   boundary regardless of what the UI shows or hides.

---

## Step 6 — Connect frontend clinical flows to the real API (replace `PatientContext.jsx` internals)

Only after Steps 0–5 pass their tests:

1. Keep every function signature in `PatientContext.jsx` the same (`addPatient`, `addDocument`,
   `confirmField`, `signDischarge`, `scheduleAppointment`) — replace only the function **bodies**
   with authenticated `fetch`/axios calls to the new endpoints, using the access token from
   `AuthContext.jsx`.
2. Add loading, error, and empty states to each page that currently assumes mock data is always
   present — `Patients.jsx`, `PatientDetail.jsx`, and each tab component.
3. Add pagination/search to the patient roster page, matching the backend's `?skip=&limit=`
   support.
4. Keep any remaining demo-only content (if some screens stay mock for now) clearly labeled in
   the UI as demo data, and ensure it cannot be confused with real API-backed records — do not
   silently mix mock and real data in the same list.

---

## Step 7 — Tests required before this phase is considered done

Add to `backend/tests/`:

- Workspace isolation: a user in Workspace A cannot retrieve, list, or mutate a patient belonging
  to Workspace B, for every new endpoint (not just patients — documents, labs, etc. too)
- Role denial: a `viewer` cannot create a patient, confirm a field, or sign a discharge (403 for
  each)
- A `records` user cannot view clinical note content or sign a discharge (403)
- A `clinician` can confirm a field and sign a discharge
- Soft-delete: a deleted patient no longer appears in `GET /patients` but the row still exists in
  the DB
- Audit events are written for: patient creation, field confirmation, discharge signing,
  appointment scheduling
- Idempotency: confirming an already-confirmed field, or signing an already-signed discharge,
  returns `409`, not a silent success

Run the full suite plus `compileall` and the frontend production build at the end of this phase,
exactly as done for the Step 0 verification, and report the actual results (not "should pass").

---

## Step 8 — Update `PROJECT_HANDOFF.md`

At the end of this phase, update the handoff document's "Implemented functionality," "API
endpoints," "Known technical boundaries," and "Latest verification" sections to reflect what was
actually built and tested — keep it as accurate as it currently is. Do not mark anything as done
that isn't covered by a passing test.

---

## Explicitly out of scope for this phase

Do not start on these yet — they come after this phase, per the existing roadmap:

- File storage for real uploaded documents (Phase 3)
- OCR/extraction, vector indexing, RAG assistant (Phase 4)
- MFA, email verification, invitations, password reset (Phase 5)
- PostgreSQL migration, HTTPS/secure cookies, rate limiting, monitoring (Phase 5)
- Any claim of HIPAA or regulatory compliance

---

## Final instruction to the IDE

> Work through Steps 1–8 above in order. Do not skip Step 0 or report it complete without
> verifying all five sub-steps. Preserve the existing package structure
> (`backend/app/api`, `controllers`, `services`, `models`, `schemas`, `core`, `db`) and existing
> API routes. Use the existing `Workspace`/`AuditEvent`/RBAC mechanisms rather than building
> parallel ones. Do not use real patient data at any point. After each step, run the backend test
> suite and `compileall`, and report actual pass/fail results before moving to the next step. Stop
> and ask before starting Step 6 (frontend wiring) if any backend test from Steps 0–5 is failing.
