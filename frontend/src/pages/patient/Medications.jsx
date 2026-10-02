import { IcPill, IcAlert } from '../../components/icons.jsx'

const FLAG_LABEL = { interaction: 'Allergy conflict', dosage: 'Dosage check' }

export default function Medications({ meds }) {
  if (!meds.length) {
    return <div className="card muted">No active medications on file for this patient.</div>
  }
  return (
    <div className="card" style={{ padding: 0 }}>
      {meds.map((m, i) => (
        <div key={i} className="row" style={{ display: 'flex', gap: 14, padding: '16px 20px', borderBottom: i < meds.length - 1 ? '1px solid var(--line)' : 'none' }}>
          <div className="doc-icon" style={{ flexShrink: 0 }}>
            <IcPill width={15} height={15} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="label" style={{ fontWeight: 600, fontSize: 13.5 }}>{m.name}</span>
              <span className="muted" style={{ fontSize: 12.5 }}>{m.dose}</span>
              {m.flag && (
                <span className="badge failed">
                  <IcAlert width={11} height={11} /> {FLAG_LABEL[m.flag]}
                </span>
              )}
            </div>
            {m.note && <div className="desc" style={{ fontSize: 12.5, color: 'var(--red)', marginTop: 4 }}>{m.note}</div>}
          </div>
          {m.flag && (
            <button className="btn btn-ghost" style={{ padding: '6px 11px', fontSize: 12.5, alignSelf: 'center' }}>
              Mark reviewed
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
