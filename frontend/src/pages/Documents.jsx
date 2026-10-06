import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useClinical } from '../context/PatientContext.jsx'
import { IcDoc, IcUpload, IcAlert, IcCheck } from '../components/icons.jsx'
import Badge from '../components/Badge.jsx'
import Confidence from '../components/Confidence.jsx'
import Modal from '../components/Modal.jsx'

const FILTERS = ['all', 'processed', 'processing', 'needs-review']
const DOC_TYPES = [
  'Lab report',
  'Clinical note',
  'Discharge summary',
  'Intake form',
  'Referral letter',
  'Insurance claim',
  'Imaging report',
  'Prescription / Medication order',
]

// Mock clinical text previews based on document type
function getDocumentPreviewText(doc) {
  const type = (doc.type || '').toLowerCase()
  if (type.includes('lab')) {
    return `CLINICAL LABORATORY REPORT
Facility: CuraMind Regional Diagnostic Center
Specimen: Venous Blood (EDTA) · Fasting: Yes
Collection Date: ${doc.date || 'Recent'}

TEST PANEL: COMPLETE BLOOD COUNT (CBC) & INFLAMMATORY MARKERS
----------------------------------------------------------------------
• White Blood Cells (WBC) : 13.4 x10^9/L   [Ref: 4.0 - 11.0]  HIGH (Flagged)
• Hemoglobin (Hb)         : 11.2 g/dL      [Ref: 12.0 - 16.0]  LOW
• Platelets               : 260 x10^9/L    [Ref: 150 - 450]   NORMAL
• C-Reactive Protein (CRP): 38.0 mg/L      [Ref: 0.0 - 5.0]   HIGH (Flagged)
• Neutrophils             : 78.4 %         [Ref: 40.0 - 75.0] HIGH

CLINICAL IMPRESSION:
Leukocytosis with significant left shift and elevated acute-phase reactant (CRP), suggesting evolving acute bacterial infection or active inflammatory response. Prescriber correlation recommended.`
  }
  if (type.includes('cardiology') || type.includes('consult') || type.includes('note')) {
    return `CLINICAL CONSULTATION & PROGRESS NOTE
Service: Cardiology / Internal Medicine
Attending: Dr. Faisal S. / Dr. N. Fatima
Encounter: Inpatient Specialty Review · Date: ${doc.date || 'Recent'}

SUBJECTIVE:
Patient reports persistent retrosternal chest pressure and epigastric discomfort radiating to left shoulder on moderate exertion (walking up stairs). Relieved with rest after 5-10 minutes. Denies syncope or orthopnea.

OBJECTIVE:
• BP: 138/84 mmHg | HR: 74 bpm regular | SpO2: 98% room air
• Cardiovascular: Regular S1/S2, no audible murmurs or gallops.
• ECG: Normal sinus rhythm, nonspecific T-wave flattening in inferolateral leads.

ASSESSMENT:
1. Stable Angina Pectoris (NYHA Class II) — ICD-10: I20.8
2. Essential Hypertension, moderate control.

PLAN & ORDERS:
• Continue Metoprolol Tartrate 50mg PO BID (renal clearance noted).
• Sublingual Nitroglycerin 0.4mg PRN for acute angina episodes.
• Outpatient exercise tolerance test / stress echocardiogram within 2 weeks.`
  }
  if (type.includes('discharge')) {
    return `DISCHARGE SUMMARY & CARE CONTINUITY PLAN
Patient: ${doc.patient || 'Patient'}
Date of Discharge: ${doc.date || 'Recent'}

FINAL DIAGNOSIS:
Primary: Functional Dyspepsia (K30), acute epigastric pain resolved.
Secondary: Gastroesophageal Reflux Disease without esophagitis.

HOSPITAL COURSE:
Admitted with acute severe epigastric discomfort. Negative for cardiac ischemia (serial troponins negative). Upper abdominal ultrasound showed normal gallbladder and biliary tree. Symptoms markedly improved following IV/oral proton pump inhibitor therapy.

DISCHARGE MEDICATIONS:
1. Omeprazole 20mg Delayed-Release Capsule — 1 capsule PO daily before breakfast for 30 days.
2. Paracetamol 500mg — 1-2 tablets PO every 6 hours PRN mild pain.

ALLERGIES & CONTRAINDICATIONS:
• Sulfa drugs (Urticaria/Nausea) · Latex (Contact dermatitis).

FOLLOW-UP INSTRUCTIONS:
Follow up with Gastroenterology (Dr. K. Farooq) in 2-3 weeks if symptoms recur.`
  }
  return `CLINICAL DOCUMENT RECORD: ${doc.name}
Patient: ${doc.patient || 'General Facility Chart'}
Classification: ${doc.type || 'Clinical Document'}
Archive Date: ${doc.date || 'Recent'} · Status: ${doc.status || 'Processed'}

RECORD SUMMARY:
This document has been ingested, OCR-processed, and fully indexed into the CuraMind Vector & Full-Text Store.
All extracted entities are linked to workspace patient records and available for instant semantic retrieval in Clinical Assistant.`
}

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

function UploadVaultModal({ patients, onSubmit, onCancel }) {
  const [file, setFile] = useState(null)
  const [name, setName] = useState('')
  const [type, setType] = useState('Clinical note')
  const [patientId, setPatientId] = useState(patients[0]?.id || '')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  const handleFileChange = (selectedFile) => {
    if (!selectedFile) return
    setFile(selectedFile)
    if (!name) {
      setName(selectedFile.name)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setUploading(true)
    const selectedPatient = patients.find(p => p.id === patientId)
    const sizeStr = file ? `${(file.size / 1024).toFixed(0)} KB` : '420 KB'
    
    onSubmit({
      name: name.trim(),
      type,
      patient: selectedPatient ? selectedPatient.name : 'General Facility Vault',
      patientId: patientId || null,
      size: sizeStr,
      status: 'processed',
    })
    setUploading(false)
  }

  return (
    <form className="form-grid" onSubmit={handleSubmit}>
      <div
        className="dropzone"
        style={{ padding: '24px 16px', marginBottom: '14px', cursor: 'pointer', textAlign: 'center' }}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          const f = e.dataTransfer?.files?.[0]
          if (f) handleFileChange(f)
        }}
      >
        <IcUpload width={32} height={32} />
        <h4 style={{ margin: '8px 0 4px 0' }}>{file ? file.name : 'Choose a file or drag here'}</h4>
        <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
          {file ? `${(file.size / 1024).toFixed(1)} KB · Ready to index` : 'PDF, DOCX, PNG, JPG up to 25MB'}
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.png,.jpg"
          style={{ display: 'none' }}
          onChange={(e) => handleFileChange(e.target.files[0])}
        />
      </div>

      <label className="form-field form-field-wide">
        <span>Document Title / File Name *</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. lab-report-cbc-25sep.pdf"
          required
        />
      </label>

      <label className="form-field form-field-wide">
        <span>Document Category / Type</span>
        <select value={type} onChange={(e) => setType(e.target.value)}>
          {DOC_TYPES.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </label>

      <label className="form-field form-field-wide">
        <span>Assign to Patient Chart</span>
        <select value={patientId} onChange={(e) => setPatientId(e.target.value)}>
          <option value="">General Facility Vault (Unassigned)</option>
          {patients.map(p => (
            <option key={p.id} value={p.id}>{p.name} · MRN {p.mrn}</option>
          ))}
        </select>
      </label>

      <p className="form-note">
        Files added to the vault are immediately indexed for RAG retrieval and hybrid semantic search.
      </p>

      <div className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={uploading}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={uploading || !name.trim()}>
          {uploading ? 'Adding…' : 'Add to Document Vault'}
        </button>
      </div>
    </form>
  )
}

export default function Documents() {
  const navigate = useNavigate()
  const {
    vaultDocuments,
    addVaultDocument,
    updateVaultDocument,
    archiveVaultDocument,
    restoreVaultDocument,
    patients,
    canAccess,
  } = useClinical()
  const [filter, setFilter] = useState('all')
  const [viewingDocument, setViewingDocument] = useState(null)
  const [editingDocument, setEditingDocument] = useState(null)
  const [archivingDocument, setArchivingDocument] = useState(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [activeViewTab, setActiveViewTab] = useState('content')

  const canEdit = canAccess('documents:edit')
  const canArchive = canAccess('documents:archive')
  const canUpload = canAccess('documents:create')

  const rows = (vaultDocuments || []).filter((doc) => filter === 'archived'
    ? doc.archived
    : !doc.archived && (filter === 'all' || doc.status === filter))

  const activePatients = (patients || []).filter(p => !p.archived)

  return (
    <div>
      <div className="toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
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
        {canUpload && (
          <button
            className="btn btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 14px', fontSize: '13px' }}
            onClick={() => setShowUploadModal(true)}
          >
            <IcUpload width={14} height={14} /> Upload to Vault
          </button>
        )}
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
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                  No documents found in vault. Click <strong>Upload to Vault</strong> to add clinical files.
                </td>
              </tr>
            ) : (
              rows.map((d) => (
                <tr key={d.id}>
                  <td>
                    <div
                      className="doc-name"
                      style={{ cursor: 'pointer' }}
                      onClick={() => { setViewingDocument(d); setActiveViewTab('content') }}
                      title="Click to open and read document"
                    >
                      <div className="doc-icon">
                        <IcDoc width={15} height={15} />
                      </div>
                      <span style={{ fontWeight: '600', color: 'var(--teal)' }}>{d.name}</span>
                    </div>
                  </td>
                  <td className="muted">{d.type}</td>
                  <td className="muted">{d.patient}</td>
                  <td className="muted">{d.date}</td>
                  <td className="muted">{d.size}</td>
                  <td>{d.archived ? <span className="badge needs-review">Archived</span> : <Badge status={d.status} />}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '3px 8px', fontSize: '12px' }}
                        onClick={() => { setViewingDocument(d); setActiveViewTab('content') }}
                      >
                        Open
                      </button>
                      {canEdit && !d.archived && (
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '3px 8px', fontSize: '12px' }}
                          onClick={() => setEditingDocument(d)}
                        >
                          Edit
                        </button>
                      )}
                      {canArchive && (d.archived
                        ? <button className="btn btn-ghost" style={{ padding: '3px 8px', fontSize: '12px' }} onClick={() => restoreVaultDocument(d.id)}>Restore</button>
                        : <button className="btn btn-danger-ghost" style={{ padding: '3px 8px', fontSize: '12px' }} onClick={() => setArchivingDocument(d)}>Archive</button>)}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── Document Viewer Modal ─────────────────────────────────────── */}
      {viewingDocument && (
        <Modal title={`📄 ${viewingDocument.name}`} onClose={() => setViewingDocument(null)} wide>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {/* Meta summary card */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--paper)', padding: '12px 16px', borderRadius: '10px', border: '1px solid var(--line)', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '12.5px' }}>
                <div><strong>Patient:</strong> {viewingDocument.patient}</div>
                <div><strong>Category:</strong> {viewingDocument.type}</div>
                <div><strong>Date:</strong> {viewingDocument.date}</div>
                <div><strong>Size:</strong> {viewingDocument.size}</div>
                <div><strong>Status:</strong> {viewingDocument.archived ? 'Archived' : viewingDocument.status}</div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-primary"
                  style={{ fontSize: '12px', padding: '5px 10px' }}
                  onClick={() => {
                    setViewingDocument(null)
                    navigate('/ask')
                  }}
                  title="Ask AI questions grounded in this document"
                >
                  🤖 Ask AI Assistant
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '12px', padding: '5px 10px' }}
                  onClick={() => {
                    setViewingDocument(null)
                    navigate('/compare')
                  }}
                  title="Compare this document with another record"
                >
                  ⚖️ Compare
                </button>
              </div>
            </div>

            {/* Viewer Tab Switcher */}
            <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--line)', paddingBottom: '8px' }}>
              <button
                className={`chip-filter ${activeViewTab === 'content' ? 'active' : ''}`}
                onClick={() => setActiveViewTab('content')}
              >
                Document Content &amp; Summary
              </button>
              <button
                className={`chip-filter ${activeViewTab === 'metadata' ? 'active' : ''}`}
                onClick={() => setActiveViewTab('metadata')}
              >
                Metadata &amp; Ingestion Info
              </button>
            </div>

            {/* Document Content Tab */}
            {activeViewTab === 'content' && (
              <div style={{
                background: 'var(--paper)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--line)',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                fontSize: '12px',
                lineHeight: '1.6',
                whiteSpace: 'pre-wrap',
                maxHeight: '420px',
                overflowY: 'auto',
                color: 'var(--text)',
              }}>
                {getDocumentPreviewText(viewingDocument)}
              </div>
            )}

            {/* Metadata Tab */}
            {activeViewTab === 'metadata' && (
              <div style={{ padding: '8px 0' }}>
                <dl className="document-details">
                  <dt>Document ID</dt><dd>{viewingDocument.id}</dd>
                  <dt>Patient Name</dt><dd>{viewingDocument.patient}</dd>
                  <dt>Document Classification</dt><dd>{viewingDocument.type}</dd>
                  <dt>File Size</dt><dd>{viewingDocument.size}</dd>
                  <dt>Creation Date</dt><dd>{viewingDocument.date}</dd>
                  <dt>Extraction Status</dt><dd>{viewingDocument.archived ? 'Archived (Retained in legal storage)' : viewingDocument.status}</dd>
                  <dt>RAG Index Status</dt><dd>Chunked &amp; Embedded (Hybrid Vector Search Ready)</dd>
                </dl>
              </div>
            )}

            <div className="form-actions" style={{ justifyContent: 'space-between' }}>
              <div>
                {canEdit && !viewingDocument.archived && (
                  <button
                    className="btn btn-ghost"
                    onClick={() => {
                      setEditingDocument(viewingDocument)
                      setViewingDocument(null)
                    }}
                  >
                    ✏️ Edit Metadata
                  </button>
                )}
              </div>
              <button className="btn btn-ghost" onClick={() => setViewingDocument(null)}>
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Upload Modal ─────────────────────────────────────────────── */}
      {showUploadModal && (
        <Modal title="Upload Clinical Document to Vault" onClose={() => setShowUploadModal(false)}>
          <UploadVaultModal
            patients={activePatients}
            onSubmit={async (docData) => {
              await addVaultDocument(docData)
              setShowUploadModal(false)
            }}
            onCancel={() => setShowUploadModal(false)}
          />
        </Modal>
      )}

      {/* ── Edit Metadata Modal ───────────────────────────────────────── */}
      {editingDocument && (
        <Modal title={`Edit Metadata · ${editingDocument.name}`} onClose={() => setEditingDocument(null)}>
          <DocumentMetadataForm
            document={editingDocument}
            onSubmit={(changes) => {
              updateVaultDocument(editingDocument.id, changes)
              setEditingDocument(null)
            }}
            onCancel={() => setEditingDocument(null)}
          />
        </Modal>
      )}

      {/* ── Archive Confirmation Modal ────────────────────────────────── */}
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


