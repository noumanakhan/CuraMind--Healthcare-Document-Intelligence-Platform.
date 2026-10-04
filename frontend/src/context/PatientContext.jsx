import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { ROLE_DEFINITIONS } from '../data/roles.js'
import { useAuth } from './AuthContext.jsx'

const PatientContext = createContext(null)

export function PatientProvider({ children }) {
  const { user, request, hasPermission, accessToken } = useAuth()
  const [patients, setPatients] = useState([])
  const [totalPatients, setTotalPatients] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Sub-resource caches mapped by patientId
  const [documents, setDocuments] = useState({})
  const [labs, setLabs] = useState({})
  const [meds, setMeds] = useState({})
  const [drafts, setDrafts] = useState({})
  const [audit, setAudit] = useState({})
  const [immunizations, setImmunizations] = useState({})
  const [vitals, setVitals] = useState({})
  const [appointments, setAppointments] = useState({})
  const [vaultDocuments, setVaultDocuments] = useState([])
  // encounters, problems, allergyRecords — not yet backed by API endpoints.
  // Exposed as empty objects so PatientDetail tabs render their empty-state
  // rather than crashing on undefined. Wire to real endpoints in Phase 3.
  const [encounters, setEncounters] = useState({}) // eslint-disable-line no-unused-vars
  const [problems, setProblems] = useState({})       // eslint-disable-line no-unused-vars
  const [allergyRecords, setAllergyRecords] = useState({}) // eslint-disable-line no-unused-vars

  const role = user?.role || 'viewer'
  const roleDefinition = ROLE_DEFINITIONS[role] || ROLE_DEFINITIONS.viewer

  // UI convenience check — the backend remains the true security boundary.
  const canAccess = useCallback((permission) => {
    return hasPermission(permission)
  }, [hasPermission])

  // Fetch patient roster from API
  const loadPatients = useCallback(async (params = {}) => {
    if (!accessToken) return
    setLoading(true)
    setError('')
    try {
      const searchParams = new URLSearchParams()
      if (params.status && params.status !== 'all') searchParams.append('status', params.status)
      if (params.search) searchParams.append('search', params.search)
      if (params.skip !== undefined) searchParams.append('skip', params.skip)
      if (params.limit !== undefined) searchParams.append('limit', params.limit)

      const qs = searchParams.toString()
      const data = await request(`/patients${qs ? `?${qs}` : ''}`)
      const formatted = (data.patients || []).map((p) => ({
        ...p,
        allergies: p.allergies && p.allergies.length ? p.allergies.map((a) => a.allergen) : ['None recorded'],
        lastUpdated: new Intl.DateTimeFormat(undefined, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }).format(new Date(p.updated_at || p.created_at)),
      }))
      setPatients(formatted)
      setTotalPatients(data.total || formatted.length)
    } catch (err) {
      setError(err.message || 'Unable to load patients')
    } finally {
      setLoading(false)
    }
  }, [accessToken, request])

  useEffect(() => {
    if (accessToken) {
      loadPatients()
    } else {
      setPatients([])
    }
  }, [accessToken, loadPatients])

  // Fetch full clinical details for a single patient
  const loadPatientData = useCallback(async (patientId) => {
    if (!accessToken || !patientId) return
    try {
      // 1. Documents
      const docs = await request(`/patients/${patientId}/documents`).catch(() => [])
      setDocuments((prev) => ({ ...prev, [patientId]: docs }))

      // 2. Medications
      const patientMeds = await request(`/patients/${patientId}/medications`).catch(() => [])
      setMeds((prev) => ({ ...prev, [patientId]: patientMeds }))

      // 3. Labs
      const patientLabs = await request(`/patients/${patientId}/labs`).catch(() => [])
      setLabs((prev) => ({ ...prev, [patientId]: patientLabs }))

      // 4. Appointments
      const patientAppts = await request(`/patients/${patientId}/appointments`).catch(() => [])
      setAppointments((prev) => ({ ...prev, [patientId]: patientAppts }))

      // 5. Immunizations
      const patientImms = await request(`/patients/${patientId}/immunizations`).catch(() => [])
      setImmunizations((prev) => ({ ...prev, [patientId]: patientImms }))

      // 6. Vitals
      const latestVitals = await request(`/patients/${patientId}/vitals/latest`).catch(() => null)
      setVitals((prev) => ({ ...prev, [patientId]: latestVitals }))

      // 7. Discharge draft (if user has permission to view clinical chart)
      if (canAccess('clinical:chart_view')) {
        const discharge = await request(`/patients/${patientId}/discharge`).catch(() => null)
        if (discharge) {
          setDrafts((prev) => ({ ...prev, [patientId]: discharge }))
        }
      }

      // 8. Audit log (if admin)
      if (canAccess('audit:view')) {
        const auditLog = await request(`/patients/${patientId}/audit`).catch(() => ({ events: [] }))
        setAudit((prev) => ({
          ...prev,
          [patientId]: (auditLog.events || []).map((e) => ({
            who: e.actor_user_id || 'System',
            action: e.detail || e.action,
            when: new Intl.DateTimeFormat(undefined, {
              dateStyle: 'medium',
              timeStyle: 'short',
            }).format(new Date(e.created_at)),
          })),
        }))
      }
    } catch (e) {
      console.error('Failed to load patient sub-resources', e)
    }
  }, [accessToken, request, canAccess])

  // --- Clinical Mutations ---

  const addPatient = async (form) => {
    try {
      const payload = {
        name: form.name,
        dob: form.dob,
        sex: form.sex,
        blood_type: form.bloodType || 'Unknown',
        phone: form.phone || '',
        email: form.email || '',
        address: form.address || '',
        emergency_contact: form.emergencyContact || '',
        insurance_provider: form.insuranceProvider || 'Self-pay',
        policy_number: form.policyNumber || '',
        ward: form.ward || '',
        status: 'admitted',
        allergies: form.allergies ? form.allergies.split(',').map((a) => a.trim()).filter(Boolean) : [],
      }
      const created = await request('/patients', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      const formatted = {
        ...created,
        allergies: created.allergies && created.allergies.length ? created.allergies.map((a) => a.allergen) : ['None recorded'],
        lastUpdated: 'Just now',
      }
      setPatients((prev) => [formatted, ...prev])
      return created.id
    } catch (err) {
      console.error('Add patient error', err)
      throw err
    }
  }

  const updatePatient = async (patientId, form) => {
    try {
      const payload = {
        name: form.name,
        dob: form.dob,
        sex: form.sex,
        blood_type: form.bloodType,
        phone: form.phone,
        email: form.email,
        address: form.address,
        emergency_contact: form.emergencyContact,
        insurance_provider: form.insuranceProvider,
        policy_number: form.policyNumber,
        ward: form.ward,
        status: form.status,
      }
      const updated = await request(`/patients/${patientId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
      setPatients((prev) => prev.map((p) => (p.id === patientId ? { ...p, ...updated, lastUpdated: 'Just now' } : p)))
      return true
    } catch (err) {
      console.error('Update patient error', err)
      throw err
    }
  }

  const archivePatient = async (patientId) => {
    try {
      await request(`/patients/${patientId}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_deleted: true }),
      })
      setPatients((prev) => prev.filter((p) => p.id !== patientId))
      return true
    } catch (err) {
      console.error('Archive patient error', err)
      throw err
    }
  }

  const restorePatient = async (patientId) => {
    try {
      await request(`/patients/${patientId}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_deleted: false }),
      })
      await loadPatients()
      return true
    } catch (err) {
      console.error('Restore patient error', err)
      throw err
    }
  }

  const scheduleAppointment = async (patientId, appt) => {
    try {
      const payload = {
        type: appt.type,
        with_provider_name: appt.with || appt.with_provider_name || 'Provider',
        date: appt.date,
        time: appt.time,
      }
      const created = await request(`/patients/${patientId}/appointments`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setAppointments((prev) => ({
        ...prev,
        [patientId]: [created, ...(prev[patientId] || [])],
      }))
      return true
    } catch (err) {
      console.error('Schedule appointment error', err)
      throw err
    }
  }

  const addDocument = async (patientId, docMeta) => {
    try {
      const payload = {
        name: docMeta.name,
        type: docMeta.type,
        source_file_url: docMeta.source_file_url || null,
        fields: docMeta.fields || [],
      }
      const created = await request(`/patients/${patientId}/documents`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setDocuments((prev) => ({
        ...prev,
        [patientId]: [created, ...(prev[patientId] || [])],
      }))
      return created.id
    } catch (err) {
      console.error('Add document error', err)
      throw err
    }
  }

  const confirmField = async (patientId, docId, fieldIdOrLabel) => {
    try {
      // Find field id if label was passed
      const doc = (documents[patientId] || []).find((d) => d.id === docId)
      const field = (doc?.extracted_fields || []).find((f) => f.id === fieldIdOrLabel || f.label === fieldIdOrLabel)
      const targetFieldId = field?.id || fieldIdOrLabel

      const confirmed = await request(`/documents/${docId}/fields/${targetFieldId}/confirm`, {
        method: 'PATCH',
      })
      setDocuments((prev) => ({
        ...prev,
        [patientId]: (prev[patientId] || []).map((d) =>
          d.id === docId
            ? {
                ...d,
                extracted_fields: (d.extracted_fields || []).map((f) =>
                  f.id === targetFieldId ? { ...f, ...confirmed, flagged: false } : f
                ),
              }
            : d
        ),
      }))
      return true
    } catch (err) {
      console.error('Confirm field error', err)
      throw err
    }
  }

  const signDischarge = async (patientId) => {
    try {
      const signed = await request(`/patients/${patientId}/discharge/sign`, {
        method: 'POST',
      })
      setDrafts((prev) => ({
        ...prev,
        [patientId]: signed,
      }))
      setPatients((prev) =>
        prev.map((p) => (p.id === patientId ? { ...p, status: 'discharged', lastUpdated: 'Just now' } : p))
      )
      return true
    } catch (err) {
      console.error('Sign discharge error', err)
      throw err
    }
  }

  const addAudit = (patientId, who, action) => {
    setAudit((prev) => ({
      ...prev,
      [patientId]: [{ who, action, when: 'Just now' }, ...(prev[patientId] || [])],
    }))
  }

  const value = {
    patients,
    totalPatients,
    loading,
    error,
    loadPatients,
    loadPatientData,
    documents,
    labs,
    meds,
    drafts,
    audit,
    immunizations,
    vitals,
    appointments,
    vaultDocuments,
    // Phase 3 stubs — no API endpoints yet; always empty so tabs render cleanly
    encounters,
    problems,
    allergyRecords,
    role,
    user,
    roleDefinition,
    canAccess,
    // Authenticated fetch helper exposed for ad-hoc API calls (e.g. dashboard/stats)
    request,
    addPatient,
    updatePatient,
    archivePatient,
    restorePatient,
    addDocument,
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
