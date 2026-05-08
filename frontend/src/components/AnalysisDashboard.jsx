import { useState } from 'react'
import PitchMap from './PitchMap'
import StatsPanel from './StatsPanel'
import TimelineChart from './TimelineChart'
import styles from './AnalysisDashboard.module.css'

const TABS = ['Pitch View', 'Analytics', 'Timeline']

export default function AnalysisDashboard({ result, clipId }) {
  const [tab, setTab] = useState(0)
  const [frameIdx, setFrameIdx] = useState(0)

  const { summary, timeline, per_frame, metadata } = result
  const frame = per_frame[frameIdx]
  const totalFrames = per_frame.length

  return (
    <div className={styles.dashboard}>
      <div className={styles.topBar}>
        <div className={styles.clipInfo}>
          <span className={styles.clipName}>{clipId}</span>
          <span className={styles.clipMeta}>
            {totalFrames} frames · {metadata?.fps?.toFixed(1) ?? '25'} fps ·{' '}
            {metadata?.width ?? '?'}×{metadata?.height ?? '?'}
          </span>
        </div>
        <div className={styles.tabs}>
          {TABS.map((t, i) => (
            <button
              key={t}
              className={`${styles.tab} ${tab === i ? styles.activeTab : ''}`}
              onClick={() => setTab(i)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.content}>
        {tab === 0 && (
          <div className={styles.pitchLayout}>
            <PitchMap frame={frame} />
            <div className={styles.frameControls}>
              <span className={styles.frameLabel}>
                Frame {frame.frame_num} — {frame.timestamp.toFixed(2)}s
              </span>
              <input
                type="range"
                min={0}
                max={totalFrames - 1}
                value={frameIdx}
                onChange={e => setFrameIdx(Number(e.target.value))}
                className={styles.scrubber}
              />
              <div className={styles.frameAnnotations}>
                <Tag color="var(--home)" label={`Home: ${frame.formation_home}`} />
                <Tag color="var(--away)" label={`Away: ${frame.formation_away}`} />
                <Tag
                  color={frame.pressing_trigger ? '#f59e0b' : 'var(--text-muted)'}
                  label={`Press: ${frame.pressing_score}`}
                />
                <Tag
                  color={frame.team_with_ball === 'home' ? 'var(--home)' : 'var(--away)'}
                  label={`Ball: ${frame.team_with_ball}`}
                />
              </div>
            </div>
          </div>
        )}

        {tab === 1 && <StatsPanel summary={summary} />}

        {tab === 2 && <TimelineChart timeline={timeline} />}
      </div>
    </div>
  )
}

function Tag({ color, label }) {
  return (
    <span className={styles.tag} style={{ borderColor: color, color }}>
      {label}
    </span>
  )
}
