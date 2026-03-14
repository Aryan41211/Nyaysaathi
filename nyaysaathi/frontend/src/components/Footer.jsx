import { Link } from 'react-router-dom'
import { useLanguage } from '../state/LanguageContext.jsx'

export default function Footer() {
  const { t } = useLanguage()
  return (
    <footer style={S.footer}>
      <div className="container">
        {/* Disclaimer banner */}
        <div style={S.disclaimer}>
          <span style={S.disclaimerIcon}>⚠️</span>
          <p style={S.disclaimerText}>
            <strong>{t('footer.legalDisclaimer')}</strong> {t('footer.legalBody')}{' '}
            <a href="tel:15100" style={S.link}>15100</a> (toll-free).
          </p>
        </div>

        <div style={S.grid}>
          <div>
            <div style={S.brand}>⚖️ NyaySaathi</div>
            <p style={S.tagline}>
              {t('footer.tagline')}
            </p>
          </div>
          <div>
            <div style={S.colHead}>{t('footer.navigate')}</div>
            <div style={S.colLinks}>
              <Link to="/"           style={S.link}>{t('nav.home')}</Link>
              <Link to="/search"     style={S.link}>{t('nav.find')}</Link>
              <Link to="/categories" style={S.link}>{t('footer.browseCategories')}</Link>
            </div>
          </div>
          <div>
            <div style={S.colHead}>{t('footer.emergency')}</div>
            <div style={S.colLinks}>
              <a href="tel:15100" style={S.link}>DLSA: 15100</a>
              <a href="tel:1091"  style={S.link}>Women: 1091</a>
              <a href="tel:14567" style={S.link}>Senior Citizen: 14567</a>
              <a href="tel:1930"  style={S.link}>Cyber Crime: 1930</a>
              <a href="tel:100"   style={S.link}>Police: 100</a>
            </div>
          </div>
        </div>

        <div style={S.bottom}>
          <span style={{ color: 'var(--ink-muted)', fontSize: '0.82rem' }}>
            © {new Date().getFullYear()} NyaySaathi. {t('footer.builtFor')}
          </span>
          <span style={{ color: 'var(--ink-muted)', fontSize: '0.82rem' }}>
            {t('footer.workflowsAndCats')}
          </span>
        </div>
      </div>
    </footer>
  )
}

const S = {
  footer: {
    background: 'var(--ink)',
    marginTop: '4rem',
    paddingTop: '2.5rem',
  },
  disclaimer: {
    display: 'flex', gap: '12px', alignItems: 'flex-start',
    background: 'rgba(212,97,26,0.15)',
    border: '1px solid rgba(212,97,26,0.3)',
    borderRadius: 'var(--r-md)',
    padding: '14px 18px',
    marginBottom: '2rem',
  },
  disclaimerIcon: { fontSize: '1.1rem', flexShrink: 0, marginTop: '2px' },
  disclaimerText: { color: '#E8C99A', fontSize: '0.84rem', lineHeight: 1.6 },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '2rem',
    paddingBottom: '2rem',
    borderBottom: '1px solid rgba(255,255,255,0.08)',
  },
  brand: {
    color: 'var(--saffron)', fontWeight: 700, fontSize: '1.1rem',
    marginBottom: '8px',
  },
  tagline: {
    color: 'rgba(255,255,255,0.45)', fontSize: '0.83rem', lineHeight: 1.6,
  },
  colHead: {
    color: 'rgba(255,255,255,0.7)', fontWeight: 600, fontSize: '0.78rem',
    textTransform: 'uppercase', letterSpacing: '0.8px',
    marginBottom: '10px',
  },
  colLinks: { display: 'flex', flexDirection: 'column', gap: '6px' },
  link: {
    color: 'rgba(255,255,255,0.5)', fontSize: '0.85rem',
    textDecoration: 'none', transition: 'color .15s',
  },
  bottom: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    flexWrap: 'wrap', gap: '8px',
    padding: '1.2rem 0',
  },
}
