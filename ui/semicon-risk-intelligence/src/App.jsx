import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Expand, MonitorUp, Search, Sparkles } from 'lucide-react'
import Sidebar from './components/Sidebar'
import MetricStrip from './components/MetricStrip'
import PortfolioMap from './components/PortfolioMap'
import ValidationPanel from './components/ValidationPanel'
import PhaseTimeline from './components/PhaseTimeline'
import MethodDecision from './components/MethodDecision'
import ModulePlaceholder from './components/ModulePlaceholder'

function CommandCenter({ presentationMode }) {
  return (
    <motion.div
      className="page-stack"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="hero-grid">
        <div>
          <div className="eyebrow">SEMICON 2.0 • MACRO-PRUDENTIAL RISK</div>
          <h1 className="page-title">Semiconductor Credit Risk <span>Command Center</span></h1>
          <p className="page-subtitle">Evidence-first project intelligence, stress testing, uncertainty analysis and capital-allocation decision support.</p>
        </div>
        <div className="hero-badge">
          <Sparkles size={16} />
          <div><strong>Research Prototype</strong><span>Validated build • pilot gaps remain</span></div>
        </div>
      </div>
      <MetricStrip />
      <div className="content-grid">
        <PortfolioMap />
        <ValidationPanel />
      </div>
      {!presentationMode && <MethodDecision />}
      <PhaseTimeline />
    </motion.div>
  )
}

export default function App() {
  const [active, setActive] = useState('Command Center')
  const [presentationMode, setPresentationMode] = useState(false)

  return (
    <div className={`app ${presentationMode ? 'presentation-mode' : ''}`}>
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      <div className="chip-pattern" />
      <Sidebar active={active} onSelect={setActive} presentationMode={presentationMode} />

      <main className="main-shell">
        <header className="topbar">
          <div className="search-shell">
            <Search size={16} />
            <span>Search projects, evidence, phases…</span>
            <kbd>⌘ K</kbd>
          </div>
          <div className="top-actions">
            <div className="engine-state"><span className="pulse" /> Engine state: stable</div>
            <button className="ghost-button" onClick={() => setPresentationMode(v => !v)}>
              {presentationMode ? <MonitorUp size={16} /> : <Expand size={16} />}
              {presentationMode ? 'Research Mode' : 'Presentation Mode'}
            </button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          {active === 'Command Center' ? (
            <CommandCenter key="command" presentationMode={presentationMode} />
          ) : (
            <ModulePlaceholder key={active} title={active} onBack={() => setActive('Command Center')} />
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}
