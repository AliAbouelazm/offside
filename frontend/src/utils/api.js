const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function fetchClips() {
  const res = await fetch(`${BASE}/api/clips`)
  if (!res.ok) throw new Error('Failed to fetch clips')
  return res.json()
}

/**
 * Stream analysis for a demo clip via SSE.
 * onProgress(event) is called for each progress event.
 * Returns the final result object.
 */
export function streamDemoAnalysis(clipId, frameSkip = 2, onProgress) {
  return new Promise((resolve, reject) => {
    const url = `${BASE}/api/analyze/demo/${clipId}?frame_skip=${frameSkip}`
    const es = new EventSource(url)

    es.onmessage = (e) => {
      let event
      try { event = JSON.parse(e.data) } catch { return }

      if (event.type === 'done') {
        es.close()
        resolve(event.result)
      } else if (event.type === 'error') {
        es.close()
        reject(new Error(event.message || 'Analysis failed'))
      } else {
        onProgress?.(event)
      }
    }

    es.onerror = () => {
      es.close()
      reject(new Error('Connection lost'))
    }
  })
}
