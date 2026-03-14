import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useLanguage } from '../state/LanguageContext.jsx'

export default function Navbar() {
  const { pathname } = useLocation()
  const { t } = useLanguage()
  const [open, setOpen]       = useState(false)
  const [mobile, setMobile]   = useState(window.innerWidth < 700)

  useEffect(() => {
    const onResize = () => setMobile(window.innerWidth < 700)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // Close drawer on route change
  useEffect(() => { setOpen(false) }, [pathname])

  const links = [
    { to: '/',           label: t('nav.home') },
    { to: '/search',     label: t('nav.find') },
    { to: '/categories', label: t('nav.browse') },
  ]

  return (
    <nav style={S.nav}>
      <div className="container" style={S.inner}>

        {/* ── Logo ── */}
        <Link to="/" style={S.logo}>
          <span style={S.logoIcon}>⚖️</span>
          <span>
            <span style={S.logoMain}>NyaySaathi</span>
            <span style={S.logoSub}>{t('nav.legalGuidance')}</span>
          </span>
        </Link>

        {/* ── Right controls ── */}
        <div style={S.right}>
          {/* Desktop nav */}
          {!mobile && (
            <div style={S.links}>
              {links.map(l => (
                <Link key={l.to} to={l.to}
                  style={{ ...S.link, ...(pathname === l.to ? S.active : {}) }}>
                  {l.label}
                </Link>
              ))}
              <Link to="/signin" style={{ ...S.link, ...(pathname === '/signin' ? S.active : {}) }}>
                {t('nav.signin')}
              </Link>
              <Link to="/search" style={S.cta}>{t('nav.getHelp')}</Link>
            </div>
          )}

          {/* Mobile hamburger */}
          {mobile && (
            <button onClick={() => setOpen(o => !o)} style={S.ham} aria-label="Toggle menu">
              {open ? '✕' : '☰'}
            </button>
          )}
        </div>
      </div>

      {/* ── Mobile drawer ── */}
      {mobile && open && (
        <div style={S.drawer}>
          {links.map(l => (
            <Link key={l.to} to={l.to} style={S.drawerLink}>
              {l.label}
            </Link>
          ))}
          <Link to="/signin" style={S.drawerLink}>{t('nav.signin')}</Link>
          <Link to="/search" style={S.drawerCta}>{t('nav.getHelpNow')}</Link>
        </div>
      )}
    </nav>
  )
}

const S = {
  nav: {
    background: 'var(--paper)',
    borderBottom: '2px solid var(--border)',
    position: 'sticky', top: 0, zIndex: 100,
    boxShadow: 'var(--shadow-sm)',
  },
  inner: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between', height: '64px',
  },
  logo: {
    display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none',
  },
  logoIcon: { fontSize: '1.5rem' },
  logoMain: {
    display: 'block', fontWeight: 700, fontSize: '1.1rem',
    color: 'var(--saffron)', letterSpacing: '-0.3px',
  },
  logoSub: {
    display: 'block', fontSize: '0.62rem', color: 'var(--ink-muted)',
    fontWeight: 400, letterSpacing: '0.4px', textTransform: 'uppercase',
  },
  links: { display: 'flex', alignItems: 'center', gap: '4px' },
  right: { display: 'flex', alignItems: 'center', gap: '8px' },
  link: {
    padding: '6px 13px', borderRadius: 'var(--r-sm)',
    color: 'var(--ink-light)', fontWeight: 500, fontSize: '0.88rem',
    textDecoration: 'none', transition: 'all .15s',
  },
  active: { color: 'var(--teal)', background: 'var(--teal-light)' },
  cta: {
    marginLeft: '6px', padding: '8px 16px',
    background: 'var(--saffron)', color: '#fff',
    borderRadius: 'var(--r-sm)', fontWeight: 600,
    fontSize: '0.86rem', textDecoration: 'none',
  },
  ham: {
    background: 'none', border: '1px solid var(--border)',
    borderRadius: 'var(--r-sm)', fontSize: '1.2rem',
    cursor: 'pointer', color: 'var(--ink)',
    width: '38px', height: '38px',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  drawer: {
    display: 'flex', flexDirection: 'column', gap: '2px',
    background: 'var(--paper)', borderTop: '1px solid var(--border)',
    padding: '0.8rem 1.2rem 1.2rem',
  },
  drawerLink: {
    padding: '12px 8px', color: 'var(--ink-light)', fontWeight: 500,
    textDecoration: 'none', borderBottom: '1px solid var(--border-light)',
    fontSize: '0.95rem',
  },
  drawerCta: {
    marginTop: '10px', padding: '13px', background: 'var(--saffron)',
    color: '#fff', borderRadius: 'var(--r-sm)', fontWeight: 600,
    textAlign: 'center', textDecoration: 'none', fontSize: '0.95rem',
  },
}
