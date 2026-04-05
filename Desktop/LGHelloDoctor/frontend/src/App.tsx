import type { CSSProperties } from 'react'
import { MedicalChatScreen } from './components/chat/MedicalChatScreen'
import { LG_BRAND_CSS_VARS } from './theme/lgBrand'

const shellStyle: CSSProperties = {
  minHeight: '100svh',
  background: 'var(--chat-page-bg)',
  ...LG_BRAND_CSS_VARS,
}

function App() {
  return (
    <div className="lg-hello-app" style={shellStyle}>
      <MedicalChatScreen />
    </div>
  )
}

export default App
