import { useState } from 'react'
import { IcActivity, IcAlert, IcClock, IcDoc, IcFileCheck, IcPill, IcUsers } from '../components/icons.jsx'
import { useClinical } from '../context/PatientContext.jsx'
import Modal from '../components/Modal.jsx'

const STATUS_LABELS = { admitted: 'Admitted', 'discharge-pending': 'Discharge pending', discharged: 'Discharged' }

function parseDate(value) {
  const match = /^\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s*$/.exec(value || '')
  if (!match) return null
  const month = new Date(`${match[2]} 1, ${match[3]}`).getMonth()
  if (Number.isNaN(month)) return null
  return new Date(Number(match[3]), month, Number(match[1]))
}

function activityAge(value) {
  if (!value || value === 'Just now') return 0
  const amount = Number.parseInt(value, 10) || 0
  if (value.includes('minute')) return amount
  if (value.includes('hour')) return amount * 60
  if (value.includes('day')) return amount * 1440
  return 100000
}

function buildReviewItems(patients, documents, meds, labs) {
  const items = []
  patients.forEach((patient) => {
    ;(meds[patient.id] || []).filter((med) => med.flag).forEach((med, index) => {
      items.push({
        id: `med-${patient.id}-${index}`,
        kind: 'medication',
        label: 'Medication flag',
        title: med.name,
        detail: med.note || 'This medication is flagged for review in the chart.',
        patient,
        tab: 'meds',
      })
    })
    ;(documents[patient.id] || []).filter((doc) => !doc.archived).forEach((doc) => {
      const flaggedFields = doc.fields.filter((field) => field.flagged)
      if (flaggedFields.length) {
        items.push({
          id: `doc-${doc.id}`,
          kind: 'document',
          label: 'Verify extracted fields',
          title: doc.name,
          detail: `${flaggedFields.length} field${flaggedFields.length === 1 ? '' : 's'} flagged: ${flaggedFields.map((field) => field.label).join(', ')}`,
          patient,
          tab: 'documents',
        })
      }
    })
    if (patient.status === 'discharge-pending') {
      items.push({
        id: `discharge-${patient.id}`,
        kind: 'discharge',
        label: 'Discharge workflow',
        title: 'Pending discharge review',
        detail: 'Review the patient chart and complete the appropriate discharge workflow.',
        patient,
        tab: 'discharge',
      })
    }
    ;(labs[patient.id] || []).forEach((series) => {
      const latest = series.points[series.points.length - 1]
      if (!latest || (latest.value >= series.range[0] && latest.value <= series.range[1])) return
      items.push({
        id: `lab-${patient.id}-${series.test}`,
        kind: 'lab',
        label: 'Outside reference range',
        title: series.test,
        detail: `Latest ${latest.value} ${series.unit} · reference ${series.range[0]}–${series.range[1]} ${series.unit}`,
        patient,
        tab: 'labs',
      })
    })
  })
  return items
}

export default function Dashboard({ onNavigate, onOpenPatient }) {
  const [showAppointments, setShowAppointments] = useState(false)
  const [showActivity, setShowActivity] = useState(false)
  const { patients, documents, meds, labs, appointments, audit, vitals, canAccess } = useClinical()
  const activePatients = patients.filter((patient) => !patient.archived)
  const admitted = activePatients.filter((patient) => patient.status === 'admitted')
  const pendingDischarge = activePatients.filter((patient) => patient.status === 'discharge-pending')
  const censusPatients = activePatients.filter((patient) => patient.status !== 'discharged')
  const chartDocuments = Object.fromEntries(Object.entries(documents).map(([id, records]) => [id, records.filter((doc) => !doc.archived)]))
  const reviewItems = buildReviewItems(activePatients, chartDocuments, meds, labs)
  const pendingFields = Object.values(chartDocuments).flat().reduce((count, doc) => count + doc.fields.filter((field) => field.flagged).length, 0)
  const medicationFlags = activePatients.reduce((count, patient) => count + (meds[patient.id] || []).filter((med) => med.flag).length, 0)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const nextAppointments = activePatients.flatMap((patient) => (appointments[patient.id] || [])
    .filter((appointment) => appointment.status === 'upcoming')
    .map((appointment) => ({ ...appointment, patient, parsedDate: parseDate(appointment.date) })))
    .filter((appointment) => !appointment.parsedDate || appointment.parsedDate >= today)
    .sort((a, b) => (a.parsedDate?.getTime() ?? Number.MAX_SAFE_INTEGER) - (b.parsedDate?.getTime() ?? Number.MAX_SAFE_INTEGER))
  const allActivity = Object.entries(audit).flatMap(([patientId, entries]) => {
    const patient = activePatients.find((item) => item.id === patientId)
    return patient ? entries.map((entry, index) => ({ ...entry, patient, id: `${patientId}-${index}` })) : []
  }).sort((a, b) => activityAge(a.when) - activityAge(b.when))
  const now = new Date()
  const greeting = now.getHours() < 12 ? 'Good morning' : now.getHours() < 17 ? 'Good afternoon' : 'Good evening'
  const todayLabel = new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(now)
  const visibleReviewItems = reviewItems.slice(0, 5)
  const visibleAppointments = nextAppointments.slice(0, 5)
  const visibleActivity = allActivity.slice(0, 5)

  return (
    <div className="clinical-dashboard">
      <section className="dashboard-welcome">
        <div>
          <div className="dashboard-eyebrow">Care operations</div>
          <h1>{greeting}, care team</h1>
          <p>{todayLabel} <span className="dashboard-welcome-separator">·</span> Your service overview for today.</p>
        </div>
        <div className="dashboard-welcome-actions">
          <span className="dashboard-demo-chip"><span /> Demo environment</span>
          <button className="btn btn-primary" onClick={() => onNavigate('workqueue')}><IcFileCheck width={15} height={15} /> Review work queue</button>
        </div>
      </section>

      <section className="dashboard-metrics" aria-label="Clinical operations metrics">
        <button className="card dashboard-metric" onClick={() => onNavigate('patients')}>
          <span className="dashboard-metric-icon teal"><IcUsers width={17} height={17} /></span>
          <span className="dashboard-metric-label">Inpatient census</span>
          <strong>{censusPatients.length}</strong>
          <small>{admitted.length} admitted · {pendingDischarge.length} discharge pending</small>
        </button>
        <button className="card dashboard-metric" onClick={() => onOpenPatient(pendingDischarge[0]?.id, 'discharge')} disabled={!pendingDischarge.length}>
          <span className="dashboard-metric-icon amber"><IcFileCheck width={17} height={17} /></span>
          <span className="dashboard-metric-label">Discharge pending</span>
          <strong>{pendingDischarge.length}</strong>
          <small>Patients awaiting workflow review</small>
        </button>
        <button className="card dashboard-metric" onClick={() => onNavigate('workqueue')}>
          <span className="dashboard-metric-icon amber"><IcDoc width={17} height={17} /></span>
          <span className="dashboard-metric-label">Fields flagged</span>
          <strong>{pendingFields}</strong>
          <small>Require chart verification</small>
        </button>
        <button className="card dashboard-metric" onClick={() => onNavigate('workqueue')}>
          <span className="dashboard-metric-icon red"><IcPill width={17} height={17} /></span>
          <span className="dashboard-metric-label">Medication flags</span>
          <strong>{medicationFlags}</strong>
          <small>Review in patient context</small>
        </button>
      </section>

      <section className="dashboard-main-grid">
        <div className="card dashboard-panel">
          <div className="dashboard-panel-heading">
            <div><div className="dashboard-panel-kicker">Needs attention</div><h2>Clinical review items</h2></div>
            <button className="text-action" onClick={() => onNavigate('workqueue')}>View work queue <span>→</span></button>
          </div>
          {visibleReviewItems.length ? (
            <div className="dashboard-review-list">
              {visibleReviewItems.map((item) => {
                const Icon = item.kind === 'medication' ? IcPill : item.kind === 'lab' ? IcActivity : item.kind === 'document' ? IcDoc : IcFileCheck
                return (
                  <button className="dashboard-review-row" key={item.id} onClick={() => onOpenPatient(item.patient.id, item.tab)}>
                    <span className={`dashboard-review-icon ${item.kind}`}><Icon width={16} height={16} /></span>
                    <span className="dashboard-review-copy">
                      <span className="dashboard-review-title">{item.label}<span className="dashboard-review-patient">{item.patient.name} · {item.patient.ward}</span></span>
                      <span className="dashboard-review-detail"><strong>{item.title}</strong> · {item.detail}</span>
                    </span>
                    <span className="dashboard-row-arrow" aria-hidden="true">→</span>
                  </button>
                )
              })}
            </div>
          ) : (
            <div className="dashboard-empty"><IcFileCheck width={20} height={20} /><strong>No review items in the current records</strong><span>New chart review items appear when records have flags or pending workflows.</span></div>
          )}
          {reviewItems.length > visibleReviewItems.length && <button className="dashboard-more-link" onClick={() => onNavigate('workqueue')}>+ {reviewItems.length - visibleReviewItems.length} more items in work queue</button>}
          <p className="dashboard-safety-note"><IcAlert width={13} height={13} /> Items are workflow prompts, not clinical determinations. Verify against the source record.</p>
        </div>

        <div className="card dashboard-panel">
          <div className="dashboard-panel-heading">
            <div><div className="dashboard-panel-kicker">Coming up</div><h2>Appointments</h2></div>
            <button className="text-action" onClick={() => onNavigate('patients')}>Patient roster <span>→</span></button>
          </div>
          {nextAppointments.length ? (
            <div className="dashboard-appointment-list">
              {visibleAppointments.map((appointment, index) => (
                <button className="dashboard-appointment-row" key={`${appointment.patient.id}-${appointment.date}-${index}`} onClick={() => onOpenPatient(appointment.patient.id, 'appointments')}>
                  <span className="dashboard-date-tile"><strong>{appointment.parsedDate ? new Intl.DateTimeFormat(undefined, { day: '2-digit' }).format(appointment.parsedDate) : '—'}</strong><small>{appointment.parsedDate ? new Intl.DateTimeFormat(undefined, { month: 'short' }).format(appointment.parsedDate) : 'Date'}</small></span>
                  <span className="dashboard-appointment-copy"><strong>{appointment.type}</strong><span>{appointment.patient.name} · {appointment.patient.ward}</span><small>{appointment.time || 'Time not set'}</small></span>
                  <span className="dashboard-row-arrow" aria-hidden="true">→</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="dashboard-empty"><IcClock width={20} height={20} /><strong>No upcoming appointments</strong><span>Scheduled visits for active charts will appear here.</span></div>
          )}
          {nextAppointments.length > 5 && (
            <button className="dashboard-more-link" onClick={() => setShowAppointments(true)}>
              View all {nextAppointments.length} appointments <span aria-hidden="true">→</span>
            </button>
          )}
        </div>
      </section>

      <section className="dashboard-lower-grid">
        <div className="card dashboard-panel">
          <div className="dashboard-panel-heading">
            <div><div className="dashboard-panel-kicker">Care team overview</div><h2>Patient census</h2></div>
            <button className="text-action" onClick={() => onNavigate('patients')}>All patients <span>→</span></button>
          </div>
          {censusPatients.length ? (
            <div className="dashboard-census-list">
              {censusPatients.slice(0, 5).map((patient) => (
                <button className="dashboard-census-row" key={patient.id} onClick={() => onOpenPatient(patient.id)}>
                  <span className="dashboard-patient-avatar">{patient.name.split(' ').map((part) => part[0]).join('').slice(0, 2)}</span>
                  <span className="dashboard-census-name"><strong>{patient.name}</strong><small>{patient.mrn} · {patient.ward}</small></span>
                  <span className={`dashboard-status ${patient.status}`}>{STATUS_LABELS[patient.status] || patient.status}</span>
                  <span className="dashboard-census-vitals">{vitals[patient.id]?.recorded ? `Vitals ${vitals[patient.id].recorded}` : 'No vitals'}</span>
                  <span className="dashboard-row-arrow" aria-hidden="true">→</span>
                </button>
              ))}
            </div>
          ) : <div className="dashboard-empty"><strong>No active patient charts</strong></div>}
        </div>

        <div className="card dashboard-panel">
          <div className="dashboard-panel-heading">
            <div><div className="dashboard-panel-kicker">Audit trail</div><h2>Recent chart activity</h2></div>
            {allActivity.length > 5 && <button className="text-action" onClick={() => setShowActivity(true)}>View all <span>→</span></button>}
          </div>
          {allActivity.length ? (
            <div className="dashboard-activity-list">
              {visibleActivity.map((entry) => (
                <button className="dashboard-activity-row" key={entry.id} onClick={() => onOpenPatient(entry.patient.id, 'audit')}>
                  <span className="dashboard-activity-dot" />
                  <span><strong>{entry.who}</strong> {entry.action}<small>{entry.patient.name} · {entry.when}</small></span>
                </button>
              ))}
            </div>
          ) : <div className="dashboard-empty"><IcClock width={20} height={20} /><strong>No chart activity recorded</strong></div>}
        </div>
      </section>

      <footer className="dashboard-footer">
        <span>Snapshot generated from the current browser demo data.</span>
        {canAccess('documents:create') && <button className="text-action" onClick={() => onNavigate('upload')}>Upload a document <span>→</span></button>}
      </footer>

      {showAppointments && (
        <Modal title={`Upcoming appointments · ${nextAppointments.length}`} onClose={() => setShowAppointments(false)} wide>
          <div className="dashboard-appointment-list dashboard-modal-list">
            {nextAppointments.map((appointment, index) => (
              <button
                className="dashboard-appointment-row"
                key={`${appointment.patient.id}-${appointment.date}-${index}`}
                onClick={() => { setShowAppointments(false); onOpenPatient(appointment.patient.id, 'appointments') }}
              >
                <span className="dashboard-date-tile"><strong>{appointment.parsedDate ? new Intl.DateTimeFormat(undefined, { day: '2-digit' }).format(appointment.parsedDate) : '—'}</strong><small>{appointment.parsedDate ? new Intl.DateTimeFormat(undefined, { month: 'short' }).format(appointment.parsedDate) : 'Date'}</small></span>
                <span className="dashboard-appointment-copy"><strong>{appointment.type}</strong><span>{appointment.patient.name} · {appointment.patient.ward}</span><small>{appointment.time || 'Time not set'}</small></span>
                <span className="dashboard-row-arrow" aria-hidden="true">→</span>
              </button>
            ))}
          </div>
        </Modal>
      )}

      {showActivity && (
        <Modal title={`Recent chart activity · ${allActivity.length}`} onClose={() => setShowActivity(false)} wide>
          <div className="dashboard-activity-list dashboard-modal-list">
            {allActivity.map((entry) => (
              <button
                className="dashboard-activity-row"
                key={entry.id}
                onClick={() => { setShowActivity(false); onOpenPatient(entry.patient.id, 'audit') }}
              >
                <span className="dashboard-activity-dot" />
                <span><strong>{entry.who}</strong> {entry.action}<small>{entry.patient.name} · {entry.when}</small></span>
              </button>
            ))}
          </div>
        </Modal>
      )}
    </div>
  )
}
