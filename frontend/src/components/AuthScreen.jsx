import { useEffect, useState } from 'react'
import brandLogo from '../logomain.png'
import { IcEye, IcEyeOff, IcShield } from './icons.jsx'

export default function AuthScreen({ onComplete }) {
  const [mode, setMode] = useState('login')
  const [showPassword, setShowPassword] = useState(false)
  const [isExiting, setIsExiting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isExiting) return undefined
    const timeout = window.setTimeout(onComplete, 560)
    return () => window.clearTimeout(timeout)
  }, [isExiting, onComplete])

  useEffect(() => {
    const keepFocusInCard = (event) => {
      if (event.key !== 'Tab') return
      const focusable = [...document.querySelectorAll('.auth-card button:not(:disabled), .auth-card input:not(:disabled)')]
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && (document.activeElement === first || !document.querySelector('.auth-card')?.contains(document.activeElement))) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', keepFocusInCard)
    return () => document.removeEventListener('keydown', keepFocusInCard)
  }, [])

  const isSignup = mode === 'signup'

  const submit = (event) => {
    event.preventDefault()
    if (isExiting) return
    const formData = new FormData(event.currentTarget)
    const password = String(formData.get('password') || '')
    const confirmPassword = String(formData.get('confirmPassword') || '')

    if (isSignup && password !== confirmPassword) {
      setError('Those passwords don’t match. Please try again.')
      return
    }

    setError('')
    setIsExiting(true)
  }

  const changeMode = (nextMode) => {
    setMode(nextMode)
    setError('')
  }

  return (
    <div className={`auth-screen${isExiting ? ' is-exiting' : ''}`}>
      <div className="auth-backdrop" aria-hidden="true" />
      <section className="auth-card" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <div className="auth-card-topline" />
        <div className="auth-brand">
          <img src={brandLogo} alt="" />
          <span><strong>Cura</strong><b>Mind</b></span>
        </div>

        <div className="auth-heading">
          <div className="auth-eyebrow">Clinical intelligence workspace</div>
          <h1 id="auth-title">{isSignup ? 'Create your account' : 'Welcome back'}</h1>
          <p>{isSignup ? 'A clearer view of care starts here.' : 'Sign in to continue to your care workspace.'}</p>
        </div>

        <div className="auth-mode-switch" role="tablist" aria-label="Account access">
          <button type="button" role="tab" aria-selected={!isSignup} className={!isSignup ? 'active' : ''} onClick={() => changeMode('login')}>Sign in</button>
          <button type="button" role="tab" aria-selected={isSignup} className={isSignup ? 'active' : ''} onClick={() => changeMode('signup')}>Create account</button>
        </div>

        <form className="auth-form" onSubmit={submit}>
          {isSignup && (
            <label className="auth-field">
              <span>Full name</span>
              <input name="name" type="text" autoComplete="name" placeholder="Your name" required />
            </label>
          )}
          <label className="auth-field">
            <span>Work email</span>
            <input name="email" type="email" autoComplete="email" placeholder="name@organization.com" required />
          </label>
          <label className="auth-field">
            <span>Password</span>
            <span className="auth-password-wrap">
              <input name="password" type={showPassword ? 'text' : 'password'} autoComplete={isSignup ? 'new-password' : 'current-password'} placeholder="At least 8 characters" minLength={8} required />
              <button type="button" className="auth-password-toggle" onClick={() => setShowPassword((shown) => !shown)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                {showPassword ? <IcEyeOff width={17} height={17} /> : <IcEye width={17} height={17} />}
              </button>
            </span>
          </label>
          {isSignup && (
            <label className="auth-field">
              <span>Confirm password</span>
              <input name="confirmPassword" type={showPassword ? 'text' : 'password'} autoComplete="new-password" placeholder="Enter password again" minLength={8} required />
            </label>
          )}

          {error && <div className="auth-error" role="alert">{error}</div>}

          {!isSignup && <button type="button" className="auth-forgot" onClick={() => setError('Password recovery will be available when authentication is connected.')}>Forgot password?</button>}

          <button className="auth-submit" type="submit" disabled={isExiting}>
            {isExiting ? 'Opening your workspace…' : isSignup ? 'Create account' : 'Sign in'}
            <span aria-hidden="true">↗</span>
          </button>
        </form>

        <div className="auth-security-note"><IcShield width={15} height={15} /><span>Your workspace is designed around privacy and responsible clinical review.</span></div>
        <p className="auth-demo-note">Prototype preview · Authentication is simulated locally and is not connected to a secure account service.</p>
      </section>
      <div className="auth-bottom-caption"><span>CURAMIND</span><i /> CLINICAL DOCUMENT INTELLIGENCE</div>
    </div>
  )
}
