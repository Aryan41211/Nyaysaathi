import { Link } from 'react-router-dom'
import SearchBox from '../components/SearchBox.jsx'
import { useLanguage } from '../state/LanguageContext.jsx'

const COMMON_ICONS = ['💼', '📱', '🏡', '🔑', '👴']

export default function SearchPage() {
  const { t } = useLanguage()
  const examples = t('searchBox.examples')
  const common = COMMON_ICONS.map((icon, idx) => ({ icon, text: examples[idx] || examples[0] || '' }))
  return (
    <div style={S.page}>
      <div className="container" style={S.inner}>
        <div style={S.header} className="anim-fade-up">
          <div style={S.badge}>{t('search.badge')}</div>
          <h1 style={S.title}>{t('search.title')}</h1>
          <p style={S.subtitle}>
            {t('search.subtitle')}
          </p>
        </div>

        <div style={S.box} className="anim-fade-up d2">
          <SearchBox large autoFocus />
        </div>

        <div style={S.common} className="anim-fade-up d3">
          <div style={S.commonTitle}>{t('search.commonTitle')}</div>
          <div style={S.quickHint}>Tap any example to search instantly.</div>
          <div style={S.grid}>
            {common.map(c => (
              <Link
                key={c.text}
                to={`/results?query=${encodeURIComponent(c.text)}`}
                style={S.chip}
              >
                <span>{c.icon}</span>
                <span style={S.chipText}>{c.text}</span>
              </Link>
            ))}
          </div>
        </div>

        <div style={S.note} className="anim-fade-up d4">
          <strong>{t('search.disclaimer')}</strong>{' '}
          <a href="tel:15100" style={{ color: 'var(--teal)', fontWeight: 700 }}>15100</a>.
        </div>
      </div>
    </div>
  )
}

const S = {
  page: { padding: '3rem 0 4rem' },
  inner: { maxWidth: '680px', margin: '0 auto' },
  header: { textAlign: 'center', marginBottom: '2rem' },
  badge: {
    display: 'inline-block',
    background: 'var(--teal-light)', color: 'var(--teal)',
    borderRadius: '100px', padding: '5px 16px',
    fontSize: '0.8rem', fontWeight: 600, marginBottom: '14px',
  },
  title: { marginBottom: '10px' },
  subtitle: {
    color: 'var(--ink-light)', fontSize: '1rem',
    lineHeight: 1.7, maxWidth: '520px', margin: '0 auto',
  },
  box: {
    background: 'var(--paper)', border: '1px solid var(--border)',
    borderRadius: 'var(--r-xl)', padding: '1.8rem',
    boxShadow: 'var(--shadow-md)', marginBottom: '2rem',
  },
  common: { marginBottom: '2rem' },
  commonTitle: {
    fontSize: '0.78rem', fontWeight: 700,
    color: 'var(--ink-muted)', textTransform: 'uppercase',
    letterSpacing: '0.5px', marginBottom: '10px',
  },
  quickHint: {
    fontSize: '0.8rem',
    color: 'var(--ink-muted)',
    marginBottom: '10px',
  },
  grid: { display: 'flex', flexWrap: 'wrap', gap: '8px' },
  chip: {
    display: 'flex', alignItems: 'center', gap: '6px',
    background: 'var(--paper)', border: '1px solid var(--border)',
    borderRadius: 'var(--r-sm)', padding: '6px 12px',
    textDecoration: 'none',
  },
  chipText: { fontSize: '0.82rem', color: 'var(--ink-light)' },
  note: {
    background: 'var(--saffron-light)', border: '1px solid #F5C6A0',
    borderRadius: 'var(--r-md)', padding: '12px 16px',
    fontSize: '0.83rem', color: 'var(--saffron-dark)', lineHeight: 1.6,
  },
}
