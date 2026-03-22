import axios from "axios"

/*
PRODUCTION ARCHITECTURE

Frontend (Vercel)
↓
Backend (Render Django)
↓
MongoDB Atlas

This file ensures stable connection between frontend and backend.
*/

const DEFAULT_PROD_API_URL = "https://nyaysaathi.onrender.com/api"
const DEFAULT_FALLBACK_API_URL = "https://nyaysaathi.onrender.com/api"

function normalizeApiBaseUrl(rawUrl) {
  if (!rawUrl) return ""

  const trimmed = rawUrl.trim().replace(/\/+$/, "")

  if (trimmed.endsWith("/api")) return trimmed

  return `${trimmed}/api`
}

function resolveApiBaseUrl() {

  const envUrl = normalizeApiBaseUrl(
    import.meta.env.VITE_API_URL
  )

  if (envUrl) return envUrl

  return DEFAULT_PROD_API_URL
}

const BASE_URL = resolveApiBaseUrl()

const FALLBACK_BASE_URL =
  normalizeApiBaseUrl(
    import.meta.env.VITE_FALLBACK_API_URL
  ) || DEFAULT_FALLBACK_API_URL


/*
Main API client
*/
const api = axios.create({

  baseURL: BASE_URL,

  // Long timeout for AI model cold start
  timeout: 90000,

  headers: {
    "Content-Type": "application/json"
  }

})


/*
Fallback API client
*/
const fallbackApi = axios.create({

  baseURL: FALLBACK_BASE_URL,

  timeout: 90000,

  headers: {
    "Content-Type": "application/json"
  }

})


/*
Error handling interceptor
*/
api.interceptors.response.use(

  response => response,

  error => {

    if (error.code === "ECONNABORTED") {

      error.message =
        "Server is waking up (cold start). Please retry once."

      return Promise.reject(error)
    }

    if (!error.response) {

      error.message =
        "Cannot reach backend server. Check deployment."

    }
    else if (error.response.status === 404) {

      error.message =
        "API endpoint not found. Check backend routes."

    }
    else if (error.response.status >= 500) {

      error.message =
        "Backend error. Please retry."

    }

    return Promise.reject(error)
  }

)


/*
Fallback retry logic
*/
function shouldRetryOnFallback(error){

  if (!import.meta.env.PROD) return false

  if (!error) return false

  if (!error.response) return true

  return (
    error.response.status === 404 ||
    error.response.status >= 500
  )

}


/*
Generic GET with fallback
*/
async function getWithFallback(
  path,
  config = {}
){

  try{

    const response =
      await api.get(path, config)

    return response.data

  }
  catch(error){

    if(!shouldRetryOnFallback(error))
      throw error

    const fallbackResponse =
      await fallbackApi.get(path, config)

    return fallbackResponse.data

  }

}


/*
API FUNCTIONS
*/

export const searchCases = (query) =>

  getWithFallback(
    "/search",
    {
      params: { q: query }
    }
  )


export const getCategories = () =>

  getWithFallback("/categories")


export const getCases = (category) =>

  getWithFallback(
    "/cases",
    {
      params:
        category
        ? { category }
        : {}
    }
  )


export const getCaseDetail = (sub) =>

  getWithFallback(
    `/case/${encodeURIComponent(sub)}`
  )


/*
Health check (recommended)
*/
export const healthCheck = () =>

  getWithFallback("/health")