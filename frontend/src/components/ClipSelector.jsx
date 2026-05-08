import { useState, useEffect } from 'react'
import { fetchClips, streamDemoAnalysis } from '../utils/api'
import styles from './ClipSelector.module.css'

const CLIP_META = {
  possession: { label: 'Possession Play', desc: 'Sustained build-up and ball retention' },
  pressing:   { label: 'High Press',      desc: 'Coordinated pressing sequence' },
  open_play:  { label: 'Open Play',       desc: 'Chelsea vs Arsenal tactical cam' },
  transition: { label: 'Transition',      desc: 'Tottenham vs Watford wide angle' },
  ucl:        { label: 'UCL Action',      desc: 'Liverpool vs PSG Champions League' },
}

export default function ClipSelector({ onResult }) {
  const [clips, setClips] = useState([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(null)
  const [progress, setProgress] = useState({ phase: '', pct: 0, message: '' })
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchClips()
      .then(setClips)
      .catch(() => setError('Could not reach the backend. Is it running?'))
      .finally(() => setLoading(false))
  }, [])

  async function handleSelect(clipId) {
    setAnalyzing(clipId)
    setError(null)
    setProgress({ phase: 'Starting…', pct: 0, message: '' })

    try {
      const result = await streamDemoAnalysis(clipId, 2, (evt) => {
        if (evt.type === 'status') {
          setProgress(p => ({ ...p, message: evt.message }))
        } else if (evt.type === 'progress') {
          setProgress({ phase: evt.phase || '', pct: evt.pct || 0, message: '' })
        }
      })
      onResult(clipId, result)
    } catch (e) {
      setError(e.message)
    } finally {
      setAnalyzing(null)
    }
  }

  if (loading) return <div className={styles.center}>Loading clips…</div>

  return (
    <div className={styles.wrapper}>
      <div className={styles.hero}>
        <h1 className={styles.title}>Tactical Analysis</h1>
        <p className={styles.subtitle}>
          Select a broadcast clip to detect players, map the pitch, and compute
          real-time formations, pressing intensity, and space control.
        </p>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {analyzing && (
        <div className={styles.progressBox}>
          <div className={styles.progressLabel}>
            {progress.message || `${progress.phase} — ${progress.pct}%`}
          </div>
          <div className={styles.progressTrack}>
            <div className={styles.progressFill} style={{ width: `${progress.pct}%` }} />
          </div>
        </div>
      )}

      <div className={styles.grid}>
        {clips.map((clip) => {
          const meta = CLIP_META[clip.id] || { label: clip.id, desc: '' }
          const isActive = analyzing === clip.id
          return (
            <button
              key={clip.id}
              className={`${styles.card} ${isActive ? styles.active : ''}`}
              onClick={() => !analyzing && handleSelect(clip.id)}
              disabled={!!analyzing}
            >
              <div className={styles.cardThumb}>
                <span className={styles.cardIcon}>▶</span>
              </div>
              <div className={styles.cardBody}>
                <div className={styles.cardTitle}>{meta.label}</div>
                <div className={styles.cardDesc}>{meta.desc}</div>
                {clip.has_cache && (
                  <span className={styles.cachedBadge}>cached</span>
                )}
              </div>
              {isActive && <div className={styles.spinner} />}
            </button>
          )
        })}
      </div>
    </div>
  )
}
