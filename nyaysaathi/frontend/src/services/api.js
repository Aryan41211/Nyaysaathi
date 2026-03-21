import axios from 'axios'

const DEFAULT_PROD_API_URL = 'https://nyaysaathi-backend.onrender.com/api'

function normalizeApiBaseUrl(rawUrl) {
  if (!rawUrl) return ''

  const trimmed = rawUrl.trim().replace(/\/+$/, '')
  if (trimmed.endsWith('/api')) return trimmed
  return `${trimmed}/api`
}

function resolveApiBaseUrl() {
  const envUrl = normalizeApiBaseUrl(import.meta.env.VITE_API_URL)
  if (envUrl) return envUrl
  if (import.meta.env.PROD) return DEFAULT_PROD_API_URL
  return '/api'
}

const BASE_URL = resolveApiBaseUrl()

const api = axios.create({
  baseURL: BASE_URL,
  // First search request can be slow on cold start (model warm-up + fallback path).
  timeout: 90000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  r => r,
  err => {
    if (err.code === 'ECONNABORTED') {
      err.message = 'Request timed out. Please try once more.'
      return Promise.reject(err)
    }
    if (!err.response) {
      err.message = `Cannot connect to backend (${BASE_URL}). Check VITE_API_URL and backend deployment status.`
    } else if (import.meta.env.PROD && err.response.status === 404) {
      err.message = `Backend endpoint not found at ${BASE_URL}. Ensure VITE_API_URL points to your deployed Django API host.`
    }
    return Promise.reject(err)
  }
)

export const searchCases   = (query)    => api.get('/search/',   { params: { query } }).then(r => r.data)
export const getCategories = ()          => api.get('/categories/').then(r => r.data)
export const getCases      = (category) => api.get('/cases/', { params: category ? { category } : {} }).then(r => r.data)
export const getCaseDetail = (sub)       => api.get(`/case/${encodeURIComponent(sub)}/`).then(r => r.data)
