import { createContext, useContext, useEffect, useState } from 'react'
import {
  PATIENTS as SEED_PATIENTS,
  PATIENT_DOCUMENTS as SEED_DOCS,
  LAB_TRENDS as SEED_LABS,
  MEDICATIONS as SEED_MEDS,
  DISCHARGE_DRAFTS as SEED_DRAFTS,
  AUDIT_LOG as SEED_AUDIT,
  IMMUNIZATIONS as SEED_IMMUNIZATIONS,
  VITALS as SEED_VITALS,
  APPOINTMENTS as SEED_APPOINTMENTS,
} from '../data/patientMock.js'
import { DOCS as SEED_VAULT_DOCS } from '../data/mock.js'
import { ROLE_DEFINITIONS } from '../data/roles.js'

const PatientContext = createContext(null)
const STORAGE_KEY = 'documind_clinical_state_v1'
const ROLE_STORAGE_KEY = 'documind_demo_role_v1'

function initialVaultDocuments() {
  return SEED_VAULT_DOCS.map((doc, index) => ({
    ...doc,
    id: `vault-${index + 1}`,
    patientId: SEED_PATIENTS.find((patient) => patient.name === doc.patient)?.id,
    archived: false,
  }))
}

function initialClinicalState() {
  return {
    patients: SEED_PATIENTS,
    documents: SEED_DOCS,
    vaultDocuments: initialVaultDocuments(),
    labs: SEED_LABS,
    meds: SEED_MEDS,
    drafts: SEED_DRAFTS,
    audit: SEED_AUDIT,
    immunizations: SEED_IMMUNIZATIONS,
    vitals: SEED_VITALS,
    appointments: SEED_APPOINTMENTS,
  }
}

function mergeSeedAppointments(savedAppointments = {}) {
  const patientIds = new Set([...Object.keys(SEED_APPOINTMENTS), ...Object.keys(savedAppointments || {})])
  return Object.fromEntries([...patientIds].map((patientId) => {
    const existing = Array.isArray(savedAppointments?.[patientId]) ? savedAppointments[patientId] : []
    const seeded = SEED_APPOINTMENTS[patientId] || []
    const seen = new Set()
    const merged = [...existing, ...seeded].filter((appointment) => {
      const key = [appointment.type, appointment.with, appointment.date, appointment.time].join('|')
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
    return [patientId, merged]
  }))
}

function loadInitial() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const saved = JSON.parse(raw)
      return {
        ...initialClinicalState(),
        ...saved,
        appointments: mergeSeedAppointments(saved.appointments),
        vaultDocuments: saved.vaultDocuments || initialVaultDocuments(),
      }
    }
  } catch (e) {
    // fall through to seed data if storage is unavailable or corrupt
  }
  return initialClinicalState()
}

function pad(n) {
  return String(n).padStart(3, '0')
}

export function PatientProvider({ children }) {
  const [state, setState] = useState(loadInitial)
  const [role, setRoleState] = useState(() => {
    try {
      const savedRole = localStorage.getItem(ROLE_STORAGE_KEY)
      return ROLE_DEFINITIONS[savedRole] ? savedRole : 'admin'
    } catch (e) {
      return 'admin'
    }
  })
  const roleDefinition = ROLE_DEFINITIONS[role] || ROLE_DEFINITIONS.viewer
  const canAccess = (permission) => roleDefinition.permissions.includes(permission)
  const setRole = (nextRole) => {
    if (!ROLE_DEFINITIONS[nextRole]) return
    setRoleState(nextRole)
    try {
      localStorage.setItem(ROLE_STORAGE_KEY, nextRole)
    } catch (e) {
      // role switching still works for this session if storage is unavailable
    }
  }

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch (e) {
      // storage full or unavailable — state still works in-memory for this session
    }
  }, [state])

  const addAudit = (patientId, who, action) => {
    setState((s) => ({
      ...s,
      audit: {
        ...s.audit,
        [patientId]: [{ who, action, when: 'Just now' }, ...(s.audit[patientId] || [])],
      },
    }))
  }

  const addPatient = (form) => {
    if (!canAccess('patients:create')) return null
    const id = 'p' + Date.now()
    const mrn = 'MRN-' + pad(Math.floor(Math.random() * 900) + 100) + Math.floor(Math.random() * 90 + 10)
    const patient = {
      id,
      name: form.name,
      mrn,
      dob: form.dob,
      sex: form.sex,
      bloodType: form.bloodType || 'Unknown',
      phone: form.phone || '—',
      email: form.email || '—',
      address: form.address || '—',
      emergencyContact: form.emergencyContact || '—',
      insuranceProvider: form.insuranceProvider || 'Self-pay',
      policyNumber: form.policyNumber || '—',
      attending: form.attending || 'Unassigned',
      ward: form.ward,
      status: 'admitted',
      allergies: form.allergies ? form.allergies.split(',').map((a) => a.trim()).filter(Boolean) : ['None recorded'],
      lastUpdated: 'Just now',
    }
    setState((s) => ({
      ...s,
      patients: [patient, ...s.patients],
      documents: { ...s.documents, [id]: [] },
      labs: { ...s.labs, [id]: [] },
      meds: { ...s.meds, [id]: [] },
      immunizations: { ...s.immunizations, [id]: [] },
      vitals: { ...s.vitals, [id]: null },
      appointments: { ...s.appointments, [id]: [] },
      audit: { ...s.audit, [id]: [{ who: roleDefinition.user, action: 'Patient admitted and chart created', when: 'Just now' }] },
    }))
    return id
  }

  const updatePatient = (patientId, form) => {
    if (!canAccess('patients:edit')) return false
    const { allergies, reason, ...demographicChanges } = form
    setState((s) => ({
      ...s,
      patients: s.patients.map((patient) => patient.id === patientId
        ? { ...patient, ...demographicChanges, allergies: patient.allergies, lastUpdated: 'Just now' }
        : patient),
    }))
    addAudit(patientId, roleDefinition.user, 'Updated patient demographics and administrative details')
    return true
  }

  const archivePatient = (patientId) => {
    if (!canAccess('patients:archive')) return false
    setState((s) => ({
      ...s,
      patients: s.patients.map((patient) => patient.id === patientId ? { ...patient, archived: true, lastUpdated: 'Just now' } : patient),
    }))
    addAudit(patientId, roleDefinition.user, 'Archived patient chart (record retained)')
    return true
  }

  const restorePatient = (patientId) => {
    if (!canAccess('patients:archive')) return false
    setState((s) => ({
      ...s,
      patients: s.patients.map((patient) => patient.id === patientId ? { ...patient, archived: false, lastUpdated: 'Just now' } : patient),
    }))
    addAudit(patientId, roleDefinition.user, 'Restored archived patient chart')
    return true
  }

  const scheduleAppointment = (patientId, appt) => {
    if (!canAccess('appointments:manage')) return false
    setState((s) => ({
      ...s,
      appointments: {
        ...s.appointments,
        [patientId]: [{ ...appt, status: 'upcoming' }, ...(s.appointments[patientId] || [])],
      },
    }))
    addAudit(patientId, roleDefinition.user, `Scheduled ${appt.type} with ${appt.with} on ${appt.date}`)
    return true
  }

  const addDocument = (patientId, docMeta) => {
    if (!canAccess('documents:create')) return null
    const patient = state.patients.find((item) => item.id === patientId)
    const doc = {
      id: 'd' + Date.now(),
      name: docMeta.name,
      type: docMeta.type,
      date: 'Just now',
      status: 'needs-review',
      fields: docMeta.fields,
      archived: false,
    }
    setState((s) => ({
      ...s,
      documents: { ...s.documents, [patientId]: [doc, ...(s.documents[patientId] || [])] },
      vaultDocuments: [{
        id: doc.id,
        name: doc.name,
        type: doc.type,
        status: doc.status,
        date: doc.date,
        size: '—',
        patient: patient?.name || 'Unknown patient',
        patientId,
        archived: false,
      }, ...(s.vaultDocuments || [])],
      patients: s.patients.map((p) => (p.id === patientId ? { ...p, lastUpdated: 'Just now' } : p)),
    }))
    addAudit(patientId, 'System (AI extraction)', `Extracted ${docMeta.fields.length} fields from ${docMeta.name}`)
    return doc.id
  }

  const updateVaultDocument = (documentId, changes) => {
    if (!canAccess('documents:edit')) return false
    const doc = state.vaultDocuments.find((item) => item.id === documentId)
    setState((s) => ({
      ...s,
      vaultDocuments: s.vaultDocuments.map((item) => item.id === documentId ? { ...item, ...changes } : item),
      documents: doc?.patientId ? {
        ...s.documents,
        [doc.patientId]: (s.documents[doc.patientId] || []).map((item) => item.id === documentId || item.name === doc.name ? { ...item, ...changes } : item),
      } : s.documents,
    }))
    if (doc?.patientId) addAudit(doc.patientId, roleDefinition.user, `Edited document metadata for ${doc.name}`)
    return true
  }

  const archiveVaultDocument = (documentId) => {
    if (!canAccess('documents:archive')) return false
    const doc = state.vaultDocuments.find((item) => item.id === documentId)
    setState((s) => ({
      ...s,
      vaultDocuments: s.vaultDocuments.map((item) => item.id === documentId ? { ...item, archived: true } : item),
      documents: doc?.patientId ? {
        ...s.documents,
        [doc.patientId]: (s.documents[doc.patientId] || []).map((item) => item.id === documentId || item.name === doc.name ? { ...item, archived: true } : item),
      } : s.documents,
    }))
    if (doc?.patientId) addAudit(doc.patientId, roleDefinition.user, `Archived document ${doc.name} (record retained)`)
    return true
  }

  const restoreVaultDocument = (documentId) => {
    if (!canAccess('documents:archive')) return false
    const doc = state.vaultDocuments.find((item) => item.id === documentId)
    setState((s) => ({
      ...s,
      vaultDocuments: s.vaultDocuments.map((item) => item.id === documentId ? { ...item, archived: false } : item),
      documents: doc?.patientId ? {
        ...s.documents,
        [doc.patientId]: (s.documents[doc.patientId] || []).map((item) => item.id === documentId || item.name === doc.name ? { ...item, archived: false } : item),
      } : s.documents,
    }))
    if (doc?.patientId) addAudit(doc.patientId, roleDefinition.user, `Restored archived document ${doc.name}`)
    return true
  }

  const confirmField = (patientId, docId, label, confirmedBy) => {
    if (!canAccess('clinical:review')) return false
    setState((s) => ({
      ...s,
      documents: {
        ...s.documents,
        [patientId]: (s.documents[patientId] || []).map((d) =>
          d.id === docId
            ? { ...d, fields: d.fields.map((f) => (f.label === label ? { ...f, flagged: false } : f)) }
            : d
        ),
      },
    }))
    addAudit(patientId, confirmedBy, `Confirmed field "${label}"`)
    return true
  }

  const signDischarge = (patientId, signedBy) => {
    if (!canAccess('clinical:review')) return false
    setState((s) => ({
      ...s,
      drafts: { ...s.drafts, [patientId]: { ...s.drafts[patientId], status: 'signed' } },
      patients: s.patients.map((p) => (p.id === patientId ? { ...p, status: 'discharge-pending' } : p)),
    }))
    addAudit(patientId, signedBy, 'Approved and signed discharge summary')
    return true
  }

  const value = {
    ...state,
    role,
    roleDefinition,
    canAccess,
    setRole,
    addPatient,
    updatePatient,
    archivePatient,
    restorePatient,
    addDocument,
    updateVaultDocument,
    archiveVaultDocument,
    restoreVaultDocument,
    confirmField,
    signDischarge,
    addAudit,
    scheduleAppointment,
  }
  return <PatientContext.Provider value={value}>{children}</PatientContext.Provider>
}

export function useClinical() {
  const ctx = useContext(PatientContext)
  if (!ctx) throw new Error('useClinical must be used within a PatientProvider')
  return ctx
}
