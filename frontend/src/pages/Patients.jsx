import { useEffect, useState } from 'react'
import { PATIENT_STATUS_LABEL } from '../data/patientMock.js'
import { IcUsers } from '../components/icons.jsx'
import { useClinical } from '../context/PatientContext.jsx'
import Modal from '../components/Modal.jsx'
import AddPatientForm from '../components/AddPatientForm.jsx'

const FILTERS = ['all', 'admitted', 'discharge_pending', 'discharged']

export default function Patients({ onOpenPatient }) {
  const {
    patients,
    totalPatients,
    loading,
    error,
    loadPatients,
    addPatient,
    updatePatient,
    archivePatient,
    restorePatient,
    canAccess,
  } = useClinical()

  const [filter, setFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 20

  const [showAdd, setShowAdd] = useState(false)
  const [editPatientId, setEditPatientId] = useState(null)
  const [archivePatientId, setArchivePatientId] = useState(null)

  const canCreate = canAccess('patients:create')
  const canEdit = canAccess('patients:edit')
  const canArchive = canAccess('patients:archive')

  useEffect(() => {
    loadPatients({
      status: filter === 'all' ? undefined : filter,
      search: searchTerm.trim() || undefined,
      skip: page * pageSize,
      limit: pageSize,
    })
  }, [filter, searchTerm, page, loadPatients])

  const selectedPatient = patients.find((patient) => patient.id === editPatientId)
  const patientToArchive = patients.find((patient) => patient.id === archivePatientId)

  const handleAdd = async (form) => {
    try {
      const id = await addPatient(form)
      setShowAdd(false)
      if (id) onOpenPatient(id)
    } catch (e) {
      alert(e.message || 'Failed to create patient')
    }
  }

  const handleEdit = async (form) => {
    try {
      await updatePatient(editPatientId, form)
      setEditPatientId(null)
    } catch (e) {
      alert(e.message || 'Failed to update patient')
    }
  }

  return (
    <div>
      <div className="toolbar" style={{ justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          {FILTERS.map((f) => (
            <button
              key={f}
              className={'chip-filter' + (filter === f ? ' active' : '')}
              onClick={() => {
                setFilter(f)
                setPage(0)
              }}
            >
              {f === 'all' ? 'All' : PATIENT_STATUS_LABEL[f] || f.replace('_', ' ')}
            </button>
          ))}
          <input
            type="search"
            placeholder="Search by name or MRN…"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setPage(0)
            }}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: 'var(--card-bg, #1a1e24)',
              color: 'inherit',
              fontSize: 13,
            }}
          />
        </div>
        {canCreate && (
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
            + Add patient
          </button>
        )}
      </div>

      {error && (
        <div className="card" style={{ color: 'var(--red, #e53e3e)', marginBottom: 16 }}>
          {error}
        </div>
      )}

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
            {loading && patients.length === 0 && (
              <tr>
                <td colSpan={7} className="muted" style={{ textAlign: 'center', padding: 30 }}>
                  Loading patient records from workspace…
                </td>
              </tr>
            )}
            {!loading && patients.length === 0 && (
              <tr>
                <td colSpan={7} className="muted" style={{ textAlign: 'center', padding: 30 }}>
                  No patients found in this workspace.
                </td>
              </tr>
            )}
            {patients.map((p) => (
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
                <td className="muted">{p.ward || '—'}</td>
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
                  <span
                    className={
                      'badge ' +
                      (p.is_deleted
                        ? 'needs-review'
                        : p.status === 'discharged'
                        ? 'processed'
                        : 'processing')
                    }
                  >
                    {p.is_deleted ? 'Archived' : PATIENT_STATUS_LABEL[p.status] || p.status}
                  </span>
                </td>
                <td className="muted">{p.lastUpdated}</td>
                <td>
                  <div className="table-actions">
                    <button className="btn btn-ghost" onClick={() => onOpenPatient(p.id)}>
                      Open chart
                    </button>
                    {canEdit && !p.is_deleted && (
                      <button className="btn btn-ghost" onClick={() => setEditPatientId(p.id)}>
                        Edit
                      </button>
                    )}
                    {canArchive &&
                      (p.is_deleted ? (
                        <button className="btn btn-ghost" onClick={() => restorePatient(p.id)}>
                          Restore
                        </button>
                      ) : (
                        <button
                          className="btn btn-danger-ghost"
                          onClick={() => setArchivePatientId(p.id)}
                        >
                          Archive
                        </button>
                      ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPatients > pageSize && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 14, alignItems: 'center' }}>
          <button
            className="btn btn-ghost"
            disabled={page === 0 || loading}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Previous
          </button>
          <span className="muted" style={{ fontSize: 13 }}>
            Page {page + 1} of {Math.ceil(totalPatients / pageSize)}
          </span>
          <button
            className="btn btn-ghost"
            disabled={(page + 1) * pageSize >= totalPatients || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}

      {showAdd && (
        <Modal title="Add new patient" onClose={() => setShowAdd(false)} wide>
          <AddPatientForm onSubmit={handleAdd} onCancel={() => setShowAdd(false)} />
        </Modal>
      )}

      {selectedPatient && (
        <Modal
          title={`Edit demographics · ${selectedPatient.name}`}
          onClose={() => setEditPatientId(null)}
          wide
        >
          <AddPatientForm
            initialValues={selectedPatient}
            onSubmit={handleEdit}
            onCancel={() => setEditPatientId(null)}
          />
        </Modal>
      )}

      {patientToArchive && (
        <Modal title="Archive patient chart?" onClose={() => setArchivePatientId(null)}>
          <p className="muted" style={{ marginTop: 0, lineHeight: 1.6 }}>
            {patientToArchive.name} will be hidden from the active roster. The record is retained and
            the action is written to the audit trail; this does not permanently delete clinical data.
          </p>
          <div className="form-actions">
            <button className="btn btn-ghost" onClick={() => setArchivePatientId(null)}>
              Cancel
            </button>
            <button
              className="btn btn-danger"
              onClick={() => {
                archivePatient(patientToArchive.id)
                setArchivePatientId(null)
              }}
            >
              Archive record
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
