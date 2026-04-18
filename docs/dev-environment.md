# LG HelloDoctor — 개발 환경 정리

## 기술 스택

| 영역 | 기술 |
|------|------|
| **Infra** | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white) ![Docker Compose](https://img.shields.io/badge/Docker_Compose-2496ED?style=flat&logo=docker&logoColor=white) |
| **Backend** | ![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) ![PyTorch](https://img.shields.io/badge/PyTorch_CPU-EE4C2C?style=flat&logo=pytorch&logoColor=white) |
| **AI 모델** | ![Groq](https://img.shields.io/badge/Groq_LLM-F55036?style=flat&logo=groq&logoColor=white) ![Whisper](https://img.shields.io/badge/Whisper_STT-412991?style=flat&logo=openai&logoColor=white) ![HuggingFace](https://img.shields.io/badge/HuggingFace-FFD21E?style=flat&logo=huggingface&logoColor=black) |
| **Frontend** | ![React](https://img.shields.io/badge/React_19-61DAFB?style=flat&logo=react&logoColor=black) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white) ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white) ![nginx](https://img.shields.io/badge/nginx-009639?style=flat&logo=nginx&logoColor=white) |
| **Database** | ![ChromaDB](https://img.shields.io/badge/ChromaDB_1.5.5-FF6B35?style=flat&logo=databricks&logoColor=white) |
| **External API** | ![Kakao](https://img.shields.io/badge/Kakao_Map_API-FFCD00?style=flat&logo=kakao&logoColor=black) |
| **UI/Design** | ![Figma](https://img.shields.io/badge/Figma-F24E1E?style=flat&logo=figma&logoColor=white) ![html.to.design](https://img.shields.io/badge/html.to.design-9B59B6?style=flat&logo=figma&logoColor=white) ![Claude MCP](https://img.shields.io/badge/Claude_MCP-CC785C?style=flat&logo=anthropic&logoColor=white) |
| **협업** | ![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white) |

> **프론트엔드 디자인 워크플로우**
> Claude MCP + [html.to.design](https://www.figma.com/community/plugin/1159123024924461424) 플러그인을 활용해 구현된 HTML/CSS를 Figma 디자인으로 자동 변환하여 UI를 문서화했습니다.

---

## 목차
1. [요구 사항](#1-요구-사항)
2. [환경 변수 설정](#2-환경-변수-설정)
3. [Docker 환경 (권장)](#3-docker-환경-권장)
4. [로컬 개발 환경](#4-로컬-개발-환경)
5. [백엔드 의존성 상세](#5-백엔드-의존성-상세)
6. [프론트엔드 의존성 상세](#6-프론트엔드-의존성-상세)
7. [포트 및 볼륨 구성](#7-포트-및-볼륨-구성)
8. [알려진 이슈 및 해결법](#8-알려진-이슈-및-해결법)

---

## 1. 요구 사항

### 필수
| 항목 | 버전 | 용도 |
|------|------|------|
| Python | 3.11 | 백엔드 런타임 |
| Node.js | 20 (LTS) | 프론트엔드 빌드 |
| Docker Desktop | 최신 | 컨테이너 실행 |
| Docker Compose | v2 이상 | 멀티 컨테이너 관리 |

### API 키
| 키 | 발급처 | 용도 |
|----|--------|------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | LLM 추론 (무료 플랜 가능) |
| `KAKAO_API_KEY` | [developers.kakao.com](https://developers.kakao.com) | 병원 위치 검색 |

### 시스템 패키지 (백엔드 Dockerfile에서 자동 설치)
```
libsndfile1   # 오디오 파일 읽기/쓰기 (soundfile 라이브러리 의존성)
ffmpeg        # 오디오 포맷 변환 (librosa 의존성)
git           # Silero VAD torch.hub 다운로드 시 필요
```

---

## 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성:

```bash
# .env
KAKAO_API_KEY=your_kakao_api_key_here
GROQ_API_KEY=your_groq_api_key_here

# 선택 사항
WHISPER_MODEL_PATH=openai/whisper-small   # 기본값, 커스텀 모델 경로로 변경 가능
DB_PATH=/app/RAG/db                       # 기본값
```

> `.env`는 `.gitignore`에 포함 — API 키를 절대 커밋하지 않는다.

---

## 3. Docker 환경 (권장)

### 최초 실행 (빌드 포함)
```bash
docker compose up --build
```

> 첫 실행 시 Whisper, Silero VAD, ko-sroberta-multitask 모델이 자동 다운로드됩니다.
> 인터넷 속도에 따라 **5~15분** 소요될 수 있습니다.

### 이후 실행
```bash
docker compose up -d          # 백그라운드 실행
docker compose logs -f backend  # 백엔드 로그 실시간 확인
docker compose down           # 종료
```

### 코드 수정 후 반영
```bash
# 볼륨 마운트 없음 → 재빌드 필요
docker compose up --build -d

# 빠른 재시작 (환경변수·설정 변경 시)
docker compose restart backend
```

### Docker 서비스 구성
```
┌─────────────────────────────────────┐
│  backend (python:3.11-slim)         │
│  포트: 8000                          │
│  볼륨: ./RAG/db → /app/RAG/db       │
│        model-cache → /root/.cache   │
│  env_file: .env                     │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  frontend (node:20-alpine → nginx)  │
│  포트: 80                            │
│  빌드 ARG: VITE_CHAT_API_URL        │
│  depends_on: backend                │
└─────────────────────────────────────┘
```

---

## 4. 로컬 개발 환경

### 백엔드 (FastAPI)
```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> `--reload`: 코드 변경 시 자동 재시작 (개발 시에만 사용)

### 프론트엔드 (React + Vite)
```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행 (HMR 지원)
npm run dev

# 프로덕션 빌드
npm run build
```

### 테스트 실행
```bash
# 전체 테스트
python tests/test_manager.py

# 개별 테스트
python -m pytest tests/test_ai_model.py -v
python -m pytest tests/test_backend.py -v
python -m pytest tests/test_rag.py -v
python -m pytest tests/test_frontend.py -v
```

---

## 5. 백엔드 의존성 상세

```
# PyPI 추가 인덱스 (CPU 전용 PyTorch)
--extra-index-url https://download.pytorch.org/whl/cpu
```

| 패키지 | 버전 | 역할 |
|--------|------|------|
| `fastapi` | 0.115.0 | API 서버 프레임워크 |
| `uvicorn[standard]` | 0.30.6 | ASGI 서버 |
| `python-dotenv` | 1.0.1 | `.env` 파일 로드 |
| `python-multipart` | 0.0.9 | 파일 업로드 처리 |
| `groq` | 0.11.0 | Groq API 클라이언트 |
| `langchain-groq` | 0.2.0 | LangChain ↔ Groq 연동 |
| `httpx` | <0.28.0 | groq와 버전 충돌 방지 (고정) |
| `torch` | 2.3.1+cpu | 딥러닝 프레임워크 (CPU 전용) |
| `torchaudio` | 2.3.1+cpu | 오디오 처리 |
| `transformers` | 4.44.2 | Whisper STT 모델 |
| `librosa` | 0.10.2 | 오디오 리샘플링 (16kHz) |
| `soundfile` | 0.12.1 | WAV 파일 읽기/쓰기 |
| `numpy` | 1.26.4 | 수치 연산 |
| `chromadb` | **1.5.5** | 벡터 DB (버전 고정 필수) |
| `sentence-transformers` | 3.1.1 | 임베딩 (jhgan/ko-sroberta-multitask) |
| `requests` | 2.32.3 | Kakao API 호출 |
| `pydantic` | 2.9.2 | 요청/응답 모델 검증 |

> **주의:** `chromadb==1.5.5` 버전 임의 변경 금지 — 로컬 DB 스키마와 불일치 시 `no such column` 오류 발생

---

## 6. 프론트엔드 의존성 상세

| 패키지 | 버전 | 역할 |
|--------|------|------|
| `react` | ^19.2.4 | UI 라이브러리 |
| `react-dom` | ^19.2.4 | DOM 렌더링 |
| `vite` | ^8.0.1 | 빌드 도구 + 개발 서버 |
| `typescript` | ~5.9.3 | 타입 안전성 |
| `@vitejs/plugin-react` | ^6.0.1 | Vite React 플러그인 |
| `eslint` | ^9.39.4 | 코드 품질 검사 |

### 빌드 환경 변수
```bash
# docker-compose.yml의 build.args로 주입
VITE_CHAT_API_URL=http://localhost:8000/chat
```

### nginx 서빙 구조
```
React 빌드 결과물 (/dist)
    → nginx:alpine 컨테이너
    → 포트 80 서빙
    → SPA 라우팅: try_files $uri /index.html
```

---

## 7. 포트 및 볼륨 구성

### 포트
| 서비스 | 내부 포트 | 외부 포트 | 용도 |
|--------|-----------|-----------|------|
| backend | 8000 | 8000 | FastAPI API 서버 |
| frontend | 80 | 80 | nginx 웹 서버 |

### 볼륨
| 이름 | 마운트 경로 | 용도 |
|------|------------|------|
| `./RAG/db` | `/app/RAG/db` | ChromaDB 데이터 (로컬 DB 공유) |
| `model-cache` | `/root/.cache` | HuggingFace + torch 모델 캐시 재사용 |

> `model-cache` 볼륨 덕분에 재빌드 시에도 모델을 다시 다운로드하지 않는다.

---

## 8. 알려진 이슈 및 해결법

| 증상 | 원인 | 해결 |
|------|------|------|
| `TypeError: proxies` | groq + httpx 버전 충돌 | `httpx<0.28.0` 고정 |
| `no such column: collections.topic` | chromadb 버전 불일치 | `chromadb==1.5.5` 고정 |
| CUDA 초기화 오류 | GPU 없는 환경 | `python:3.11-slim` 기반 이미지 사용, CPU 전용 torch |
| CORS 오류 | 프론트 API URL 불일치 | `frontend/.env` 또는 `docker-compose.yml`의 `VITE_CHAT_API_URL` 확인 |
| 응답에 영어 단어 혼입 | LLM 프롬프트 미흡 | `format_response()`의 `re.sub(r'\b[a-zA-Z]+\b', '', answer)` 동작 확인 |
| Whisper 첫 로드 느림 | 모델 다운로드 | `model-cache` 볼륨으로 이후 실행 시 캐시 재사용 |
