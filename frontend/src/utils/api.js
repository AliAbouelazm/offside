const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function fetchClips() {
  const res = await fetch(`${BASE}/api/clips`)
  if (!res.ok) throw new Error('Failed to fetch clips')
  return res.json()
}

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

export async function streamUploadAnalysis(file, frameSkip = 2, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(
    `${BASE}/api/analyze/upload?frame_skip=${frameSkip}`,
    { method: 'POST', body: formData },
  )

  if (!response.ok) throw new Error(`Upload failed: ${response.statusText}`)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  return new Promise((resolve, reject) => {
    async function pump() {
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) { reject(new Error('Stream ended unexpectedly')); return }

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop()

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const event = JSON.parse(line.slice(6))
              if (event.type === 'done') { resolve(event.result); return }
              if (event.type === 'error') { reject(new Error(event.message || 'Analysis failed')); return }
              onProgress?.(event)
            } catch {}
          }
        }
      } catch (e) {
        reject(e)
      }
    }
    pump()
  })
}
