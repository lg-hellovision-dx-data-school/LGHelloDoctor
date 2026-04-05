import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// API는 src/api/chat.ts 의 CHAT_API_URL 로 직접 호출합니다. /api/chat 프록시 없음.

export default defineConfig({
  plugins: [react()],
})
