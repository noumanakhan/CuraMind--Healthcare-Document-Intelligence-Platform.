import { IcFileCheck, IcCheck } from '../../components/icons.jsx'

export default function DischargeSummary({ draft, onSign, canReview = true }) {
  if (!draft) {
    return (
      <div className="card muted">
        No discharge draft has been generated for this patient yet. A draft is created automatically once
        discharge is initiated, using the patient's clinical notes, medication orders, and nursing notes as
        source material — every sentence carries a citation back to its source document for clinician review.
      </div>
    )
  }

  const signed = draft.status === 'signed'

  return (
    <div>
      <div className="card" style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="card-title" style={{ margin: 0 }}>AI-drafted discharge summary</div>
          <span className={'badge ' + (signed ? 'processed' : 'processing')}>{signed ? 'Signed' : 'Pending clinician review'}</span>
        </div>
        <p className="muted" style={{ fontSize: 12.5, marginTop: 8 }}>
          Every statement below is generated from source documents and must be reviewed and signed by a clinician
          before it becomes part of the patient record. Nothing here is finalized automatically.
        </p>
      </div>

      <div className="card">
        {draft.paragraphs.map((p, i) => (
          <div key={i} style={{ marginBottom: i < draft.paragraphs.length - 1 ? 16 : 0 }}>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{p.text}</p>
            <span className="cite" style={{ marginTop: 8 }}>
              📄 {p.cite}
            </span>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
        {canReview && <button className="btn btn-primary" onClick={onSign} disabled={signed}>
          <IcFileCheck width={15} height={15} />
          {signed ? 'Approved & signed' : 'Approve & sign'}
        </button>}
        {signed && (
          <span className="stat-delta" style={{ alignSelf: 'center' }}>
            <IcCheck width={13} height={13} /> Logged to audit trail
          </span>
        )}
      </div>
    </div>
  )
}
