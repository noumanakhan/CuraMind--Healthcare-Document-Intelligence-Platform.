# CuraMind Frontend

React 18 + Vite interface for CuraMind's clinical document intelligence prototype. It includes a dashboard, patient roster/charts, global appointments, document vault/upload screens, assistant and comparison demos, settings, and a FastAPI-backed login/role-management flow.

## Important data boundary

Only authentication and role management are currently connected to the FastAPI service in `../backend`. Patient charts, appointments, documents, extracted fields, work queue, AI assistant, and workspace preferences are still seeded mock data held in React Context and `localStorage`. Do not enter real patient information; frontend role checks do not secure locally stored data.

## Run the frontend

Install npm dependencies and start Vite from this directory using the package scripts. The default API URL follows the host used to open the frontend (`localhost` or `127.0.0.1`) and points to port 8000. If the API is elsewhere, set `VITE_API_BASE_URL` in a local `.env` file and make sure the backend CORS origins match the frontend origin.

## Authentication behavior

- Sign-up sends name, email, and password to FastAPI. New accounts receive the `viewer` role; users cannot select their own role.
- Sign-in obtains a short-lived access token held in memory plus a refresh token in an HttpOnly cookie.
- Refresh-on-load restores a valid session; sign-out revokes the refresh session.
- The authenticated backend role drives the current UI permission gates. Admins can assign roles and disable workspace accounts from Settings.
- Password reset, email verification, MFA, invitations, and production rate limiting are not implemented.

See `../backend/README.md` for backend dependencies, configuration, starting the API, CLI admin bootstrap, and test instructions.

## Patient chart sections

The chart provides Overview, Encounters, Problems & allergies, Documents, Lab trends, Medications, Appointments, Discharge summary, and Audit log. Encounter, problem, and allergy examples are mock records. Allergy entries show source/verification state; “not recorded” must not be interpreted as “none.”

## Build

Use the `build` npm script from this directory to create a Vite production bundle.
