import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { searchCases } from '../services/api.js'
import CaseCard from '../components/CaseCard.jsx'
import { LoadingSpinner, ErrorMessage, EmptyState } from '../components/Feedback.jsx'
import SearchBox from '../components/SearchBox.jsx'
import { useLanguage } from '../state/LanguageContext.jsx'

const LANG_FLAGS = {
  English: '🇬🇧', Hindi: '🇮🇳', Marathi: '🟠', Mixed: '🌐', Unknown: '🌐'
}

const CONFIDENCE_STYLE = {
  High:    { bg: '#D4EDDA', color: '#1A6B45', label: 'High confidence' },
  Medium:  { bg: '#FFF3CD', color: '#856404', label: 'Medium confidence' },
  Low:     { bg: '#FDECEA', color: '#B83232', label: 'Low confidence'   },
}

function NLPInsightBar({ nlp, t }) {
  if (!nlp || !nlp.understood_as) return null

  const confMap = {
    High: { ...CONFIDENCE_STYLE.High, label: t('results.high') },
    Medium: { ...CONFIDENCE_STYLE.Medium, label: t('results.medium') },
    Low: { ...CONFIDENCE_STYLE.Low, label: t('results.low') },
  }
  const conf    = confMap[nlp.confidence] || confMap.Low
  const flag    = LANG_FLAGS[nlp.detected_language] || '🌐'
  const isClaude = nlp.nlp_source === 'claude'

  return (
    <div style={S.nlpBar}>
      <div style={S.nlpLeft}>
        <span style={S.nlpIcon}>🧠</span>
        <div>
          <div style={S.nlpLabel}>{t('results.understoodAs')}</div>
          <div style={S.nlpQuery}>"{nlp.understood_as}"</div>
          {nlp.keywords?.length > 0 && (
            <div style={S.keywords}>
              {nlp.keywords.slice(0, 6).map(k => (
                <span key={k} style={S.kw}>{k}</span>
              ))}
            </div>
          )}
        </div>
      </div>
      <div style={S.nlpRight}>
        <span style={S.langBadge}>{flag} {nlp.detected_language}</span>
        <span style={{ ...S.confBadge, background: conf.bg, color: conf.color }}>
          {conf.label}
        </span>
        {isClaude && <span style={S.aiBadge}>{t('results.aiEnhanced')}</span>}
      </div>
    </div>
  )
}

function asArray(value) {
  return Array.isArray(value) ? value : []
}

export default function ResultsPage() {
  const { t } = useLanguage()
  const [params]   = useSearchParams()
  const query      = params.get('query') || ''
  const [results,  setResults]  = useState([])
  const [nlp,      setNlp]      = useState(null)
  const [clarificationRequired, setClarificationRequired] = useState(false)
  const [clarificationMessage, setClarificationMessage] = useState('')
  const [clarificationQuestions, setClarificationQuestions] = useState([])
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)
  const [searched, setSearched] = useState(false)

  useEffect(() => {
    if (!query) return
    setLoading(true)
    setError(null)
    setSearched(false)
    setNlp(null)
    setClarificationRequired(false)
    setClarificationMessage('')
    setClarificationQuestions([])

    searchCases(query)
      .then(r => {
        setResults(asArray(r?.data))
        setNlp(r?.nlp && typeof r.nlp === 'object' ? r.nlp : null)
        setClarificationRequired(Boolean(r.clarification_required))
        setClarificationMessage(r.clarification_message || '')
        setClarificationQuestions(asArray(r?.clarification_questions))
        setSearched(true)
      })
      .catch(e => {
        setError(e?.response?.data?.error || e?.message || 'Could not connect to the server. Please try again.')
      })
      .finally(() => setLoading(false))
  }, [query])

  return (
    <div style={S.page}>
      <div className="container">

        {/* Search bar */}
        <div style={S.searchBar} className="anim-fade-up">
          <SearchBox defaultValue={query} />
        </div>

        {/* NLP insight bar */}
        {searched && nlp && <NLPInsightBar nlp={nlp} t={t} />}

        {/* Clarification follow-up for low-confidence understanding */}
        {searched && !loading && clarificationRequired && (
          <div style={S.clarifyBox} className="anim-fade-up">
            <div style={S.clarifyTitle}>Need a few details for higher accuracy</div>
            {clarificationMessage && <div style={S.clarifyMsg}>{clarificationMessage}</div>}
            {clarificationQuestions.length > 0 && (
              <ul style={S.clarifyList}>
                {clarificationQuestions.map((q, i) => (
                  <li key={`${i}-${q}`} style={S.clarifyItem}>{q}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Results header */}
        {searched && !loading && (
          <div style={S.header} className="anim-fade-up">
            <div style={S.queryTag}>
              🔍 "<strong>{query}</strong>"
            </div>
            <div style={S.count}>
              {results.length > 0
                ? `${results.length} ${results.length > 1 ? t('results.matchesFound') : t('results.oneMatchFound')}`
                : t('results.noResults')}
            </div>
          </div>
        )}

        {/* States */}
        {loading && <LoadingSpinner message={t('results.analysing')} />}
        {error   && <ErrorMessage message={error} onRetry={() => window.location.reload()} />}
        {!loading && !error && searched && results.length === 0 && <EmptyState query={query} />}

        {/* Results */}
        {!loading && !error && results.length > 0 && (
          <div style={S.list}>
            {results.map((c, i) => (
              <div key={c?.subcategory || `case-${i}`} style={{ animationDelay: `${i * 0.08}s` }}>
                <CaseCard caseData={c} compact />
              </div>
            ))}
          </div>
        )}

        {/* Disclaimer + browse link */}
        {!loading && (
          <div style={S.disclaimer}>
            <strong>{t('results.disclaimer')}</strong>{' '}
            <a href="tel:15100" style={{ color: 'var(--teal)', fontWeight: 700 }}>15100</a>.
            {' '}<Link to="/categories" style={{ color: 'var(--teal)' }}>{t('results.browseAll')}</Link>
          </div>
        )}
      </div>
    </div>
  )
}

const S = {
  page: { padding: '2rem 0 4rem' },
  searchBar: { background: 'var(--paper)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '1.2rem', marginBottom: '1rem', boxShadow: 'var(--shadow-sm)' },

  nlpBar: {
    background: 'var(--paper)', border: '1px solid var(--border)',
    borderRadius: 'var(--r-md)', padding: '12px 16px',
    marginBottom: '1rem', display: 'flex',
    justifyContent: 'space-between', alignItems: 'flex-start',
    flexWrap: 'wrap', gap: '10px',
    borderLeft: '3px solid var(--teal)',
  },
  nlpLeft:  { display: 'flex', gap: '10px', alignItems: 'flex-start', flex: 1 },
  nlpIcon:  { fontSize: '1.2rem', flexShrink: 0, marginTop: '2px' },
  nlpLabel: { fontSize: '0.72rem', fontWeight: 600, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: '4px' },
  nlpQuery: { fontSize: '0.92rem', fontWeight: 600, color: 'var(--ink)', fontStyle: 'italic' },
  keywords: { display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '6px' },
  kw:       { padding: '2px 8px', background: 'var(--teal-light)', color: 'var(--teal)', borderRadius: '100px', fontSize: '0.72rem', fontWeight: 500 },
  nlpRight: { display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', flexShrink: 0 },
  langBadge: { padding: '3px 10px', background: 'var(--parchment)', border: '1px solid var(--border)', borderRadius: '100px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--ink-light)' },
  confBadge: { padding: '3px 10px', borderRadius: '100px', fontSize: '0.75rem', fontWeight: 600 },
  aiBadge:  { padding: '3px 10px', background: '#EDE7F6', color: '#4527A0', borderRadius: '100px', fontSize: '0.73rem', fontWeight: 600 },

  clarifyBox: {
    background: '#FFF8E1',
    border: '1px solid #F0D79A',
    borderLeft: '3px solid #E0A800',
    borderRadius: 'var(--r-md)',
    padding: '12px 16px',
    marginBottom: '1rem',
  },
  clarifyTitle: {
    fontSize: '0.9rem',
    fontWeight: 700,
    color: '#7A5A00',
    marginBottom: '6px',
  },
  clarifyMsg: {
    fontSize: '0.84rem',
    color: '#7A5A00',
    marginBottom: '6px',
    lineHeight: 1.5,
  },
  clarifyList: {
    margin: 0,
    paddingLeft: '1.1rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  clarifyItem: {
    fontSize: '0.82rem',
    color: '#7A5A00',
    lineHeight: 1.5,
  },

  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' },
  queryTag: { background: 'var(--parchment)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '6px 14px', fontSize: '0.9rem', color: 'var(--ink-light)' },
  count: { fontSize: '0.9rem', color: 'var(--ink-muted)', fontWeight: 500 },

  list:       { display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' },
  disclaimer: { background: 'var(--saffron-light)', border: '1px solid #F5C6A0', borderRadius: 'var(--r-md)', padding: '12px 16px', fontSize: '0.83rem', color: 'var(--saffron-dark)', lineHeight: 1.6, marginTop: '1.5rem' },
}
