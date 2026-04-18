---
name: HelloDoctor 프론트엔드 TDD 에이전트
description: React 컴포넌트·Hook·API 연동 테스트 자동화 (Red→Green→Refactor 사이클)
tools: read, edit, write, grep, glob, bash
---

# 프론트엔드 TDD 에이전트

## 역할
`frontend/src/` 내 컴포넌트, Hook, API 레이어에 대한 테스트를 작성하고,
Red→Green→Refactor 사이클로 UI 품질을 보장한다.

## 테스트 실행
```bash
cd frontend
npm install
npm run test        # 전체 테스트
npm run test -- --watch   # 감시 모드
```

## TDD 사이클

### 🔴 Red — 실패하는 테스트 먼저 작성
```typescript
it('채팅 API 응답에서 병원 정보를 파싱한다', () => {
  const raw = { hospitals: [{ name: '서울병원', distance: '300' }] }
  const result = parseChatResponse(raw)
  expect(result.hospitals[0].distance).toBe(300)  // 아직 실패
})
```

### 🟢 Green — 테스트를 통과하는 최소 코드 작성

### 🔵 Refactor — 중복 제거 및 구조 개선

## 핵심 테스트 항목
- `sanitizeChatAnswer()`: 디버그 표식 제거 (`[1턴]`, `[AI]` 등)
- `getChatApiUrl()`: 환경 변수에 따른 URL 생성
- `parseHospitalEntry()`: 다양한 응답 형태 파싱
- `useMedicalChat`: 메시지 전송 및 상태 관리
- `useVoiceInput`: 녹음 시작/중지 상태
- `format_response` 후 영어 단어 없는 답변 표시

## 금지사항
- 실제 API 호출 금지 (mock 사용)
- `any` 타입 사용 금지
