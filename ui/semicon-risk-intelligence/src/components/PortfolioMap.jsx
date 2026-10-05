import { motion } from 'framer-motion'
import { portfolioMap } from '../data/projectData'

export default function PortfolioMap() {
  return (
    <section className="panel portfolio-panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">PROJECT UNIVERSE</div>
          <h2>Portfolio Intelligence Map</h2>
        </div>
        <div className="legend">
          <span><i className="dot manufacturing" /> Manufacturing</span>
          <span><i className="dot design" /> DLI / Design</span>
        </div>
      </div>
      <div className="map-note">UI preview coordinates only — calibrated project risk will come from the validated engine/API.</div>
      <div className="portfolio-map">
        <div className="axis axis-y">Relative project strength</div>
        <div className="axis axis-x">Comparative risk dimension</div>
        <div className="grid-lines" />
        {portfolioMap.map((p, index) => (
          <motion.button
            key={p.id}
            className={`bubble ${p.kind === 'Manufacturing' ? 'bubble-manufacturing' : 'bubble-design'}`}
            style={{ left: `${p.x}%`, bottom: `${p.y}%`, width: p.size, height: p.size }}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.25 + index * 0.025, type: 'spring', stiffness: 180, damping: 18 }}
            title={`${p.id} • ${p.kind} • visualization placeholder`}
          />
        ))}
        <div className="map-crosshair crosshair-v" />
        <div className="map-crosshair crosshair-h" />
      </div>
      <div className="map-footer">
        <div><span className="strong">36</span> verified projects in the canonical research universe</div>
        <div className="map-tag">Evidence-first • no fabricated default labels</div>
      </div>
    </section>
  )
}
