import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    // Temporary debug logging for route/page crashes.
    console.error('Case page crashed:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={S.wrap}>
          <div style={S.card}>
            <h2 style={S.title}>Something went wrong</h2>
            <p style={S.text}>Please try again. If the problem continues, use search to reopen this guidance.</p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

const S = {
  wrap: { padding: '3rem 1rem' },
  card: {
    maxWidth: '680px',
    margin: '0 auto',
    background: 'var(--paper)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-lg)',
    padding: '1.5rem',
  },
  title: { fontSize: '1.2rem', marginBottom: '0.5rem' },
  text: { color: 'var(--ink-light)', lineHeight: 1.6 },
}
