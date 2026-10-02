import { useState } from 'react'
import { IcUpload } from '../components/icons.jsx'
import { useClinical } from '../context/PatientContext.jsx'
import AddDocumentForm from '../components/AddDocumentForm.jsx'

export default function Upload() {
  const { patients, addDocument, canAccess } = useClinical()
  const activePatients = patients.filter((patient) => !patient.archived)
  const [patientId, setPatientId] = useState(activePatients[0]?.id || '')
  const [justAdded, setJustAdded] = useState(null)

  if (!canAccess('documents:create')) {
    return <div className="card access-denied"><h2>Upload access required</h2><p>Your current role can view records but cannot add documents. Ask a workspace administrator to review your access.</p></div>
  }

  const handleSubmit = (meta) => {
    addDocument(patientId, meta)
    setJustAdded(meta.name)
    setTimeout(() => setJustAdded(null), 4000)
  }

  return (
    <div>
      <div className="dropzone">
        <div className="icon">
          <IcUpload width={44} height={44} />
        </div>
        <h3>Drag files in, or browse</h3>
        <p>PDF, DOCX, and scanned images up to 25MB. Every file is attached to a patient chart and run through the extraction pipeline automatically.</p>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="card-title">Attach to patient</div>
        <select
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          style={{ padding: '10px 12px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--paper)', color: 'var(--text)', fontSize: 13.5, width: '100%', maxWidth: 320 }}
        >
          {activePatients.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} · {p.mrn}
            </option>
          ))}
        </select>
      </div>

      <div className="card">
        <div className="card-title">Upload &amp; run extraction</div>
        {justAdded ? (
          <p style={{ color: 'var(--teal)', fontSize: 13.5 }}>✓ {justAdded} processed and added to the patient's chart.</p>
        ) : (
          <AddDocumentForm onSubmit={handleSubmit} onCancel={() => {}} />
        )}
      </div>
    </div>
  )
}
