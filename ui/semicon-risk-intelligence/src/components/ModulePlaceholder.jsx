import { motion } from 'framer-motion'
import { Construction, ArrowLeft } from 'lucide-react'

export default function ModulePlaceholder({ title, onBack }) {
  return (
    <motion.div className="module-placeholder" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="placeholder-icon"><Construction size={34} /></div>
      <div className="eyebrow">UI PHASE 1</div>
      <h1>{title}</h1>
      <p>The application shell is ready. This module is intentionally waiting for its dedicated UI build and the real validated-engine API contract.</p>
      <button className="primary-button" onClick={onBack}><ArrowLeft size={16} /> Return to Command Center</button>
    </motion.div>
  )
}
