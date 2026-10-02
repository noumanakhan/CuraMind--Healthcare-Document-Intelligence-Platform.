import { IcMenu, IcSearch, IcUpload } from './icons.jsx'
import { useClinical } from '../context/PatientContext.jsx'

export default function Topbar({ title, sub, setOpen, setActive }) {
  const { canAccess } = useClinical()
  return (
    <div className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button className="menu-btn" onClick={() => setOpen((o) => !o)}>
          <IcMenu width={18} height={18} />
        </button>
        <div>
          <div className="page-title">{title}</div>
          {sub && <div className="page-sub">{sub}</div>}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div className="search">
          <IcSearch width={15} height={15} />
          <span>Search documents…</span>
        </div>
        {canAccess('documents:create') && <button className="btn btn-primary" onClick={() => setActive('upload')}>
          <IcUpload width={15} height={15} />
          Upload
        </button>}
      </div>
    </div>
  )
}
