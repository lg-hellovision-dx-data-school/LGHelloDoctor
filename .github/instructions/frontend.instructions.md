---
applyTo: "frontend/**"
---

# 프론트엔드 지침 (frontend/)

## 개요
React 19 + Vite + TypeScript 기반 시니어 의료 AI 채팅 UI.
TV 화면 최적화 레이아웃(`HelloBeeTvScreen`)과 모바일 채팅 레이아웃(`MedicalChatScreen`) 두 가지 모드 지원.

## 기술 스택
| 항목 | 내용 |
|------|------|
| 프레임워크 | React 19 + TypeScript |
| 빌드 | Vite 8 |
| 서빙 | nginx (Docker) |
| 상태관리 | React Hooks (전역 상태 없음) |

## 디렉토리 구조
```
src/
├── api/
│   ├── chat.ts          # POST /chat 호출, 응답 파싱
│   └── stt.ts           # POST /api/stt 호출
├── components/
│   ├── chat/            # 채팅 UI 컴포넌트
│   │   ├── MedicalChatScreen.tsx   # 메인 채팅 화면
│   │   ├── VoiceInputPanel.tsx     # 음성 입력 UI
│   │   ├── TextComposer.tsx        # 텍스트 입력
│   │   ├── HospitalInfoPanel.tsx   # 병원 정보 패널
│   │   └── MessageBubble.tsx       # 메시지 말풍선
│   └── tv/
│       └── HelloBeeTvScreen.tsx    # TV 전용 화면
├── hooks/
│   ├── useMedicalChat.ts   # 채팅 로직 (API 호출, 메시지 관리)
│   ├── useVoiceInput.ts    # 마이크 녹음 (MediaRecorder)
│   ├── useWakeWord.ts      # 호출어 감지 ("헬로비")
│   └── useGeolocation.ts   # GPS 위치 획득
└── types/
    └── chat.ts             # ChatApiResponse, Hospital, EmergencyInfo 타입
```

## API 연결 설정

### 환경 변수 (frontend/.env)
```env
VITE_CHAT_API_URL=http://localhost:8000/chat   # 백엔드 채팅 API
VITE_API_URL=http://localhost:8000             # 백엔드 베이스 URL
```
- `VITE_CHAT_API_URL`: `/chat` 포함 여부 자동 보정 (`getChatApiUrl()` 참고)
- `VITE_API_URL`: STT 등 기타 엔드포인트 베이스

### Docker 빌드 시
`docker-compose.yml`의 `build.args.VITE_CHAT_API_URL`로 주입.
외부 서버에 배포 시 해당 값을 실제 서버 주소로 변경.

## 주요 타입 (src/types/chat.ts)
```typescript
type Hospital = {
  name: string; address: string; phone: string;
  distance: number; navi_url: string;
  walk_time: number; drive_time: number | null;
}
type EmergencyInfo = { is_emergency: boolean; severity: 'HIGH' | 'MEDIUM' | 'LOW' }
type ChatApiResponse = {
  answer: string; intent?: string;
  hospitals: Hospital[]; emergency?: EmergencyInfo;
}
```

## 핵심 Hook

### useMedicalChat
- `sendMessage(text, lat, lng)`: 텍스트 메시지 전송
- `messages`: 대화 이력
- `ready_for_c`: false이면 백엔드가 추가 질문 중 → 마이크 자동 활성화

### useVoiceInput
- `startRecording()` / `stopRecording()`: MediaRecorder로 음성 녹음
- 녹음 완료 시 `POST /api/stt`로 전송 → 텍스트 반환

### useWakeWord
- "헬로비" 호출어 감지 (Whisper 기반)
- 감지 시 마이크 활성화

## 응답 처리 규칙 (chat.ts)
- `sanitizeChatAnswer()`: `[1턴]`, `[AI]` 등 디버그 표식 제거
- 병원 데이터: `hospitals` 배열 또는 `{ nearby: [] }` 형태 모두 처리
- HTTP 에러 코드별 한국어 메시지 반환

## 개발 명령어
```bash
npm install       # 의존성 설치
npm run dev       # 개발 서버 (localhost:5173)
npm run build     # 프로덕션 빌드 (dist/)
npm run lint      # ESLint
```

## Docker 빌드
```dockerfile
# 1단계: Node 빌드
FROM node:20-alpine AS builder
RUN npm ci && npm run build

# 2단계: nginx 서빙
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

## 주의사항
- `VITE_*` 환경 변수는 **빌드 시** 번들에 포함됨 — 런타임 변경 불가
- ngrok URL이 `.env`에 남아있으면 CORS 오류 발생 → 반드시 로컬/실제 서버 주소로 변경
- `nginx.conf`의 `try_files $uri /index.html` — SPA 라우팅 필수 설정
