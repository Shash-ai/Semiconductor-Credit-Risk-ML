import {
  Activity,
  Blocks,
  ChartNoAxesCombined,
  CircleGauge,
  DatabaseZap,
  FlaskConical,
  Gauge,
  Layers3,
  Network,
  ShieldCheck,
  Waypoints,
} from 'lucide-react'
import { motion } from 'framer-motion'

const items = [
  ['Command Center', Gauge],
  ['Project Intelligence', Blocks],
  ['Risk Analytics', ChartNoAxesCombined],
  ['Stress Lab', FlaskConical],
  ['Monte Carlo', Activity],
  ['Credit Optimizer', Waypoints],
  ['Scenario Compare', Layers3],
  ['Evidence Center', DatabaseZap],
  ['Validation & Governance', ShieldCheck],
  ['Research Insights', Network],
]

export default function Sidebar({ active, onSelect, presentationMode }) {
  return (
    <aside className={`sidebar ${presentationMode ? 'sidebar--presentation' : ''}`}>
      <div className="brand">
        <div className="brand-mark"><CircleGauge size={22} /></div>
        <div>
          <div className="brand-title">SEMICON RISK</div>
          <div className="brand-subtitle">INTELLIGENCE</div>
        </div>
      </div>

      <div className="side-caption">DECISION SUPPORT SYSTEM</div>
      <nav className="nav-list">
        {items.map(([label, Icon], index) => {
          const selected = active === label
          return (
            <motion.button
              key={label}
              whileHover={{ x: 3 }}
              whileTap={{ scale: 0.985 }}
              className={`nav-item ${selected ? 'active' : ''}`}
              onClick={() => onSelect(label)}
            >
              <span className="nav-index">{String(index + 1).padStart(2, '0')}</span>
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
            </motion.button>
          )
        })}
      </nav>
      <div className="sidebar-foot">
        <div className="tiny-status"><span className="pulse" /> Research Prototype</div>
        <div className="muted">Validated build • pilot gaps remain</div>
      </div>
    </aside>
  )
}
