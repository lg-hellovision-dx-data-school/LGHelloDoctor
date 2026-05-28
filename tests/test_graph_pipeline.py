"""LangGraph StateGraph 파이프라인 테스트 — 목(mock) 워커로 흐름 검증.

실행: python -m pytest tests/test_graph_pipeline.py -v

main.py(모델 로드)를 import 하지 않고 graph_pipeline 만 단독 검증한다.
워커는 모두 mock 이라 Ollama/Groq/네트워크 없이 그래프 라우팅·상태 누적을 테스트.

검증 대상:
  - START → stt → intent → followup → END  (다중턴 후속질문, ready_for_c=False)
  - START → stt → intent → tools → answer → END  (일반 답변 + Evaluator)
  - 응급(HIGH) 시 answer 노드가 generate 건너뛰고 즉시 119 안내
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from agent_patterns import AnswerEvaluator, PipelineWorkers  # noqa: E402
from graph_pipeline import build_graph, run_graph  # noqa: E402


def _stt(p):
    return {"text": p}


def _fmt(ans, is_emergency):
    if is_emergency:
        return "지금 바로 119에 전화해 주세요."
    return ans or "죄송합니다. 다시 한번 말씀해 주시겠어요?"


def _gen(text, ctx, conf, ent):
    return {"answer": "어르신 무릎이 불편하시군요. 가까운 정형외과로 조심히 다녀오세요."}


def _make_workers(scenario):
    def chat(text, sid):
        if scenario == "followup":
            return {"answer": "무릎이 많이 아프시군요. 걷기가 힘드신가요?",
                    "intent": "symptom_inquiry", "ready_for_c": False, "output_for_c": None}
        if scenario == "emergency":
            return {"answer": "위험", "intent": "emergency", "ready_for_c": True,
                    "output_for_c": {"intent": "emergency", "entities": {}, "query": text, "confidence": 0.99}}
        return {"answer": None, "intent": "symptom_inquiry", "ready_for_c": True,
                "output_for_c": {"intent": "symptom_inquiry", "entities": {"body_part": "무릎"},
                                 "query": text, "confidence": 0.85}}

    def router(out_b, lat, lng):
        if scenario == "emergency":
            return {"intent": "emergency", "rag_context": None, "rag_sources": [], "hospitals": None,
                    "emergency": {"is_emergency": True, "severity": "HIGH", "score": 100, "action": "119"}}
        return {"intent": "symptom_inquiry",
                "rag_context": "무릎 통증은 정형외과 진료가 필요합니다.",
                "rag_sources": [{"doc_id": "d1", "score": 0.9, "source": "KDCA"}],
                "hospitals": {"department": "정형외과",
                              "nearby": [{"name": "튼튼정형외과", "address": "서울", "phone": "02-1", "distance": 200}]},
                "emergency": None}

    return PipelineWorkers(stt=_stt, chat_followup=chat, tool_router=router,
                           answer_generator=_gen, formatter=_fmt)


EVAL = AnswerEvaluator(forbidden_words=["치료", "진단"])


def _run(scenario, text="무릎이 아파요"):
    app = build_graph(_make_workers(scenario), evaluator=EVAL)
    return run_graph(app, text, session_id="t1")


class TestMultiTurnBranch:
    def test_후속질문이면_도구_미호출_조기종료(self):
        r = _run("followup")
        assert r["ready_for_c"] is False
        assert r["hospitals"] is None
        assert r["emergency"] is None
        assert "걷기" in r["answer"]  # followup 질문 그대로 반환


class TestNormalAnswerBranch:
    def test_일반흐름_병원_출처_평가_포함(self):
        r = _run("normal")
        assert r["intent"] == "symptom_inquiry"
        assert r["ready_for_c"] is True
        assert r["hospitals"]["department"] == "정형외과"
        assert len(r["rag_sources"]) == 1
        assert r["eval"]["attempts"] >= 1
        assert "정형외과" in r["answer"]


class TestEmergencyBranch:
    def test_HIGH응급_즉시_119_생성생략(self):
        r = _run("emergency")
        assert r["emergency"]["severity"] == "HIGH"
        assert "119" in r["answer"]
        assert r["eval"] is None  # generate_answer/Evaluator 건너뜀


class TestEvaluatorRetry:
    def test_금지어_포함시_재생성_시도(self):
        # 항상 금지어가 든 답변을 내는 generator → max_retries 만큼 시도
        bad = "이 약으로 완치됩니다. 진단 결과를 알려드릴게요."

        def gen_bad(text, ctx, conf, ent):
            return {"answer": bad}

        w = _make_workers("normal")
        w = PipelineWorkers(stt=w.stt, chat_followup=w.chat_followup, tool_router=w.tool_router,
                            answer_generator=gen_bad, formatter=_fmt)
        app = build_graph(w, evaluator=EVAL)
        r = run_graph(app, "무릎이 아파요", "t2")
        assert r["eval"]["attempts"] == 3          # 1 + 최대 2회 재시도
        assert r["eval"]["passed"] is False
