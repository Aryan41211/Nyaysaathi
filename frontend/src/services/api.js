import axios from 'axios'

const DEFAULT_PROD_API_URL = '/api'
const DEFAULT_FALLBACK_API_URL = 'https://nyaysaathi-backend.onrender.com/api'

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
const FALLBACK_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_FALLBACK_API_URL) || DEFAULT_FALLBACK_API_URL

const api = axios.create({
  baseURL: BASE_URL,
  // First search request can be slow on cold start (model warm-up + fallback path).
  timeout: 90000,
  headers: { 'Content-Type': 'application/json' },
})

const fallbackApi = axios.create({
  baseURL: FALLBACK_BASE_URL,
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

function shouldRetryOnFallback(err) {
  if (!import.meta.env.PROD) return false
  if (!err) return false
  if (!err.response) return true
  return err.response.status === 404 || err.response.status >= 500
}

async function getWithFallback(path, config = {}) {
  try {
    const response = await api.get(path, config)
    return response.data
  } catch (err) {
    if (!shouldRetryOnFallback(err)) throw err
    const fallbackResponse = await fallbackApi.get(path, config)
    return fallbackResponse.data
  }
}

export const searchCases   = (query)    => getWithFallback('/search/',   { params: { query } })
export const getCategories = ()          => getWithFallback('/categories/')
export const getCases      = (category) => getWithFallback('/cases/', { params: category ? { category } : {} })
export const getCaseDetail = (sub)       => getWithFallback(`/case/${encodeURIComponent(sub)}/`)
