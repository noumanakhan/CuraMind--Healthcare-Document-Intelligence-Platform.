import { useCallback, useEffect, useRef, useState } from 'react'
import { COMPARE_ROWS } from '../data/mock.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useClinical } from '../context/PatientContext.jsx'

const RAG_BASE = 'http://localhost:8001/api/v1'

// ─── icons ───────────────────────────────────────────────────────────────────
const IcUpload = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="17 8 12 3 7 8"/>
    <line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
)
const IcFile = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
  </svg>
)
const IcSpark = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
  </svg>
)
const IcCopy = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  </svg>
)

// ─── Mode Tabs ────────────────────────────────────────────────────────────────
const MODES = [
  { id: 'upload-compare', label: '⚡ AI Compare (Upload)', desc: 'Upload 2 documents — LLM compares them' },
  { id: 'upload-summarise', label: '📋 Summarise Document', desc: 'Upload 1 document — LLM generates clinical summary' },
  { id: 'existing', label: '🗂 Compare Existing', desc: 'Compare documents already in your vault' },
]

// ─── Drop Zone Component ──────────────────────────────────────────────────────
function DropZone({ label, slot, file, onFile }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) onFile(f)
  }, [onFile])

  return (
    <div className={`dropzone${file ? ' dropzone-filled' : ''}${dragging ? ' dropzone-drag' : ''}`}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      role="button" tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && inputRef.current?.click()}
      aria-label={`Upload ${label}`}
    >
      <input ref={inputRef} type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
        style={{ display: 'none' }} onChange={e => { if (e.target.files[0]) onFile(e.target.files[0]) }} />
      {file ? (
        <>
          <div className="dropzone-icon filled"><IcFile /></div>
          <div className="dropzone-filled-name">{file.name}</div>
          <div className="dropzone-filled-size">{(file.size / 1024).toFixed(1)} KB · click to change</div>
        </>
      ) : (
        <>
          <div className="dropzone-icon"><IcUpload /></div>
          <div className="dropzone-label">{label}</div>
          <div className="dropzone-hint">Drop PDF, DOCX, or image · or click to browse</div>
        </>
      )}
    </div>
  )
}

// ─── Markdown-ish renderer ────────────────────────────────────────────────────
function AiOutput({ text }) {
  if (!text) return null
  const lines = text.split('\n')
  return (
    <div className="ai-output">
      {lines.map((line, i) => {
        if (line.startsWith('## ')) return <h3 key={i} className="ai-h3">{line.slice(3)}</h3>
        if (line.startsWith('# ')) return <h2 key={i} className="ai-h2">{line.slice(2)}</h2>
        if (line.startsWith('**') && line.endsWith('**')) return <p key={i} className="ai-bold">{line.slice(2, -2)}</p>
        if (line.trim().startsWith('⚠️')) return <p key={i} className="ai-warn">{line}</p>
        if (line.trim() === '') return <div key={i} className="ai-spacer" />
        return <p key={i} className="ai-p">{line}</p>
      })}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Compare({ patientId = null }) {
  const { token } = useAuth()
  const { documents } = useClinical()
  const [mode, setMode] = useState('upload-compare')

  // upload-compare state
  const [fileA, setFileA] = useState(null)
  const [fileB, setFileB] = useState(null)
  const [cmpResult, setCmpResult] = useState(null)

  // summarise state
  const [fileSumm, setFileSumm] = useState(null)
  const [summResult, setSummResult] = useState(null)

  // existing compare state
  const [docList, setDocList] = useState([])
  const [doc1Id, setDoc1Id] = useState('')
  const [doc2Id, setDoc2Id] = useState('')
  const [existingCmp, setExistingCmp] = useState(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let list = patientId && documents[patientId] ? documents[patientId] : Object.values(documents).flat()
    setDocList(list)
    if (list.length >= 2) { setDoc1Id(list[0].id); setDoc2Id(list[1].id) }
  }, [patientId, documents])

  const handleUploadCompare = async () => {
    if (!fileA || !fileB) return setError('Please upload both Document A and Document B.')
    if (!token) return setError('Sign in to compare clinical documents.')
    setLoading(true); setError(null); setCmpResult(null)
    try {
      const fd = new FormData()
      fd.append('file_a', fileA)
      fd.append('file_b', fileB)
      const res = await fetch(`${RAG_BASE}/documents/upload-compare`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
      })
      if (!res.ok) throw new Error(`Comparison failed (${res.status}): ${await res.text()}`)
      setCmpResult(await res.json())
    } catch (e) { setError(e.message || 'Upload comparison failed. Check the RAG service connection.') }
    setLoading(false)
  }

  const handleSummarise = async () => {
    if (!fileSumm) return setError('Please upload a document to summarise.')
    if (!token) return setError('Sign in to summarise clinical documents.')
    setLoading(true); setError(null); setSummResult(null)
    try {
      const fd = new FormData()
      fd.append('file', fileSumm)
      const res = await fetch(`${RAG_BASE}/documents/summarise`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
      })
      if (!res.ok) throw new Error(`Summarisation failed (${res.status}): ${await res.text()}`)
      setSummResult(await res.json())
    } catch (e) { setError(e.message || 'Summarisation failed. Check the RAG service connection.') }
    setLoading(false)
  }

  const handleExistingCompare = async () => {
    if (!doc1Id || !doc2Id) return
    if (!token) return setError('Sign in to compare clinical documents.')
    setLoading(true); setError(null); setExistingCmp(null)
    try {
      const url = patientId ? `${RAG_BASE}/patients/${patientId}/documents/compare` : `${RAG_BASE}/documents/compare`
      const res = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ doc1_id: doc1Id, doc2_id: doc2Id, mode: 'both' }),
      })
      if (!res.ok) throw new Error(`Comparison failed (${res.status}): ${await res.text()}`)
      setExistingCmp(await res.json())
    } catch (e) { setError(e.message || 'Comparison service unavailable.') }
    setLoading(false)
  }

  useEffect(() => { if (mode === 'existing' && doc1Id && doc2Id) handleExistingCompare() }, [doc1Id, doc2Id])

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
  }

  const activeMode = MODES.find(m => m.id === mode)

  return (
    <div className="compare-v2-wrap">
      {/* Mode tabs */}
      <div className="cmp-mode-tabs">
        {MODES.map(m => (
          <button key={m.id} className={`cmp-mode-tab${mode === m.id ? ' active' : ''}`}
            onClick={() => { setMode(m.id); setError(null); setCmpResult(null); setSummResult(null); setExistingCmp(null) }}>
            {m.label}
          </button>
        ))}
      </div>
      <p className="cmp-mode-desc">{activeMode?.desc}</p>

      {/* ── UPLOAD COMPARE ────────────────────────────────── */}
      {mode === 'upload-compare' && (
        <div className="cmp-upload-section">
          <div className="cmp-drop-row">
            <DropZone label="Document A" slot="a" file={fileA} onFile={setFileA} />
            <div className="cmp-vs-badge">VS</div>
            <DropZone label="Document B" slot="b" file={fileB} onFile={setFileB} />
          </div>
          <button className="btn btn-primary btn-compare-run" onClick={handleUploadCompare} disabled={loading || !fileA || !fileB}>
            {loading ? <><span className="btn-spinner" /> Analysing with AI…</> : <><IcSpark /> Run AI Comparison</>}
          </button>
          {error && <div className="cmp-error">{error}</div>}
          {cmpResult && (
            <div className="cmp-ai-result">
              <div className="cmp-ai-header">
                <div className="cmp-ai-badge"><IcSpark /> AI Analysis</div>
                <div className="cmp-doc-pills">
                  <span className="doc-pill a">{cmpResult.doc_a?.filename} · {cmpResult.doc_a?.chunks_count} chunks</span>
                  <span className="doc-pill b">{cmpResult.doc_b?.filename} · {cmpResult.doc_b?.chunks_count} chunks</span>
                </div>
                <button className="copy-btn" onClick={() => handleCopy(cmpResult.ai_comparison)} title="Copy result">
                  <IcCopy /> {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <AiOutput text={cmpResult.ai_comparison} />
              <p className="cmp-disclaimer">⚠️ AI output requires licensed clinician review before any clinical action.</p>
            </div>
          )}
        </div>
      )}

      {/* ── SUMMARISE ─────────────────────────────────────── */}
      {mode === 'upload-summarise' && (
        <div className="cmp-upload-section">
          <div className="cmp-drop-row single">
            <DropZone label="Upload Document to Summarise" slot="s" file={fileSumm} onFile={setFileSumm} />
          </div>
          <button className="btn btn-primary btn-compare-run" onClick={handleSummarise} disabled={loading || !fileSumm}>
            {loading ? <><span className="btn-spinner" /> Generating Summary…</> : <><IcSpark /> Generate Clinical Summary</>}
          </button>
          {error && <div className="cmp-error">{error}</div>}
          {summResult && (
            <div className="cmp-ai-result">
              <div className="cmp-ai-header">
                <div className="cmp-ai-badge"><IcSpark /> Clinical Summary</div>
                <span className="doc-pill a">{summResult.filename} · {summResult.chunks_count} chunks indexed</span>
                <button className="copy-btn" onClick={() => handleCopy(summResult.summary)} title="Copy summary">
                  <IcCopy /> {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <AiOutput text={summResult.summary} />
              <p className="cmp-disclaimer">⚠️ AI output requires licensed clinician review before any clinical action.</p>
            </div>
          )}
        </div>
      )}

      {/* ── EXISTING DOCS COMPARE ─────────────────────────── */}
      {mode === 'existing' && (
        <div className="cmp-existing-section">
          <div className="cmp-picker-row">
            <div className="cmp-picker-slot">
              <label>Document A</label>
              <select value={doc1Id} onChange={e => setDoc1Id(e.target.value)} className="cmp-select">
                {docList.length === 0 && <option>No documents in vault</option>}
                {docList.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div className="cmp-vs-badge">VS</div>
            <div className="cmp-picker-slot">
              <label>Document B</label>
              <select value={doc2Id} onChange={e => setDoc2Id(e.target.value)} className="cmp-select">
                {docList.map(d => <option key={d.id} value={d.id} disabled={d.id === doc1Id}>{d.name}</option>)}
              </select>
            </div>
          </div>
          <button className="btn btn-primary btn-compare-run" onClick={handleExistingCompare} disabled={loading}>
            {loading ? <><span className="btn-spinner" /> Comparing…</> : '↻ Re-compare'}
          </button>
          {error && <div className="cmp-error">{error}</div>}
          {existingCmp && (
            <div className="cmp-existing-result">
              <div className="cmp-existing-meta">
                <span className="badge processing">{existingCmp.total_differences_count} difference{existingCmp.total_differences_count !== 1 ? 's' : ''}</span>
                <span className="cmp-summary-text">{existingCmp.summary}</span>
              </div>
              <table className="cmp-table">
                <thead>
                  <tr>
                    <th>Clinical Field</th>
                    <th>{existingCmp.doc1_name}</th>
                    <th>{existingCmp.doc2_name}</th>
                  </tr>
                </thead>
                <tbody>
                  {(existingCmp.structured_diffs || []).map((r, i) => (
                    <tr key={i} className={r.status === 'differ' ? 'diff-row' : ''}>
                      <td className="cmp-field-name">
                        <strong>{r.label}</strong>
                        {r.status === 'differ' && <span className="diff-tag">Modified</span>}
                      </td>
                      <td className={r.status === 'differ' ? 'cmp-diff' : ''}>{r.doc1_value || <span className="text-muted">—</span>}</td>
                      <td className={r.status === 'differ' ? 'cmp-diff' : ''}>{r.doc2_value || <span className="text-muted">—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
