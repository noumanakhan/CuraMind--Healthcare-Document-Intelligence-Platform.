function InfoRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid var(--line)', fontSize: 13 }}>
      <span className="muted">{label}</span>
      <span style={{ fontWeight: 600, textAlign: 'right' }}>{value}</span>
    </div>
  )
}

export default function Overview({ patient, vitals, immunizations, encounters = [], problems = [], allergyRecords = [] }) {
  const currentEncounter = encounters.find((encounter) => encounter.status !== 'completed')
  const activeProblems = problems.filter((problem) => problem.status === 'active')
  const activeAllergies = allergyRecords.filter((allergy) => allergy.status === 'active')

  return (
    <div className="row2">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div className="card">
          <div className="card-title">Contact &amp; demographics</div>
          <InfoRow label="Date of birth" value={patient.dob} />
          <InfoRow label="Sex" value={patient.sex} />
          <InfoRow label="Blood type" value={patient.bloodType} />
          <InfoRow label="Phone" value={patient.phone} />
          <InfoRow label="Email" value={patient.email} />
          <InfoRow label="Address" value={patient.address} />
          <InfoRow label="Emergency contact" value={patient.emergencyContact} />
        </div>

        <div className="card">
          <div className="card-title">Insurance &amp; billing</div>
          <InfoRow label="Provider" value={patient.insuranceProvider} />
          <InfoRow label="Policy number" value={patient.policyNumber} />
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div className="card">
          <div className="card-title">Care team</div>
          <InfoRow label="Attending" value={patient.attending} />
          <InfoRow label="Ward / setting" value={patient.ward} />
        </div>

          <div className="card overview-highlight-card">
            <div className="card-title">Current encounter</div>
            {currentEncounter ? (
              <>
                <div className="overview-highlight-title">{currentEncounter.reason || currentEncounter.type}</div>
                <div className="overview-highlight-meta">{currentEncounter.type} · {currentEncounter.date}</div>
                <div className="overview-highlight-meta">{currentEncounter.location || patient.ward}</div>
                <span className={`record-state ${currentEncounter.status}`}>{currentEncounter.status.replace(/-/g, ' ')}</span>
              </>
            ) : <div className="muted" style={{ fontSize: 12 }}>No active encounter on file.</div>}
          </div>

          <div className="card overview-highlight-card">
            <div className="card-title">Active problems &amp; allergies</div>
            <div className="overview-summary-group">
              <span className="overview-summary-label">Problems</span>
              {activeProblems.length ? activeProblems.slice(0, 3).map((problem) => <span className="overview-summary-item" key={problem.id}>{problem.name}</span>) : <span className="muted overview-no-data">No active problems listed</span>}
            </div>
            <div className="overview-summary-group">
              <span className="overview-summary-label">Allergies</span>
              {activeAllergies.length ? activeAllergies.map((allergy) => <span className="overview-summary-item allergy" key={allergy.id}>{allergy.substance}<small>{allergy.verification}</small></span>) : <span className="muted overview-no-data">No allergy records on file</span>}
            </div>
            <div className="overview-summary-disclaimer">Reported status should be verified in the source chart.</div>
          </div>

        <div className="card">
          <div className="card-title">Latest vitals</div>
          {vitals ? (
            <>
              <InfoRow label="Blood pressure" value={vitals.bp} />
              <InfoRow label="Heart rate" value={vitals.hr} />
              <InfoRow label="Temperature" value={vitals.temp} />
              <InfoRow label="SpO2" value={vitals.spo2} />
              <InfoRow label="Weight" value={vitals.weight} />
              <div className="muted" style={{ fontSize: 11.5, marginTop: 8 }}>Recorded {vitals.recorded}</div>
            </>
          ) : (
            <div className="muted" style={{ fontSize: 13 }}>No vitals recorded yet.</div>
          )}
        </div>

        <div className="card">
          <div className="card-title">Immunization history</div>
          {immunizations.length === 0 && <div className="muted" style={{ fontSize: 13 }}>No immunizations on file.</div>}
          {immunizations.map((im, i) => (
            <InfoRow key={i} label={im.vaccine} value={im.date} />
          ))}
        </div>
      </div>
    </div>
  )
}
