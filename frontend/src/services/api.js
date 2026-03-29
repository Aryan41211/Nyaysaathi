import axios from "axios"

/*
SIMPLE & STABLE API CONFIG
(No env confusion, direct production connection)
*/

const BASE_URL = "https://nyaysaathi-1.onrender.com/api"

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