import { useState } from 'react'
import { PATIENT_STATUS_LABEL } from '../data/patientMock.js'
import { IcUsers } from '../components/icons.jsx'
import { useClinical } from '../context/PatientContext.jsx'
import Modal from '../components/Modal.jsx'
import AddPatientForm from '../components/AddPatientForm.jsx'

const FILTERS = ['all', 'admitted', 'discharge-pending', 'discharged']

export default function Patients({ onOpenPatient }) {
  const { patients, addPatient, updatePatient, archivePatient, restorePatient, canAccess } = useClinical()
  const [filter, setFilter] = useState('all')
  const [showAdd, setShowAdd] = useState(false)
  const [editPatientId, setEditPatientId] = useState(null)
  const [archivePatientId, setArchivePatientId] = useState(null)
  const canCreate = canAccess('patients:create')
  const canEdit = canAccess('patients:edit')
  const canArchive = canAccess('patients:archive')
  const selectedPatient = patients.find((patient) => patient.id === editPatientId)
  const patientToArchive = patients.find((patient) => patient.id === archivePatientId)
  const rows = patients.filter((p) => filter === 'archived'
    ? p.archived
    : !p.archived && (filter === 'all' || p.status === filter))

  const handleAdd = (form) => {
    const id = addPatient(form)
    setShowAdd(false)
    if (id) onOpenPatient(id)
  }

  const handleEdit = (form) => {
    updatePatient(editPatientId, form)
    setEditPatientId(null)
  }

  return (
    <div>
      <div className="toolbar" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 10 }}>
          {[...FILTERS, ...(canArchive ? ['archived'] : [])].map((f) => (
            <button key={f} className={'chip-filter' + (filter === f ? ' active' : '')} onClick={() => setFilter(f)}>
              {f === 'all' ? 'All' : f === 'archived' ? 'Archived' : PATIENT_STATUS_LABEL[f]}
            </button>
          ))}
        </div>
        {canCreate && <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add patient</button>}
      </div>

      <div className="doc-table">
        <table>
          <thead>
            <tr>
              {['Patient', 'MRN', 'Ward', 'Allergies', 'Status', 'Updated', 'Actions'].map((h, i) => (
                <th key={i}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="muted" style={{ textAlign: 'center', padding: 30 }}>
                  No patients match this filter.
                </td>
              </tr>
            )}
            {rows.map((p) => (
              <tr key={p.id}>
                <td>
                  <div className="doc-name">
                    <div className="doc-icon">
                      <IcUsers width={15} height={15} />
                    </div>
                    {p.name}
                  </div>
                </td>
                <td className="muted">{p.mrn}</td>
                <td className="muted">{p.ward}</td>
                <td>
                  {p.allergies.includes('None recorded') ? (
                    <span className="muted">None recorded</span>
                  ) : (
                    p.allergies.map((a) => (
                      <span key={a} className="badge failed" style={{ marginRight: 4 }}>
                        {a}
                      </span>
                    ))
                  )}
                </td>
                <td>
                  <span className={'badge ' + (p.archived ? 'needs-review' : p.status === 'discharged' ? 'processed' : 'processing')}>
                    {p.archived ? 'Archived' : PATIENT_STATUS_LABEL[p.status]}
                  </span>
                </td>
                <td className="muted">{p.lastUpdated}</td>
                <td>
                  <div className="table-actions">
                    <button className="btn btn-ghost" onClick={() => onOpenPatient(p.id)}>Open chart</button>
                    {canEdit && !p.archived && <button className="btn btn-ghost" onClick={() => setEditPatientId(p.id)}>Edit</button>}
                    {canArchive && (p.archived
                      ? <button className="btn btn-ghost" onClick={() => restorePatient(p.id)}>Restore</button>
                      : <button className="btn btn-danger-ghost" onClick={() => setArchivePatientId(p.id)}>Archive</button>)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <Modal title="Add new patient" onClose={() => setShowAdd(false)} wide>
          <AddPatientForm onSubmit={handleAdd} onCancel={() => setShowAdd(false)} />
        </Modal>
      )}

      {selectedPatient && (
        <Modal title={`Edit demographics · ${selectedPatient.name}`} onClose={() => setEditPatientId(null)} wide>
          <AddPatientForm initialValues={selectedPatient} onSubmit={handleEdit} onCancel={() => setEditPatientId(null)} />
        </Modal>
      )}

      {patientToArchive && (
        <Modal title="Archive patient chart?" onClose={() => setArchivePatientId(null)}>
          <p className="muted" style={{ marginTop: 0, lineHeight: 1.6 }}>
            {patientToArchive.name} will be hidden from the active roster. The record is retained and the action is written to the audit trail; this does not permanently delete clinical data.
          </p>
          <div className="form-actions">
            <button className="btn btn-ghost" onClick={() => setArchivePatientId(null)}>Cancel</button>
            <button className="btn btn-danger" onClick={() => { archivePatient(patientToArchive.id); setArchivePatientId(null) }}>Archive record</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
