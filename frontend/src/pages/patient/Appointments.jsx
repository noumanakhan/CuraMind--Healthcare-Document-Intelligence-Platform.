import { useState } from 'react'
import Modal from '../../components/Modal.jsx'

function ScheduleForm({ onSubmit, onCancel }) {
  const [form, setForm] = useState({ type: '', with: '', date: '', time: '' })
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = (e) => {
    e.preventDefault()
    if (!form.type.trim() || !form.date.trim()) {
      setError('Appointment type and date are required.')
      return
    }
    onSubmit(form)
  }

  return (
    <form onSubmit={submit} className="form-grid">
      {error && <div className="form-error">{error}</div>}
      <label className="form-field form-field-wide">
        <span>Appointment type *</span>
        <input value={form.type} onChange={set('type')} placeholder="e.g. Follow-up · Cardiology" />
      </label>
      <label className="form-field form-field-wide">
        <span>With</span>
        <input value={form.with} onChange={set('with')} placeholder="e.g. Dr. Faisal S." />
      </label>
      <label className="form-field">
        <span>Date *</span>
        <input value={form.date} onChange={set('date')} placeholder="e.g. 05 Oct 2026" />
      </label>
      <label className="form-field">
        <span>Time</span>
        <input value={form.time} onChange={set('time')} placeholder="e.g. 10:00 AM" />
      </label>
      <div className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary">
          Schedule
        </button>
      </div>
    </form>
  )
}

export default function Appointments({ appointments, onSchedule, canManage = true }) {
  const [showForm, setShowForm] = useState(false)

  const handleSubmit = (form) => {
    onSchedule(form)
    setShowForm(false)
  }

  const upcoming = appointments.filter((a) => a.status === 'upcoming')
  const past = appointments.filter((a) => a.status !== 'upcoming')

  const Row = ({ a }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid var(--line)' }}>
      <div>
        <div style={{ fontWeight: 600, fontSize: 13.5 }}>{a.type}</div>
        <div className="muted" style={{ fontSize: 12.5 }}>{a.with}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 13 }}>{a.date}</div>
        <div className="muted" style={{ fontSize: 12 }}>{a.time}</div>
      </div>
      <span className={'badge ' + (a.status === 'upcoming' ? 'processing' : 'processed')} style={{ marginLeft: 14 }}>
        {a.status === 'upcoming' ? 'Upcoming' : 'Completed'}
      </span>
    </div>
  )

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 14 }}>
        {canManage && <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Schedule appointment</button>}
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="card-title">Upcoming</div>
        {upcoming.length === 0 && <div className="muted" style={{ fontSize: 13 }}>No upcoming appointments.</div>}
        {upcoming.map((a, i) => (
          <Row key={i} a={a} />
        ))}
      </div>

      <div className="card">
        <div className="card-title">Past</div>
        {past.length === 0 && <div className="muted" style={{ fontSize: 13 }}>No past appointments recorded.</div>}
        {past.map((a, i) => (
          <Row key={i} a={a} />
        ))}
      </div>

      {showForm && (
        <Modal title="Schedule appointment" onClose={() => setShowForm(false)}>
          <ScheduleForm onSubmit={handleSubmit} onCancel={() => setShowForm(false)} />
        </Modal>
      )}
    </div>
  )
}
