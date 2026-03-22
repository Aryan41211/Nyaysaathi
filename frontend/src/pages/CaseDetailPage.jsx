import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { getCaseDetail } from '../services/api.js'
import { LoadingSpinner, ErrorMessage } from '../components/Feedback.jsx'
import { useLanguage } from '../state/LanguageContext.jsx'

export default function CaseDetailPage() {
  const { t } = useLanguage()
  const { subcategory } = useParams()
  const navigate = useNavigate()
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [copied,  setCopied]  = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getCaseDetail(decodeURIComponent(subcategory))
      .then(r => setData(r.data))
      .catch(e => setError(e?.response?.data?.error || 'Could not load case details.'))
      .finally(() => setLoading(false))
  }, [subcategory])

  const copyTemplate = () => {
    if (!data?.complaint_template) return
    navigator.clipboard.writeText(data.complaint_template)
      .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2500) })
      .catch(() => alert(t('caseDetail.couldNotCopy')))
  }

  if (loading) return <div style={{ padding: '3rem 0' }}><LoadingSpinner message={t('caseDetail.loading')} /></div>
  if (error)   return <div style={{ padding: '3rem 0' }}><div className="container"><ErrorMessage message={error} onRetry={() => navigate(-1)} /></div></div>
  if (!data)   return null

  const steps    = data.workflow_steps      || []
  const docs     = data.required_documents  || []
  const auths    = data.authorities         || []
  const esc      = data.escalation_path     || []
  const portals  = data.online_portals      || []
  const helplines = data.helplines          || []

  return (
    <div style={S.page}>
      <div className="container">
        {/* Breadcrumb */}
        <div style={S.breadcrumb} className="anim-fade-up">
          <Link to="/" style={S.breadLink}>{t('common.home')}</Link>
          <span style={S.sep}>›</span>
          <Link to="/categories" style={S.breadLink}>{t('common.categories')}</Link>
          <span style={S.sep}>›</span>
          <Link to={`/categories?cat=${encodeURIComponent(data.category)}`} style={S.breadLink}>
            {data.category}
          </Link>
          <span style={S.sep}>›</span>
          <span style={{ color: 'var(--ink-muted)', fontSize: '0.85rem' }}>{data.subcategory}</span>
        </div>

        {/* Header */}
        <div style={S.header} className="anim-fade-up d1">
          <span style={S.catTag}>{data.category}</span>
          <h1 style={S.title}>{data.subcategory}</h1>
          {data.problem_description && (
            <p style={S.desc}>{data.problem_description}</p>
          )}
        </div>

        {/* 2-col on desktop, stacked on mobile via CSS class */}
        <div className="case-detail-layout">

          {/* Left: main content */}
          <div style={S.main}>

            {/* Steps */}
            {steps.length > 0 && (
              <div style={{ ...S.card, borderTop: '3px solid var(--saffron)' }} className="anim-fade-up">
                <h2 style={{ ...S.cardTitle, color: 'var(--saffron)' }}>{t('caseDetail.stepsTitle')}</h2>
                <div style={S.stepsList}>
                  {steps.map((step, i) => (
                    <div key={i} style={S.stepRow}>
                      <div style={S.stepBubble}>{i + 1}</div>
                      <p style={S.stepText}>{step}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Escalation */}
            {esc.length > 0 && (
              <div style={{ ...S.card, borderTop: '3px solid var(--indigo)' }} className="anim-fade-up">
                <h2 style={{ ...S.cardTitle, color: 'var(--indigo)' }}>{t('caseDetail.escalationTitle')}</h2>
                {esc.map((e, i) => (
                  <div key={i} style={S.escItem}>
                    <span style={S.escArrow}>→</span>
                    <span style={S.escText}>{e}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Complaint Template */}
            {data.complaint_template && (
              <div style={{ ...S.card, borderTop: '3px solid var(--teal)' }} className="anim-fade-up">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <h2 style={{ ...S.cardTitle, color: 'var(--teal)', marginBottom: 0 }}>{t('caseDetail.templateTitle')}</h2>
                  <button onClick={copyTemplate} style={S.copyBtn}>
                    {copied ? t('caseDetail.copied') : t('caseDetail.copy')}
                  </button>
                </div>
                <pre style={S.template}>{data.complaint_template}</pre>
              </div>
            )}
          </div>

          {/* Right: sidebar */}
          <div className="case-sidebar" style={S.sidebar}>

            {/* Documents */}
            {docs.length > 0 && (
              <div style={{ ...S.sideCard, borderLeft: '3px solid var(--saffron)' }} className="anim-fade-up">
                <h3 style={{ ...S.sideTitle, color: 'var(--saffron)' }}>{t('caseDetail.requiredDocs')}</h3>
                <ul style={S.docList}>
                  {docs.map((d, i) => (
                    <li key={i} style={S.docItem}>
                      <span style={S.docDot} />{d}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Authorities */}
            {auths.length > 0 && (
              <div style={{ ...S.sideCard, borderLeft: '3px solid var(--teal)' }} className="anim-fade-up">
                <h3 style={{ ...S.sideTitle, color: 'var(--teal)' }}>{t('caseDetail.whomToApproach')}</h3>
                {auths.map((a, i) => (
                  <div key={i} style={S.authItem}>
                    <div style={S.authName}>{typeof a === 'object' ? a.name : a}</div>
                    {a.level && <div style={S.authLevel}>{a.level} {t('caseDetail.level')}</div>}
                  </div>
                ))}
              </div>
            )}

            {/* Online Portals */}
            {portals.length > 0 && (
              <div style={{ ...S.sideCard, borderLeft: '3px solid var(--indigo)' }} className="anim-fade-up">
                <h3 style={{ ...S.sideTitle, color: 'var(--indigo)' }}>{t('caseDetail.portals')}</h3>
                {portals.map((p, i) => (
                  <div key={i} style={{ marginBottom: '6px' }}>
                    {p.startsWith('http')
                      ? <a href={p.split(' ')[0]} target="_blank" rel="noreferrer" style={S.portalLink}>{p}</a>
                      : <span style={{ fontSize: '0.83rem', color: 'var(--ink-light)' }}>{p}</span>}
                  </div>
                ))}
              </div>
            )}

            {/* Helplines */}
            {helplines.length > 0 && (
              <div style={{ ...S.sideCard, borderLeft: '3px solid var(--success)' }} className="anim-fade-up">
                <h3 style={{ ...S.sideTitle, color: 'var(--success)' }}>{t('caseDetail.helplines')}</h3>
                {helplines.map((h, i) => (
                  <div key={i} style={S.helplineItem}>{h}</div>
                ))}
              </div>
            )}

            {/* Free legal aid box */}
            <div style={S.aidBox} className="anim-fade-up">
              <div style={S.aidTitle}>{t('caseDetail.legalHelp')}</div>
              <p style={S.aidText}>
                {t('caseDetail.legalHelpBody')}
              </p>
              <a href="tel:15100" style={S.aidBtn}>{t('caseDetail.callFree')}</a>
            </div>
          </div>
        </div>

        {/* Disclaimer */}
        <div style={S.disclaimer}>
          {t('caseDetail.disclaimer')}
        </div>
      </div>
    </div>
  )
}

const S = {
  page: { padding: '1.5rem 0 4rem' },
  breadcrumb: { display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '4px', marginBottom: '1.5rem' },
  breadLink: { color: 'var(--teal)', fontSize: '0.84rem', textDecoration: 'none' },
  sep: { color: 'var(--ink-muted)', fontSize: '0.84rem' },
  header: { marginBottom: '2rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border)' },
  catTag: { display: 'inline-block', background: 'var(--teal-light)', color: 'var(--teal)', borderRadius: '100px', padding: '4px 14px', fontSize: '0.78rem', fontWeight: 600, marginBottom: '10px' },
  title: { fontSize: 'clamp(1.3rem, 3vw, 2rem)', marginBottom: '10px' },
  desc: { color: 'var(--ink-light)', fontSize: '0.95rem', lineHeight: 1.75, maxWidth: '680px' },
  main: { display: 'flex', flexDirection: 'column', gap: '1.2rem' },
  sidebar: { display: 'flex', flexDirection: 'column', gap: '1rem', position: 'sticky', top: '80px' },
  card: { background: 'var(--paper)', borderRadius: 'var(--r-lg)', padding: '1.4rem', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' },
  cardTitle: { fontSize: '1rem', fontWeight: 700, marginBottom: '14px' },
  stepsList: { display: 'flex', flexDirection: 'column', gap: '14px' },
  stepRow: { display: 'flex', gap: '12px', alignItems: 'flex-start' },
  stepBubble: { flexShrink: 0, width: '28px', height: '28px', borderRadius: '50%', background: 'var(--saffron)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.8rem', marginTop: '2px' },
  stepText: { fontSize: '0.92rem', color: 'var(--ink-light)', lineHeight: 1.7 },
  escItem: { display: 'flex', gap: '8px', alignItems: 'flex-start', marginBottom: '6px' },
  escArrow: { color: 'var(--indigo)', fontWeight: 700, flexShrink: 0 },
  escText: { fontSize: '0.87rem', color: 'var(--ink-light)', lineHeight: 1.6 },
  copyBtn: { padding: '6px 14px', background: 'var(--teal)', color: '#fff', border: 'none', borderRadius: 'var(--r-sm)', fontFamily: 'var(--font)', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', flexShrink: 0 },
  template: { background: 'var(--parchment)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '1rem', fontSize: '0.82rem', color: 'var(--ink-light)', lineHeight: 1.8, whiteSpace: 'pre-wrap', fontFamily: 'var(--font)', overflowX: 'auto', maxHeight: '400px', overflowY: 'auto' },
  sideCard: { background: 'var(--paper)', borderRadius: 'var(--r-md)', padding: '1.1rem', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' },
  sideTitle: { fontSize: '0.88rem', fontWeight: 700, marginBottom: '10px' },
  docList: { listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '7px' },
  docItem: { display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '0.83rem', color: 'var(--ink-light)', lineHeight: 1.5 },
  docDot: { width: '6px', height: '6px', borderRadius: '50%', background: 'var(--saffron)', flexShrink: 0, marginTop: '5px' },
  authItem: { padding: '7px 0', borderBottom: '1px solid var(--border-light)' },
  authName: { fontSize: '0.84rem', fontWeight: 600, color: 'var(--ink)' },
  authLevel: { fontSize: '0.74rem', color: 'var(--ink-muted)', marginTop: '2px' },
  portalLink: { fontSize: '0.81rem', color: 'var(--teal)', wordBreak: 'break-all' },
  helplineItem: { padding: '6px 0', borderBottom: '1px solid var(--border-light)', fontSize: '0.83rem', color: 'var(--ink-light)' },
  aidBox: { background: 'linear-gradient(135deg, var(--teal-dark), var(--teal))', borderRadius: 'var(--r-md)', padding: '1.2rem' },
  aidTitle: { color: '#fff', fontWeight: 700, marginBottom: '6px', fontSize: '0.95rem' },
  aidText: { color: 'rgba(255,255,255,0.8)', fontSize: '0.81rem', lineHeight: 1.6, marginBottom: '12px' },
  aidBtn: { display: 'inline-block', padding: '8px 18px', background: 'var(--saffron)', color: '#fff', borderRadius: 'var(--r-sm)', fontWeight: 700, fontSize: '0.88rem', textDecoration: 'none' },
  disclaimer: { marginTop: '2rem', background: 'var(--saffron-light)', border: '1px solid #F5C6A0', borderRadius: 'var(--r-md)', padding: '12px 16px', fontSize: '0.83rem', color: 'var(--saffron-dark)', lineHeight: 1.6 },
}
