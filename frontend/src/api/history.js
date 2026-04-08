/**
 * Search history — persisted to localStorage.
 * Each entry: { disease, jobId, timestamp, candidateCount, goCount, topScore }
 */

const STORAGE_KEY = 'molforge_search_history'
const MAX_ENTRIES = 20

export function getHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function addToHistory(entry) {
  const history = getHistory()
  // Deduplicate by jobId
  const filtered = history.filter(h => h.jobId !== entry.jobId)
  filtered.unshift(entry)
  // Cap at MAX_ENTRIES
  if (filtered.length > MAX_ENTRIES) filtered.length = MAX_ENTRIES
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered))
}

export function removeFromHistory(jobId) {
  const history = getHistory().filter(h => h.jobId !== jobId)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
}

export function clearHistory() {
  localStorage.removeItem(STORAGE_KEY)
}

export function formatTimeAgo(timestamp) {
  const now = Date.now()
  const then = new Date(timestamp).getTime()
  const diff = now - then
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return new Date(timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
