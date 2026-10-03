/**
 * UI display metadata for roles and permissions.
 *
 * NOTE: Authorization is strictly enforced by the backend API.
 * The permission checks in the frontend UI are for UX convenience only.
 * The single source of truth for granted permissions is the GET /auth/permissions endpoint.
 */

export const ROLE_LABELS = {
  admin: 'Workspace admin',
  clinician: 'Clinician',
  records: 'Records staff',
  viewer: 'Read-only',
}

export const ROLE_DESCRIPTIONS = {
  admin: 'Manage workspace data, users, and administrative settings.',
  clinician: 'Review clinical charts, verify extracted fields, manage care plans, and sign discharge summaries.',
  records: 'Register patients, maintain demographics, upload documents, and schedule appointments.',
  viewer: 'Read-only access to patient summaries and documents.',
}

export const ROLE_IDS = ['admin', 'clinician', 'records', 'viewer']

export const PERMISSION_LABELS = [
  ['patients:view', 'View patient charts'],
  ['patients:create', 'Register patients'],
  ['patients:edit', 'Edit demographics'],
  ['clinical:chart_view', 'View full clinical charts and notes'],
  ['documents:view', 'View documents'],
  ['documents:create', 'Upload documents'],
  ['documents:edit', 'Edit document metadata'],
  ['fields:confirm', 'Confirm extracted fields'],
  ['discharge:sign', 'Sign discharge summaries'],
  ['appointments:manage', 'Schedule appointments'],
  ['medications:review', 'Review medications'],
  ['vitals:record', 'Record vitals & immunizations'],
  ['settings:manage', 'Manage workspace settings'],
  ['users:manage', 'Manage workspace users and roles'],
  ['audit:view', 'View clinical & authentication audit logs'],
]

// Backward-compatible minimal role definition helper for display
export const ROLE_DEFINITIONS = {
  admin: { label: ROLE_LABELS.admin, description: ROLE_DESCRIPTIONS.admin },
  clinician: { label: ROLE_LABELS.clinician, description: ROLE_DESCRIPTIONS.clinician },
  records: { label: ROLE_LABELS.records, description: ROLE_DESCRIPTIONS.records },
  viewer: { label: ROLE_LABELS.viewer, description: ROLE_DESCRIPTIONS.viewer },
}
