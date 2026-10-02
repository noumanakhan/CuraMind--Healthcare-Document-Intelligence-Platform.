import { useState } from 'react'

const DOC_TYPES = {
  'Lab report': ['Test name', 'Result value', 'Reference range', 'Collection date'],
  'Clinical note': ['Assessment', 'Plan', 'Suggested ICD-10'],
  'Intake form': ['Reason for visit', 'Known allergies', 'Emergency contact'],
  'Referral letter': ['Referring physician', 'Reason for referral', 'Requested specialty'],
  'Insurance claim': ['Policy number', 'Claim amount', 'Prior-authorization code'],
  Prescription: ['Medication', 'Dosage', 'Prescriber'],
}

function fakeConfidence() {
  // Skew toward high confidence but leave room for flagged fields, like a real extractor would
  const r = Math.random()
  return r > 0.75 ? 0.6 + Math.random() * 0.25 : 0.85 + Math.random() * 0.14
}

export default function AddDocumentForm({ onSubmit, onCancel }) {
  const [name, setName] = useState('')
  const [type, setType] = useState('Lab report')
  const [stage, setStage] = useState('form') // form -> processing -> done
  const [error, setError] = useState('')

  const submit = (e) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Enter a file name so the document can be identified in the chart.')
      return
    }
    setStage('processing')
    setTimeout(() => {
      const fields = DOC_TYPES[type].map((label) => {
        const confidence = fakeConfidence()
        return { label, value: '(pending clinician review)', confidence, flagged: confidence < 0.8 }
      })
      setStage('done')
      setTimeout(() => onSubmit({ name: name.trim(), type, fields }), 500)
    }, 1200)
  }

  if (stage !== 'form') {
    return (
      <div className="upload-sim">
        <div className="pipeline" style={{ marginTop: 0 }}>
          {['Upload', 'OCR', 'Extract fields', 'PHI scan', 'Index'].map((s, i) => (
            <div key={s} className={'pstep ' + (stage === 'done' ? 'done' : i < 2 ? 'done' : i === 2 ? 'active' : '')}>
              <div className="circ">{stage === 'done' || i < 2 ? '✓' : i + 1}</div>
              <div className="plabel">{s}</div>
            </div>
          ))}
        </div>
        <p className="muted" style={{ textAlign: 'center', fontSize: 13, marginTop: 10 }}>
          {stage === 'done' ? 'Extraction complete — fields added to the chart for review.' : 'Running the extraction pipeline…'}
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="form-grid">
      {error && <div className="form-error">{error}</div>}
      <label className="form-field form-field-wide">
        <span>File name</span>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. lab-report-28sep.pdf" />
      </label>
      <label className="form-field form-field-wide">
        <span>Document type</span>
        <select value={type} onChange={(e) => setType(e.target.value)}>
          {Object.keys(DOC_TYPES).map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </label>
      <p className="muted" style={{ fontSize: 12.5, margin: '0 0 4px' }}>
        This demo simulates the extraction pipeline rather than parsing a real file — in production this
        step would run OCR and schema-constrained extraction against the uploaded document.
      </p>
      <div className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary">
          Run extraction
        </button>
      </div>
    </form>
  )
}
