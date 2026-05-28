"""Use Cases layer — 애플리케이션 비즈니스 규칙 (A→B→C→D 흐름).

Clean Architecture: domain 만 의존하고 외부 프레임워크/인프라는 의존하지 않는다.
이 패키지는 **기존 모듈을 계층 경로로 노출하는 파사드**(facade)다. 실제 구현은:
  - graph_pipeline.py — LangGraph StateGraph (노드 + 조건부 엣지)
  - agent_patterns.py — Anthropic 5패턴(워커·평가자·라우터·체인)
워커(STT/LLM/RAG/Map/Ontology)는 PipelineWorkers DI 로 주입 → 의존성 역전 달성.
"""

from agent_patterns import (
    AnswerEvaluator,
    IntentRouter,
    PipelineOrchestrator,
    PipelineWorkers,
    PromptChain,
    gate_intent_to_tools,
    gate_stt_to_intent,
    generate_with_evaluator,
    run_c_team_parallel,
)
from graph_pipeline import PipelineState, build_graph, run_graph

# 도메인 규칙만 의존하는 순수 유스케이스 (DI 기반)
from .hospital import find_nearby_hospital
from .rag import rrf_fuse, select_confident

__all__ = [
    "build_graph",
    "run_graph",
    "PipelineState",
    "PipelineWorkers",
    "PipelineOrchestrator",
    "AnswerEvaluator",
    "IntentRouter",
    "PromptChain",
    "generate_with_evaluator",
    "run_c_team_parallel",
    "gate_intent_to_tools",
    "gate_stt_to_intent",
    "find_nearby_hospital",
    "rrf_fuse",
    "select_confident",
]
