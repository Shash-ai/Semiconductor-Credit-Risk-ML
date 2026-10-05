// UI Phase 1 connector.
// When the validated Python engine is exposed through an API, replace the mock
// functions below with real fetch() calls. Keeping the adapter isolated prevents
// frontend work from changing validated research logic.

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function getCommandCenter() {
  return null
}

export async function getProjects() {
  return null
}
