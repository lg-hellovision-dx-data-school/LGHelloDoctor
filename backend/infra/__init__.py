"""Infrastructure layer — 외부 시스템 구현체 (가장 바깥, 언제든 교체).

Clean Architecture: domain/usecases 가 정의한 포트(domain.ports)를 구현한다.
이 패키지는 기존 모듈을 계층 경로로 노출하는 파사드(facade)다.

구현 매핑:
  - OntologyGateway  ← backend/ontology_store.py (rdflib + SPARQL Graph DB)
  - STTGateway       ← backend/main.py::stt_pipeline (Whisper + Silero VAD)
  - LLMGateway       ← backend/main.py (Ollama + Groq fallback)
  - VectorRepository ← backend/main.py::full_rag_pipeline (ChromaDB + BM25 + reranker)
  - MapGateway       ← backend/main.py::search_kakao (Kakao Local API)

모델 weight·DB 핸들은 라이프사이클 비용이 커서, main.py 합성 루트에서 모듈 import
시점에 한 번만 로드해 워커 함수로 노출하는 형태를 유지한다.
"""

from ontology_store import HD, OntologyStore, ontology

from .map_kakao import KakaoMapGateway, search_kakao

__all__ = ["OntologyStore", "ontology", "HD", "KakaoMapGateway", "search_kakao"]
