// Patient roster — fields modeled on core EHR demographic/administrative data:
// identity, contact, emergency contact, insurance, blood type, and assigned care team.
export const PATIENTS = [
  {
    id: 'p1',
    name: 'Amina Yusuf',
    mrn: 'MRN-88213',
    dob: '14 Mar 1988',
    sex: 'Female',
    bloodType: 'O+',
    phone: '0300-1234567',
    email: 'amina.yusuf@example.com',
    address: 'House 12, Street 4, Gulberg, Lahore',
    emergencyContact: 'Zainab Yusuf (Sister) · 0300-7654321',
    insuranceProvider: 'State Life Health',
    policyNumber: 'SLH-44219-A',
    attending: 'Dr. Faisal S. — Internal Medicine',
    ward: 'Internal Medicine · Bed 4B',
    status: 'admitted',
    allergies: ['Penicillin'],
    lastUpdated: '2 hours ago',
  },
  {
    id: 'p2',
    name: 'Hassan Raza',
    mrn: 'MRN-77190',
    dob: '02 Nov 1965',
    sex: 'Male',
    bloodType: 'A+',
    phone: '0321-9988776',
    email: 'hassan.raza@example.com',
    address: 'Flat 6B, DHA Phase 5, Karachi',
    emergencyContact: 'Bilal Raza (Son) · 0321-1122334',
    insuranceProvider: 'Jubilee Health Insurance',
    policyNumber: 'JHI-88012-B',
    attending: 'Dr. N. Fatima — Cardiology',
    ward: 'Cardiology · Bed 1A',
    status: 'discharge-pending',
    allergies: ['None recorded'],
    lastUpdated: '25 min ago',
  },
  {
    id: 'p3',
    name: 'Layla Ahmed',
    mrn: 'MRN-90344',
    dob: '29 Jul 2001',
    sex: 'Female',
    bloodType: 'B-',
    phone: '0333-4455667',
    email: 'layla.ahmed@example.com',
    address: 'House 88, Model Town, Lahore',
    emergencyContact: 'Ahmed Raza (Father) · 0333-7788990',
    insuranceProvider: 'Self-pay',
    policyNumber: '—',
    attending: 'Dr. Faisal S. — Outpatient',
    ward: 'Outpatient',
    status: 'discharged',
    allergies: ['Sulfa drugs', 'Latex'],
    lastUpdated: '1 day ago',
  },
  {
    id: 'p4',
    name: 'Omar Siddiqui',
    mrn: 'MRN-65521',
    dob: '18 Jan 1979',
    sex: 'Male',
    bloodType: 'AB+',
    phone: '0345-2233445',
    email: 'omar.siddiqui@example.com',
    address: 'House 21, F-10, Islamabad',
    emergencyContact: 'Sana Siddiqui (Wife) · 0345-5566778',
    insuranceProvider: 'EFU Health',
    policyNumber: 'EFU-30291-C',
    attending: 'Dr. N. Fatima — Critical Care',
    ward: 'ICU · Bed 2',
    status: 'admitted',
    allergies: ['None recorded'],
    lastUpdated: '10 min ago',
  },
]

// Patient encounter history for the chart timeline and visit context.
export const ENCOUNTERS = {
  p1: [
    { id: 'enc-p1-2', type: 'Inpatient', status: 'in-progress', date: '24 Sep 2026', reason: 'Persistent abdominal pain', attending: 'Dr. Faisal S.', location: 'Internal Medicine · Bed 4B' },
    { id: 'enc-p1-1', type: 'Outpatient', status: 'completed', date: '12 Jan 2025', reason: 'Follow-up consultation', attending: 'Dr. Faisal S.', location: 'Internal Medicine Clinic' },
  ],
  p2: [
    { id: 'enc-p2-2', type: 'Inpatient', status: 'discharge-pending', date: '26 Sep 2026', reason: 'Exertional chest pain', attending: 'Dr. N. Fatima', location: 'Cardiology · Bed 1A' },
    { id: 'enc-p2-1', type: 'Outpatient', status: 'completed', date: '08 Jun 2025', reason: 'Cardiology review', attending: 'Dr. N. Fatima', location: 'Cardiology Clinic' },
  ],
  p3: [
    { id: 'enc-p3-1', type: 'Outpatient', status: 'completed', date: '30 Sep 2026', reason: 'GI referral follow-up', attending: 'Dr. K. Farooq', location: 'Outpatient' },
  ],
  p4: [
    { id: 'enc-p4-2', type: 'Inpatient · ICU', status: 'in-progress', date: '25 Sep 2026', reason: 'Post-operative monitoring', attending: 'Dr. N. Fatima', location: 'ICU · Bed 2' },
    { id: 'enc-p4-1', type: 'Inpatient', status: 'completed', date: '18 Jan 2024', reason: 'Surgical admission', attending: 'Dr. N. Fatima', location: 'Surgery Ward' },
  ],
}

// Structured problem list; entries are documented chart context, not generated diagnoses.
export const PATIENT_PROBLEMS = {
  p1: [
    { id: 'prob-p1-1', name: 'Persistent abdominal pain', status: 'active', recorded: '25 Sep 2026', source: 'Intake form', note: 'Documented reason for visit; clinician assessment required.' },
  ],
  p2: [
    { id: 'prob-p2-1', name: 'Stable angina · NYHA class II', status: 'active', recorded: '26 Sep 2026', source: 'Cardiology consult note', note: 'Extracted diagnosis; verify against the signed source record.' },
  ],
  p3: [
    { id: 'prob-p3-1', name: 'Abdominal pain', status: 'monitoring', recorded: '30 Sep 2026', source: 'Referral follow-up', note: 'Follow-up with gastroenterology was recommended.' },
  ],
  p4: [
    { id: 'prob-p4-1', name: 'Post-operative monitoring', status: 'active', recorded: '27 Sep 2026', source: 'ICU progress note', note: 'Documented post-operative status; see source note for context.' },
  ],
}

// Structured allergy records retain verification state and source instead of relying on a string list.
export const ALLERGY_RECORDS = {
  p1: [
    { id: 'allergy-p1-1', substance: 'Penicillin', reaction: 'Not documented', severity: 'Unknown', status: 'active', verification: 'Needs verification', source: 'Intake form' },
  ],
  p2: [{ id: 'allergy-p2-none', substance: 'No known allergies reported', reaction: '—', severity: '—', status: 'none-reported', verification: 'Not confirmed', source: 'Patient chart' }],
  p3: [
    { id: 'allergy-p3-1', substance: 'Sulfa drugs', reaction: 'Not documented', severity: 'Unknown', status: 'active', verification: 'Unverified', source: 'Patient chart' },
    { id: 'allergy-p3-2', substance: 'Latex', reaction: 'Not documented', severity: 'Unknown', status: 'active', verification: 'Unverified', source: 'Patient chart' },
  ],
  p4: [{ id: 'allergy-p4-none', substance: 'No known allergies reported', reaction: '—', severity: '—', status: 'none-reported', verification: 'Not confirmed', source: 'Patient chart' }],
}

// Immunization history per patient
export const IMMUNIZATIONS = {
  p1: [
    { vaccine: 'Tetanus (Td)', date: '12 Jan 2024' },
    { vaccine: 'Influenza', date: '03 Oct 2025' },
  ],
  p2: [
    { vaccine: 'Influenza', date: '15 Nov 2025' },
    { vaccine: 'Pneumococcal', date: '20 Mar 2023' },
  ],
  p3: [{ vaccine: 'HPV (3rd dose)', date: '08 Feb 2022' }],
  p4: [{ vaccine: 'Tetanus (Td)', date: '19 Jun 2025' }],
}

// Latest vitals snapshot per patient
export const VITALS = {
  p1: { bp: '118/76', hr: '92 bpm', temp: '38.1°C', spo2: '97%', weight: '61 kg', recorded: '1 hour ago' },
  p2: { bp: '132/84', hr: '78 bpm', temp: '36.8°C', spo2: '98%', weight: '84 kg', recorded: '3 hours ago' },
  p3: { bp: '110/70', hr: '72 bpm', temp: '36.6°C', spo2: '99%', weight: '58 kg', recorded: '1 day ago' },
  p4: { bp: '128/82', hr: '91 bpm', temp: '37.4°C', spo2: '96%', weight: '76 kg', recorded: '10 min ago' },
}

// Appointments per patient — past and upcoming
export const APPOINTMENTS = {
  p1: [
    { type: 'Inpatient medicine review', with: 'Dr. Faisal S.', date: '05 Oct 2026', time: '09:15 AM', status: 'upcoming' },
    { type: 'Follow-up · Internal Medicine', with: 'Dr. Faisal S.', date: '02 Oct 2026', time: '10:30 AM', status: 'upcoming' },
    { type: 'Initial consult', with: 'Dr. Faisal S.', date: '25 Sep 2026', time: '09:00 AM', status: 'completed' },
  ],
  p2: [
    { type: 'Post-discharge review · Cardiology', with: 'Dr. N. Fatima', date: '10 Oct 2026', time: '02:00 PM', status: 'upcoming' },
    { type: 'Cardiac rehabilitation assessment', with: 'Dr. N. Fatima', date: '14 Oct 2026', time: '11:00 AM', status: 'upcoming' },
    { type: 'Cardiology consult', with: 'Dr. N. Fatima', date: '26 Sep 2026', time: '11:15 AM', status: 'completed' },
  ],
  p3: [{ type: 'GI referral follow-up', with: 'Dr. K. Farooq', date: '30 Sep 2026', time: '04:00 PM', status: 'upcoming' }],
  p4: [
    { type: 'Critical care follow-up', with: 'Dr. N. Fatima', date: '08 Oct 2026', time: '08:30 AM', status: 'upcoming' },
    { type: 'ICU rounds', with: 'Dr. N. Fatima', date: '27 Sep 2026', time: '08:00 AM', status: 'completed' },
  ],
}

export const PATIENT_STATUS_LABEL = {
  admitted: 'Admitted',
  'discharge-pending': 'Discharge pending',
  discharged: 'Discharged',
}

// Per-patient extracted documents, with confidence scores per field (0-1)
export const PATIENT_DOCUMENTS = {
  p1: [
    {
      id: 'd1',
      name: 'intake-form-amina-yusuf.pdf',
      type: 'Intake form',
      date: '25 Sep 2026',
      status: 'needs-review',
      fields: [
        { label: 'Patient name', value: 'Amina Yusuf', confidence: 0.98, flagged: false },
        { label: 'Date of birth', value: '14 Mar 1988', confidence: 0.95, flagged: false },
        { label: 'Reason for visit', value: 'Persistent abdominal pain, 3 days', confidence: 0.81, flagged: false },
        { label: 'Known allergies', value: 'Penicillin', confidence: 0.62, flagged: true },
        { label: 'Emergency contact', value: 'Zainab Yusuf — 0300•••••12', confidence: 0.9, flagged: false },
      ],
    },
    {
      id: 'd2',
      name: 'lab-report-cbc-25sep.pdf',
      type: 'Lab report',
      date: '25 Sep 2026',
      status: 'processed',
      fields: [
        { label: 'WBC count', value: '13.4 x10⁹/L', confidence: 0.97, flagged: true },
        { label: 'Hemoglobin', value: '11.2 g/dL', confidence: 0.96, flagged: false },
        { label: 'Platelets', value: '260 x10⁹/L', confidence: 0.95, flagged: false },
        { label: 'CRP', value: '38 mg/L', confidence: 0.88, flagged: true },
      ],
    },
  ],
  p2: [
    {
      id: 'd3',
      name: 'cardiology-consult-note.pdf',
      type: 'Clinical note',
      date: '26 Sep 2026',
      status: 'processed',
      fields: [
        { label: 'Diagnosis', value: 'Stable angina, NYHA class II', confidence: 0.89, flagged: false },
        { label: 'Suggested ICD-10', value: 'I20.8', confidence: 0.74, flagged: true },
        { label: 'Follow-up', value: 'Outpatient review in 2 weeks', confidence: 0.93, flagged: false },
      ],
    },
  ],
  p3: [],
  p4: [
    {
      id: 'd4',
      name: 'icu-progress-note-27sep.pdf',
      type: 'Clinical note',
      date: '27 Sep 2026',
      status: 'needs-review',
      fields: [
        { label: 'Vitals summary', value: 'BP 128/82, HR 91, SpO2 96%', confidence: 0.94, flagged: false },
        { label: 'Assessment', value: 'Post-op day 2, stable, monitor for infection', confidence: 0.7, flagged: true },
      ],
    },
  ],
}

// Lab trend series: [{date, value}], with a normal reference range
export const LAB_TRENDS = {
  p1: [
    {
      test: 'White Blood Cell Count',
      unit: 'x10⁹/L',
      range: [4, 11],
      points: [
        { date: 'Sep 20', value: 8.1 },
        { date: 'Sep 22', value: 9.6 },
        { date: 'Sep 24', value: 12.1 },
        { date: 'Sep 25', value: 13.4 },
      ],
    },
    {
      test: 'C-Reactive Protein',
      unit: 'mg/L',
      range: [0, 10],
      points: [
        { date: 'Sep 20', value: 6 },
        { date: 'Sep 22', value: 14 },
        { date: 'Sep 24', value: 27 },
        { date: 'Sep 25', value: 38 },
      ],
    },
  ],
  p2: [
    {
      test: 'LDL Cholesterol',
      unit: 'mg/dL',
      range: [0, 100],
      points: [
        { date: 'Sep 10', value: 142 },
        { date: 'Sep 18', value: 128 },
        { date: 'Sep 26', value: 109 },
      ],
    },
  ],
  p3: [],
  p4: [
    {
      test: 'Lactate',
      unit: 'mmol/L',
      range: [0.5, 2.2],
      points: [
        { date: 'Sep 25', value: 3.1 },
        { date: 'Sep 26', value: 2.4 },
        { date: 'Sep 27', value: 1.8 },
      ],
    },
  ],
}

export const MEDICATIONS = {
  p1: [
    { name: 'Amoxicillin 500mg', dose: '3x daily', flag: 'interaction', note: 'Patient has a documented penicillin allergy — cross-reactivity risk.' },
    { name: 'Paracetamol 1g', dose: 'As needed', flag: null, note: null },
  ],
  p2: [
    { name: 'Atorvastatin 40mg', dose: 'Nightly', flag: null, note: null },
    { name: 'Aspirin 75mg', dose: 'Daily', flag: null, note: null },
    { name: 'Metoprolol 50mg', dose: '2x daily', flag: 'dosage', note: 'Dose is above the typical starting range for this patient\u2019s renal function — confirm with prescriber.' },
  ],
  p3: [],
  p4: [
    { name: 'Piperacillin-Tazobactam', dose: '4.5g IV, 3x daily', flag: null, note: null },
    { name: 'Norepinephrine infusion', dose: 'Titrated', flag: null, note: null },
  ],
}

export const DISCHARGE_DRAFTS = {
  p2: {
    status: 'draft',
    paragraphs: [
      { text: 'Mr. Hassan Raza was admitted for evaluation of exertional chest pain, subsequently diagnosed as stable angina (NYHA class II).', cite: 'cardiology-consult-note.pdf · Page 1' },
      { text: 'During admission, the patient was started on atorvastatin 40mg nightly and aspirin 75mg daily; metoprolol dosing was flagged for prescriber review prior to discharge.', cite: 'medication-order-26sep.pdf · Page 1' },
      { text: 'The patient remained hemodynamically stable throughout the admission with no further chest pain episodes reported.', cite: 'nursing-notes-26sep.pdf · Page 3' },
      { text: 'Patient is discharged in stable condition with outpatient cardiology follow-up scheduled in 2 weeks.', cite: 'cardiology-consult-note.pdf · Page 2' },
    ],
  },
}

export const AUDIT_LOG = {
  p1: [
    { who: 'Dr. Faisal S.', action: 'Viewed patient record', when: '2 hours ago' },
    { who: 'System (AI extraction)', action: 'Extracted 5 fields from intake-form-amina-yusuf.pdf', when: '3 hours ago' },
    { who: 'Nurse R. Bibi', action: 'Confirmed emergency contact field', when: '3 hours ago' },
    { who: 'System (AI extraction)', action: 'Flagged allergy field for review — low confidence (62%)', when: '3 hours ago' },
  ],
  p2: [
    { who: 'Dr. Faisal S.', action: 'Reviewed discharge summary draft', when: '20 min ago' },
    { who: 'System (AI extraction)', action: 'Drafted discharge summary from 3 source documents', when: '1 hour ago' },
    { who: 'Pharmacist A. Khan', action: 'Flagged metoprolol dosage for review', when: '2 hours ago' },
  ],
  p3: [{ who: 'Dr. Faisal S.', action: 'Closed patient episode', when: '1 day ago' }],
  p4: [
    { who: 'System (AI extraction)', action: 'Extracted vitals summary from ICU progress note', when: '10 min ago' },
    { who: 'Dr. N. Fatima', action: 'Viewed patient record', when: '15 min ago' },
  ],
}
