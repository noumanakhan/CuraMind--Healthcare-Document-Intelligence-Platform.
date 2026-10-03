import { IcActivity, IcClock, IcUsers } from '../../components/icons.jsx'

const STATUS_LABELS = {
  'in-progress': 'In progress',
  'discharge-pending': 'Discharge pending',
  completed: 'Completed',
}

function EncounterCard({ encounter }) {
  const isOpen = encounter.status !== 'completed'
  return (
    <article className="encounter-card">
      <div className={`encounter-marker ${isOpen ? 'open' : 'closed'}`}><IcActivity width={15} height={15} /></div>
      <div className="encounter-card-main">
        <div className="encounter-card-heading">
          <div><span className="encounter-type">{encounter.type}</span><h3>{encounter.reason || 'Visit reason not recorded'}</h3></div>
          <span className={`encounter-status ${encounter.status}`}>{STATUS_LABELS[encounter.status] || encounter.status}</span>
        </div>
        <div className="encounter-meta">
          <span><IcClock width={13} height={13} /> {encounter.date}</span>
          <span><IcUsers width={13} height={13} /> {encounter.attending || 'Clinician not assigned'}</span>
          <span>{encounter.location || 'Location not recorded'}</span>
        </div>
      </div>
    </article>
  )
}

export default function Encounters({ encounters = [] }) {
  const sortedEncounters = [...encounters].reverse()
  const activeEncounters = sortedEncounters.filter((encounter) => encounter.status !== 'completed')
  const pastEncounters = sortedEncounters.filter((encounter) => encounter.status === 'completed')

  return (
    <div className="patient-record-section">
      <section className="card record-section-card">
        <div className="record-section-heading">
          <div><div className="dashboard-panel-kicker">Patient history</div><h2>Encounters</h2></div>
          <span className="record-count">{encounters.length} total</span>
        </div>
        {activeEncounters.length ? (
          <div className="encounter-list">
            {activeEncounters.map((encounter) => <EncounterCard key={encounter.id} encounter={encounter} />)}
          </div>
        ) : <div className="record-empty">No active encounters on file.</div>}
      </section>

      <section className="card record-section-card">
        <div className="record-section-heading">
          <div><div className="dashboard-panel-kicker">Completed care</div><h2>Previous visits</h2></div>
          <span className="record-count">{pastEncounters.length} visits</span>
        </div>
        {pastEncounters.length ? (
          <div className="encounter-list">
            {pastEncounters.map((encounter) => <EncounterCard key={encounter.id} encounter={encounter} />)}
          </div>
        ) : <div className="record-empty">Completed visits will appear here.</div>}
      </section>
    </div>
  )
}
