import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import Modal from '../components/Modal.jsx'

const RAG_BASE = 'http://localhost:8001/api/v1'

// ─── Icons ────────────────────────────────────────────────────────────────────
const IcDoc = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
  </svg>
)
const IcAttach = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
  </svg>
)
const IcSpark = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
  </svg>
)
const IcSend = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
)
const IcX = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
)
const IcTrash = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    <line x1="10" y1="11" x2="10" y2="17" />
    <line x1="14" y1="11" x2="14" y2="17" />
  </svg>
)
const IcPlus = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
)
const IcChat = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
)
const IcSidebarToggle = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="9" y1="3" x2="9" y2="21" />
  </svg>
)

// ─── Markdown-ish AI output ────────────────────────────────────────────────────
function AiMsgContent({ text }) {
  if (!text) return null
  const lines = text.split('\n')
  return (
    <div className="chat-ai-formatted">
      {lines.map((line, i) => {
        if (line.startsWith('## ')) return <h4 key={i} className="chat-h4">{line.slice(3)}</h4>
        if (line.trim().startsWith('⚠️')) return <p key={i} className="chat-warn">{line}</p>
        if (line.startsWith('**') && line.endsWith('**')) return <p key={i} className="chat-bold">{line.slice(2, -2)}</p>
        if (line.trim() === '') return <div key={i} style={{ height: '6px' }} />
        const parts = line.split(/(\*\*[^*]+\*\*)/)
        return (
          <p key={i} className="chat-p">
            {parts.map((p, j) =>
              p.startsWith('**') && p.endsWith('**')
                ? <strong key={j}>{p.slice(2, -2)}</strong>
                : p
            )}
          </p>
        )
      })}
    </div>
  )
}

// ─── Document context pill ─────────────────────────────────────────────────────
function DocContextPill({ file, onRemove }) {
  return (
    <div className="chat-doc-pill">
      <IcDoc /> <span>{file.name}</span>
      <button onClick={onRemove} className="chat-pill-remove" title="Remove"><IcX /></button>
    </div>
  )
}

// ─── Suggested prompts ─────────────────────────────────────────────────────────
const SUGGESTIONS = [
  'Summarise the key findings in this document',
  'What medications are prescribed?',
  'Are there any abnormal lab values?',
  'What is the primary diagnosis?',
  'List all follow-up actions',
]

function getInitialGreeting(patientId) {
  return {
    id: 'init',
    role: 'assistant',
    content: patientId
      ? `Hello. I am the CuraMind Clinical Assistant. You are reviewing patient **${patientId}**.\n\nYou can ask questions grounded in indexed documents, or upload a PDF/document for me to analyse directly.`
      : `Hello. I am the CuraMind Clinical Assistant.\n\nAsk me anything about indexed clinical records — or upload a document and I will summarise and answer questions from it.`,
    citations: [],
  }
}

export default function Ask({ patientId = null }) {
  const { token: authTok, accessToken } = useAuth()
  const token = accessToken || authTok
  const [conversations, setConversations] = useState([])
  const [activeConvId, setActiveConvId] = useState(null)
  const [msgs, setMsgs] = useState([])
  const [val, setVal] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [error, setError] = useState(null)
  const [attachedFile, setAttachedFile] = useState(null)
  const [fileContext, setFileContext] = useState(null)
  const [fileLoading, setFileLoading] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  
  // Deletion modal state
  const [targetDeleteConv, setTargetDeleteConv] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const chatScrollRef = useRef(null)
  const attachRef = useRef(null)
  const inputRef = useRef(null)

  // ── Load Conversation List & Active Session ──────────────────────────────────
  const loadConversations = useCallback(async () => {
    if (!token) return
    try {
      const url = patientId ? `${RAG_BASE}/patients/${patientId}/conversations` : `${RAG_BASE}/conversations`
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const list = await res.json()
        setConversations(list || [])
        return list || []
      }
    } catch {
      // offline fallback
    }
    return []
  }, [patientId, token])

  // ── Load Messages for a specific conversation ────────────────────────────────
  const loadMessages = useCallback(async (convId) => {
    if (!token || !convId) return
    setLoadingHistory(true)
    try {
      const res = await fetch(`${RAG_BASE}/conversations/${convId}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        if (data && data.length > 0) {
          setMsgs(data.map(m => ({
            id: m.id,
            role: m.role,
            content: m.content,
            citations: m.citations || [],
            disclaimer: m.disclaimer || (m.role === 'assistant' ? 'Informational output only. Requires clinician review.' : undefined),
          })))
        } else {
          setMsgs([getInitialGreeting(patientId)])
        }
      } else {
        setMsgs([getInitialGreeting(patientId)])
      }
    } catch {
      setMsgs([getInitialGreeting(patientId)])
    } finally {
      setLoadingHistory(false)
    }
  }, [patientId, token])

  // ── Create a Brand New Chat ──────────────────────────────────────────────────
  const createNewChat = useCallback(async () => {
    if (!token) {
      const localId = `local-${Date.now()}`
      setActiveConvId(localId)
      setMsgs([getInitialGreeting(patientId)])
      setAttachedFile(null)
      setFileContext(null)
      setVal('')
      return
    }

    try {
      const url = patientId ? `${RAG_BASE}/patients/${patientId}/conversations` : `${RAG_BASE}/conversations`
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ patient_id: patientId, title: 'New Chat' }),
      })
      if (res.ok) {
        const newConv = await res.json()
        setConversations(prev => [newConv, ...prev.filter(c => c.id !== newConv.id)])
        setActiveConvId(newConv.id)
        setMsgs([getInitialGreeting(patientId)])
        setAttachedFile(null)
        setFileContext(null)
        setVal('')
        setError(null)
      }
    } catch {
      // offline fallback
      const localId = `local-${Date.now()}`
      setActiveConvId(localId)
      setMsgs([getInitialGreeting(patientId)])
    }
  }, [patientId, token])

  // ── Select a Conversation ────────────────────────────────────────────────────
  const selectConversation = (conv) => {
    if (conv.id === activeConvId) return
    setActiveConvId(conv.id)
    setAttachedFile(null)
    setFileContext(null)
    setError(null)
    setVal('')
    loadMessages(conv.id)
  }

  // ── Initial Mount: Fetch or Create ───────────────────────────────────────────
  useEffect(() => {
    let mounted = true
    const init = async () => {
      const list = await loadConversations()
      if (!mounted) return
      if (list && list.length > 0) {
        const first = list[0]
        setActiveConvId(first.id)
        await loadMessages(first.id)
      } else {
        await createNewChat()
      }
    }
    init()
    return () => { mounted = false }
  }, [loadConversations, loadMessages, createNewChat])

  useEffect(() => {
    if (chatScrollRef.current) chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
  }, [msgs, loading])

  // ── Handle document attachment ──────────────────────────────────────────────
  const handleAttachFile = useCallback(async (file) => {
    if (!file) return
    setAttachedFile(file)
    setFileContext(null)
    setFileLoading(true)

    setMsgs(prev => [...prev, {
      id: `attach-${Date.now()}`,
      role: 'system',
      content: `📎 Document attached: **${file.name}** (${(file.size / 1024).toFixed(1)} KB)\nIndexing through RAG pipeline…`,
      citations: [],
    }])

    try {
      if (token) {
        const fd = new FormData()
        fd.append('file', file)
        const res = await fetch(`${RAG_BASE}/documents/summarise`, {
          method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
        })
        if (res.ok) {
          const data = await res.json()
          setFileContext(data)
          setMsgs(prev => [...prev, {
            id: `attach-ok-${Date.now()}`,
            role: 'assistant',
            content: `✅ Document **${file.name}** has been processed through the RAG pipeline (${data.chunks_count} chunks indexed).\n\nHere's a quick summary:\n\n${data.summary}`,
            citations: [],
          }])
          setFileLoading(false)
          return
        }
      }
    } catch { /* fallback */ }

    await new Promise(r => setTimeout(r, 600))
    setFileContext({ filename: file.name, chunks_count: 8, summary: 'Document indexed (offline mode).' })
    setMsgs(prev => [...prev, {
      id: `attach-ok-${Date.now()}`,
      role: 'assistant',
      content: `✅ Document **${file.name}** attached. I'll use it to answer your questions.\n\n*(RAG service offline — using local context mode)*`,
      citations: [],
    }])
    setFileLoading(false)
  }, [token])

  // ── Delete Conversation Handler ──────────────────────────────────────────────
  const handleDeleteChat = async () => {
    if (!targetDeleteConv) return
    const convId = targetDeleteConv.id
    setDeleting(true)
    try {
      if (token && !convId.startsWith('local-')) {
        await fetch(`${RAG_BASE}/conversations/${convId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        })
      }
    } catch (err) {
      console.error('Failed to delete chat:', err)
    } finally {
      setDeleting(false)
      const remaining = conversations.filter(c => c.id !== convId)
      setConversations(remaining)
      setTargetDeleteConv(null)

      // If deleted active conversation, switch or create new
      if (activeConvId === convId) {
        if (remaining.length > 0) {
          const nextConv = remaining[0]
          setActiveConvId(nextConv.id)
          loadMessages(nextConv.id)
        } else {
          createNewChat()
        }
      }
    }
  }

  // ── Send message ─────────────────────────────────────────────────────────────
  const send = async (text) => {
    const msg = (text || val).trim()
    if (!msg || loading) return
    setVal('')
    setError(null)
    setMsgs(prev => [...prev, { id: `u-${Date.now()}`, role: 'user', content: msg, citations: [] }])
    setLoading(true)

    // Auto update title in sidebar if it's currently "New Chat"
    const currentConv = conversations.find(c => c.id === activeConvId)
    if (currentConv && (currentConv.title === 'New Chat' || currentConv.title === 'Clinical Assistant Session')) {
      const cleanTitle = msg.split('\n')[0].slice(0, 36)
      setConversations(prev => prev.map(c => c.id === activeConvId ? { ...c, title: cleanTitle } : c))
    }

    try {
      // PATH A: Uploaded doc attached → Full RAG pipeline via /documents/ask
      if (attachedFile && token) {
        const fd = new FormData()
        fd.append('file', attachedFile)
        fd.append('question', msg)
        const res = await fetch(`${RAG_BASE}/documents/ask`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: fd,
        })
        if (res.ok) {
          const data = await res.json()
          setMsgs(prev => [...prev, {
            id: `ai-rag-${Date.now()}`,
            role: 'assistant',
            content: data.answer,
            citations: (data.citations || []).map((c) => ({
              document_name: attachedFile.name,
              page_number: c.page_number,
              snippet: c.snippet,
            })),
            disclaimer: 'RAG pipeline: extract → chunk → embed → hybrid search (semantic + BM25) → RRF → top-K → LLM',
          }])
          setLoading(false)
          return
        }
        const message = await res.text()
        throw new Error(`Document question failed (${res.status}): ${message}`)
      }

      // PATH B: No file → standard conversation RAG
      if (token) {
        let convId = activeConvId
        // If activeConvId is missing or local, provision a real conversation on the RAG service
        if (!convId || convId.startsWith('local-')) {
          try {
            const url = patientId ? `${RAG_BASE}/patients/${patientId}/conversations` : `${RAG_BASE}/conversations`
            const cRes = await fetch(url, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
              body: JSON.stringify({ patient_id: patientId, title: msg.split('\n')[0].slice(0, 36) }),
            })
            if (cRes.ok) {
              const newConv = await cRes.json()
              convId = newConv.id
              setActiveConvId(newConv.id)
              setConversations(prev => [newConv, ...prev.filter(c => c.id !== newConv.id && !c.id.startsWith('local-'))])
            }
          } catch (e) {
            throw new Error(`Could not create a RAG conversation: ${e.message}`)
          }
          if (!convId || convId.startsWith('local-')) {
            throw new Error('Could not create a RAG conversation. Check that the RAG service is available.')
          }
        }

        if (convId && !convId.startsWith('local-')) {
          const res = await fetch(`${RAG_BASE}/conversations/${convId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ content: msg }),
          })
          if (res.ok) {
            const aiMsg = await res.json()
            setMsgs(prev => [...prev, {
              id: aiMsg.id,
              role: 'assistant',
              content: aiMsg.content,
              citations: aiMsg.citations || [],
              disclaimer: aiMsg.disclaimer || 'Informational output only. Requires clinician review.',
            }])
            setLoading(false)
            loadConversations()
            return
          }
          const message = await res.text()
          throw new Error(`RAG request failed (${res.status}): ${message}`)
        }
      }
      throw new Error(token ? 'No RAG response was received.' : 'Sign in to use the clinical RAG assistant.')
    } catch (e) {
      setError(e.message || 'Failed to reach RAG Assistant.')
    }
    setLoading(false)
  }

  const clearFile = () => { setAttachedFile(null); setFileContext(null) }

  // Filter conversations
  const filteredConversations = conversations.filter(c =>
    (c.title || 'New Chat').toLowerCase().includes(searchQuery.toLowerCase())
  )

  const activeConversation = conversations.find(c => c.id === activeConvId)

  return (
    <div className="chat-layout-v2">
      {/* ── ChatGPT-Style History Sidebar ─────────────────────────────── */}
      <aside className={`chat-sidebar-v2 ${!isSidebarOpen ? 'collapsed' : ''}`}>
        <div className="chat-sidebar-head">
          <button className="btn-new-chat" onClick={createNewChat} title="Start a fresh conversation">
            <IcPlus /> New Chat
          </button>
          <input
            type="text"
            className="chat-search-input"
            placeholder="Search conversations…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="chat-sessions-list">
          <div className="chat-sessions-label">
            {patientId ? `Patient ${patientId} Chats` : 'Chat History'}
          </div>

          {filteredConversations.length === 0 ? (
            <div style={{ padding: '20px 12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              {searchQuery ? 'No chats found' : 'No previous conversations'}
            </div>
          ) : (
            filteredConversations.map(c => {
              const isActive = c.id === activeConvId
              return (
                <div
                  key={c.id}
                  className={`chat-session-item ${isActive ? 'active' : ''}`}
                  onClick={() => selectConversation(c)}
                >
                  <div className="chat-session-main">
                    <span className="chat-session-icon"><IcChat /></span>
                    <span className="chat-session-title" title={c.title || 'New Chat'}>
                      {c.title || 'New Chat'}
                    </span>
                  </div>
                  <div className="chat-session-actions">
                    <button
                      className="chat-session-del-btn"
                      title="Delete chat session"
                      onClick={(e) => {
                        e.stopPropagation()
                        setTargetDeleteConv(c)
                      }}
                    >
                      <IcTrash />
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>

        <div className="chat-sidebar-footer">
          <span>{conversations.length} conversation{conversations.length !== 1 ? 's' : ''}</span>
          <span>CuraMind RAG</span>
        </div>
      </aside>

      {/* ── Main Chat Area ────────────────────────────────────────────── */}
      <div className="chat-main-v2"
        onDragOver={e => e.preventDefault()}
        onDrop={e => { const f = e.dataTransfer?.files?.[0]; if (f) handleAttachFile(f); e.preventDefault() }}
      >
        {/* Header bar */}
        <div className="chat-header-bar">
          <div className="chat-header-left">
            <button
              className="btn btn-ghost"
              style={{ padding: '6px', display: 'flex', alignItems: 'center' }}
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              title={isSidebarOpen ? 'Collapse sidebar' : 'Show chat history'}
            >
              <IcSidebarToggle />
            </button>
            <span className="chat-badge-ai"><IcSpark /> CuraMind AI</span>
            {activeConversation && (
              <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text)' }}>
                {activeConversation.title || 'New Chat'}
              </span>
            )}
            {fileContext && (
              <span className="chat-doc-context-badge">
                <IcDoc /> {fileContext.filename} · {fileContext.chunks_count} chunks
                <button onClick={clearFile} className="chat-pill-remove" title="Remove"><IcX /></button>
              </span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="chat-disclaimer-inline">
              ⚠️ Informational only
            </div>
            <button
              className="btn btn-secondary"
              style={{ padding: '4px 9px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
              onClick={createNewChat}
              title="Start a fresh chat"
            >
              <IcPlus /> New Chat
            </button>
            {activeConversation && (
              <button
                className="btn btn-danger-ghost"
                style={{ padding: '4px 9px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', borderRadius: '6px' }}
                onClick={() => setTargetDeleteConv(activeConversation)}
                title="Delete this chat session from database"
                disabled={loading || deleting}
              >
                <IcTrash /> Delete
              </button>
            )}
          </div>
        </div>

        {/* Messages feed */}
        <div className="chat-scroll-v2" ref={chatScrollRef}>
          {loadingHistory ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
              Loading conversation…
            </div>
          ) : (
            msgs.map(m => (
              <div key={m.id} className={`msg-v2 ${m.role === 'user' ? 'user' : m.role === 'system' ? 'system' : 'ai'}`}>
                {m.role !== 'user' && (
                  <div className="msg-avatar">{m.role === 'system' ? '📎' : '🤖'}</div>
                )}
                <div className="msg-body">
                  <AiMsgContent text={m.content} />
                  {m.citations && m.citations.length > 0 && (
                    <div className="msg-citations-v2">
                      <span className="cite-label">Sources:</span>
                      {m.citations.map((c, j) => (
                        <span key={j} className="cite-pill" title={c.snippet}>
                          <IcDoc /> {c.document_name}{c.page_number ? ` p.${c.page_number}` : ''}
                        </span>
                      ))}
                    </div>
                  )}
                  {m.disclaimer && <p className="msg-disclaimer">{m.disclaimer}</p>}
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="msg-v2 ai">
              <div className="msg-avatar">🤖</div>
              <div className="msg-body">
                <div className="typing-v2"><span /><span /><span /></div>
                <small className="typing-label">{fileLoading ? 'Indexing document…' : 'Searching clinical records…'}</small>
              </div>
            </div>
          )}
          {error && <div className="chat-error">{error}</div>}
        </div>

        {/* Suggestions — shown only on clean fresh conversations */}
        {msgs.length <= 1 && !loading && !loadingHistory && (
          <div className="chat-suggestions">
            {SUGGESTIONS.map((s, i) => (
              <button key={i} className="suggestion-chip" onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}

        {/* Input bar */}
        <div className="chat-input-v2">
          {attachedFile && !fileContext && (
            <DocContextPill file={attachedFile} onRemove={clearFile} />
          )}
          <div className="chat-input-row">
            <button className="chat-attach-btn" title="Attach document"
              onClick={() => attachRef.current?.click()}>
              <IcAttach />
            </button>
            <input ref={attachRef} type="file" accept=".pdf,.docx,.txt,.png,.jpg"
              style={{ display: 'none' }}
              onChange={e => { if (e.target.files[0]) handleAttachFile(e.target.files[0]) }} />
            <input
              ref={inputRef}
              className="chat-input-field"
              value={val}
              onChange={e => setVal(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
              disabled={loading || loadingHistory}
              placeholder={fileContext
                ? `Ask about ${fileContext.filename}…`
                : patientId
                  ? 'Ask about this patient\'s records…'
                  : 'Ask about indexed clinical records or attach a document…'
              }
            />
            <button className="chat-send-btn" onClick={() => send()} disabled={loading || !val.trim() || loadingHistory}>
              <IcSend />
            </button>
          </div>
          <div className="chat-input-hint">
            Drop a PDF to analyse · Enter to send · Shift+Enter for newline
          </div>
        </div>
      </div>

      {/* Delete Chat Confirmation Modal */}
      {targetDeleteConv && (
        <Modal title="Delete Conversation?" onClose={() => setTargetDeleteConv(null)}>
          <div style={{ padding: '8px 0' }}>
            <p style={{ marginBottom: '16px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
              Are you sure you want to delete <strong>&quot;{targetDeleteConv.title || 'this chat'}&quot;</strong>? All messages and citations in this conversation will be permanently removed from the database.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setTargetDeleteConv(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleDeleteChat}
                disabled={deleting}
              >
                {deleting ? 'Deleting…' : 'Delete Chat'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

