import { useState } from 'react'
import ClipSelector from './components/ClipSelector'
import AnalysisDashboard from './components/AnalysisDashboard'
import styles from './App.module.css'

export default function App() {
  const [result, setResult] = useState(null)
  const [activeClip, setActiveClip] = useState(null)

  function handleResult(clipId, data) {
    setActiveClip(clipId)
    setResult(data)
  }

  function handleBack() {
    setResult(null)
    setActiveClip(null)
  }

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>⚽</span>
          <span className={styles.logoText}>Offside</span>
        </div>
        {result && (
          <button className={styles.backBtn} onClick={handleBack}>
            ← Back to clips
          </button>
        )}
      </header>

      <main className={styles.main}>
        {result ? (
          <AnalysisDashboard result={result} clipId={activeClip} />
        ) : (
          <ClipSelector onResult={handleResult} />
        )}
      </main>
    </div>
  )
}
