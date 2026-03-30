import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useLanguage } from '../state/LanguageContext.jsx'
import { useAuth } from '../state/AuthContext.jsx'

export default function SignInPage() {
  const { t } = useLanguage()
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const onSubmit = (e) => {
    e.preventDefault()
    setError('')

    const result = login(email.trim(), password)
    if (!result.ok) {
      setSuccess(false)
      setError(result.message)
      return
    }

    setSuccess(true)
    const redirectTo = location.state?.from?.pathname || '/'
    setTimeout(() => navigate(redirectTo, { replace: true }), 500)
  }

  return (
    <div style={S.page}>
      <div className="container" style={S.inner}>
        <div style={S.header} className="anim-fade-up">
          <h1 style={{ marginBottom: '10px' }}>{t('signin.title')}</h1>
          <p style={S.sub}>{t('signin.subtitle')}</p>
        </div>

        <div style={S.card} className="anim-fade-up d2">
          {success && (
            <div style={S.success} role="status">
              {t('signin.success')}
            </div>
          )}

          {error && (
            <div style={S.error} role="alert">
              {error}
            </div>
          )}

          <form onSubmit={onSubmit} style={S.form}>
            <label style={S.label}>
              {t('signin.email')}
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="text"
                placeholder="admin"
                style={S.input}
                required
              />
            </label>

            <label style={S.label}>
              {t('signin.password')}
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                placeholder="••••••••"
                style={S.input}
                required
              />
            </label>

            <button type="submit" style={S.button}>
              {t('signin.button')} →
            </button>

            <div style={S.note}>
              <span style={{ fontWeight: 700 }}>ℹ️</span> {t('signin.demoNote')}
              {' '}
              Use username <strong>admin</strong> and password <strong>1234</strong>.
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

const S = {
  page: { padding: '3rem 0 4rem' },
  inner: { maxWidth: '540px', margin: '0 auto' },
  header: { textAlign: 'center', marginBottom: '1.5rem' },
  sub: { color: 'var(--ink-light)', fontSize: '1rem', lineHeight: 1.7 },
  card: {
    background: 'var(--paper)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-xl)',
    padding: '1.8rem',
    boxShadow: 'var(--shadow-md)',
  },
  success: {
    background: 'var(--success-bg)',
    border: '1px solid rgba(26,107,69,0.2)',
    color: 'var(--success)',
    borderRadius: 'var(--r-md)',
    padding: '10px 12px',
    fontSize: '0.9rem',
    fontWeight: 600,
    marginBottom: '12px',
  },
  error: {
    background: '#FFF1F1',
    border: '1px solid #F5B5B5',
    color: '#9B1C1C',
    borderRadius: 'var(--r-md)',
    padding: '10px 12px',
    fontSize: '0.9rem',
    fontWeight: 600,
    marginBottom: '12px',
  },
  form: { display: 'flex', flexDirection: 'column', gap: '12px' },
  label: { display: 'flex', flexDirection: 'column', gap: '6px', fontWeight: 700, fontSize: '0.88rem', color: 'var(--ink)' },
  input: {
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-md)',
    padding: '11px 12px',
    fontFamily: 'var(--font)',
    fontSize: '0.95rem',
    outline: 'none',
  },
  button: {
    marginTop: '6px',
    padding: '12px 16px',
    background: 'var(--saffron)',
    color: '#fff',
    border: 'none',
    borderRadius: 'var(--r-md)',
    fontWeight: 800,
    fontSize: '0.95rem',
    cursor: 'pointer',
  },
  note: {
    marginTop: '8px',
    background: 'var(--parchment)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-md)',
    padding: '10px 12px',
    fontSize: '0.85rem',
    color: 'var(--ink-light)',
    lineHeight: 1.55,
  },
}
