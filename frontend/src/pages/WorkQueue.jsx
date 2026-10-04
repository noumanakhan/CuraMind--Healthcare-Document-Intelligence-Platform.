import { useMemo, useState } from 'react'
import { IcActivity, IcAlert, IcFileCheck, IcPill } from '../components/icons.jsx'
import { useClinical } from '../context/PatientContext.jsx'

const FILTERS = [
  { id: 'all', label: 'All items' },
  { id: 'safety', label: 'Safety review' },
  { id: 'documents', label: 'Documents' },
  { id: 'discharge', label: 'Discharge' },
  { id: 'labs', label: 'Lab results' },
]

function createWorkItems({ patients, documents, meds, labs }) {
  const items = []

  patients.forEach((patient) => {
    const patientDocs = documents[patient.id] || []
    const patientMeds = meds[patient.id] || []
    const patientLabs = labs[patient.id] || []

    patientMeds.filter((med) => med.flag).forEach((med, index) => {
      items.push({
        id: `med-${patient.id}-${index}`,
        category: 'safety',
        priority: 'high',
        priorityLabel: 'Safety review',
        title: `Review medication flag · ${med.name}`,
        summary: med.note || 'This medication is marked for clinician review in the chart.',
        source: 'Medication list',
        patient,
        tab: 'meds',
        icon: IcPill,
      })
    })

    patientDocs.forEach((doc) => {
      const flagged = doc.fields.filter((field) => field.flagged)
      if (flagged.length) {
        items.push({
          id: `doc-${doc.id}`,
          category: 'documents',
          priority: 'review',
          priorityLabel: 'Needs review',
          title: `Verify extracted fields · ${doc.name}`,
          summary: `${flagged.length} field${flagged.length === 1 ? '' : 's'} flagged for clinician verification: ${flagged.map((field) => field.label).join(', ')}.`,
          source: `${doc.type} · ${doc.date}`,
          patient,
          tab: 'documents',
          icon: IcFileCheck,
        })
      }
    })

    if (patient.status === 'discharge-pending' || patient.status === 'discharge_pending') {
      items.push({
        id: `discharge-${patient.id}`,
        category: 'discharge',
        priority: 'routine',
        priorityLabel: 'Pending sign-off',
        title: 'Complete discharge workflow',
        summary: 'The chart is marked discharge pending. Review the discharge summary and complete the appropriate sign-off.',
        source: 'Patient status',
        patient,
        tab: 'discharge',
        icon: IcFileCheck,
      })
    }

    patientLabs.forEach((series) => {
      const latest = series.points[series.points.length - 1]
      if (!latest || (latest.value >= series.range[0] && latest.value <= series.range[1])) return
      items.push({
        id: `lab-${patient.id}-${series.test}`,
        category: 'labs',
        priority: 'review',
        priorityLabel: 'Out of range',
        title: `Review lab result · ${series.test}`,
        summary: `Latest result ${latest.value} ${series.unit}; reference range ${series.range[0]}–${series.range[1]} ${series.unit}. Review in clinical context.`,
        source: `Latest recorded · ${latest.date}`,
        patient,
        tab: 'labs',
        icon: IcActivity,
      })
    })
  })

  const rank = { high: 0, review: 1, routine: 2 }
  return items.sort((a, b) => rank[a.priority] - rank[b.priority] || a.patient.name.localeCompare(b.patient.name))
}

export default function WorkQueue({ onOpenPatient }) {
  const { patients, documents, meds, labs } = useClinical()
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')
  const items = useMemo(() => createWorkItems({
    patients: patients.filter((patient) => !patient.archived),
    documents: Object.fromEntries(Object.entries(documents).map(([id, records]) => [id, records.filter((doc) => !doc.archived)])),
    meds,
    labs,
  }), [patients, documents, meds, labs])
  const visibleItems = items.filter((item) => {
    const matchesFilter = filter === 'all' || item.category === filter
    const searchText = `${item.title} ${item.summary} ${item.patient.name} ${item.patient.mrn}`.toLowerCase()
    return matchesFilter && searchText.includes(query.trim().toLowerCase())
  })
  const safetyCount = items.filter((item) => item.category === 'safety').length
  const documentCount = items.filter((item) => item.category === 'documents').length
  const highPriorityCount = items.filter((item) => item.priority === 'high').length

  return (
    <div className="work-queue">
      <section className="queue-intro">
        <div>
          <div className="queue-eyebrow">Clinical operations</div>
          <h2>Work queue</h2>
          <p>Review chart items that need clinician attention. Items are generated from the current patient records.</p>
        </div>
        <div className="queue-scope"><IcAlert width={15} height={15} /> Clinician review required</div>
      </section>

      <div className="queue-stats">
        <div className="card queue-stat"><span>Open items</span><strong>{items.length}</strong><small>Across {patients.length} patient charts</small></div>
        <div className="card queue-stat"><span>Safety flags</span><strong className={highPriorityCount ? 'queue-number-alert' : ''}>{highPriorityCount}</strong><small>Medication records flagged</small></div>
        <div className="card queue-stat"><span>Documents to verify</span><strong>{documentCount}</strong><small>{safetyCount} medication flag{safetyCount === 1 ? '' : 's'} included above</small></div>
      </div>

      <div className="queue-toolbar">
        <div className="toolbar queue-filters" role="tablist" aria-label="Filter work queue">
          {FILTERS.map((item) => (
            <button key={item.id} className={'chip-filter' + (filter === item.id ? ' active' : '')} onClick={() => setFilter(item.id)}>
              {item.label}
              {item.id === 'all' && <span className="queue-filter-count">{items.length}</span>}
            </button>
          ))}
        </div>
        <label className="queue-search">
          <span className="sr-only">Search work queue</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search patient or item…" />
        </label>
      </div>

      <div className="queue-list">
        {visibleItems.map((item) => {
          const Icon = item.icon
          return (
            <article className="queue-item card" key={item.id}>
              <div className={`queue-item-icon ${item.priority}`}><Icon width={18} height={18} /></div>
              <div className="queue-item-content">
                <div className="queue-item-heading">
                  <h3>{item.title}</h3>
                  <span className={`queue-priority ${item.priority}`}>{item.priorityLabel}</span>
                </div>
                <p>{item.summary}</p>
                <div className="queue-item-meta"><strong>{item.patient.name}</strong><span>{item.patient.mrn}</span><span>{item.patient.ward}</span><span>{item.source}</span></div>
              </div>
              <button className="btn btn-ghost queue-action" onClick={() => onOpenPatient(item.patient.id, item.tab)}>
                Review chart <span aria-hidden="true">→</span>
              </button>
            </article>
          )
        })}
        {visibleItems.length === 0 && (
          <div className="card queue-empty">
            <div className="queue-empty-icon"><IcFileCheck width={21} height={21} /></div>
            <h3>{items.length ? 'No matching work items' : 'You’re all caught up'}</h3>
            <p>{items.length ? 'Try a different filter or search term.' : 'New chart review items will appear here when records are flagged.'}</p>
          </div>
        )}
      </div>
      <p className="queue-disclaimer">Work queue items are workflow prompts only. Confirm findings against the source record and use clinical judgment.</p>
    </div>
  )
}
