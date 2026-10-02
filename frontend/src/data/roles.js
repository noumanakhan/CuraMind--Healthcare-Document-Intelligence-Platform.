export const ROLE_DEFINITIONS = {
  admin: {
    label: 'Workspace admin',
    user: 'Faisal S.',
    description: 'Manage workspace data and administrative records. Archiving preserves a record in the audit trail.',
    permissions: [
      'patients:view',
      'patients:create',
      'patients:edit',
      'patients:archive',
      'documents:view',
      'documents:create',
      'documents:edit',
      'documents:archive',
      'appointments:manage',
      'settings:manage',
    ],
  },
  clinician: {
    label: 'Clinician',
    user: 'Dr. N. Fatima',
    description: 'Review clinical information, verify extracted fields, manage appointments, and sign clinical workflows.',
    permissions: [
      'patients:view',
      'documents:view',
      'documents:create',
      'clinical:review',
      'appointments:manage',
    ],
  },
  records: {
    label: 'Records staff',
    user: 'S. Ahmed',
    description: 'Register patients and maintain demographic and document metadata; clinical decisions remain with clinicians.',
    permissions: [
      'patients:view',
      'patients:create',
      'patients:edit',
      'documents:view',
      'documents:create',
      'documents:edit',
      'appointments:manage',
    ],
  },
  viewer: {
    label: 'Read-only',
    user: 'R. Malik',
    description: 'View patient records and documents without changing them.',
    permissions: ['patients:view', 'documents:view'],
  },
}

export const ROLE_IDS = Object.keys(ROLE_DEFINITIONS)

export const PERMISSION_LABELS = [
  ['patients:view', 'View patient charts'],
  ['patients:create', 'Register patients'],
  ['patients:edit', 'Edit demographics'],
  ['patients:archive', 'Archive patient records'],
  ['documents:view', 'View documents'],
  ['documents:create', 'Upload documents'],
  ['documents:edit', 'Edit document metadata'],
  ['documents:archive', 'Archive documents'],
  ['clinical:review', 'Confirm extracted fields / sign-off'],
  ['appointments:manage', 'Manage appointments'],
  ['settings:manage', 'Manage workspace settings'],
]
