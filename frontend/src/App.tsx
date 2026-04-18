import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'
import { MedicalChatScreen } from './components/chat/MedicalChatScreen'
import { HelloBeeTvScreen } from './components/tv/HelloBeeTvScreen'
import { TvErrorBoundary } from './components/tv/TvErrorBoundary'
import { LG_BRAND_CSS_VARS } from './theme/lgBrand'

const shellStyle: CSSProperties = {
  minHeight: '100svh',
  background: 'var(--chat-page-bg)',
  ...LG_BRAND_CSS_VARS,
}

function readTvModeFromLocation(): boolean {
  if (import.meta.env.VITE_TV_MODE === '1') return true
  const q = new URLSearchParams(window.location.search)
  if (q.get('tv') === '1') return true
  const hash = window.location.hash.replace(/^#/, '')
  if (hash === 'tv' || hash === 'tv=1') return true
  if (hash.startsWith('tv=')) {
    return new URLSearchParams(hash).get('tv') === '1'
  }
  return false
}

function App() {
  const [tvMode, setTvMode] = useState(readTvModeFromLocation)

  useEffect(() => {
    const sync = () => setTvMode(readTvModeFromLocation())
    window.addEventListener('popstate', sync)
    window.addEventListener('hashchange', sync)
    return () => {
      window.removeEventListener('popstate', sync)
      window.removeEventListener('hashchange', sync)
    }
  }, [])

  if (tvMode) {
    return (
      <div
        className="lg-hello-app"
        style={{
          minHeight: '100svh',
          background: '#1a202c',
          ...LG_BRAND_CSS_VARS,
        }}
      >
        <TvErrorBoundary>
          <HelloBeeTvScreen />
        </TvErrorBoundary>
      </div>
    )
  }

  return (
    <div className="lg-hello-app" style={shellStyle}>
      <MedicalChatScreen />
    </div>
  )
}

export default App
