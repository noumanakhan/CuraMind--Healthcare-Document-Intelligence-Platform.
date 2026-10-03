import { IcActivity, IcAlert, IcCheck, IcDoc } from '../../components/icons.jsx'

function formatLabel(value) {
  return value ? value.replace(/-/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Not recorded'
}

export default function ProblemsAllergies({ problems = [], allergyRecords = [] }) {
  const knownAllergies = allergyRecords.filter((item) => item.status === 'active')
  const reportedNone = allergyRecords.some((item) => item.status === 'none-reported')

  return (
    <div className="patient-record-section">
      <section className="card record-section-card">
        <div className="record-section-heading">
          <div><div className="dashboard-panel-kicker">Longitudinal chart</div><h2>Problems</h2></div>
          <span className="record-count">{problems.length} listed</span>
        </div>
        {problems.length ? (
          <div className="clinical-record-list">
            {problems.map((problem) => (
              <article className="clinical-record-row" key={problem.id}>
                <span className={`clinical-record-icon ${problem.status === 'active' ? 'attention' : ''}`}><IcActivity width={16} height={16} /></span>
                <div className="clinical-record-copy">
                  <div className="clinical-record-title"><strong>{problem.name}</strong><span className={`record-state ${problem.status}`}>{formatLabel(problem.status)}</span></div>
                  <p>{problem.note || 'No additional note.'}</p>
                  <small><IcDoc width={12} height={12} /> {problem.source || 'Source not recorded'} · {problem.recorded || 'Date not recorded'}</small>
                </div>
              </article>
            ))}
          </div>
        ) : <div className="record-empty">No problems are currently listed.</div>}
      </section>

      <section className="card record-section-card">
        <div className="record-section-heading">
          <div><div className="dashboard-panel-kicker">Safety information</div><h2>Allergies &amp; intolerances</h2></div>
          <span className={`record-count ${knownAllergies.length ? 'alert' : ''}`}>{knownAllergies.length ? `${knownAllergies.length} recorded` : 'Review status'}</span>
        </div>
        {knownAllergies.length ? (
          <div className="clinical-record-list">
            {knownAllergies.map((allergy) => (
              <article className="clinical-record-row allergy-record-row" key={allergy.id}>
                <span className="clinical-record-icon attention"><IcAlert width={16} height={16} /></span>
                <div className="clinical-record-copy">
                  <div className="clinical-record-title"><strong>{allergy.substance}</strong><span className="record-state needs-review">{formatLabel(allergy.verification)}</span></div>
                  <div className="allergy-detail-grid"><span>Reaction <strong>{allergy.reaction || 'Not documented'}</strong></span><span>Severity <strong>{allergy.severity || 'Unknown'}</strong></span></div>
                  <small><IcDoc width={12} height={12} /> Source: {allergy.source || 'Not recorded'}</small>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="allergy-none-recorded">
            <IcCheck width={16} height={16} />
            <div><strong>{reportedNone ? 'No known allergies reported' : 'No allergy records on file'}</strong><span>{reportedNone ? 'This is a reported status and may require confirmation.' : 'Absence of a record does not confirm absence of allergies.'}</span></div>
          </div>
        )}
      </section>
      <p className="record-safety-note"><IcAlert width={13} height={13} /> Review allergy details against the source chart. “Not recorded” does not mean “none.”</p>
    </div>
  )
}
