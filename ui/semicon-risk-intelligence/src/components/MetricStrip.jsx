import { motion } from 'framer-motion'
import { buildMetrics } from '../data/projectData'

export default function MetricStrip() {
  return (
    <div className="metric-strip">
      {buildMetrics.map((metric, index) => (
        <motion.div
          key={metric.label}
          className="metric-cell"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 * index, duration: 0.45 }}
        >
          <div className="metric-label">{metric.label}</div>
          <div className="metric-value">{metric.value}</div>
          <div className="metric-detail">{metric.detail}</div>
        </motion.div>
      ))}
    </div>
  )
}
