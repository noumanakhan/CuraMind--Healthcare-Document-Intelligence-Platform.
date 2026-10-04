import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PATIENT_STATUS_LABEL } from '../data/patientMock.js'
import { IcArrowLeft, IcEye, IcEyeOff, IcUsers } from '../components/icons.jsx'
import { useClinical } from '../context/PatientContext.jsx'
import Overview from './patient/Overview.jsx'
import DocumentReview from './patient/DocumentReview.jsx'
import LabTrends from './patient/LabTrends.jsx'
import Medications from './patient/Medications.jsx'
import Appointments from './patient/Appointments.jsx'
import DischargeSummary from './patient/DischargeSummary.jsx'
import AuditLog from './patient/AuditLog.jsx'
import Encounters from './patient/Encounters.jsx'
import ProblemsAllergies from './patient/ProblemsAllergies.jsx'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'encounters', label: 'Encounters' },
  { id: 'problems', label: 'Problems & allergies' },
  { id: 'documents', label: 'Documents' },
  { id: 'labs', label: 'Lab trends' },
  { id: 'meds', label: 'Medications' },
  { id: 'appointments', label: 'Appointments' },
  { id: 'discharge', label: 'Discharge summary' },
  { id: 'audit', label: 'Audit log' },
]

function mask(value) {
  return value.replace(/./g, (c, i) => (c === ' ' ? ' ' : i < 2 ? c : '•'))
}

export default function PatientDetail({ patientId, initialTab = 'overview', onBack }) {
  const navigate = useNavigate()
  const { tab: routeTab } = useParams()
  const tab = TABS.some((item) => item.id === (routeTab || initialTab)) ? (routeTab || initialTab) : 'overview'
  const [hidePHI, setHidePHI] = useState(false)
  const {
    patients,
    documents,
    labs,
    meds,
    drafts,
    audit,
    immunizations,
    vitals,
    appointments,
    encounters,
    problems,
    allergyRecords,
    loadPatientData,
    addDocument,
    confirmField,
    signDischarge,
    scheduleAppointment,
    canAccess,
    roleDefinition,
  } = useClinical()

  useEffect(() => {
    if (patientId && loadPatientData) {
      loadPatientData(patientId)
    }
  }, [patientId, loadPatientData])

  const patient = patients.find((p) => p.id === patientId)
  if (!patient) return null


  const patientDocs = (documents[patientId] || []).filter((doc) => !doc.archived)
  const patientLabs = labs[patientId] || []
  const patientMeds = meds[patientId] || []
  const draft = drafts[patientId]
  const patientAudit = audit[patientId] || []
  const patientImmunizations = immunizations[patientId] || []
  const patientVitals = vitals[patientId]
  const patientAppointments = appointments[patientId] || []
  const patientEncounters = encounters[patientId] || []
  const patientProblems = problems[patientId] || []
  const patientAllergyRecords = allergyRecords[patientId] || []

  return (
    <div>
      <button className="btn btn-ghost" style={{ marginBottom: 16, fontSize: 12.5, padding: '6px 11px' }} onClick={onBack}>
        <IcArrowLeft width={14} height={14} /> Back to patients
      </button>

      <div className="card" style={{ marginBottom: 18, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div className="doc-icon" style={{ width: 44, height: 44 }}>
            <IcUsers width={20} height={20} />
          </div>
          <div>
            <div style={{ fontFamily: 'var(--serif)', fontWeight: 600, fontSize: 19 }}>
              {hidePHI ? mask(patient.name) : patient.name}
            </div>
            <div className="muted" style={{ fontSize: 12.5, marginTop: 2 }}>
              {patient.mrn} · {hidePHI ? mask(patient.dob) : patient.dob} · {patient.sex} · {patient.ward}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {patient.allergies.map((a) =>
            a === 'None recorded' ? null : (
              <span key={a} className="badge failed">
                {a}
              </span>
            )
          )}
          <span className={'badge ' + (patient.status === 'discharged' ? 'processed' : 'processing')}>
            {PATIENT_STATUS_LABEL[patient.status]}
          </span>
          <button className="btn btn-ghost" style={{ fontSize: 12.5, padding: '6px 11px' }} onClick={() => setHidePHI((v) => !v)}>
            {hidePHI ? <IcEyeOff width={14} height={14} /> : <IcEye width={14} height={14} />}
            {hidePHI ? 'PHI hidden' : 'Show PHI'}
          </button>
        </div>
      </div>

      <div className="toolbar">
        {TABS.map((t) => (
          <button key={t.id} className={'chip-filter' + (tab === t.id ? ' active' : '')} onClick={() => navigate(`/patients/${encodeURIComponent(patientId)}/${t.id}`)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <Overview patient={patient} vitals={patientVitals} immunizations={patientImmunizations} encounters={patientEncounters} problems={patientProblems} allergyRecords={patientAllergyRecords} />}
      {tab === 'encounters' && <Encounters encounters={patientEncounters} />}
      {tab === 'problems' && <ProblemsAllergies problems={patientProblems} allergyRecords={patientAllergyRecords} />}
      {tab === 'documents' && (
        <DocumentReview
          documents={patientDocs}
          onAddDocument={(meta) => addDocument(patientId, meta)}
          onConfirmField={(docId, label) => confirmField(patientId, docId, label, roleDefinition.user)}
          canUpload={canAccess('documents:create')}
          canReview={canAccess('clinical:review')}
        />
      )}
      {tab === 'labs' && <LabTrends series={patientLabs} />}
      {tab === 'meds' && <Medications meds={patientMeds} />}
      {tab === 'appointments' && (
        <Appointments appointments={patientAppointments} onSchedule={(appt) => scheduleAppointment(patientId, appt)} canManage={canAccess('appointments:manage')} />
      )}
      {tab === 'discharge' && <DischargeSummary draft={draft} onSign={() => signDischarge(patientId, roleDefinition.user)} canReview={canAccess('clinical:review')} />}
      {tab === 'audit' && <AuditLog entries={patientAudit} />}
    </div>
  )
}
