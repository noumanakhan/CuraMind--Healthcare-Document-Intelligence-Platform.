# CuraMind FastAPI authentication backend

This backend provides email/password authentication, short-lived JWT access tokens, rotating opaque refresh tokens in HttpOnly cookies, workspace-scoped roles, permission dependencies, admin user management, and authentication audit events.

> This is an authentication/RBAC foundation, not a complete production health-data platform. Patient/document endpoints are not yet implemented here; frontend clinical records remain demo/local data. Do not enter real patient data until the complete system has had security, privacy, clinical, and legal review.

## Backend structure

The backend is an API-only MVC-style application. Controllers handle HTTP concerns, services hold reusable application operations, models represent persisted entities, and Pydantic schemas define API contracts. The React frontend is the presentation/view layer; FastAPI does not render HTML templates.

- `app/api/v1/` — versioned API router.
- `app/api/dependencies.py` — authentication and permission dependencies.
- `app/controllers/` — endpoint handlers grouped by feature (`auth.py`, `users.py`).
- `app/services/` — reusable operations, currently audit events and default-workspace creation.
- `app/models/` — SQLAlchemy entities, one module per entity, re-exported by the package.
- `app/schemas/` — request and response contracts grouped by feature.
- `app/core/` — runtime settings, JWT/password security, and role-permission policy.
- `app/db/` — SQLAlchemy engine, session factory, and declarative base.
- `app/main.py` — FastAPI app creation, middleware, startup, and health endpoint.
- `app/cli.py` — trusted local account administration commands.
- `tests/` — API-level authentication and RBAC tests.

Use the package locations above as the canonical imports; root-level duplicate wrappers have been removed.

## Requirements

- Python 3.9+
- A virtual environment is recommended.
- SQLite is the local default. Select PostgreSQL for a deployed environment.

## Local setup

From this directory:

1. Create/activate a virtual environment.
2. Install `requirements.txt`.
3. Copy `.env.example` to `.env` and replace `JWT_SECRET` with a fresh random secret.
4. Start the API with `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
5. Create the first admin account using `python -m app.cli create-user --email admin@example.com --name "Workspace Admin" --role admin`. The CLI prompts for the password without echoing it.
6. The frontend expects `VITE_API_BASE_URL=http://localhost:8000/api/v1` (default). Restart Vite after changing it.

Open `/docs` in local development for the OpenAPI UI. The schema/docs endpoints are disabled when `APP_ENV=production`.

## Account and role policy

- Public signup creates a `viewer` account. A user cannot choose or elevate their own role.
- An admin assigns `admin`, `clinician`, `records`, or `viewer` through the protected user-management endpoints.
- The workspace retains at least one active administrator.
- To bootstrap or recover administrators, use the trusted CLI on the server; do not expose CLI/admin secrets to the browser.
- Set `ALLOW_PUBLIC_REGISTRATION=false` where self-service registration is not approved.
- Current signup joins one configured default workspace. Multi-organization onboarding, invitation flows, email verification, password recovery, and MFA are not implemented yet.

## API

All API routes use `/api/v1`.

- `POST /auth/register` — create viewer account; returns access token and user, sets refresh cookie.
- `POST /auth/login` — authenticate, returns access token and user, sets refresh cookie.
- `POST /auth/refresh` — rotate the refresh cookie and return a new access token.
- `POST /auth/logout` — revoke current refresh session and clear cookie.
- `GET /auth/me` — current authenticated user.
- `GET /auth/permissions` — effective role and permission list.
- `GET /users` — admin-only workspace user list.
- `PATCH /users/{user_id}/role` — admin-only role assignment.
- `PATCH /users/{user_id}/status` — admin-only account activation/deactivation; deactivation revokes refresh sessions.
- `GET /admin/auth-audit` — admin-only authentication/role audit events.
- `GET /health` — service health.

Send the access token as `Authorization: Bearer <token>`. The long-lived refresh token is never returned in JSON; it is stored in an HttpOnly cookie with `SameSite=Lax` and a configurable Secure flag.

## Configuration

See `.env.example`. Important deployment settings:

- `APP_ENV=production`
- `DATABASE_URL` — PostgreSQL URL for deployment (SQLite is for local development only).
- `JWT_SECRET` — unique high-entropy value, at least 32 characters.
- `REFRESH_COOKIE_SECURE=true` — required for HTTPS production.
- `CORS_ORIGINS` — exact trusted frontend origins; do not use `*` with credentials.
- `ALLOW_PUBLIC_REGISTRATION=false` unless public signup is intentionally allowed.

Production mode refuses the known development JWT secret, insecure refresh cookies, and open registration. Configure an HTTPS reverse proxy, rate limits for login/signup, monitoring, backups, and database migrations before deployment. `Base.metadata.create_all` is only for local initialization; use a migration tool such as Alembic for real releases.

## Tests

Run `pytest` from this directory. Tests use an isolated temporary SQLite database and do not require a real account or secret.
