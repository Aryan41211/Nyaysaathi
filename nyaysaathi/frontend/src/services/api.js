import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  r => r,
  err => {
    if (!err.response) err.message = 'Cannot connect to server. Please check your connection.'
    return Promise.reject(err)
  }
)

export const searchCases   = (query)    => api.get('/search/',   { params: { query } }).then(r => r.data)
export const getCategories = ()          => api.get('/categories/').then(r => r.data)
export const getCases      = (category) => api.get('/cases/', { params: category ? { category } : {} }).then(r => r.data)
export const getCaseDetail = (sub)       => api.get(`/case/${encodeURIComponent(sub)}/`).then(r => r.data)
