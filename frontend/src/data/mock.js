export const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: 'IcGrid' },
  { id: 'workqueue', label: 'Work queue', icon: 'IcFileCheck' },
  { id: 'patients', label: 'Patients', icon: 'IcUsers' },
  { id: 'documents', label: 'Document Vault', icon: 'IcDoc' },
  { id: 'upload', label: 'Upload', icon: 'IcUpload' },
  { id: 'ask', label: 'Clinical Assistant', icon: 'IcChat' },
  { id: 'compare', label: 'Compare Reports', icon: 'IcCompare' },
]

export const TITLES = {
  dashboard: ['Clinical Dashboard', 'Ward activity and review priorities'],
  workqueue: ['Work queue', 'Prioritized chart review and care coordination items'],
  documents: ['Document Vault', 'All clinical documents indexed across every patient'],
  upload: ['Upload', 'Add a new clinical document and attach it to a patient chart'],
  ask: ['Clinical Assistant', 'Ask questions across patient records, with cited sources'],
  compare: ['Compare Reports', 'See differences between two clinical documents side by side'],
  settings: ['Settings', 'Manage workspace and compliance preferences'],
}

// Facility-wide document vault (spans all patients) — clinical document types only
export const DOCS = [
  { name: 'lab-report-cbc-25sep.pdf', type: 'Lab report', status: 'processed', date: '25 Sep 2026', size: '214 KB', patient: 'Amina Yusuf' },
  { name: 'cardiology-consult-note.pdf', type: 'Clinical note', status: 'processed', date: '26 Sep 2026', size: '1.1 MB', patient: 'Hassan Raza' },
  { name: 'intake-form-amina-yusuf.pdf', type: 'Intake form', status: 'needs-review', date: '25 Sep 2026', size: '340 KB', patient: 'Amina Yusuf' },
  { name: 'referral-letter-layla-ahmed.pdf', type: 'Referral letter', status: 'processed', date: '24 Sep 2026', size: '88 KB', patient: 'Layla Ahmed' },
  { name: 'discharge-summary-layla-ahmed.pdf', type: 'Discharge summary', status: 'processed', date: '23 Sep 2026', size: '560 KB', patient: 'Layla Ahmed' },
  { name: 'insurance-claim-hassan-raza.pdf', type: 'Insurance claim', status: 'processing', date: '20 Sep 2026', size: '2.3 MB', patient: 'Hassan Raza' },
  { name: 'icu-progress-note-27sep.pdf', type: 'Clinical note', status: 'needs-review', date: '27 Sep 2026', size: '980 KB', patient: 'Omar Siddiqui' },
]

export const PIPELINE = ['Upload', 'Extract text', 'OCR', 'Clean', 'Classify', 'Extract fields', 'PHI scan', 'Validate', 'Embed', 'Index']

export const BY_TYPE = [
  ['Lab reports', 62],
  ['Clinical notes', 45],
  ['Referrals', 21],
  ['Discharge summaries', 14],
]

export const ACTIVITY = [
  { level: 'ok', text: 'discharge-summary-layla-ahmed.pdf signed by Dr. Faisal S.', meta: '20 min ago · logged to audit trail' },
  { level: 'warn', text: 'icu-progress-note-27sep.pdf flagged for review', meta: '35 min ago · low-confidence assessment field' },
  { level: 'err', text: 'insurance-claim-hassan-raza.pdf missing required field', meta: '1 hour ago · prior-authorization code' },
  { level: 'ok', text: 'lab-report-cbc-25sep.pdf indexed for Amina Yusuf', meta: '2 hours ago · WBC flagged out of range' },
]

export const INITIAL_MESSAGES = [
  { role: 'user', text: 'Has Amina Yusuf had any abnormal lab values this admission?' },
  {
    role: 'ai',
    text: 'Yes. Her white blood cell count has risen from 8.1 to 13.4 x10⁹/L over the last five days, and CRP is elevated at 38 mg/L, both above the reference range and trending upward — consistent with an evolving infection.',
    cites: ['lab-report-cbc-25sep.pdf · Page 1'],
  },
  { role: 'user', text: 'Does Hassan Raza have any medication flags before discharge?' },
  {
    role: 'ai',
    text: 'Yes — his metoprolol dose is above the typical starting range given his renal function. This has been flagged for prescriber review and is not yet cleared for discharge.',
    cites: ['cardiology-consult-note.pdf · Page 1'],
  },
]

export const COMPARE_ROWS = [
  ['Chief complaint', 'Chest pain on exertion', 'Persistent abdominal pain', true],
  ['Suggested ICD-10', 'I20.8 — stable angina', 'R10.9 — abdominal pain, unspecified', true],
  ['Follow-up window', '2 weeks, outpatient cardiology', '3 days, GI referral if unresolved', true],
  ['Attending physician', 'Dr. Faisal S.', 'Dr. Faisal S.', false],
]

export const SETTINGS_ITEMS = [
  ['Email notifications', 'Get notified when a document finishes processing', true],
  ['Auto-OCR scanned files', 'Run OCR automatically when no text layer is found', true],
  ['Hybrid search', 'Combine keyword and semantic search for retrieval', true],
  ['Require sign-off for AI-drafted notes', 'Block discharge summaries and coding suggestions from finalizing without clinician approval', true],
  ['Share de-identified data for model evaluation', 'Helps improve extraction accuracy; data is redacted before use', false],
]
