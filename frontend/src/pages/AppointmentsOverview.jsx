import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { IcCalendar, IcClock, IcUsers } from '../components/icons.jsx'
import { useClinical } from '../context/PatientContext.jsx'
import Modal from '../components/Modal.jsx'

const FILTERS = [
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'completed', label: 'Past' },
  { id: 'all', label: 'All appointments' },
]

function parseDate(value) {
  const match = /^\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s*$/.exec(value || '')
  if (!match) return null
  const month = new Date(`${match[2]} 1, ${match[3]}`).getMonth()
  return Number.isNaN(month) ? null : new Date(Number(match[3]), month, Number(match[1]))
}

function formatDate(value) {
  const parsed = parseDate(value)
  return parsed
    ? new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }).format(parsed)
    : value
}

export default function AppointmentsOverview() {
  const { patients, appointments, scheduleAppointment, canAccess } = useClinical()
  const navigate = useNavigate()
  const [filter, setFilter] = useState('upcoming')
  const [query, setQuery] = useState('')
  const [showSchedule, setShowSchedule] = useState(false)
  const activePatients = patients.filter((patient) => !patient.archived)
  const [appointmentForm, setAppointmentForm] = useState({ patientId: activePatients[0]?.id || '', type: '', with: '', date: '', time: '' })
  const canManage = canAccess('appointments:manage')

  const allAppointments = useMemo(() => patients
    .filter((patient) => !patient.archived)
    .flatMap((patient) => (appointments[patient.id] || []).map((appointment, index) => ({
      ...appointment,
      patient,
      id: `${patient.id}-${appointment.date}-${appointment.time}-${index}`,
      parsedDate: parseDate(appointment.date),
    })))
    .sort((a, b) => (a.parsedDate?.getTime() ?? Number.MAX_SAFE_INTEGER) - (b.parsedDate?.getTime() ?? Number.MAX_SAFE_INTEGER)), [patients, appointments])

  const visibleAppointments = allAppointments.filter((appointment) => {
    const matchesFilter = filter === 'all' || appointment.status === filter
    const searchable = `${appointment.type} ${appointment.with} ${appointment.patient.name} ${appointment.patient.mrn} ${appointment.patient.ward}`.toLowerCase()
    return matchesFilter && searchable.includes(query.trim().toLowerCase())
  })
  const upcomingCount = allAppointments.filter((appointment) => appointment.status === 'upcoming').length
  const completedCount = allAppointments.filter((appointment) => appointment.status === 'completed').length

  const updateAppointmentForm = (field) => (event) => {
    setAppointmentForm((current) => ({ ...current, [field]: event.target.value }))
  }

  const submitAppointment = (event) => {
    event.preventDefault()
    if (!appointmentForm.patientId || !appointmentForm.type.trim() || !appointmentForm.date) return
    const [year, month, day] = appointmentForm.date.split('-').map(Number)
    const formattedDate = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(year, month - 1, day))
    const saved = scheduleAppointment(appointmentForm.patientId, {
      type: appointmentForm.type.trim(),
      with: appointmentForm.with.trim() || 'Provider not assigned',
      date: formattedDate,
      time: appointmentForm.time ? new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' }).format(new Date(`2000-01-01T${appointmentForm.time}`)) : '',
    })
    if (!saved) return
    setAppointmentForm({ patientId: activePatients[0]?.id || '', type: '', with: '', date: '', time: '' })
    setFilter('upcoming')
    setQuery('')
    setShowSchedule(false)
  }

  return (
    <div className="appointments-overview">
      <section className="appointments-intro">
        <div>
          <div className="dashboard-eyebrow">Care coordination</div>
          <h1>Appointments</h1>
          <p>Quickly review scheduled and completed visits across patient charts.</p>
        </div>
        <div className="appointments-intro-actions">
          <div className="appointments-intro-icon"><IcCalendar width={21} height={21} /></div>
          {canManage && <button className="btn btn-primary" onClick={() => setShowSchedule(true)} disabled={!activePatients.length}><IcCalendar width={15} height={15} /> Schedule appointment</button>}
        </div>
      </section>

      <section className="appointments-summary" aria-label="Appointment summary">
        <div className="card appointment-summary-card">
          <span className="appointment-summary-icon upcoming"><IcCalendar width={17} height={17} /></span>
          <span className="appointment-summary-label">Upcoming</span>
          <strong>{upcomingCount}</strong>
          <small>Scheduled visits</small>
        </div>
        <div className="card appointment-summary-card">
          <span className="appointment-summary-icon completed"><IcClock width={17} height={17} /></span>
          <span className="appointment-summary-label">Past visits</span>
          <strong>{completedCount}</strong>
          <small>Completed appointments</small>
        </div>
        <div className="card appointment-summary-card">
          <span className="appointment-summary-icon patients"><IcUsers width={17} height={17} /></span>
          <span className="appointment-summary-label">Patients scheduled</span>
          <strong>{new Set(allAppointments.filter((appointment) => appointment.status === 'upcoming').map((appointment) => appointment.patient.id)).size}</strong>
          <small>With upcoming appointments</small>
        </div>
      </section>

      <section className="card appointments-list-card">
        <div className="appointments-list-heading">
          <div>
            <div className="dashboard-panel-kicker">Schedule</div>
            <h2>{filter === 'completed' ? 'Past appointments' : filter === 'all' ? 'All appointments' : 'Upcoming appointments'}</h2>
          </div>
          <label className="appointments-search">
            <span className="sr-only">Search appointments</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search patient or visit…" />
          </label>
        </div>

        <div className="toolbar appointments-filters" role="tablist" aria-label="Filter appointments">
          {FILTERS.map((item) => (
            <button key={item.id} className={'chip-filter' + (filter === item.id ? ' active' : '')} onClick={() => setFilter(item.id)}>
              {item.label}
              {item.id === 'upcoming' && <span className="queue-filter-count">{upcomingCount}</span>}
              {item.id === 'completed' && <span className="queue-filter-count">{completedCount}</span>}
            </button>
          ))}
        </div>

        {visibleAppointments.length ? (
          <div className="appointments-table-wrap">
            <table className="appointments-table">
              <thead>
                <tr><th>Date &amp; time</th><th>Patient</th><th>Visit</th><th>Provider</th><th>Status</th><th /></tr>
              </thead>
              <tbody>
                {visibleAppointments.map((appointment) => (
                  <tr key={appointment.id}>
                    <td><strong>{formatDate(appointment.date)}</strong><small>{appointment.time || 'Time not set'}</small></td>
                    <td><strong>{appointment.patient.name}</strong><small>{appointment.patient.mrn} · {appointment.patient.ward}</small></td>
                    <td>{appointment.type}</td>
                    <td>{appointment.with || 'Provider not assigned'}</td>
                    <td><span className={`appointment-status ${appointment.status}`}>{appointment.status === 'upcoming' ? 'Upcoming' : 'Completed'}</span></td>
                    <td><button className="btn btn-ghost appointments-open-chart" onClick={() => navigate(`/patients/${encodeURIComponent(appointment.patient.id)}/appointments`)}>Open chart</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="appointments-empty"><IcCalendar width={22} height={22} /><strong>No appointments found</strong><span>Try another filter or search term.</span></div>
        )}
      </section>

      {showSchedule && (
        <Modal title="Schedule appointment" onClose={() => setShowSchedule(false)}>
          <form className="form-grid appointment-schedule-form" onSubmit={submitAppointment}>
            <label className="form-field form-field-wide">
              <span>Patient *</span>
              <select value={appointmentForm.patientId} onChange={updateAppointmentForm('patientId')} required>
                {activePatients.map((patient) => <option key={patient.id} value={patient.id}>{patient.name} · {patient.mrn}</option>)}
              </select>
            </label>
            <label className="form-field form-field-wide">
              <span>Appointment type *</span>
              <input value={appointmentForm.type} onChange={updateAppointmentForm('type')} placeholder="e.g. Cardiology follow-up" required />
            </label>
            <label className="form-field form-field-wide">
              <span>Provider</span>
              <input value={appointmentForm.with} onChange={updateAppointmentForm('with')} placeholder="e.g. Dr. Faisal S." />
            </label>
            <label className="form-field">
              <span>Date *</span>
              <input type="date" value={appointmentForm.date} onChange={updateAppointmentForm('date')} required />
            </label>
            <label className="form-field">
              <span>Time</span>
              <input type="time" value={appointmentForm.time} onChange={updateAppointmentForm('time')} />
            </label>
            <div className="form-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowSchedule(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={!activePatients.length}>Schedule appointment</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
