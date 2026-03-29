import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLanguage } from '../state/LanguageContext.jsx'

export default function SearchBox({ defaultValue = '', autoFocus = false, large = false }) {
  const [query, setQuery] = useState(defaultValue)
  const navigate = useNavigate()
  const { t } = useLanguage()

  const handleSubmit = (e) => {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    navigate(`/results?query=${encodeURIComponent(q)}`)
  }

  const examplesRaw = t('searchBox.examples')
  const examples = Array.isArray(examplesRaw) ? examplesRaw : []

  return (
    <div>
      <form onSubmit={handleSubmit} style={S.form}>
        <div style={S.inputWrap}>
          <span style={S.searchIcon}>🔍</span>
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={t('searchBox.placeholder')}
            style={{ ...S.input, ...(large ? S.inputLarge : {}) }}
            rows={large ? 3 : 1}
            autoFocus={autoFocus}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e) }
            }}
          />
        </div>
        <div style={S.helperRow}>
          <span style={S.hintText}>Press Enter to search. Use Shift + Enter for a new line.</span>
          {query.trim() && (
            <button type="button" style={S.clearBtn} onClick={() => setQuery('')}>
              Clear
            </button>
          )}
        </div>
        <button type="submit" style={{ ...S.btn, ...(large ? S.btnLarge : {}) }}
          disabled={!query.trim()}>
          {t('searchBox.button')}
        </button>
      </form>

      {large && (
        <div style={S.examplesWrap}>
          <span style={S.exLabel}>{t('searchBox.tryAsking')}</span>
          <div style={S.examples}>
            {examples.map((ex) => (
              <button key={ex} type="button" style={S.pill}
                onClick={() => setQuery(ex)}>
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const S = {
  form: { display: 'flex', flexDirection: 'column', gap: '10px' },
  inputWrap: {
    position: 'relative',
    background: 'var(--paper)',
    border: '2px solid var(--border)',
    borderRadius: 'var(--r-md)',
    transition: 'border-color .2s',
    display: 'flex', alignItems: 'flex-start',
  },
  searchIcon: {
    position: 'absolute', left: '14px', top: '14px',
    fontSize: '1.1rem', pointerEvents: 'none',
  },
  input: {
    width: '100%', padding: '13px 14px 13px 42px',
    border: 'none', background: 'transparent',
    fontFamily: 'var(--font)', fontSize: '0.95rem',
    color: 'var(--ink)', resize: 'none', outline: 'none',
    lineHeight: 1.5,
  },
  inputLarge: {
    fontSize: '1.05rem', padding: '15px 16px 15px 44px',
  },
  helperRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '8px',
  },
  hintText: {
    fontSize: '0.78rem',
    color: 'var(--ink-muted)',
  },
  clearBtn: {
    background: 'transparent',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-sm)',
    color: 'var(--ink-light)',
    fontFamily: 'var(--font)',
    fontSize: '0.76rem',
    cursor: 'pointer',
    padding: '5px 10px',
    flexShrink: 0,
  },
  btn: {
    padding: '12px 24px', background: 'var(--saffron)',
    color: '#fff', border: 'none', borderRadius: 'var(--r-sm)',
    fontFamily: 'var(--font)', fontWeight: 600, fontSize: '0.95rem',
    cursor: 'pointer', transition: 'background .15s',
    alignSelf: 'flex-end',
  },
  btnLarge: {
    padding: '14px 32px', fontSize: '1rem', alignSelf: 'stretch',
  },
  examplesWrap: { marginTop: '14px' },
  exLabel: {
    display: 'block', fontSize: '0.78rem', fontWeight: 600,
    color: 'var(--ink-muted)', textTransform: 'uppercase',
    letterSpacing: '0.5px', marginBottom: '8px',
  },
  examples: { display: 'flex', flexWrap: 'wrap', gap: '8px' },
  pill: {
    padding: '6px 12px', background: 'var(--parchment)',
    border: '1px solid var(--border)', borderRadius: '100px',
    fontFamily: 'var(--font)', fontSize: '0.78rem',
    color: 'var(--ink-light)', cursor: 'pointer',
    transition: 'all .15s', textAlign: 'left',
  },
}
