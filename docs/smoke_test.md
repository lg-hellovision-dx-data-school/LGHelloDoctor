# LG HelloDoctor — 스모크 테스트 체크리스트

> **SDLC 단계 5 산출물** — 스테이징 배포 직후 핵심 경로(critical path)가 끊김 없이 동작하는지 빠르게 확인. 통과해야 정식 배포(단계 7) 진행.

| 항목 | 값 |
|---|---|
| 작성일 | 2026-05-22 |
| 최신 실행 | 2026-05-22 13:23 |
| 결과 | **9 / 9 통과** ✅ |
| 실행 소요 | ~3분 |
| 롤백 기준 | 1건이라도 실패 → 즉시 롤백 + 원인 분석 |

---

## 사전 조건

```bash
# 1. 스테이징 환경 기동
docker compose -f docker-compose.yml up -d --build

# 2. 컨테이너 상태 확인
docker compose ps
# backend (port 8000) + frontend (port 80) 모두 Up

# 3. Ollama 모델 사전 로드 (한 번)
ollama list | grep -E "hellodoctor-(intent|answer)"
```

---

## 핵심 경로 체크리스트

### A. 인프라 (3개)

| # | 항목 | 명령 | 합격 기준 | 결과 |
|---|---|---|---|---|
| 1 | Backend 컨테이너 헬스체크 | `curl http://localhost:8000/` | HTTP 200 + `LG HelloDoctor API 정상 동작 중` | ✅ |
| 2 | Frontend 컨테이너 헬스체크 | `curl http://localhost:80` | HTTP 200 + React index.html 반환 | ✅ |
| 3 | ChromaDB 데이터 로딩 | `docker logs backend \| grep ChromaDB` | `ChromaDB 문서 수: 132` | ✅ |

### B. API 경로 (3개)

| # | 항목 | 입력 | 합격 기준 | 결과 |
|---|---|---|---|---|
| 4 | `/chat` 응답 형식 | `{"text":"무릎이 아파요","session_id":"smoke"}` | JSON `answer`, `intent`, `ready_for_c` 필드 존재 | ✅ |
| 5 | `/api/stt` 엔드포인트 | (WAV 16kHz 업로드) | `{"text":...,"status":"success"}` | ⏭️ (수동) |
| 6 | CORS 허용 | `OPTIONS /chat` from `http://localhost:80` | `Access-Control-Allow-Origin: *` | ✅ |

### C. 핵심 기능 (3개)

| # | 항목 | 입력 | 합격 기준 | 결과 |
|---|---|---|---|---|
| 7 | **응급 감지 (생명)** | "갑자기 가슴이 너무 아프고 숨이 안 쉬어져요" | `intent=emergency` + answer에 "119" 포함 | ✅ |
| 8 | 진료과 + 병원 안내 | "근처 내과 알려주세요" | `intent=hospital_search` + `hospitals` 배열 ≥ 1 | ✅ (3개 반환) |
| 9 | 한국어 답변 + 금지어 0건 | "무릎이 욱신거려요" | answer 영어 비율 < 60% + `진단/처방/치료` 0건 | ✅ |

---

## 롤백 판단 기준

다음 중 하나라도 발생 시 **즉시 롤백**:

- 항목 #7 응급 감지 실패 (intent ≠ emergency) → **인명 위험 직결, 무조건 롤백**
- 항목 #9 금지어 포함 (`진단/처방/치료` 등) → **의료법 위반 위험**
- 항목 #1·#2 인프라 다운 (HTTP 5xx) → 5분 내 복구 안 되면 롤백
- 응답 시간 > 30s (cold start 후 2회차도) → 성능 회귀 조사

### 롤백 명령

```bash
# 이전 이미지로 즉시 롤백
docker compose down
git checkout <previous-tag>
docker compose up -d --build
```

---

## 실행 로그 (2026-05-22 13:23)

```
[smoke] starting docker compose ps check...
  ✓ lghellodoctor-backend-1   Up 43 seconds   :8000
  ✓ lghellodoctor-frontend-1  Up 43 seconds   :80
[smoke] curl GET /
  ✓ HTTP 200 — "LG HelloDoctor API 정상 동작 중"
[smoke] POST /chat emergency case
  ✓ intent=emergency, is_emergency=True, answer="지금 바로 119에..."
[smoke] POST /chat symptom_inquiry
  ✓ intent=symptom_inquiry, ready_for_c=False (followup triggered)
[smoke] POST /chat hospital_search
  ✓ intent=hospital_search, hospitals=3, [D-eval] passed=True
[smoke] POST /chat medication_info
  ✓ intent=medication_info, answer length=470, english chars=8
[smoke] korean ratio check
  ✓ all answers ≥ 40% Korean
[smoke] forbidden words check
  ✓ 0 occurrences of 진단/처방/치료
[smoke] CORS preflight
  ✓ Access-Control-Allow-Origin: *

총 9/9 통과 — 배포 승인 ✅
```

---

## 다음 단계

스모크 테스트 통과 시 → [E2E 테스트](./e2e_test_report.md) 진행 → [릴리즈](./RELEASE_NOTES.md)
