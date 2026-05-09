import { useState, useEffect, useRef } from 'react'
import { fetchClips, streamDemoAnalysis, streamUploadAnalysis } from '../utils/api'
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
  const [progress, setProgress] = useState({ pct: 0, message: '' })
  const [error, setError] = useState(null)

  const fileRef = useRef(null)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState({ pct: 0, message: '' })
  const [uploadError, setUploadError] = useState(null)

  useEffect(() => {
    fetchClips()
      .then(setClips)
      .catch(() => setError('Could not reach the backend. Is it running?'))
      .finally(() => setLoading(false))
  }, [])

  async function handleSelect(clipId) {
    setAnalyzing(clipId)
    setError(null)
    setProgress({ pct: 0, message: 'Starting...' })
    try {
      const result = await streamDemoAnalysis(clipId, 2, (evt) => {
        if (evt.type === 'status') {
          setProgress(p => ({ ...p, message: evt.message }))
        } else if (evt.type === 'progress') {
          const label = evt.phase === 'tracking'
            ? `Tracking, frame ${evt.frame} / ${evt.total}`
            : `Analytics, frame ${evt.frame} / ${evt.total}`
          setProgress({ pct: evt.pct || 0, message: label })
        }
      })
      onResult(clipId, result, false)
    } catch (e) {
      setError(e.message)
    } finally {
      setAnalyzing(null)
    }
  }

  async function handleUpload() {
    if (!uploadFile) return
    setUploading(true)
    setUploadError(null)
    setUploadProgress({ pct: 0, message: 'Uploading...' })
    try {
      const result = await streamUploadAnalysis(uploadFile, 2, (evt) => {
        if (evt.type === 'status') {
          setUploadProgress(p => ({ ...p, message: evt.message }))
        } else if (evt.type === 'progress') {
          const label = evt.phase === 'tracking'
            ? `Tracking, frame ${evt.frame} / ${evt.total}`
            : `Analytics, frame ${evt.frame} / ${evt.total}`
          setUploadProgress({ pct: evt.pct || 0, message: label })
        }
      })
      onResult(uploadFile.name.replace(/\.[^.]+$/, ''), result, true)
    } catch (e) {
      setUploadError(e.message)
    } finally {
      setUploading(false)
    }
  }

  if (loading) return <div className={styles.center}>Loading...</div>

  const busy = !!analyzing || uploading

  return (
    <div className={styles.wrapper}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Tactical Analysis</h1>
        <p className={styles.subtitle}>
          Select a demo clip or upload your own broadcast footage. The pipeline
          detects players, maps the pitch, and computes formations, pressing
          intensity, and space control.
        </p>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {analyzing && (
        <ProgressBox
          progress={progress}
          hint="First run takes 5-10 min on CPU. Subsequent runs use cached results."
        />
      )}

      <section className={styles.section}>
        <h2 className={styles.sectionHeading}>Demo Clips</h2>
        <div className={styles.grid}>
          {clips.map((clip) => {
            const meta = CLIP_META[clip.id] || { label: clip.id, desc: '' }
            const isActive = analyzing === clip.id
            return (
              <button
                key={clip.id}
                className={`${styles.card} ${isActive ? styles.active : ''}`}
                onClick={() => !busy && handleSelect(clip.id)}
                disabled={busy}
              >
                <div className={styles.cardThumb} />
                <div className={styles.cardBody}>
                  <div className={styles.cardTitle}>{meta.label}</div>
                  <div className={styles.cardDesc}>{meta.desc}</div>
                  {clip.has_cache && !isActive && (
                    <span className={styles.cachedBadge}>instant</span>
                  )}
                </div>
                {isActive && <div className={styles.spinner} />}
              </button>
            )
          })}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionHeading}>Upload Clip</h2>
        {uploadError && <div className={styles.error}>{uploadError}</div>}
        {uploading && (
          <ProgressBox
            progress={uploadProgress}
            hint="Processing uploaded clip, this may take several minutes on CPU."
          />
        )}
        <div className={styles.uploadPanel}>
          <div className={styles.requirements}>
            <p className={styles.reqTitle}>Requirements</p>
            <ul className={styles.reqList}>
              <li>Broadcast or fixed tactical camera angle</li>
              <li>Full pitch or at least half the pitch visible</li>
              <li>MP4, MOV, or AVI, max 500 MB</li>
              <li>Minimum 10 seconds, 25 fps recommended</li>
            </ul>
          </div>
          <div className={styles.uploadActions}>
            <input
              ref={fileRef}
              type="file"
              accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska"
              className={styles.fileInput}
              onChange={e => setUploadFile(e.target.files[0] || null)}
            />
            <button
              className={styles.fileButton}
              onClick={() => fileRef.current?.click()}
              disabled={busy}
              title={uploadFile ? uploadFile.name : undefined}
            >
              {uploadFile ? uploadFile.name : 'Choose file'}
            </button>
            {uploadFile && (
              <button
                className={styles.analyzeButton}
                onClick={handleUpload}
                disabled={busy}
              >
                {uploading ? 'Analyzing...' : 'Analyze'}
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}

function ProgressBox({ progress, hint }) {
  return (
    <div className={styles.progressBox}>
      <div className={styles.progressLabel}>
        <span>{progress.message || 'Starting...'}</span>
        <span className={styles.progressPct}>
          {progress.pct > 0 ? `${progress.pct}%` : ''}
        </span>
      </div>
      <div className={styles.progressTrack}>
        <div
          className={styles.progressFill}
          style={{ width: `${Math.max(progress.pct, 3)}%` }}
        />
      </div>
      <div className={styles.progressHint}>{hint}</div>
    </div>
  )
}
