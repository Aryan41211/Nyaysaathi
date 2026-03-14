import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCategories, getCases } from '../services/api.js'
import { LoadingSpinner, ErrorMessage } from '../components/Feedback.jsx'
import { useLanguage } from '../state/LanguageContext.jsx'

const ICONS = {
  'Land and Property Disputes':            '🏡',
  'Labour and Wage Issues':                '👷',
  'Domestic Violence and Family Disputes': '🏠',
  'Cyber Fraud and Digital Scams':         '💻',
  'Consumer Complaints':                   '🛒',
  'Police Complaints and Local Crime':     '🚔',
  'Government Scheme and Public Service Issues': '🏛️',
  'Tenant–Landlord Disputes':              '🔑',
  'Environmental and Public Nuisance Complaints': '🌿',
  'Senior Citizen Protection Issues':      '👴',
}

export default function CategoriesPage() {
  const { t } = useLanguage()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeCat = searchParams.get('cat') || null

  const [categories, setCategories] = useState([])
  const [cases,      setCases]      = useState([])
  const [loadingCats, setLoadingCats] = useState(true)
  const [loadingCases, setLoadingCases] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getCategories()
      .then(r => setCategories(r.data || []))
      .catch(() => setError('Could not load categories.'))
      .finally(() => setLoadingCats(false))
  }, [])

  useEffect(() => {
    if (!activeCat) { setCases([]); return }
    setLoadingCases(true)
    getCases(activeCat)
      .then(r => setCases(r.data || []))
      .catch(() => setCases([]))
      .finally(() => setLoadingCases(false))
  }, [activeCat])

  if (loadingCats) return <div style={{ padding: '3rem 0' }}><LoadingSpinner message={t('categories.loadingCats')} /></div>
  if (error) return <div style={{ padding: '3rem 0' }}><div className="container"><ErrorMessage message={error} /></div></div>

  return (
    <div style={S.page}>
      <div className="container">
        <div style={S.header} className="anim-fade-up">
          <h1>{t('categories.title')}</h1>
          <p style={{ color: 'var(--ink-light)', marginTop: '8px' }}>
            {t('categories.subtitle')}
          </p>
        </div>

        {/* Uses CSS class cat-browse-layout for responsive: 260px sidebar → stacked on mobile */}
        <div className="cat-browse-layout">

          {/* Sidebar */}
          <div style={S.sidebar} className="categories-sidebar">
            <div style={S.sideTitle}>{t('categories.allCategories')}</div>
            {categories.map(cat => (
              <button
                key={cat.category}
                style={{ ...S.catBtn, ...(activeCat === cat.category ? S.catBtnActive : {}) }}
                onClick={() => setSearchParams({ cat: cat.category })}
              >
                <span style={S.catIcon}>{ICONS[cat.category] || '⚖️'}</span>
                <span style={S.catLabel}>
                  <span style={S.catName}>{cat.category}</span>
                  <span style={S.catCount}>✨ {cat.subcategory_count} {t('categories.workflows')}</span>
                </span>
              </button>
            ))}
          </div>

          {/* Main panel */}
          <div style={S.main}>
            {!activeCat && (
              <div style={S.welcome} className="anim-fade-up">
                <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>👆</div>
                <h3>{t('categories.selectPromptTitle')}</h3>
                <p style={{ color: 'var(--ink-muted)', marginTop: '8px', fontSize: '0.92rem' }}>
                  {t('categories.selectPromptBody')}
                </p>
                <Link to="/search" style={S.searchLink}>
                  {t('categories.searchDirect')}
                </Link>
              </div>
            )}

            {activeCat && loadingCases && <LoadingSpinner message={t('categories.loadingCases')} />}

            {activeCat && !loadingCases && cases.length > 0 && (
              <>
                <div style={S.catHeader} className="anim-fade-up">
                  <h2 style={{ fontSize: '1.2rem' }}>
                    {ICONS[activeCat] || '⚖️'} &nbsp;{activeCat}
                  </h2>
                  <span style={S.badge}>{cases.length} {t('categories.workflows')}</span>
                </div>
                <div style={S.grid}>
                  {cases.map((c, i) => (
                    <Link
                      key={c.subcategory}
                      to={`/case/${encodeURIComponent(c.subcategory)}`}
                      style={S.caseCard}
                      className={`anim-fade-up d${(i % 6) + 1}`}
                    >
                      <div style={S.caseTitle}>📄 {c.subcategory}</div>
                      <div style={S.caseDesc}>
                        {(c.problem_description || '').slice(0, 130)}…
                      </div>
                      <div style={S.caseArrow}>{t('categories.viewGuidance')}</div>
                    </Link>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

const S = {
  page: { padding: '2rem 0 4rem' },
  header: { marginBottom: '2rem' },
  sidebar: { background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden' },
  sideTitle: { padding: '12px 16px', fontWeight: 700, fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.6px', color: 'var(--ink-muted)', borderBottom: '1px solid var(--border)', background: 'var(--parchment)' },
  catBtn: { width: '100%', display: 'flex', alignItems: 'center', gap: '10px', padding: '11px 16px', background: 'none', border: 'none', borderBottom: '1px solid var(--border-light)', cursor: 'pointer', textAlign: 'left', transition: 'background .15s', fontFamily: 'var(--font)' },
  catBtnActive: { background: 'var(--teal-light)', borderLeft: '3px solid var(--teal)' },
  catIcon: { fontSize: '1.2rem', flexShrink: 0 },
  catLabel: { display: 'flex', flexDirection: 'column' },
  catName: { fontSize: '0.81rem', fontWeight: 600, color: 'var(--ink)', lineHeight: 1.3, textAlign: 'left' },
  catCount: { fontSize: '0.71rem', color: 'var(--ink-muted)', marginTop: '2px' },
  main: { minHeight: '300px' },
  welcome: { background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '3rem 2rem', textAlign: 'center' },
  searchLink: { display: 'inline-block', marginTop: '16px', color: 'var(--teal)', fontWeight: 600, fontSize: '0.9rem' },
  catHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '1rem' },
  badge: { background: 'var(--teal-light)', color: 'var(--teal)', borderRadius: '100px', padding: '4px 12px', fontSize: '0.78rem', fontWeight: 700 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px,1fr))', gap: '1rem' },
  caseCard: { background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '1.1rem', textDecoration: 'none', display: 'flex', flexDirection: 'column', gap: '8px' },
  caseTitle: { fontWeight: 700, fontSize: '0.9rem', color: 'var(--ink)', lineHeight: 1.3 },
  caseDesc: { fontSize: '0.8rem', color: 'var(--ink-muted)', lineHeight: 1.55, flex: 1 },
  caseArrow: { fontSize: '0.78rem', color: 'var(--teal)', fontWeight: 600 },
}
