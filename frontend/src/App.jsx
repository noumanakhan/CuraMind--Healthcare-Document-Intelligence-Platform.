import { useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import Topbar from './components/Topbar.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Documents from './pages/Documents.jsx'
import Upload from './pages/Upload.jsx'
import Ask from './pages/Ask.jsx'
import Compare from './pages/Compare.jsx'
import Settings from './pages/Settings.jsx'
import Patients from './pages/Patients.jsx'
import PatientDetail from './pages/PatientDetail.jsx'
import WorkQueue from './pages/WorkQueue.jsx'
import AuthScreen from './components/AuthScreen.jsx'
import { TITLES } from './data/mock.js'

const VIEWS = {
  dashboard: Dashboard,
  documents: Documents,
  upload: Upload,
  ask: Ask,
  compare: Compare,
  workqueue: WorkQueue,
  settings: Settings,
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [active, setActive] = useState('dashboard')
  const [open, setOpen] = useState(false)
  const [selectedPatientId, setSelectedPatientId] = useState(null)
  const [selectedPatientTab, setSelectedPatientTab] = useState('overview')

  // Selecting a patient overrides the normal view switcher until the user backs out
  const showingPatientDetail = active === 'patients' && selectedPatientId

  const [title, sub] = showingPatientDetail
    ? ['Patient chart', 'Documents, labs, medications, and discharge workflow']
    : active === 'patients'
    ? ['Patients', 'Active roster across wards and outpatient']
    : TITLES[active]

  const goToPatients = (id, tab = 'overview') => {
    setActive('patients')
    setSelectedPatientTab(tab)
    setSelectedPatientId(id)
  }
  const openWorkItem = (id, tab) => {
    setActive('patients')
    setSelectedPatientTab(tab)
    setSelectedPatientId(id)
  }
  const backToRoster = () => setSelectedPatientId(null)

  const setActiveAndReset = (id) => {
    setActive(id)
    if (id !== 'patients') setSelectedPatientId(null)
  }

  let View
  if (showingPatientDetail) {
    View = () => <PatientDetail key={selectedPatientId} patientId={selectedPatientId} initialTab={selectedPatientTab} onBack={backToRoster} />
  } else if (active === 'dashboard') {
    View = () => <Dashboard onNavigate={setActiveAndReset} onOpenPatient={goToPatients} />
  } else if (active === 'patients') {
    View = () => <Patients onOpenPatient={goToPatients} />
  } else if (active === 'workqueue') {
    View = () => <WorkQueue onOpenPatient={openWorkItem} />
  } else {
    View = VIEWS[active]
  }

  return (
    <>
      <div className={`app${isAuthenticated ? '' : ' auth-preview'}`} aria-hidden={!isAuthenticated}>
        <Sidebar active={active} setActive={setActiveAndReset} open={open} setOpen={setOpen} />
        <div className="main">
          <Topbar title={title} sub={sub} setOpen={setOpen} setActive={setActiveAndReset} />
          <div className="content">
            <View />
          </div>
        </div>
      </div>
      {!isAuthenticated && <AuthScreen onComplete={() => setIsAuthenticated(true)} />}
    </>
  )
}
