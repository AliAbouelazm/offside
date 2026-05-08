import { useEffect, useRef, useState } from 'react'
import styles from './TimelineChart.module.css'

const METRICS = [
  { key: 'pressing_scores',    label: 'Pressing Score',     color: '#f59e0b', max: 100 },
  { key: 'space_control_home', label: 'Home Space %',       color: '#2563eb', max: 100 },
  { key: 'space_control_away', label: 'Away Space %',       color: '#dc2626', max: 100 },
]

const PAD = { top: 20, right: 20, bottom: 40, left: 50 }

export default function TimelineChart({ timeline }) {
  const canvasRef = useRef(null)
  const [activeMetrics, setActiveMetrics] = useState(new Set(METRICS.map(m => m.key)))
  const [hovered, setHovered] = useState(null)

  const { timestamps, pressing_triggers } = timeline

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height
    const plotW = W - PAD.left - PAD.right
    const plotH = H - PAD.top - PAD.bottom

    ctx.clearRect(0, 0, W, H)

    // Background
    ctx.fillStyle = '#111827'
    ctx.fillRect(0, 0, W, H)

    const n = timestamps.length
    if (n === 0) return

    const xScale = (i) => PAD.left + (i / (n - 1)) * plotW
    const yScale = (v, max) => PAD.top + plotH - (v / max) * plotH

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'
    ctx.lineWidth = 1
    for (let y = 0; y <= 4; y++) {
      const yy = PAD.top + (y / 4) * plotH
      ctx.beginPath()
      ctx.moveTo(PAD.left, yy)
      ctx.lineTo(PAD.left + plotW, yy)
      ctx.stroke()
      ctx.fillStyle = 'rgba(255,255,255,0.3)'
      ctx.font = '11px Inter, sans-serif'
      ctx.textAlign = 'right'
      ctx.fillText(String(100 - y * 25), PAD.left - 6, yy + 4)
    }

    // X axis labels
    const step = Math.ceil(n / 8)
    ctx.fillStyle = 'rgba(255,255,255,0.4)'
    ctx.font = '11px Inter, sans-serif'
    ctx.textAlign = 'center'
    for (let i = 0; i < n; i += step) {
      ctx.fillText(timestamps[i].toFixed(1) + 's', xScale(i), H - PAD.bottom + 16)
    }

    // Pressing trigger markers
    const pressTrigs = timeline.pressing_scores?.map((_, i) => i).filter(
      i => i > 0 &&
        timeline.pressing_scores[i] - timeline.pressing_scores[i - 1] >= 20
    ) || []
    for (const ti of pressTrigs) {
      const x = xScale(ti)
      ctx.strokeStyle = 'rgba(245,158,11,0.35)'
      ctx.lineWidth = 1
      ctx.setLineDash([3, 3])
      ctx.beginPath()
      ctx.moveTo(x, PAD.top)
      ctx.lineTo(x, PAD.top + plotH)
      ctx.stroke()
      ctx.setLineDash([])
    }

    // Lines
    for (const m of METRICS) {
      if (!activeMetrics.has(m.key)) continue
      const data = timeline[m.key]
      if (!data) continue

      ctx.beginPath()
      ctx.strokeStyle = m.color
      ctx.lineWidth = 2
      ctx.lineJoin = 'round'
      for (let i = 0; i < n; i++) {
        const x = xScale(i)
        const y = yScale(data[i], m.max)
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
      }
      ctx.stroke()
    }

    // Hover crosshair
    if (hovered !== null) {
      const x = xScale(hovered)
      ctx.strokeStyle = 'rgba(255,255,255,0.2)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x, PAD.top)
      ctx.lineTo(x, PAD.top + plotH)
      ctx.stroke()
    }
  }, [timeline, activeMetrics, hovered])

  function handleMouseMove(e) {
    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const plotW = canvas.width - PAD.left - PAD.right
    const n = timestamps.length
    const idx = Math.round(((mx - PAD.left) / plotW) * (n - 1))
    setHovered(Math.max(0, Math.min(n - 1, idx)))
  }

  const hoveredInfo = hovered !== null ? {
    time: timestamps[hovered]?.toFixed(2),
    press: timeline.pressing_scores?.[hovered]?.toFixed(1),
    home: timeline.space_control_home?.[hovered]?.toFixed(1),
    away: timeline.space_control_away?.[hovered]?.toFixed(1),
    formHome: timeline.formation_home?.[hovered],
    formAway: timeline.formation_away?.[hovered],
  } : null

  return (
    <div className={styles.wrapper}>
      <div className={styles.controls}>
        {METRICS.map(m => (
          <button
            key={m.key}
            className={`${styles.toggle} ${activeMetrics.has(m.key) ? styles.on : ''}`}
            style={activeMetrics.has(m.key) ? { borderColor: m.color, color: m.color } : {}}
            onClick={() => setActiveMetrics(prev => {
              const next = new Set(prev)
              next.has(m.key) ? next.delete(m.key) : next.add(m.key)
              return next
            })}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className={styles.chartWrap}>
        <canvas
          ref={canvasRef}
          width={900}
          height={300}
          className={styles.canvas}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHovered(null)}
        />
        {hoveredInfo && (
          <div className={styles.tooltip}>
            <div className={styles.tooltipTime}>{hoveredInfo.time}s</div>
            <div style={{ color: '#f59e0b' }}>Press: {hoveredInfo.press}</div>
            <div style={{ color: '#2563eb' }}>Home space: {hoveredInfo.home}%</div>
            <div style={{ color: '#dc2626' }}>Away space: {hoveredInfo.away}%</div>
            <div className={styles.tooltipForm}>
              {hoveredInfo.formHome} / {hoveredInfo.formAway}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
