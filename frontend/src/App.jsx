import { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
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
import AppointmentsOverview from './pages/AppointmentsOverview.jsx'
import AuthScreen from './components/AuthScreen.jsx'
import { useAuth } from './context/AuthContext.jsx'
import { TITLES } from './data/mock.js'

function WorkspaceRoutes({ navigateTo, openPatient }) {
  return (
    <Routes>
      <Route path="/" element={<Dashboard onNavigate={navigateTo} onOpenPatient={openPatient} />} />
      <Route path="/workqueue" element={<WorkQueue onOpenPatient={openPatient} />} />
      <Route path="/patients" element={<Patients onOpenPatient={openPatient} />} />
      <Route path="/appointments" element={<AppointmentsOverview />} />
      <Route path="/patients/:patientId" element={<PatientChartRoute onBack={() => navigateTo('patients')} />} />
      <Route path="/patients/:patientId/:tab" element={<PatientChartRoute onBack={() => navigateTo('patients')} />} />
      <Route path="/documents" element={<Documents />} />
      <Route path="/upload" element={<Upload />} />
      <Route path="/ask" element={<Ask />} />
      <Route path="/compare" element={<Compare />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function PatientChartRoute({ onBack }) {
  const { patientId, tab = 'overview' } = useParams()
  return <PatientDetail key={patientId} patientId={patientId} initialTab={tab} onBack={onBack} />
}

function AppShell() {
  const { user, authLoading, logout } = useAuth()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const restoredSession = useRef(false)
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const isPatientChart = location.pathname.startsWith('/patients/')
  const active = isPatientChart ? 'patients' : location.pathname.split('/')[1] || 'dashboard'
  const [title, sub] = isPatientChart
    ? ['Patient chart', 'Encounters, problems, documents, and clinical context']
    : active === 'patients'
      ? ['Patients', 'Active roster across wards and outpatient']
      : TITLES[active] || TITLES.dashboard

  const navigateTo = (destination) => {
    const path = destination.startsWith('/') ? destination : destination === 'dashboard' ? '/' : `/${destination}`
    navigate(path)
  }
  const openPatient = (patientId, tab = 'overview') => {
    if (!patientId) return
    navigate(`/patients/${encodeURIComponent(patientId)}/${encodeURIComponent(tab)}`)
  }

  const completeAuthentication = () => setIsAuthenticated(true)
  const handleLogout = async () => {
    await logout()
    setIsAuthenticated(false)
    navigate('/')
  }

  useEffect(() => {
    if (authLoading) return
    if (!restoredSession.current) {
      restoredSession.current = true
      if (user) setIsAuthenticated(true)
      return
    }
    if (!user) setIsAuthenticated(false)
  }, [authLoading, user])

  return (
    <>
      <div className={`app${isAuthenticated ? '' : ' auth-preview'}`} aria-hidden={!isAuthenticated}>
        <Sidebar active={active} setActive={navigateTo} open={open} setOpen={setOpen} onLogout={handleLogout} />
        <div className="main">
          <Topbar title={title} sub={sub} setOpen={setOpen} setActive={navigateTo} />
          <div className="content">
            <WorkspaceRoutes navigateTo={navigateTo} openPatient={openPatient} />
          </div>
        </div>
      </div>
      {authLoading && <div className="auth-loading-screen"><div className="auth-loading-mark" /><span>Restoring secure session…</span></div>}
      {!authLoading && !isAuthenticated && <AuthScreen onComplete={completeAuthentication} />}
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}
