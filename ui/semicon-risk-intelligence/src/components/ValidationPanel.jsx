import { CheckCircle2, CircleDashed, TriangleAlert } from 'lucide-react'
import { validationItems } from '../data/projectData'

function iconFor(tone) {
  if (tone === 'good') return <CheckCircle2 size={17} />
  if (tone === 'warn') return <TriangleAlert size={17} />
  return <CircleDashed size={17} />
}

export default function ValidationPanel() {
  return (
    <section className="panel validation-panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">MODEL GOVERNANCE</div>
          <h2>Validation Status</h2>
        </div>
        <span className="status-pill status-good">13J PASS</span>
      </div>
      <div className="validation-list">
        {validationItems.map(item => (
          <div className="validation-row" key={item.label}>
            <div className={`validation-icon ${item.tone}`}>{iconFor(item.tone)}</div>
            <div className="validation-label">{item.label}</div>
            <div className={`validation-state ${item.tone}`}>{item.status}</div>
          </div>
        ))}
      </div>
      <div className="governance-note">
        <strong>Research boundary:</strong> internal validation does not imply calibrated PD/LGD/EAD, external bank validation, or production readiness.
      </div>
    </section>
  )
}
