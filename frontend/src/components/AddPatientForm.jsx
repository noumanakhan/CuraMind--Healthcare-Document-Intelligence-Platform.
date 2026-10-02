import { useState } from 'react'

const WARDS = ['Internal Medicine', 'Cardiology', 'ICU', 'Outpatient', 'Pediatrics', 'Surgery']
const BLOOD_TYPES = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'Unknown']

export default function AddPatientForm({ onSubmit, onCancel, initialValues = null }) {
  const isEditing = Boolean(initialValues)
  const [form, setForm] = useState(() => ({
    name: '',
    dob: '',
    sex: 'Female',
    bloodType: 'Unknown',
    ward: 'Internal Medicine',
    attending: '',
    phone: '',
    email: '',
    address: '',
    emergencyContact: '',
    insuranceProvider: '',
    policyNumber: '',
    reason: '',
    ...initialValues,
    allergies: Array.isArray(initialValues?.allergies) ? initialValues.allergies.join(', ') : initialValues?.allergies || '',
  }))
  const [error, setError] = useState('')

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.dob.trim()) {
      setError('Patient name and date of birth are required.')
      return
    }
    onSubmit(form)
  }

  return (
    <form onSubmit={submit} className="form-grid">
      {error && <div className="form-error">{error}</div>}

      <div className="form-section-label">Identity</div>
      <label className="form-field">
        <span>Full name *</span>
        <input value={form.name} onChange={set('name')} placeholder="e.g. Sara Malik" />
      </label>
      <label className="form-field">
        <span>Date of birth *</span>
        <input value={form.dob} onChange={set('dob')} placeholder="e.g. 12 May 1990" />
      </label>
      <label className="form-field">
        <span>Sex</span>
        <select value={form.sex} onChange={set('sex')}>
          <option>Female</option>
          <option>Male</option>
          <option>Other</option>
        </select>
      </label>
      <label className="form-field">
        <span>Blood type</span>
        <select value={form.bloodType} onChange={set('bloodType')}>
          {BLOOD_TYPES.map((b) => (
            <option key={b}>{b}</option>
          ))}
        </select>
      </label>

      <div className="form-section-label">Contact</div>
      <label className="form-field">
        <span>Phone</span>
        <input value={form.phone} onChange={set('phone')} placeholder="e.g. 0300-1234567" />
      </label>
      <label className="form-field">
        <span>Email</span>
        <input value={form.email} onChange={set('email')} placeholder="e.g. name@example.com" />
      </label>
      <label className="form-field form-field-wide">
        <span>Address</span>
        <input value={form.address} onChange={set('address')} placeholder="Street, area, city" />
      </label>
      <label className="form-field form-field-wide">
        <span>Emergency contact</span>
        <input value={form.emergencyContact} onChange={set('emergencyContact')} placeholder="Name (relation) · phone number" />
      </label>

      <div className="form-section-label">Care &amp; coverage</div>
      <label className="form-field">
        <span>Ward / setting</span>
        <select value={form.ward} onChange={set('ward')}>
          {WARDS.map((w) => (
            <option key={w}>{w}</option>
          ))}
        </select>
      </label>
      <label className="form-field">
        <span>Attending physician</span>
        <input value={form.attending} onChange={set('attending')} placeholder="e.g. Dr. Faisal S." />
      </label>
      <label className="form-field">
        <span>Insurance provider</span>
        <input value={form.insuranceProvider} onChange={set('insuranceProvider')} placeholder="e.g. State Life Health, or Self-pay" />
      </label>
      <label className="form-field">
        <span>Policy number</span>
        <input value={form.policyNumber} onChange={set('policyNumber')} placeholder="e.g. SLH-44219-A" />
      </label>

      {!isEditing && (
        <>
          <div className="form-section-label">Clinical</div>
          <label className="form-field form-field-wide">
            <span>Known allergies (comma-separated)</span>
            <input value={form.allergies} onChange={set('allergies')} placeholder="e.g. Penicillin, Latex — leave blank if none" />
          </label>
          <label className="form-field form-field-wide">
            <span>Reason for admission / visit</span>
            <textarea value={form.reason} onChange={set('reason')} rows={3} placeholder="Brief note — this stays in the audit trail" />
          </label>
        </>
      )}

      <div className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary">
          {isEditing ? 'Save demographic changes' : 'Create patient chart'}
        </button>
      </div>
    </form>
  )
}
