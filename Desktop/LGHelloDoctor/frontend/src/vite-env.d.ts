/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** (선택) `https://.../chat` 전체 URL — 설정 시 `chat.ts` 기본 ngrok 주소 대신 사용 */
  readonly VITE_CHAT_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
