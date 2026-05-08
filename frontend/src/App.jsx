import { useState } from 'react'
import ClipSelector from './components/ClipSelector'
import AnalysisDashboard from './components/AnalysisDashboard'
import styles from './App.module.css'

export default function App() {
  const [result, setResult] = useState(null)
  const [activeClip, setActiveClip] = useState(null)
  const [videoUrl, setVideoUrl] = useState(null)

  function handleResult(clipId, data, isUpload = false) {
    setActiveClip(clipId)
    setResult(data)
    setVideoUrl(isUpload ? null : `/api/clips/${clipId}/video`)
  }

  function handleBack() {
    setResult(null)
    setActiveClip(null)
    setVideoUrl(null)
  }

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <span className={styles.logoText}>Offside</span>
        {result && (
          <button className={styles.backBtn} onClick={handleBack}>
            Back
          </button>
        )}
      </header>
      <main className={styles.main}>
        {result ? (
          <AnalysisDashboard result={result} clipId={activeClip} videoUrl={videoUrl} />
        ) : (
          <ClipSelector onResult={handleResult} />
        )}
      </main>
    </div>
  )
}
