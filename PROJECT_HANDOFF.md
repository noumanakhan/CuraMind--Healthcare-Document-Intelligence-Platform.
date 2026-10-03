# CuraMind Project Handoff

## Overview
CuraMind is a clinical document intelligence workspace with multi-role access control, secure authentication, and workspace-scoped clinical data records.

## Architecture & Layering
The backend is structured under `backend/app/`:
- **`core/`**: Settings (`config.py`), security hashing/JWT (`security.py`), and RBAC policy (`rbac.py`).
- **`db/`**: SQLAlchemy session factory, declarative base, and Alembic database migrations (`backend/alembic/`).
- **`models/`**: Workspace-scoped entities with UUID primary keys:
  - `Workspace`, `User`, `RefreshSession`, `AuditEvent`
  - `Patient`, `Allergy`
  - `Document`, `ExtractedField`
  - `Medication`
  - `LabTest`, `LabResultPoint`
  - `Appointment`
  - `DischargeDraft`, `DischargeParagraph`
  - `Immunization`, `Vitals`
- **`schemas/`**: Pydantic v2 validation contracts for auth, user administration, and clinical records.
- **`services/`**: Business logic, workspace isolation enforcement, and audit event emission:
  - `workspaces.py`, `audit.py`, `clinical.py`
- **`controllers/`**: Versioned REST endpoints under `/api/v1`:
  - `auth.py`, `users.py`, `clinical.py`

## Role-Based Access Control (RBAC)
Four primary roles enforced server-side:
- **`admin`**: Full workspace administration, user & role management, clinical actions, and audit logs.
- **`clinician`**: Clinical reviews, chart viewing, document uploads, extracted field confirmations, discharge signing, medication reviews, and vitals recording.
- **`records`**: Patient registration & demographic editing, document uploads, and appointment scheduling.
- **`viewer`**: Read-only demographic and document viewing.

## Implemented API Endpoints (`/api/v1`)
- **Authentication**:
  - `POST /auth/register`
  - `POST /auth/login`
  - `POST /auth/refresh`
  - `POST /auth/logout`
  - `GET  /auth/me`
  - `GET  /auth/permissions`
- **User Administration**:
  - `GET   /users`
  - `PATCH /users/{id}/role`
  - `PATCH /users/{id}/status`
- **Clinical & Workspace Operations**:
  - `GET    /patients` (paginated, workspace-scoped, status filter, search)
  - `POST   /patients`
  - `GET    /patients/{id}`
  - `PATCH  /patients/{id}`
  - `GET    /patients/{id}/documents`
  - `POST   /patients/{id}/documents`
  - `PATCH  /documents/{doc_id}/fields/{field_id}/confirm`
  - `GET    /patients/{id}/medications`
  - `PATCH  /medications/{id}/review`
  - `GET    /patients/{id}/labs`
  - `POST   /patients/{id}/labs/{test_id}/points`
  - `GET    /patients/{id}/appointments`
  - `POST   /patients/{id}/appointments`
  - `GET    /patients/{id}/discharge`
  - `POST   /patients/{id}/discharge/sign`
  - `GET    /patients/{id}/immunizations`
  - `GET    /patients/{id}/vitals/latest`
  - `POST   /patients/{id}/vitals`
  - `GET    /patients/{id}/audit` (admin-only)
  - `GET    /dashboard/stats` (workspace-scoped metrics)

## Database Migrations
Alembic is configured in `backend/` using `core/config.py` database settings:
- Initial migration `ff7896daaf32`: Core auth and workspace schema.
- Migration `a73fc8a503aa`: Clinical models (`patients`, `allergies`, `documents`, `extracted_fields`, `medications`, `labs`, `appointments`, `discharge`, `immunizations`, `vitals`).
- Migration `8d254f062da3`: `patient_id` column addition to audit events.

## Latest Verification
- **Automated Tests**: 10/10 pytest tests passing (`tests/test_auth.py`, `tests/test_clinical.py`).
  - Tests verify workspace isolation across all resources, role denials/allowances, soft deletion, audit logging, and idempotency conflicts (409).
- **Python Compilation**: `compileall` clean on `app`, `tests`, and `alembic`.
- **Frontend Build**: `npm run build` completed cleanly with zero warnings or errors.
