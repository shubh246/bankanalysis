import { useState } from 'react'
import { login, register, setToken } from '../api'

export default function Login({ onLoggedIn }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const switchMode = (next) => {
    setMode(next)
    setError(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const res = mode === 'login' ? await login(username, password) : await register(username, password)
      setToken(res.data.access_token)
      onLoggedIn()
    } catch (e) {
      setError(e.response?.data?.detail || `${mode === 'login' ? 'Login' : 'Registration'} failed. Please try again.`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h2>Bank Statement Analysis</h2>
        <p className="muted">
          {mode === 'login' ? 'Sign in to continue.' : 'Create an account to get started.'}
        </p>
        <div className="field">
          <label>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            required
          />
        </div>
        <div className="field">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={mode === 'register' ? 6 : undefined}
            required
          />
          {mode === 'register' && <span className="muted">At least 6 characters.</span>}
        </div>
        {error && <div className="alert alert-error">{error}</div>}
        <button type="submit" disabled={busy}>
          {busy ? (mode === 'login' ? 'Signing in...' : 'Creating account...') : (mode === 'login' ? 'Sign in' : 'Create account')}
        </button>
        <p className="muted login-switch">
          {mode === 'login' ? (
            <>Don&apos;t have an account? <button type="button" className="btn-link" onClick={() => switchMode('register')}>Register</button></>
          ) : (
            <>Already have an account? <button type="button" className="btn-link" onClick={() => switchMode('login')}>Sign in</button></>
          )}
        </p>
      </form>
    </div>
  )
}
