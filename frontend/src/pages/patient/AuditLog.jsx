import { IcShield, IcClock } from '../../components/icons.jsx'

export default function AuditLog({ entries }) {
  if (!entries.length) {
    return <div className="card muted">No audit activity recorded for this patient yet.</div>
  }
  return (
    <div className="card">
      {entries.map((e, i) => (
        <div key={i} className="activity">
          <IcShield width={14} height={14} style={{ color: 'var(--text-muted)', marginTop: 2, flexShrink: 0 }} />
          <div>
            <div>
              <strong>{e.who}</strong> — {e.action}
            </div>
            <div className="activity-meta">
              <IcClock width={11} height={11} style={{ verticalAlign: '-1px', marginRight: 3 }} />
              {e.when}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
