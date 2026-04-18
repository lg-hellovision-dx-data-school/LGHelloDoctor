# /test — 전체 테스트 실행

LG HelloDoctor TDD 테스트 스위트를 실행합니다.

## 실행

```bash
python tests/test_manager.py
```

## 개별 테스트 실행

```bash
# 백엔드 API 테스트
python -m pytest tests/test_backend.py -v

# AI 모델 테스트 (STT 전처리, 금지어, 응답 품질)
python -m pytest tests/test_ai_model.py -v

# RAG 파이프라인 테스트
python -m pytest tests/test_rag.py -v

# 프론트엔드 API 계약 테스트
python -m pytest tests/test_frontend.py -v
```

## 테스트 파일 위치
| 파일 | 담당 |
|------|------|
| `tests/test_backend.py` | FastAPI 엔드포인트, 파이프라인 통합 |
| `tests/test_ai_model.py` | STT 전처리, 금지어, 응답 품질, 의도 분류 |
| `tests/test_rag.py` | ChromaDB 검색, 임베딩, 병원 API |
| `tests/test_frontend.py` | 프론트-백엔드 API 계약, sanitize 로직 |
| `tests/test_manager.py` | 전체 테스트 오케스트레이터 |

## 품질 기준 (TDD 목표)
- `MEDICAL_CORRECTIONS` ≥ 50개
- `FORBIDDEN_WORDS` ≥ 10개
- 응답 최대 6문장
- 응급 키워드 감지 신뢰도 1.0
- 한국어 비율 ≥ 70%
