import axios from "axios"

function resolveBaseUrl() {
  // In local dev, always use Vite proxy so requests hit localhost Django backend.
  if (typeof window !== "undefined") {
    const host = window.location.hostname
    if (host === "localhost" || host === "127.0.0.1") {
      return "/api"
    }
  }

  const raw = String(import.meta.env.VITE_API_URL || "/api").trim().replace(/\/+$/, "")

  // Relative paths (e.g. /api) are used as-is and can be proxied by Vite.
  if (!/^https?:\/\//i.test(raw)) {
    return raw || "/api"
  }

  // Absolute hosts should point at Django API prefix.
  return raw.endsWith("/api") ? raw : `${raw}/api`
}

const BASE_URL = resolveBaseUrl()

/*
Main API client
*/
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json"
  }
})

/*
Error handling
*/
api.interceptors.response.use(
  response => response,
  error => {
    if (error.code === "ECONNABORTED") {
      error.message = "Server is waking up. Please retry."
    } 
    else if (!error.response) {
      error.message = "Cannot reach backend server."
    } 
    else if (error.response.status === 404) {
      error.message = "API endpoint not found."
    } 
    else if (error.response.status >= 500) {
      error.message = "Backend error."
    }

    return Promise.reject(error)
  }
)

/*
API FUNCTIONS
*/

// ✅ FIXED (POST request)
export const searchCases = async (query) => {
  const response = await api.post("/search/", {
    query: query
  })
  return response.data
}

// Optional APIs (can keep or remove)
export const getCategories = async () => {
  const response = await api.get("/categories/")
  return response.data
}

export const getCases = async (category) => {
  const response = await api.get("/cases/", {
    params: category ? { category } : {}
  })
  return response.data
}

export const getCaseDetail = async (sub) => {
  const response = await api.get(`/case/${encodeURIComponent(sub)}`)
  return response.data
}

// Health check
export const healthCheck = async () => {
  const response = await api.get("/health/")
  return response.data
}