import { useState } from 'react'
import { INITIAL_MESSAGES } from '../data/mock.js'

export default function Ask() {
  const [msgs, setMsgs] = useState(INITIAL_MESSAGES)
  const [val, setVal] = useState('')

  const send = () => {
    if (!val.trim()) return
    setMsgs((m) => [
      ...m,
      { role: 'user', text: val },
      {
        role: 'ai',
        text: 'Let me check the indexed documents for that and get back to you with a sourced answer.',
        cites: [],
      },
    ])
    setVal('')
  }

  return (
    <div className="chat-wrap">
      <div className="chat-scroll">
        {msgs.map((m, i) => (
          <div key={i} className={'msg ' + m.role}>
            {m.text}
            {m.cites && m.cites.length > 0 && (
              <div>
                {m.cites.map((c, j) => (
                  <span key={j} className="cite">
                    📄 {c}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="chat-input-bar">
        <input
          value={val}
          onChange={(ev) => setVal(ev.target.value)}
          onKeyDown={(ev) => {
            if (ev.key === 'Enter') send()
          }}
          placeholder="Ask a question about your documents…"
        />
        <button className="btn btn-primary" onClick={send}>
          Send
        </button>
      </div>
    </div>
  )
}
