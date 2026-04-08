import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

api.interceptors.response.use(
  res => res,
  err => {
    const detail = err?.response?.data?.detail || err?.response?.data?.error || err.message
    throw new Error(detail)
  }
)

/**
 * POST /api/discover — start a new drug discovery pipeline.
 */
export async function postDiscover(diseaseName) {
  const response = await api.post('/api/discover', { disease: diseaseName })
  return response.data
}

/**
 * GET /api/status/{jobId} — poll job status.
 */
export async function getStatus(jobId) {
  const response = await api.get(`/api/status/${jobId}`)
  return response.data
}

/**
 * GET /api/results/{jobId} — fetch final results for a completed job.
 */
export async function getResults(jobId) {
  const response = await api.get(`/api/results/${jobId}`)
  return response.data
}

/**
 * Returns the URL string for the PDF report download.
 */
export function getReportUrl(jobId) {
  return `${BASE_URL}/api/report/${jobId}`
}

/**
 * Returns the URL string for a molecule SVG image.
 */
export function getMoleculeSvg(jobId, index) {
  return `${BASE_URL}/api/molecule/svg/${jobId}/${index}`
}

/**
 * GET /api/candidate/{jobId}/{index} — fetch full research detail for one candidate.
 */
export async function getCandidateDetail(jobId, index) {
  const response = await api.get(`/api/candidate/${jobId}/${index}`)
  return response.data
}

/**
 * GET /health — backend liveness check.
 */
export async function getHealth() {
  const response = await api.get('/health')
  return response.data
}
