/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** (선택) `https://...` 백엔드 베이스 — STT 등 `/api/stt` 경로는 `chat` URL에서 유추하거나 여기서 지정 */
  readonly VITE_API_URL?: string
  /** (선택) `https://.../chat` 전체 URL — 설정 시 `chat.ts` 기본 ngrok 주소 대신 사용 */
  readonly VITE_CHAT_API_URL?: string
  /** `1`이면 URL과 관계없이 항상 TV 전용 화면(HelloBeeTvScreen)을 씁니다. 카카오미니 등 임베디드용. */
  readonly VITE_TV_MODE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
