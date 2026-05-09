import { useState, useRef } from 'react'
import PitchMap from './PitchMap'
import StatsPanel from './StatsPanel'
import TimelineChart from './TimelineChart'
import styles from './AnalysisDashboard.module.css'

export default function AnalysisDashboard({ result, clipId, videoUrl }) {
  const [tab, setTab] = useState(0)
  const [frameIdx, setFrameIdx] = useState(0)
  const videoRef = useRef(null)
  const syncingFromScrubber = useRef(false)

  const { summary, timeline, per_frame, metadata } = result
  const frame = per_frame[frameIdx]
  const totalFrames = per_frame.length

  function handleScrub(idx) {
    setFrameIdx(idx)
    if (videoRef.current && per_frame[idx]) {
      syncingFromScrubber.current = true
      videoRef.current.currentTime = per_frame[idx].timestamp
    }
  }

  function handleTimeUpdate() {
    if (syncingFromScrubber.current) {
      syncingFromScrubber.current = false
      return
    }
    const t = videoRef.current?.currentTime ?? 0
    let lo = 0, hi = totalFrames - 1
    while (lo < hi) {
      const mid = (lo + hi) >> 1
      if (per_frame[mid].timestamp < t) lo = mid + 1
      else hi = mid
    }
    setFrameIdx(lo)
  }

  return (
    <div className={styles.dashboard}>
      <div className={styles.topBar}>
        <div className={styles.clipInfo}>
          <span className={styles.clipName}>{clipId}</span>
          <span className={styles.clipMeta}>
            {totalFrames} frames &middot; {metadata?.fps?.toFixed(1) ?? '25'} fps &middot;{' '}
            {metadata?.width ?? '?'}&times;{metadata?.height ?? '?'}
          </span>
        </div>
        <div className={styles.tabs}>
          {['Pitch', 'Analytics', 'Timeline'].map((t, i) => (
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

      {tab === 0 && (
        <div className={styles.pitchView}>
          <div className={styles.splitPane}>
            {videoUrl ? (
              <div className={styles.videoPane}>
                <video
                  ref={videoRef}
                  src={videoUrl}
                  className={styles.video}
                  controls
                  onTimeUpdate={handleTimeUpdate}
                />
              </div>
            ) : (
              <div className={styles.noVideo}>
                <span>No video, uploaded clips do not persist on the server</span>
              </div>
            )}
            <div className={styles.pitchPane}>
              <PitchMap frame={frame} />
            </div>
          </div>
          <div className={styles.scrubRow}>
            <div className={styles.frameTags}>
              <Tag color="var(--home)" label={`Home  ${frame.formation_home}`} />
              <Tag color="var(--away)" label={`Away  ${frame.formation_away}`} />
              <Tag
                color={frame.pressing_trigger ? '#f59e0b' : 'var(--text-muted)'}
                label={`Press ${frame.pressing_score}`}
              />
              <Tag
                color={frame.team_with_ball === 'home' ? 'var(--home)' : 'var(--away)'}
                label={`Ball  ${frame.team_with_ball ?? '-'}`}
              />
            </div>
            <div className={styles.scrubWrap}>
              <span className={styles.scrubTime}>{frame.timestamp?.toFixed(2)}s</span>
              <input
                type="range"
                min={0}
                max={totalFrames - 1}
                value={frameIdx}
                onChange={e => handleScrub(Number(e.target.value))}
                className={styles.scrubber}
              />
              <span className={styles.scrubTime}>
                {per_frame[totalFrames - 1]?.timestamp?.toFixed(2)}s
              </span>
            </div>
          </div>
        </div>
      )}

      {tab === 1 && <StatsPanel summary={summary} />}
      {tab === 2 && <TimelineChart timeline={timeline} />}
    </div>
  )
}

function Tag({ color, label }) {
  return (
    <span className={styles.tag} style={{ color, borderColor: color + '44' }}>
      {label}
    </span>
  )
}
