import { useState } from 'react'
import { IcAlert, IcCheck, IcDoc } from '../../components/icons.jsx'
import Confidence from '../../components/Confidence.jsx'
import Modal from '../../components/Modal.jsx'
import AddDocumentForm from '../../components/AddDocumentForm.jsx'

export default function DocumentReview({ documents, onAddDocument, onConfirmField, canUpload = true, canReview = true }) {
  const [showAdd, setShowAdd] = useState(false)

  const handleAdd = (meta) => {
    onAddDocument(meta)
    setShowAdd(false)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 14 }}>
        {canUpload && <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add document</button>}
      </div>

      {documents.length === 0 && <div className="card muted">No documents on file for this patient yet. Add one to run extraction.</div>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {documents.map((doc) => (
          <div key={doc.id} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div className="doc-name">
                <div className="doc-icon">
                  <IcDoc width={15} height={15} />
                </div>
                {doc.name}
                <span className="muted" style={{ fontWeight: 500, fontSize: 12.5 }}>· {doc.type}</span>
              </div>
              <span className={'badge ' + (doc.status === 'needs-review' ? 'processing' : 'processed')}>
                {doc.status === 'needs-review' ? 'Needs review' : 'Processed'}
              </span>
            </div>

            <div className="review-fields">
              {doc.fields.map((f) => {
                const isConfirmed = !f.flagged
                return (
                  <div key={f.label} className={'review-row' + (f.flagged ? ' flagged' : '')}>
                    <div className="review-label">
                      {f.flagged && <IcAlert width={13} height={13} style={{ color: 'var(--amber)', flexShrink: 0 }} />}
                      {f.label}
                    </div>
                    <div className="review-value">{f.value}</div>
                    <Confidence score={f.confidence} />
                    {canReview && <button
                      className={'btn btn-ghost review-confirm' + (isConfirmed ? ' confirmed' : '')}
                      onClick={() => onConfirmField(doc.id, f.label)}
                      disabled={isConfirmed}
                    >
                      {isConfirmed ? (
                        <>
                          <IcCheck width={13} height={13} /> Confirmed
                        </>
                      ) : (
                        'Confirm'
                      )}
                    </button>}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {showAdd && (
        <Modal title="Add clinical document" onClose={() => setShowAdd(false)}>
          <AddDocumentForm onSubmit={handleAdd} onCancel={() => setShowAdd(false)} />
        </Modal>
      )}
    </div>
  )
}
