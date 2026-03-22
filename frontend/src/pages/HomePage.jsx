import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SearchBox from '../components/SearchBox.jsx'
import { getCategories } from '../services/api.js'
import { useLanguage } from '../state/LanguageContext.jsx'

const CATEGORY_ICONS = {
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

const STATS = [
  { n: '201',   label: 'Legal Workflows' },
  { n: '10',    label: 'Categories' },
  { n: 'Free',  label: 'Always Free' },
  { n: '24/7',  label: 'Available' },
]

export default function HomePage() {
  const { t } = useLanguage()
  const [categories, setCategories] = useState([])

  useEffect(() => {
    getCategories().then(r => setCategories(r.data || [])).catch(() => {})
  }, [])

  return (
    <div>
      {/* Hero */}
      <section style={S.hero}>
        <div className="container">
          {/* Uses CSS class for responsive 2-col → 1-col */}
          <div className="hero-grid">
            <div style={S.heroLeft}>
              <div style={S.badge} className="anim-fade-up d1">{t('home.forCitizens')}</div>
              <h1 style={S.heroTitle} className="anim-fade-up d2">
                {t('home.title1')}<br />
                <span style={S.accent}>{t('home.title2')}</span><br />
                {t('home.title3')}
              </h1>
              <p style={S.heroSubtitle} className="anim-fade-up d3">
                {t('home.subtitle')}
              </p>
              <div style={S.searchWrap} className="anim-fade-up d4">
                <SearchBox large autoFocus />
              </div>
            </div>
            <div className="anim-fade-up d3">
              <div style={S.infoCard}>
                <div style={S.infoTitle}>{t('home.noteTitle')}</div>
                <p style={S.infoText}>
                  {t('home.noteBody')}
                </p>
                <div style={S.infoHelp}>
                  <span style={S.helpDot} />
                  {t('home.legalAid')} <a href="tel:15100" style={S.helpLink}>15100</a>
                </div>
                <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {['🏠 Domestic Violence → 1091', '💻 Cyber Crime → 1930', '👴 Senior Citizen → 14567', '🚔 Police → 100'].map(h => (
                    <div key={h} style={S.helpRow}>{h}</div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats bar – CSS class for responsive */}
      <div style={S.statsBar}>
        <div className="container">
          <div className="stats-grid">
            {STATS.map((s, i) => (
              <div key={s.label} style={{ ...S.stat, ...(i < 3 ? S.statBorder : {}) }}>
                <span style={S.statNum}>{s.n}</span>
                <span style={S.statLabel}>
                  {s.label === 'Legal Workflows' && t('home.stats.workflows')}
                  {s.label === 'Categories' && t('home.stats.categories')}
                  {s.label === 'Always Free' && t('home.stats.free')}
                  {s.label === 'Available' && t('home.stats.available')}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* How it works – CSS class for responsive */}
      <section style={S.section}>
        <div className="container">
          <h2 style={S.sectionTitle} className="anim-fade-up">{t('home.howItWorks')}</h2>
          <p style={S.sectionSub} className="anim-fade-up d1">{t('home.howSub')}</p>
          <div className="steps-grid">
            {[
              { n:'1', icon:'✍️', title:t('home.steps.oneTitle'), desc:t('home.steps.oneDesc') },
              { n:'2', icon:'🔍', title:t('home.steps.twoTitle'), desc:t('home.steps.twoDesc') },
              { n:'3', icon:'📋', title:t('home.steps.threeTitle'), desc:t('home.steps.threeDesc') },
            ].map((step, i) => (
              <div key={step.n} style={S.stepCard} className={`anim-fade-up d${i+1}`}>
                <div style={S.stepNum}>{step.n}</div>
                <div style={S.stepIcon}>{step.icon}</div>
                <h3 style={S.stepTitle}>{step.title}</h3>
                <p style={S.stepDesc}>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Categories */}
      <section style={{ ...S.section, background: 'var(--paper)' }}>
        <div className="container">
          <h2 style={S.sectionTitle} className="anim-fade-up">{t('home.browseTitle')}</h2>
          <p style={S.sectionSub} className="anim-fade-up d1">
            {t('home.browseSub')}
          </p>
          <div style={S.catGrid} className="cat-grid">
            {(categories.length > 0
              ? categories
              : Object.keys(CATEGORY_ICONS).map(c => ({ category: c, subcategory_count: 0 }))
            ).map((cat, i) => (
              <Link
                key={cat.category}
                to={`/categories?cat=${encodeURIComponent(cat.category)}`}
                style={S.catCard}
                className={`anim-fade-up d${(i % 6) + 1}`}
              >
                <span style={S.catIcon}>{CATEGORY_ICONS[cat.category] || '⚖️'}</span>
                <span style={S.catName}>{cat.category}</span>
                {cat.subcategory_count > 0 && (
                  <span style={S.catCount}>{cat.subcategory_count} workflows</span>
                )}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={S.cta}>
        <div className="container" style={{ textAlign: 'center' }}>
          <h2 style={{ color: '#fff', marginBottom: '12px' }} className="anim-fade-up">
            {t('home.ctaTitle')}
          </h2>
          <p style={{ color: 'rgba(255,255,255,0.8)', marginBottom: '24px', fontSize: '1.05rem' }} className="anim-fade-up d1">
            {t('home.ctaSub')}
          </p>
          <Link to="/search" style={S.ctaBtn} className="anim-fade-up d2">
            {t('home.ctaBtn')}
          </Link>
        </div>
      </section>
    </div>
  )
}

const S = {
  hero: { background: 'linear-gradient(135deg, var(--parchment) 0%, #FFF5EB 100%)', borderBottom: '1px solid var(--border)', padding: '4rem 0 3rem' },
  heroLeft: { display: 'flex', flexDirection: 'column', gap: '18px' },
  badge: { display: 'inline-flex', alignItems: 'center', background: 'var(--saffron-light)', color: 'var(--saffron-dark)', border: '1px solid #F5C6A0', borderRadius: '100px', padding: '5px 14px', fontSize: '0.8rem', fontWeight: 600, width: 'fit-content' },
  heroTitle: { fontWeight: 800, lineHeight: 1.1, color: 'var(--ink)' },
  accent: { color: 'var(--saffron)' },
  heroSubtitle: { fontSize: '1.05rem', color: 'var(--ink-light)', lineHeight: 1.75, maxWidth: '480px' },
  searchWrap: { background: 'var(--paper)', borderRadius: 'var(--r-lg)', padding: '1.4rem', boxShadow: 'var(--shadow-md)', border: '1px solid var(--border)' },
  infoCard: { background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '1.4rem', borderLeft: '4px solid var(--saffron)' },
  infoTitle: { fontWeight: 700, fontSize: '0.95rem', marginBottom: '8px', color: 'var(--ink)' },
  infoText: { fontSize: '0.875rem', color: 'var(--ink-light)', lineHeight: 1.65 },
  infoHelp: { display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', fontSize: '0.85rem', color: 'var(--ink-light)' },
  helpDot: { width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', display: 'inline-block', flexShrink: 0 },
  helpLink: { color: 'var(--teal)', fontWeight: 700 },
  helpRow: { fontSize: '0.8rem', color: 'var(--ink-muted)', padding: '4px 8px', background: 'var(--parchment)', borderRadius: 'var(--r-sm)' },
  statsBar: { background: 'var(--ink)', padding: '1rem 0' },
  stat: { padding: '0.6rem 0' },
  statBorder: { borderRight: '1px solid rgba(255,255,255,0.1)' },
  statNum: { display: 'block', fontSize: '1.5rem', fontWeight: 800, color: 'var(--saffron)' },
  statLabel: { fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.5px' },
  section: { padding: '4rem 0' },
  sectionTitle: { textAlign: 'center', marginBottom: '8px' },
  sectionSub: { textAlign: 'center', color: 'var(--ink-muted)', marginBottom: '2.5rem', fontSize: '1rem' },
  stepCard: { background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '1.8rem 1.4rem', textAlign: 'center', position: 'relative' },
  stepNum: { position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)', background: 'var(--saffron)', color: '#fff', width: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.8rem' },
  stepIcon: { fontSize: '2.2rem', margin: '12px 0 10px' },
  stepTitle: { fontWeight: 700, marginBottom: '8px', color: 'var(--ink)', fontSize: '1rem' },
  stepDesc: { fontSize: '0.875rem', color: 'var(--ink-light)', lineHeight: 1.65 },
  catGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px,1fr))', gap: '1rem' },
  catCard: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', padding: '1.4rem 1rem', background: 'var(--parchment)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', textDecoration: 'none', textAlign: 'center' },
  catIcon: { fontSize: '2rem' },
  catName: { fontSize: '0.82rem', fontWeight: 600, color: 'var(--ink)', lineHeight: 1.3 },
  catCount: { fontSize: '0.74rem', color: 'var(--teal)', fontWeight: 600 },
  cta: { background: 'linear-gradient(135deg, var(--teal-dark), var(--teal))', padding: '4rem 0' },
  ctaBtn: { display: 'inline-block', padding: '16px 36px', background: 'var(--saffron)', color: '#fff', borderRadius: 'var(--r-md)', fontWeight: 700, fontSize: '1.05rem', textDecoration: 'none' },
}
