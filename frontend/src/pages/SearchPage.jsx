import { Link } from 'react-router-dom'
import SearchBox from '../components/SearchBox.jsx'
import { useLanguage } from '../state/LanguageContext.jsx'

export default function SearchPage() {
  const { t } = useLanguage()
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

        <div style={S.note} className="anim-fade-up d3">
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
  note: {
    background: 'var(--saffron-light)', border: '1px solid #F5C6A0',
    borderRadius: 'var(--r-md)', padding: '12px 16px',
    fontSize: '0.83rem', color: 'var(--saffron-dark)', lineHeight: 1.6,
  },
}