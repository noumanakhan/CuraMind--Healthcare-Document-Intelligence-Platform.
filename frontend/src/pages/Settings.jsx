import { useEffect, useState } from 'react'
import { SETTINGS_ITEMS } from '../data/mock.js'
import { PERMISSION_LABELS, ROLE_DEFINITIONS, ROLE_IDS } from '../data/roles.js'
import { useClinical } from '../context/PatientContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'

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
  const { role, roleDefinition, canAccess, user } = useClinical()
  const { request } = useAuth()
  const [team, setTeam] = useState([])
  const [teamError, setTeamError] = useState('')
  const [teamLoading, setTeamLoading] = useState(false)
  const canManageSettings = canAccess('settings:manage')
  const canManageUsers = canAccess('users:manage')
  const darkModeEnabled = theme === 'dark' || (theme === 'system' && systemPrefersDark)

  const loadTeam = async () => {
    setTeamLoading(true)
    setTeamError('')
    try {
      const result = await request('/users')
      setTeam(result.users || [])
    } catch (error) {
      setTeamError(error.message || 'Unable to load workspace users.')
    } finally {
      setTeamLoading(false)
    }
  }

  const updateTeamMember = async (memberId, endpoint, body) => {
    setTeamError('')
    try {
      const updated = await request(endpoint, { method: 'PATCH', body: JSON.stringify(body) })
      setTeam((current) => current.map((member) => member.id === memberId ? updated : member))
    } catch (error) {
      setTeamError(error.message || 'Unable to update workspace user.')
    }
  }

  useEffect(() => {
    if (canManageUsers) loadTeam()
  }, [canManageUsers])

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
          <div className="card-title">Your workspace access</div>
          <p>Your role is assigned by a workspace administrator and checked by the authentication service.</p>
        </div>
        <div className="role-description"><strong>{user?.name || user?.email}</strong><span>{roleDefinition.label} · {roleDefinition.description}</span></div>
      </section>

      {canManageUsers && (
        <section className="card workspace-users-card">
          <div className="workspace-users-heading">
            <div><div className="settings-section-heading">Workspace users</div><p>Assign roles and deactivate accounts. New self-registered accounts start as read-only.</p></div>
            <button type="button" className="btn btn-ghost" onClick={loadTeam} disabled={teamLoading}>{teamLoading ? 'Refreshing…' : 'Refresh'}</button>
          </div>
          {teamError && <div className="form-error workspace-users-error" role="alert">{teamError}</div>}
          <div className="doc-table workspace-users-table-wrap">
            <table>
              <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Joined</th><th>Actions</th></tr></thead>
              <tbody>
                {team.map((member) => (
                  <tr key={member.id}>
                    <td><strong>{member.name}</strong><span className="workspace-user-email">{member.email}</span></td>
                    <td>
                      <select aria-label={`Role for ${member.email}`} value={member.role} disabled={member.id === user?.id} onChange={(event) => updateTeamMember(member.id, `/users/${member.id}/role`, { role: event.target.value })}>
                        {ROLE_IDS.map((id) => <option value={id} key={id}>{ROLE_DEFINITIONS[id].label}</option>)}
                      </select>
                    </td>
                    <td><span className={`workspace-user-status ${member.is_active ? 'active' : 'inactive'}`}>{member.is_active ? 'Active' : 'Disabled'}</span></td>
                    <td className="muted">{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(member.created_at))}</td>
                    <td><button className="btn btn-ghost workspace-user-action" disabled={member.id === user?.id} onClick={() => updateTeamMember(member.id, `/users/${member.id}/status`, { is_active: !member.is_active })}>{member.is_active ? 'Disable' : 'Enable'}</button></td>
                  </tr>
                ))}
                {!teamLoading && team.length === 0 && <tr><td colSpan={5} className="muted" style={{ textAlign: 'center', padding: 22 }}>No workspace users found.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="card role-matrix-card">
        <div className="card-title">Permission matrix</div>
        <div className="doc-table role-matrix-wrap">
          <table className="role-matrix">
            <thead>
              <tr><th>Capability</th>{ROLE_IDS.map((id) => <th key={id}>{ROLE_DEFINITIONS[id].label}</th>)}</tr>
            </thead>
            <tbody>
              {PERMISSION_LABELS.map(([permission, label]) => {
                const isCurrentAllowed = canAccess(permission)
                return (
                  <tr key={permission}>
                    <td>{label}</td>
                    {ROLE_IDS.map((id) => {
                      const allowedForRole = id === role ? isCurrentAllowed : id === 'admin'
                      return (
                        <td key={id} className={allowedForRole ? 'permission-yes' : 'permission-no'}>
                          {allowedForRole ? 'Allowed' : '—'}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
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
      <p className="settings-note">Role changes are applied immediately by the authentication service. Clinical records are persisted in and served from the backend API — not stored locally in the browser.</p>
    </div>
  )
}
