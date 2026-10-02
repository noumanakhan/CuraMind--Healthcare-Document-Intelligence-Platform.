import { useState } from 'react'
import { useClinical } from '../context/PatientContext.jsx'
import { IcDoc } from '../components/icons.jsx'
import Badge from '../components/Badge.jsx'
import Modal from '../components/Modal.jsx'

const FILTERS = ['all', 'processed', 'processing', 'needs-review']

function DocumentMetadataForm({ document, onSubmit, onCancel }) {
  const [name, setName] = useState(document.name)
  const [type, setType] = useState(document.type)

  const submit = (event) => {
    event.preventDefault()
    if (name.trim()) onSubmit({ name: name.trim(), type: type.trim() || document.type })
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <label className="form-field form-field-wide">
        <span>Document name</span>
        <input value={name} onChange={(event) => setName(event.target.value)} required />
      </label>
      <label className="form-field form-field-wide">
        <span>Document type</span>
        <input value={type} onChange={(event) => setType(event.target.value)} required />
      </label>
      <p className="form-note">Metadata edits are audited. The source clinical file is not modified.</p>
      <div className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
        <button type="submit" className="btn btn-primary">Save changes</button>
      </div>
    </form>
  )
}

export default function Documents() {
  const { vaultDocuments, updateVaultDocument, archiveVaultDocument, restoreVaultDocument, canAccess } = useClinical()
  const [filter, setFilter] = useState('all')
  const [editingDocument, setEditingDocument] = useState(null)
  const [editMode, setEditMode] = useState(false)
  const [archivingDocument, setArchivingDocument] = useState(null)
  const canEdit = canAccess('documents:edit')
  const canArchive = canAccess('documents:archive')
  const rows = (vaultDocuments || []).filter((doc) => filter === 'archived'
    ? doc.archived
    : !doc.archived && (filter === 'all' || doc.status === filter))

  return (
    <div>
      <div className="toolbar">
        {[...FILTERS, ...(canArchive ? ['archived'] : [])].map((f) => (
          <button
            key={f}
            className={'chip-filter' + (filter === f ? ' active' : '')}
            onClick={() => setFilter(f)}
          >
            {f === 'all' ? 'All' : f === 'archived' ? 'Archived' : f === 'needs-review' ? 'Needs review' : f[0].toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="doc-table">
        <table>
          <thead>
            <tr>
              {['Document', 'Type', 'Patient', 'Date', 'Size', 'Status', 'Actions'].map((h, i) => (
                <th key={i}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id}>
                <td>
                  <div className="doc-name">
                    <div className="doc-icon">
                      <IcDoc width={15} height={15} />
                    </div>
                    {d.name}
                  </div>
                </td>
                <td className="muted">{d.type}</td>
                <td className="muted">{d.patient}</td>
                <td className="muted">{d.date}</td>
                <td className="muted">{d.size}</td>
                <td>{d.archived ? <span className="badge needs-review">Archived</span> : <Badge status={d.status} />}</td>
                <td>
                  <div className="table-actions">
                    <button className="btn btn-ghost" onClick={() => { setEditingDocument(d); setEditMode(false) }}>Details</button>
                    {canEdit && !d.archived && <button className="btn btn-ghost" onClick={() => { setEditingDocument(d); setEditMode(true) }}>Edit</button>}
                    {canArchive && (d.archived
                      ? <button className="btn btn-ghost" onClick={() => restoreVaultDocument(d.id)}>Restore</button>
                      : <button className="btn btn-danger-ghost" onClick={() => setArchivingDocument(d)}>Archive</button>)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editingDocument && (
        <Modal title={`${editMode ? 'Edit metadata' : 'Document details'} · ${editingDocument.name}`} onClose={() => setEditingDocument(null)}>
          {editMode && canEdit && !editingDocument.archived ? (
            <DocumentMetadataForm
              document={editingDocument}
              onSubmit={(changes) => { updateVaultDocument(editingDocument.id, changes); setEditingDocument(null) }}
              onCancel={() => setEditingDocument(null)}
            />
          ) : (
            <div>
              <p className="muted" style={{ marginTop: 0 }}>Document metadata</p>
              <dl className="document-details">
                <dt>Patient</dt><dd>{editingDocument.patient}</dd>
                <dt>Type</dt><dd>{editingDocument.type}</dd>
                <dt>Date</dt><dd>{editingDocument.date}</dd>
                <dt>Status</dt><dd>{editingDocument.archived ? 'Archived — retained' : editingDocument.status}</dd>
              </dl>
              <div className="form-actions"><button className="btn btn-ghost" onClick={() => setEditingDocument(null)}>Close</button></div>
            </div>
          )}
        </Modal>
      )}

      {archivingDocument && (
        <Modal title="Archive document?" onClose={() => setArchivingDocument(null)}>
          <p className="muted" style={{ marginTop: 0, lineHeight: 1.6 }}>
            “{archivingDocument.name}” will be removed from the active vault but retained in the archived records and audit trail. Follow your organization’s retention policy; this is not permanent deletion.
          </p>
          <div className="form-actions">
            <button className="btn btn-ghost" onClick={() => setArchivingDocument(null)}>Cancel</button>
            <button className="btn btn-danger" onClick={() => { archiveVaultDocument(archivingDocument.id); setArchivingDocument(null) }}>Archive document</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
