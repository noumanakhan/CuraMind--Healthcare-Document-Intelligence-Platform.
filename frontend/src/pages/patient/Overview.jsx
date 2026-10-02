function InfoRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid var(--line)', fontSize: 13 }}>
      <span className="muted">{label}</span>
      <span style={{ fontWeight: 600, textAlign: 'right' }}>{value}</span>
    </div>
  )
}

export default function Overview({ patient, vitals, immunizations }) {
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
