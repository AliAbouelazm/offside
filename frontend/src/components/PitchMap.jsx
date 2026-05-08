import { useEffect, useRef } from 'react'
import styles from './PitchMap.module.css'

// Pitch dimensions in meters
const PW = 105
const PH = 68
// Canvas scale: pixels per meter
const SCALE = 8
const CW = PW * SCALE
const CH = PH * SCALE

const TEAM_COLORS = { home: '#2563eb', away: '#dc2626', referee: '#f59e0b' }
const BALL_COLOR = '#ffffff'

function meterToCanvas(x, y) {
  return [x * SCALE, y * SCALE]
}

function drawPitch(ctx) {
  // Grass
  ctx.fillStyle = '#1a3a1a'
  ctx.fillRect(0, 0, CW, CH)

  // Alternating stripes
  for (let i = 0; i < 10; i++) {
    if (i % 2 === 0) {
      ctx.fillStyle = 'rgba(255,255,255,0.03)'
      ctx.fillRect(i * (CW / 10), 0, CW / 10, CH)
    }
  }

  ctx.strokeStyle = 'rgba(255,255,255,0.7)'
  ctx.lineWidth = 1.5

  // Outline
  ctx.strokeRect(0, 0, CW, CH)

  // Centre line
  ctx.beginPath()
  ctx.moveTo(CW / 2, 0)
  ctx.lineTo(CW / 2, CH)
  ctx.stroke()

  // Centre circle (radius 9.15m)
  ctx.beginPath()
  ctx.arc(CW / 2, CH / 2, 9.15 * SCALE, 0, Math.PI * 2)
  ctx.stroke()

  // Centre spot
  ctx.fillStyle = 'rgba(255,255,255,0.7)'
  ctx.beginPath()
  ctx.arc(CW / 2, CH / 2, 3, 0, Math.PI * 2)
  ctx.fill()

  // Penalty areas (16.5m deep, 40.3m wide)
  const paDepth = 16.5 * SCALE
  const paWidth = 40.32 * SCALE
  const paY = (CH - paWidth) / 2

  ctx.strokeRect(0, paY, paDepth, paWidth)
  ctx.strokeRect(CW - paDepth, paY, paDepth, paWidth)

  // Goal areas (5.5m deep, 18.3m wide)
  const gaDepth = 5.5 * SCALE
  const gaWidth = 18.32 * SCALE
  const gaY = (CH - gaWidth) / 2

  ctx.strokeRect(0, gaY, gaDepth, gaWidth)
  ctx.strokeRect(CW - gaDepth, gaY, gaDepth, gaWidth)

  // Goals (7.32m wide, 2m deep visual)
  const goalWidth = 7.32 * SCALE
  const goalDepth = 2 * SCALE
  const goalY = (CH - goalWidth) / 2
  ctx.strokeStyle = 'rgba(255,255,255,0.5)'
  ctx.strokeRect(-goalDepth, goalY, goalDepth, goalWidth)
  ctx.strokeRect(CW, goalY, goalDepth, goalWidth)
}

function drawVoronoiCells(ctx, cells) {
  if (!cells?.length) return
  for (const cell of cells) {
    if (!cell.polygon?.length) continue
    const color = TEAM_COLORS[cell.team] || '#888'
    ctx.beginPath()
    const [fx, fy] = meterToCanvas(cell.polygon[0][0], cell.polygon[0][1])
    ctx.moveTo(fx, fy)
    for (let i = 1; i < cell.polygon.length; i++) {
      const [px, py] = meterToCanvas(cell.polygon[i][0], cell.polygon[i][1])
      ctx.lineTo(px, py)
    }
    ctx.closePath()
    ctx.fillStyle = color + '22'
    ctx.fill()
    ctx.strokeStyle = color + '55'
    ctx.lineWidth = 0.5
    ctx.stroke()
  }
}

function drawPlayers(ctx, homePlayers, awayPlayers) {
  const all = [
    ...homePlayers.map(p => ({ ...p, team: 'home' })),
    ...awayPlayers.map(p => ({ ...p, team: 'away' })),
  ]
  for (const p of all) {
    if (p.pitch_x == null) continue
    const [cx, cy] = meterToCanvas(p.pitch_x, p.pitch_y)
    const color = TEAM_COLORS[p.team]

    // Shadow
    ctx.beginPath()
    ctx.arc(cx, cy + 2, 6, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(0,0,0,0.3)'
    ctx.fill()

    // Player dot
    ctx.beginPath()
    ctx.arc(cx, cy, 6, 0, Math.PI * 2)
    ctx.fillStyle = color
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 1.5
    ctx.stroke()

    // Goalkeeper marker
    if (p.class_name === 'goalkeeper') {
      ctx.beginPath()
      ctx.arc(cx, cy, 9, 0, Math.PI * 2)
      ctx.strokeStyle = color
      ctx.lineWidth = 1.5
      ctx.stroke()
    }
  }
}

function drawBall(ctx, ball) {
  if (!ball || ball.pitch_x == null) return
  const [cx, cy] = meterToCanvas(ball.pitch_x, ball.pitch_y)

  ctx.beginPath()
  ctx.arc(cx, cy, 5, 0, Math.PI * 2)
  ctx.fillStyle = BALL_COLOR
  ctx.fill()
  ctx.strokeStyle = '#333'
  ctx.lineWidth = 1
  ctx.stroke()
}

export default function PitchMap({ frame }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!frame) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')

    ctx.clearRect(0, 0, CW, CH)
    drawPitch(ctx)

    if (frame.space?.cells) {
      drawVoronoiCells(ctx, frame.space.cells)
    }

    drawPlayers(ctx, frame.home_players || [], frame.away_players || [])
    drawBall(ctx, frame.ball)
  }, [frame])

  return (
    <div className={styles.wrapper}>
      <canvas
        ref={canvasRef}
        width={CW}
        height={CH}
        className={styles.canvas}
      />
      <div className={styles.legend}>
        <LegendItem color="var(--home)" label="Home" />
        <LegendItem color="var(--away)" label="Away" />
        <LegendItem color={BALL_COLOR} label="Ball" />
        <LegendItem color="rgba(37,99,235,0.15)" label="Space control" border="var(--home)" />
      </div>
    </div>
  )
}

function LegendItem({ color, label, border }) {
  return (
    <div className={styles.legendItem}>
      <span
        className={styles.legendDot}
        style={{ background: color, border: border ? `1px solid ${border}` : 'none' }}
      />
      <span>{label}</span>
    </div>
  )
}
