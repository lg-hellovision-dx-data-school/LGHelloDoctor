# /deploy — Docker 배포 자동화

LG HelloDoctor 전체 스택을 Docker로 배포합니다.

## 실행 순서

1. **환경 변수 확인**
   ```bash
   test -f .env && echo "✅ .env 존재" || echo "❌ .env 없음 — KAKAO_API_KEY, GROQ_API_KEY 필요"
   ```

2. **기존 컨테이너 종료**
   ```bash
   docker compose down
   ```

3. **이미지 빌드 및 실행**
   ```bash
   docker compose up --build -d
   ```

4. **헬스체크**
   ```bash
   sleep 10 && curl -s http://localhost:8000/ | python -m json.tool
   ```

5. **로그 확인**
   ```bash
   docker compose logs --tail=50 backend
   ```

## 주의사항
- `.env` 파일에 `KAKAO_API_KEY`와 `GROQ_API_KEY`가 반드시 있어야 합니다.
- 첫 빌드 시 Whisper 모델 다운로드로 5~10분 소요됩니다.
- ChromaDB 버전은 `1.5.5`로 고정 — 임의 변경 금지.

## 트러블슈팅
| 증상 | 원인 | 해결 |
|------|------|------|
| CUDA 오류 | GPU 없는 환경 | Dockerfile에서 CPU 이미지 사용 확인 |
| chromadb KeyError | 버전 불일치 | `chromadb==1.5.5` 고정 확인 |
| CORS 오류 | 프론트 URL 불일치 | `frontend/.env` VITE_API_URL 확인 |
