import { useLanguage } from '../state/LanguageContext.jsx'

export function LoadingSpinner({ message = 'Searching for guidance…' }) {
  const { t } = useLanguage()
  return (
    <div style={S.wrap}>
      <div style={S.spinner} />
      <p style={S.msg}>{message || t('feedback.searching')}</p>
      <p style={S.sub}>{t('feedback.searchingSub')}</p>
    </div>
  )
}

export function ErrorMessage({ message, onRetry }) {
  const { t } = useLanguage()
  return (
    <div style={S.err}>
      <div style={S.errIcon}>⚠️</div>
      <h3 style={S.errTitle}>{t('feedback.wentWrong')}</h3>
      <p style={S.errMsg}>{message || t('feedback.unexpected')}</p>
      {onRetry && (
        <button style={S.errBtn} onClick={onRetry}>{t('common.tryAgain')}</button>
      )}
    </div>
  )
}

export function EmptyState({ query }) {
  const { t } = useLanguage()
  return (
    <div style={S.empty}>
      <div style={S.emptyIcon}>🔎</div>
      <h3 style={S.emptyTitle}>{t('feedback.noMatching')}</h3>
      <p style={S.emptyMsg}>
        {t('feedback.noMatchingMsgA')} <strong>"{query}"</strong>.<br />
        {t('feedback.noMatchingMsgB')}
      </p>
      <div style={S.emptyTips}>
        <strong style={{ fontSize: '0.85rem', color: 'var(--ink)' }}>{t('feedback.tips')}</strong>
        <ul style={S.tipList}>
          <li>{t('feedback.tip1')}</li>
          <li>{t('feedback.tip2')}</li>
          <li>{t('feedback.tip3')}</li>
        </ul>
      </div>
    </div>
  )
}

const S = {
  wrap: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    gap: '14px', padding: '4rem 1rem',
  },
  spinner: {
    width: '44px', height: '44px',
    border: '4px solid var(--border)',
    borderTop: '4px solid var(--saffron)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  msg: { fontWeight: 600, color: 'var(--ink)', fontSize: '1.05rem' },
  sub: { color: 'var(--ink-muted)', fontSize: '0.85rem' },

  err: {
    background: 'var(--error-bg)', border: '1px solid #F5C6CB',
    borderRadius: 'var(--r-lg)', padding: '2rem',
    textAlign: 'center', maxWidth: '480px', margin: '3rem auto',
  },
  errIcon: { fontSize: '2rem', marginBottom: '8px' },
  errTitle: { fontSize: '1.1rem', color: 'var(--error)', marginBottom: '8px' },
  errMsg: { fontSize: '0.9rem', color: '#721C24' },
  errBtn: {
    marginTop: '14px', padding: '10px 24px',
    background: 'var(--error)', color: '#fff',
    border: 'none', borderRadius: 'var(--r-sm)',
    fontFamily: 'var(--font)', fontWeight: 600, cursor: 'pointer',
  },

  empty: {
    textAlign: 'center', padding: '3rem 1rem',
    maxWidth: '480px', margin: '0 auto',
  },
  emptyIcon: { fontSize: '2.5rem', marginBottom: '12px' },
  emptyTitle: { fontSize: '1.2rem', marginBottom: '10px', color: 'var(--ink)' },
  emptyMsg: { fontSize: '0.92rem', color: 'var(--ink-light)', lineHeight: 1.7 },
  emptyTips: {
    marginTop: '1.5rem', background: 'var(--teal-light)',
    borderRadius: 'var(--r-md)', padding: '1rem 1.2rem',
    textAlign: 'left',
  },
  tipList: {
    marginTop: '8px', paddingLeft: '1.2rem',
    display: 'flex', flexDirection: 'column', gap: '4px',
  },
}
