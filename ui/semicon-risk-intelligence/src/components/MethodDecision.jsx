import { ArrowRight, Ban, Braces, ShieldCheck } from 'lucide-react'

export default function MethodDecision() {
  return (
    <section className="panel method-panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">METHODOLOGY DECISION</div>
          <h2>Why We Did Not Force a Default Classifier</h2>
        </div>
        <span className="status-pill status-info">RESEARCH INTEGRITY</span>
      </div>
      <div className="decision-flow">
        <div className="decision-box">
          <Braces size={22} />
          <div><b>36 verified projects</b><span>Real project universe</span></div>
        </div>
        <ArrowRight className="decision-arrow" />
        <div className="decision-box danger">
          <Ban size={22} />
          <div><b>No reliable default labels</b><span>Supervised PD classification withheld</span></div>
        </div>
        <ArrowRight className="decision-arrow" />
        <div className="decision-box success">
          <ShieldCheck size={22} />
          <div><b>Decision-support reframing</b><span>PCA / clustering + stress + MC + allocation</span></div>
        </div>
      </div>
    </section>
  )
}
