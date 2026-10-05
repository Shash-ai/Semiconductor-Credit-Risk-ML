import { Check, ChevronRight } from 'lucide-react'
import { phaseTimeline } from '../data/projectData'

export default function PhaseTimeline() {
  return (
    <section className="panel phase-panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">BUILD JOURNEY</div>
          <h2>Research Development Timeline</h2>
        </div>
        <span className="subtle-label">Evidence → Risk → Stress → Decision</span>
      </div>
      <div className="timeline">
        {phaseTimeline.map((item, index) => (
          <div className={`timeline-item ${item.state}`} key={item.phase}>
            <div className="timeline-node">{item.state === 'complete' ? <Check size={14} /> : <span />}</div>
            <div className="timeline-copy">
              <div className="timeline-phase">PHASE {item.phase}</div>
              <div className="timeline-title">{item.title}</div>
            </div>
            {index < phaseTimeline.length - 1 && <ChevronRight className="timeline-chevron" size={16} />}
          </div>
        ))}
      </div>
    </section>
  )
}
