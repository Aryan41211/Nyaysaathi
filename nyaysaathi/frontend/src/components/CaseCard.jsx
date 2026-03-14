import { Link } from 'react-router-dom'
import { useLanguage } from '../state/LanguageContext.jsx'

const CATEGORY_COLORS = {
  'Land and Property Disputes':            { bg: '#FFF3E0', dot: '#E65100' },
  'Labour and Wage Issues':                { bg: '#E8F5E9', dot: '#2E7D32' },
  'Domestic Violence and Family Disputes': { bg: '#FCE4EC', dot: '#B71C1C' },
  'Cyber Fraud and Digital Scams':         { bg: '#E3F2FD', dot: '#1565C0' },
  'Consumer Complaints':                   { bg: '#EDE7F6', dot: '#4527A0' },
  'Police Complaints and Local Crime':     { bg: '#EFEBE9', dot: '#4E342E' },
  'Government Scheme and Public Service Issues': { bg: '#E0F2F1', dot: '#004D40' },
  'Tenant–Landlord Disputes':              { bg: '#FFF8E1', dot: '#F57F17' },
  'Environmental and Public Nuisance Complaints': { bg: '#F1F8E9', dot: '#33691E' },
  'Senior Citizen Protection Issues':      { bg: '#E8EAF6', dot: '#283593' },
}

export default function CaseCard({ caseData, compact = false }) {
  const { t } = useLanguage()
  const { category, subcategory, problem_description, workflow_steps = [],
          required_documents = [], score } = caseData

  const colors = CATEGORY_COLORS[category] || { bg: 'var(--teal-light)', dot: 'var(--teal)' }
  const slug = encodeURIComponent(subcategory)

  return (
    <div style={S.card} className="anim-fade-up">
      {/* Header */}
      <div style={S.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ ...S.catBadge, background: colors.bg, color: colors.dot }}>
            <span style={{ ...S.catDot, background: colors.dot }} />
            {category}
          </span>
          {score !== undefined && (
            <span style={S.score}>
              {Math.round(score * 100)}% {t('caseCard.match')}
            </span>
          )}
        </div>
        <h3 style={S.title}>{subcategory}</h3>
        {problem_description && (
          <p style={S.desc}>
            {compact
              ? (problem_description.slice(0, 160) + (problem_description.length > 160 ? '…' : ''))
              : problem_description}
          </p>
        )}
      </div>

      {/* Steps preview */}
      {workflow_steps.length > 0 && (
        <div style={S.stepsPreview}>
          <div style={S.stepsLabel}>
            📋 {workflow_steps.length} {t('caseCard.stepsToFollow')}
          </div>
          <div style={S.firstStep}>
            {workflow_steps[0]}
          </div>
          {workflow_steps.length > 1 && compact && (
            <div style={S.more}>+{workflow_steps.length - 1} {t('caseCard.moreSteps')}</div>
          )}
        </div>
      )}

      {/* Docs count */}
      {required_documents.length > 0 && (
        <div style={S.meta}>
          <span style={S.metaItem}>📄 {required_documents.length} {t('caseCard.documentsNeeded')}</span>
        </div>
      )}

      {/* CTA */}
      <Link to={`/case/${slug}`} style={S.btn}>
        {t('caseCard.viewFull')}
      </Link>
    </div>
  )
}

const S = {
  card: {
    background: 'var(--paper)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-lg)',
    padding: '1.4rem',
    boxShadow: 'var(--shadow-sm)',
    display: 'flex', flexDirection: 'column', gap: '12px',
    transition: 'box-shadow .2s, transform .2s',
  },
  header: { display: 'flex', flexDirection: 'column', gap: '8px' },
  catBadge: {
    display: 'inline-flex', alignItems: 'center', gap: '6px',
    padding: '3px 10px', borderRadius: '100px',
    fontSize: '0.74rem', fontWeight: 600,
  },
  catDot: { width: '6px', height: '6px', borderRadius: '50%' },
  score: {
    background: 'var(--teal-light)', color: 'var(--teal)',
    fontSize: '0.74rem', fontWeight: 700,
    padding: '3px 10px', borderRadius: '100px',
  },
  title: {
    fontSize: '1.05rem', fontWeight: 700, color: 'var(--ink)',
    lineHeight: 1.3,
  },
  desc: { fontSize: '0.875rem', color: 'var(--ink-light)', lineHeight: 1.6 },
  stepsPreview: {
    background: 'var(--parchment)',
    borderRadius: 'var(--r-sm)',
    padding: '10px 14px',
    borderLeft: '3px solid var(--saffron)',
  },
  stepsLabel: {
    fontSize: '0.75rem', fontWeight: 600,
    color: 'var(--ink-muted)', marginBottom: '6px',
    textTransform: 'uppercase', letterSpacing: '0.4px',
  },
  firstStep: { fontSize: '0.85rem', color: 'var(--ink-light)', lineHeight: 1.55 },
  more: {
    marginTop: '4px', fontSize: '0.78rem',
    color: 'var(--saffron)', fontWeight: 600,
  },
  meta: { display: 'flex', gap: '12px', flexWrap: 'wrap' },
  metaItem: { fontSize: '0.82rem', color: 'var(--ink-muted)' },
  btn: {
    display: 'inline-block', marginTop: '4px',
    padding: '10px 18px', background: 'var(--teal)',
    color: '#fff', borderRadius: 'var(--r-sm)',
    fontWeight: 600, fontSize: '0.87rem', textDecoration: 'none',
    textAlign: 'center', transition: 'background .15s',
  },
}
