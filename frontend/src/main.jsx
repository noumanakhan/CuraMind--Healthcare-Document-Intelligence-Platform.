import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { PatientProvider } from './context/PatientContext.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import favicon from './logomain.png'
import './styles/index.css'

const THEME_KEY = 'curamind_theme'

function initializeTheme() {
  let theme = 'system'
  try {
    const savedTheme = localStorage.getItem(THEME_KEY)
    if (savedTheme === 'light' || savedTheme === 'dark' || savedTheme === 'system') theme = savedTheme
  } catch (error) {
    // Use the operating-system preference when browser storage is unavailable.
  }

  if (theme === 'system') {
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.removeProperty('color-scheme')
  } else {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
  }
}

initializeTheme()

const faviconLink = document.querySelector('link[rel="icon"]') || document.createElement('link')
faviconLink.rel = 'icon'
faviconLink.href = favicon
document.head.appendChild(faviconLink)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <PatientProvider>
        <App />
      </PatientProvider>
    </AuthProvider>
  </React.StrictMode>
)
