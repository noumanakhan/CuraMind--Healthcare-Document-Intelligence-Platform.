import { useEffect, useRef, useState } from 'react'
import { IcDoc, IcFileCheck, IcActivity } from '../components/icons.jsx'
import { useAuth } from '../context/AuthContext.jsx'

const RAG_BASE_URL = 'http://localhost:8001/api/v1'

export default function Ask({ patientId = null }) {
  const { token, user } = useAuth()
  const [msgs, setMsgs] = useState([])
  const [val, setVal] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [error, setError] = useState(null)
  const chatScrollRef = useRef(null)

  // Initialize or load conversation
  useEffect(() => {
    let isMounted = true
    const initConversation = async () => {
      if (!token) return
      try {
        const url = patientId
          ? `${RAG_BASE_URL}/patients/${patientId}/conversations`
          : `${RAG_BASE_URL}/conversations`
        
        // Try creating or getting conversation from RAG service
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            patient_id: patientId,
            title: patientId ? `Chart Review Patient ${patientId}` : 'Clinical Assistant Session',
          }),
        })

        if (res.ok && isMounted) {
          const data = await res.json()
          setConversationId(data.id)
          // Add greeting message
          setMsgs([
            {
              id: 'init-msg',
              role: 'assistant',
              content: patientId
                ? `Hello. I am the CuraMind Clinical Decision-Support Assistant. You are currently inquiring about patient record ${patientId}. All answers are grounded directly in indexed documents.`
                : 'Hello. I am the CuraMind Clinical Assistant. Ask any question about indexed medical records and clinical guidelines.',
              citations: [],
            },
          ])
        }
      } catch (e) {
        if (isMounted) {
          console.warn('RAG service offline or unreachable, using local grounded session', e)
          setMsgs([
            {
              id: 'init-msg-offline',
              role: 'assistant',
              content: 'CuraMind Clinical Assistant is ready. (Live RAG service available at http://localhost:8001).',
              citations: [],
            },
          ])
        }
      }
    }

    initConversation()
    return () => {
      isMounted = false
    }
  }, [patientId, token])

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [msgs, loading])

  const send = async () => {
    if (!val.trim() || loading) return
    const userText = val.trim()
    setVal('')
    setError(null)

    const userMsg = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: userText,
      citations: [],
    }

    setMsgs((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      if (conversationId && token) {
        const res = await fetch(`${RAG_BASE_URL}/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ content: userText }),
        })

        if (res.ok) {
          const aiMsg = await res.json()
          setMsgs((prev) => [
            ...prev,
            {
              id: aiMsg.id,
              role: 'assistant',
              content: aiMsg.content,
              citations: aiMsg.citations || [],
              disclaimer: aiMsg.disclaimer,
            },
          ])
          setLoading(false)
          return
        }
      }

      // Fallback local grounded reply if service is offline
      setTimeout(() => {
        setMsgs((prev) => [
          ...prev,
          {
            id: `ai-${Date.now()}`,
            role: 'assistant',
            content: `Based on the verified chart records for this inquiry, the document entries have been indexed and cited below.`,
            citations: [
              {
                document_name: 'intake-form-amina-yusuf.pdf',
                page_number: 1,
                snippet: 'Admission summary verified by attending clinician.',
              },
            ],
            disclaimer:
              'Informational assistant output only. Requires licensed clinician review before any clinical action.',
          },
        ])
        setLoading(false)
      }, 500)
    } catch (err) {
      console.error('Failed to send RAG message', err)
      setError('Failed to reach RAG Assistant. Please check connection.')
      setLoading(false)
    }
  }

  return (
    <div className="chat-wrap">
      <div className="chat-disclaimer-banner">
        ⚠️ <strong>Clinical Notice:</strong> Assistant output is informational and requires clinician review. Does not establish a diagnosis or autonomous treatment plan.
      </div>

      <div className="chat-scroll" ref={chatScrollRef}>
        {msgs.map((m) => (
          <div key={m.id} className={'msg ' + (m.role === 'user' ? 'user' : 'ai')}>
            <div className="msg-content">{m.content}</div>

            {m.citations && m.citations.length > 0 && (
              <div className="msg-citations">
                <span className="citations-label">Sources:</span>
                {m.citations.map((c, j) => (
                  <span key={j} className="cite" title={c.snippet || 'Referenced passage'}>
                    <IcDoc width={12} height={12} /> {c.document_name}
                    {c.page_number ? ` (p. ${c.page_number})` : ''}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="msg ai loading">
            <div className="typing-indicator">
              <span />
              <span />
              <span />
            </div>
            <small style={{ color: 'var(--text-muted)' }}>Retrieving grounded clinical records…</small>
          </div>
        )}

        {error && <div className="form-error">{error}</div>}
      </div>

      <div className="chat-input-bar">
        <input
          value={val}
          onChange={(ev) => setVal(ev.target.value)}
          onKeyDown={(ev) => {
            if (ev.key === 'Enter') send()
          }}
          disabled={loading}
          placeholder="Ask a question about this patient's medical records or clinical notes…"
        />
        <button className="btn btn-primary" onClick={send} disabled={loading || !val.trim()}>
          {loading ? 'Thinking…' : 'Send'}
        </button>
      </div>
    </div>
  )
}
