"""LangGraph StateGraph — A→B→C→D 오케스트레이션.

기존 main.full_pipeline / agent_patterns.PipelineOrchestrator 의 흐름을
LangGraph 의 명시적 그래프(노드 + 조건부 엣지)로 재구성한다.

  START → stt → intent ─┬─(ready_for_c=False)→ followup → END
                        └─(ready_for_c=True)──→ tools → answer → END

워커(stt/chat_followup/tool_router/answer_generator/formatter)는 외부에서 주입(DI)하므로
이 모듈은 langchain/모델 의존성 없이 단독 테스트가 가능하다.
오케스트레이션 패턴 매핑: docs/AGENT_PATTERNS.md (④ Orchestrator-Worker).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from agent_patterns import (
    AnswerEvaluator,
    PipelineWorkers,
    generate_with_evaluator,
)

AUDIO_EXT = (".wav", ".mp3", ".m4a", ".flac", ".ogg")


class PipelineState(TypedDict, total=False):
    """그래프를 통과하며 누적되는 상태."""
    raw_text: str
    session_id: str
    lat: float
    lng: float
    text: str
    b_result: Dict[str, Any]
    intent: str
    ready_for_c: bool
    output_for_c: Optional[Dict[str, Any]]
    c_result: Dict[str, Any]
    combined_context: str
    answer: str
    hospitals: Optional[Dict[str, Any]]
    emergency: Optional[Dict[str, Any]]
    rag_sources: List[Dict[str, Any]]
    eval: Optional[Dict[str, Any]]


def _format_hospital_text(hospitals: Optional[Dict]) -> str:
    if not hospitals or not hospitals.get("nearby"):
        return ""
    lines = ["\n[주변 추천 병원 목록]"]
    for i, h in enumerate(hospitals["nearby"][:3]):
        walk = max(1, round(h["distance"] / 66.6))
        lines.append(
            f"{i+1}. {h['name']}: 거리 {h['distance']}m, 도보 약 {walk}분\n"
            f"   - 주소: {h['address']}\n"
            f"   - 전화: {h['phone']}"
        )
    return "\n".join(lines)


def build_graph(workers: PipelineWorkers, evaluator: Optional[AnswerEvaluator] = None):
    """워커를 주입받아 컴파일된 LangGraph 앱을 반환한다."""

    # ── A: STT ──────────────────────────────────────────────────────────────
    def node_stt(state: PipelineState) -> Dict[str, Any]:
        raw = state["raw_text"]
        if isinstance(raw, str) and raw.lower().endswith(AUDIO_EXT):
            text = workers.stt(raw).get("text", "")
        else:
            text = raw
        return {"text": text}

    # ── B: 의도 분류 + 다중턴 ────────────────────────────────────────────────
    def node_intent(state: PipelineState) -> Dict[str, Any]:
        b = workers.chat_followup(state["text"], state.get("session_id", "default"))
        return {
            "b_result": b,
            "intent": b.get("intent"),
            "ready_for_c": bool(b.get("ready_for_c")),
            "output_for_c": b.get("output_for_c"),
        }

    # ── 다중턴 중간(후속 질문) → 도구 호출 없이 종료 ─────────────────────────
    def node_followup(state: PipelineState) -> Dict[str, Any]:
        b = state["b_result"]
        return {
            "answer": workers.formatter(b.get("answer", ""), False),
            "hospitals": None,
            "emergency": None,
            "rag_sources": [],
            "eval": None,
        }

    # ── C: 라우팅 + 병렬 도구 호출 ───────────────────────────────────────────
    def node_tools(state: PipelineState) -> Dict[str, Any]:
        c = workers.tool_router(state["output_for_c"], state.get("lat", 37.5012), state.get("lng", 127.0396))
        rag_context = c.get("rag_context") or ""
        combined = f"{rag_context}\n{_format_hospital_text(c.get('hospitals'))}".strip()
        return {
            "c_result": c,
            "hospitals": c.get("hospitals"),
            "emergency": c.get("emergency"),
            "rag_sources": c.get("rag_sources") or [],
            "combined_context": combined,
        }

    # ── D: 답변 생성 (+ Evaluator-Optimizer) / 응급 즉시 119 ─────────────────
    def node_answer(state: PipelineState) -> Dict[str, Any]:
        emergency = state.get("emergency")
        if emergency and emergency.get("severity") == "HIGH":
            return {"answer": workers.formatter("", True), "eval": None}

        b = state.get("b_result", {})
        out_b = state.get("output_for_c") or {}
        combined = state.get("combined_context", "")
        text = state["text"]
        entities = out_b.get("entities") or {}
        confidence = out_b.get("confidence", 0.85)

        if not combined:
            raw_answer = (b.get("answer") if b else None) or "죄송해요, 관련 정보를 찾지 못했습니다."
            return {"answer": workers.formatter(raw_answer, False), "eval": None}

        def _gen():
            return workers.answer_generator(text, combined, confidence, entities)

        if evaluator is not None:
            result = generate_with_evaluator(_gen, evaluator, max_retries=2)
            eval_meta = {
                "attempts": result["attempts"],
                "passed": result["eval_passed"],
                "issues": result["eval_issues"],
                "score": result["eval_score"],
            }
            return {"answer": workers.formatter(result["answer"], False), "eval": eval_meta}

        raw_answer = _gen().get("answer", "")
        return {"answer": workers.formatter(raw_answer, False), "eval": None}

    # ── 조건부 엣지: B 이후 분기 ─────────────────────────────────────────────
    def route_after_intent(state: PipelineState) -> str:
        return "tools" if state.get("ready_for_c") else "followup"

    g = StateGraph(PipelineState)
    g.add_node("stt", node_stt)
    g.add_node("intent", node_intent)
    g.add_node("followup", node_followup)
    g.add_node("tools", node_tools)
    g.add_node("answer", node_answer)

    g.add_edge(START, "stt")
    g.add_edge("stt", "intent")
    g.add_conditional_edges("intent", route_after_intent, {"tools": "tools", "followup": "followup"})
    g.add_edge("tools", "answer")
    g.add_edge("answer", END)
    g.add_edge("followup", END)

    return g.compile()


def run_graph(
    app,
    raw_text: str,
    session_id: str = "default",
    lat: float = 37.5012,
    lng: float = 127.0396,
) -> Dict[str, Any]:
    """컴파일된 그래프를 실행하고 main.full_pipeline 과 동일한 형태의 결과를 반환."""
    final: PipelineState = app.invoke({
        "raw_text": raw_text,
        "session_id": session_id,
        "lat": lat,
        "lng": lng,
    })
    return {
        "answer": final.get("answer", ""),
        "intent": final.get("intent"),
        "ready_for_c": bool(final.get("ready_for_c")),
        "hospitals": final.get("hospitals"),
        "emergency": final.get("emergency"),
        "rag_sources": final.get("rag_sources") or [],
        "eval": final.get("eval"),
    }
