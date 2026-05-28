"""Ports — Use Case 가 의존하는 추상 인터페이스 (Dependency Inversion).

안쪽(도메인/유스케이스)이 인터페이스를 정의하고, 바깥(infra)이 구현한다.
덕분에 외부 시스템 교체(Whisper→Clova, Ollama→vLLM, ChromaDB→Pinecone, Kakao→Naver)가
안쪽 코드 수정 없이 가능하다 (docs/CLEAN_ARCHITECTURE.md §3).

실제 주입 구현체:
  - STTGateway      ← main.stt_pipeline (Whisper + Silero VAD)
  - LLMGateway      ← Ollama / Groq (main.classify_intent · generate_answer)
  - VectorRepository← main.full_rag_pipeline (ChromaDB + BM25 + reranker)
  - MapGateway      ← main.search_hospital (Kakao Local API)
  - OntologyGateway ← ontology_store.OntologyStore (rdflib SPARQL)
graph_pipeline.PipelineWorkers 가 이들을 묶어 LangGraph 노드에 주입한다.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, Tuple

from .entities import Hospital, Intent, MedicalKnowledge


class STTGateway(Protocol):
    def transcribe(self, audio_path: str) -> str: ...


class LLMGateway(Protocol):
    def generate(self, prompt: str, **opts) -> str: ...


class VectorRepository(Protocol):
    def search(self, query: str, top_k: int = 3) -> List[MedicalKnowledge]: ...


class MapGateway(Protocol):
    def nearby(self, category: str, lat: float, lng: float) -> List[Hospital]: ...


class OntologyGateway(Protocol):
    """Graph DB(온톨로지) 질의 포트 — rdflib 구현."""
    def emergency_score(self, text: str) -> Dict[str, object]: ...
    def symptom_to_department(self, text: str) -> Optional[Tuple[str, str]]: ...
    def body_parts_under(self, region_local_name: str) -> List[str]: ...


class ConversationRepository(Protocol):
    def load(self, session_id: str) -> Dict: ...
    def save(self, session_id: str, state: Dict) -> None: ...
