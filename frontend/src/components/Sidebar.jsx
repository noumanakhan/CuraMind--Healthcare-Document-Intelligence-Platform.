import { IcGrid, IcDoc, IcUpload, IcChat, IcCompare, IcSettings, IcUsers, IcFileCheck } from './icons.jsx'
import brandLogo from '../logomain.png'
import { NAV } from '../data/mock.js'
import { useClinical } from '../context/PatientContext.jsx'

const ICONS = { IcGrid, IcDoc, IcUpload, IcChat, IcCompare, IcSettings, IcUsers, IcFileCheck }

export default function Sidebar({ active, setActive, open, setOpen }) {
  const { roleDefinition, canAccess } = useClinical()
  const visibleNavigation = NAV.filter((item) => item.id !== 'upload' || canAccess('documents:create'))

  return (
    <div className={'sidebar' + (open ? ' open' : '')}>
      <button
        type="button"
        className="brand"
        aria-label="Go to dashboard"
        onClick={() => {
          setActive('dashboard')
          setOpen(false)
        }}
      >
        <img className="brand-logo" src={brandLogo} alt="CuraMind" />
        <span className="brand-name"><span>Cura</span><span>Mind</span></span>
      </button>
      <div style={{ fontSize: 11, color: '#767c8c', padding: '0 8px 14px' }}>Clinical Document Intelligence</div>

      <div className="nav-label">Workspace</div>
      {visibleNavigation.map((item) => {
        const Icon = ICONS[item.icon]
        return (
          <button
            key={item.id}
            className={'nav-item' + (active === item.id ? ' active' : '')}
            onClick={() => {
              setActive(item.id)
              setOpen(false)
            }}
          >
            <Icon width={17} height={17} />
            {item.label}
          </button>
        )
      })}

      <div className="nav-label">Manage</div>
      <button
        className={'nav-item' + (active === 'settings' ? ' active' : '')}
        onClick={() => {
          setActive('settings')
          setOpen(false)
        }}
      >
        <IcSettings width={17} height={17} />
        Settings
      </button>

      <div className="sidebar-foot">
        <div className="user-chip">
          <div className="user-avatar">{roleDefinition.user.split(' ').map((part) => part[0]).join('').slice(0, 2)}</div>
          <div className="user-meta">
            <div className="name">{roleDefinition.user}</div>
            <div className="role" style={{ color: '#818989' }}>
              {roleDefinition.label}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
