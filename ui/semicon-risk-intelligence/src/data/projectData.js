export const buildMetrics = [
  { label: 'Verified Projects', value: '36', detail: '12 manufacturing • 24 DLI/design' },
  { label: 'Monte Carlo Runs', value: '10,000', detail: 'uncertainty simulation layer' },
  { label: 'Scenario Tests', value: '162', detail: 'stress + allocation combinations' },
  { label: 'Validation Gate', value: '13J PASS', detail: 'controlled sandbox validation' },
  { label: 'Hard Failures', value: '0', detail: 'latest internal audit' },
]

export const validationItems = [
  { label: 'Research decision-support build', status: 'COMPLETE', tone: 'good' },
  { label: 'Internal audit', status: 'PASS', tone: 'good' },
  { label: 'Canonical dataset integrity', status: 'PROTECTED', tone: 'good' },
  { label: 'Phase 13J sandbox validation', status: 'PASS', tone: 'good' },
  { label: 'Monte Carlo method reproduction', status: 'REVIEW REQUIRED', tone: 'warn' },
  { label: 'External validation', status: 'PENDING', tone: 'neutral' },
  { label: 'Real-bank pilot', status: 'PENDING', tone: 'neutral' },
]

export const phaseTimeline = [
  { phase: '01–03', title: 'Research Design', state: 'complete' },
  { phase: '04–06', title: 'Data + Features', state: 'complete' },
  { phase: '07', title: 'Label Validation', state: 'complete' },
  { phase: '08–09', title: 'ML Reframing', state: 'complete' },
  { phase: '10–11', title: 'Stress + Allocation', state: 'complete' },
  { phase: '12', title: 'Evidence Audit', state: 'complete' },
  { phase: '13J', title: 'Controlled Validation', state: 'complete' },
  { phase: 'NEXT', title: 'Pilot + External Validation', state: 'pending' },
]

// UI demonstration points only. These coordinates are visual placeholders for the
// future API-backed project map. They do NOT represent calibrated project risk.
export const portfolioMap = [
  { id: 'P01', x: 21, y: 78, size: 22, kind: 'Manufacturing' },
  { id: 'P02', x: 29, y: 61, size: 18, kind: 'Manufacturing' },
  { id: 'P03', x: 43, y: 72, size: 26, kind: 'Manufacturing' },
  { id: 'P04', x: 55, y: 48, size: 20, kind: 'Manufacturing' },
  { id: 'P05', x: 64, y: 67, size: 16, kind: 'Manufacturing' },
  { id: 'P06', x: 72, y: 39, size: 23, kind: 'Manufacturing' },
  { id: 'P07', x: 84, y: 53, size: 14, kind: 'Manufacturing' },
  { id: 'D01', x: 18, y: 35, size: 11, kind: 'DLI / Design' },
  { id: 'D02', x: 31, y: 27, size: 13, kind: 'DLI / Design' },
  { id: 'D03', x: 46, y: 32, size: 10, kind: 'DLI / Design' },
  { id: 'D04', x: 59, y: 22, size: 12, kind: 'DLI / Design' },
  { id: 'D05', x: 70, y: 28, size: 11, kind: 'DLI / Design' },
  { id: 'D06', x: 81, y: 19, size: 9, kind: 'DLI / Design' },
]
