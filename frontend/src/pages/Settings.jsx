import { useEffect, useState } from 'react'
import { SETTINGS_ITEMS } from '../data/mock.js'
import { PERMISSION_LABELS, ROLE_DEFINITIONS, ROLE_IDS } from '../data/roles.js'
import { useClinical } from '../context/PatientContext.jsx'

const THEME_KEY = 'curamind_theme'

function getInitialTheme() {
  try {
    const savedTheme = localStorage.getItem(THEME_KEY)
    if (savedTheme === 'light' || savedTheme === 'dark' || savedTheme === 'system') return savedTheme
  } catch (error) {
    // The appearance control remains usable for this session without storage.
  }
  return 'system'
}

function prefersDarkAppearance() {
  return typeof window !== 'undefined' && Boolean(window.matchMedia?.('(prefers-color-scheme: dark)').matches)
}

function applyTheme(theme) {
  if (theme === 'system') {
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.removeProperty('color-scheme')
  } else {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
  }
}

export default function Settings() {
  const [state, setState] = useState(SETTINGS_ITEMS.map((i) => i[2]))
  const [theme, setTheme] = useState(getInitialTheme)
  const [systemPrefersDark, setSystemPrefersDark] = useState(prefersDarkAppearance)
  const { role, roleDefinition, setRole, canAccess } = useClinical()
  const canManageSettings = canAccess('settings:manage')
  const darkModeEnabled = theme === 'dark' || (theme === 'system' && systemPrefersDark)

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-color-scheme: dark)')
    if (!media) return undefined
    const updatePreference = (event) => setSystemPrefersDark(event.matches)
    if (media.addEventListener) media.addEventListener('change', updatePreference)
    else media.addListener(updatePreference)
    return () => {
      if (media.removeEventListener) media.removeEventListener('change', updatePreference)
      else media.removeListener(updatePreference)
    }
  }, [])

  useEffect(() => {
    applyTheme(theme)
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch (error) {
      // Theme changes remain applied until the page is closed if storage is unavailable.
    }
  }, [theme])

  return (
    <div className="settings-page">
      <section className="card role-preview">
        <div className="role-preview-copy">
          <div className="card-title">Role-based access preview</div>
          <p>This prototype switch lets you inspect what each staff role can see and change. In production, roles must come from authenticated server-side accounts.</p>
        </div>
        <label className="form-field role-select">
          <span>Preview as</span>
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            {ROLE_IDS.map((id) => <option key={id} value={id}>{ROLE_DEFINITIONS[id].label}</option>)}
          </select>
        </label>
        <div className="role-description"><strong>{roleDefinition.label}</strong><span>{roleDefinition.description}</span></div>
      </section>

      <section className="card role-matrix-card">
        <div className="card-title">Permission matrix</div>
        <div className="doc-table role-matrix-wrap">
          <table className="role-matrix">
            <thead>
              <tr><th>Capability</th>{ROLE_IDS.map((id) => <th key={id}>{ROLE_DEFINITIONS[id].label}</th>)}</tr>
            </thead>
            <tbody>
              {PERMISSION_LABELS.map(([permission, label]) => (
                <tr key={permission}>
                  <td>{label}</td>
                  {ROLE_IDS.map((id) => (
                    <td key={id} className={ROLE_DEFINITIONS[id].permissions.includes(permission) ? 'permission-yes' : 'permission-no'}>
                      {ROLE_DEFINITIONS[id].permissions.includes(permission) ? 'Allowed' : '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="settings-note">Current profile: <strong>{roleDefinition.label}</strong> · “{PERMISSION_LABELS.filter(([permission]) => canAccess(permission)).map(([, label]) => label).join(', ')}”</p>
      </section>

      <section className="card appearance-card">
        <div className="appearance-copy">
          <div className="settings-section-heading">Appearance</div>
          <p>Choose the display theme for the whole workspace.</p>
        </div>
        <div className="appearance-controls">
          <span className="appearance-mode-label">{darkModeEnabled ? 'Dark mode' : 'Light mode'}</span>
          <button
            type="button"
            role="switch"
            aria-checked={darkModeEnabled}
            aria-label="Dark mode"
            className={'toggle appearance-toggle' + (darkModeEnabled ? ' on' : '')}
            onClick={() => setTheme(darkModeEnabled ? 'light' : 'dark')}
          >
            <span className="knob" />
          </button>
          <button type="button" className="btn btn-ghost appearance-system" onClick={() => setTheme('system')}>
            Use system
          </button>
        </div>
      </section>

      <section className="card settings-list" style={{ padding: 0 }}>
        <div className="settings-section-heading">Workspace preferences</div>
        {!canManageSettings && <p className="settings-access-note">Only workspace administrators can change these preferences.</p>}
        {SETTINGS_ITEMS.map((it, i) => (
          <div key={i} className="row">
            <div>
              <div className="label">{it[0]}</div>
              <div className="desc">{it[1]}</div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={state[i]}
              aria-label={it[0]}
              className={'toggle' + (state[i] ? ' on' : '')}
              disabled={!canManageSettings}
              onClick={() => setState((s) => s.map((v, j) => (j === i ? !v : v)))}
            >
              <span className="knob" />
            </button>
          </div>
        ))}
      </section>
      <p className="settings-note">A role picker is included for demonstration only. It is not authentication or a HIPAA compliance control.</p>
    </div>
  )
}
