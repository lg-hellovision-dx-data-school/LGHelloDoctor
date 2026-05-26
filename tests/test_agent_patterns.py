"""agent_patterns 모듈 회귀 테스트.

LLM·네트워크 의존 없이 ⑤ Evaluator-Optimizer · ③ Parallelization · ② Routing 동작을 검증한다.
실행: docker compose exec backend python -m pytest tests/test_agent_patterns.py -v
"""

import sys
import os
import time
import threading

_HERE = os.path.dirname(__file__)
for _p in (os.path.join(_HERE, "..", "backend"), os.path.join(_HERE, ".."), "/app"):
    if os.path.exists(os.path.join(_p, "agent_patterns.py")):
        sys.path.insert(0, _p)
        break

import pytest
from agent_patterns import (
    AnswerEvaluator,
    IntentRouter,
    generate_with_evaluator,
    run_c_team_parallel,
)


FORBIDDEN = ["예후", "처방전", "투약", "병변", "진단", "확정", "완치", "확신", "치료", "부작용"]


# ─────────────────────────────────────────────────────────────
# ⑤ Evaluator-Optimizer — AnswerEvaluator 단위 테스트
# ─────────────────────────────────────────────────────────────

class TestAnswerEvaluator:
    def setup_method(self):
        self.evaluator = AnswerEvaluator(forbidden_words=FORBIDDEN)

    def test_정상_답변_통과(self):
        answer = "어르신, 무릎이 많이 아프시군요. 가까운 정형외과에 다녀오시는 게 좋겠어요."
        report = self.evaluator.evaluate(answer)
        assert report.passed is True
        assert report.score == 1.0
        assert report.issues == []

    def test_빈_답변_실패(self):
        report = self.evaluator.evaluate("")
        assert report.passed is False
        assert "empty_answer" in report.issues

    def test_영어_혼입_낮은_한국어_비율_실패(self):
        # 한국어 비율 < 0.4 → 차단
        answer = "Hello, that is a very long english answer with many english words inside."
        report = self.evaluator.evaluate(answer)
        assert report.passed is False
        assert any("low_korean_ratio" in i for i in report.issues)

    def test_너무_짧은_답변_실패(self):
        answer = "네."
        report = self.evaluator.evaluate(answer)
        assert report.passed is False
        assert any("too_short" in i for i in report.issues)

    def test_금지어_포함_실패(self):
        answer = "어르신, 이 증상은 확실히 위염으로 진단됩니다. 치료를 받으셔야 합니다."
        report = self.evaluator.evaluate(answer)
        assert report.passed is False
        forbidden_issue = [i for i in report.issues if "forbidden_word" in i]
        assert len(forbidden_issue) == 1
        assert "진단" in forbidden_issue[0]
        assert "치료" in forbidden_issue[0]


# ─────────────────────────────────────────────────────────────
# ⑤ Evaluator-Optimizer — 재생성 루프 (generate_with_evaluator)
# ─────────────────────────────────────────────────────────────

class TestGenerateWithEvaluator:
    def setup_method(self):
        self.evaluator = AnswerEvaluator(forbidden_words=FORBIDDEN)

    def test_첫_시도_통과시_재시도_없음(self):
        good = "어르신, 무릎이 많이 아프시겠어요. 가까운 정형외과에 다녀오시는 게 좋겠습니다."
        calls = {"n": 0}

        def gen():
            calls["n"] += 1
            return {"answer": good}

        result = generate_with_evaluator(gen, self.evaluator, max_retries=2)
        assert calls["n"] == 1
        assert result["attempts"] == 1
        assert result["eval_passed"] is True

    def test_실패시_재생성_후_통과(self):
        answers = iter([
            "Hello, that is bad",  # 한국어 비율 낮음
            "어르신 안녕하세요 무릎통증은 정형외과 진료를 권해드려요.",  # 통과
        ])
        calls = {"n": 0}

        def gen():
            calls["n"] += 1
            return {"answer": next(answers)}

        result = generate_with_evaluator(gen, self.evaluator, max_retries=2)
        assert calls["n"] == 2
        assert result["attempts"] == 2
        assert result["eval_passed"] is True

    def test_최대_재시도_초과시_마지막_답변_반환(self):
        def gen():
            return {"answer": "Bad bad bad english only here always."}

        result = generate_with_evaluator(gen, self.evaluator, max_retries=2)
        assert result["attempts"] == 3  # 1 + max_retries
        assert result["eval_passed"] is False
        assert result["answer"] == "Bad bad bad english only here always."

    def test_금지어_포함시_재생성_트리거(self):
        answers = iter([
            "어르신은 위염으로 확실히 진단되며 치료가 필요합니다 지금요.",  # 금지어
            "어르신 무릎이 많이 불편하시군요 정형외과 다녀오세요 부탁드려요.",  # 통과
        ])

        def gen():
            return {"answer": next(answers)}

        result = generate_with_evaluator(gen, self.evaluator, max_retries=2)
        assert result["attempts"] == 2
        assert result["eval_passed"] is True


# ─────────────────────────────────────────────────────────────
# ③ Parallelization — run_c_team_parallel
# ─────────────────────────────────────────────────────────────

class TestParallelExecution:
    def test_세_도구_병렬_실행이_직렬보다_빠름(self):
        """각 fn이 100ms sleep 하면 직렬은 300ms+, 병렬은 150ms 미만이어야 한다."""

        def slow_rag(q):
            time.sleep(0.1)
            return {"context": "rag-ctx", "sources": []}

        def slow_hosp(q, lat, lng):
            time.sleep(0.1)
            return {"department": "내과", "nearby": []}

        def slow_emerg(q):
            time.sleep(0.1)
            return {"is_emergency": False, "severity": "LOW", "score": 0, "action": None}

        start = time.perf_counter()
        result = run_c_team_parallel(
            query="무릎이 아파요",
            intent="symptom_inquiry",
            lat=37.5, lng=127.0,
            rag_fn=slow_rag, hospital_fn=slow_hosp, emergency_fn=slow_emerg,
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.25, f"병렬 실행이 너무 느림: {elapsed:.3f}s"
        assert result["rag_context"] == "rag-ctx"
        assert result["hospitals"]["department"] == "내과"
        assert result["emergency"]["is_emergency"] is False

    def test_intent별_필요_도구만_제출(self):
        """hospital_search는 RAG fn을 호출하지 않아야 한다."""
        rag_called = threading.Event()

        def rag_fn(q):
            rag_called.set()
            return {"context": "x", "sources": []}

        def hosp_fn(q, lat, lng):
            return {"department": "내과", "nearby": []}

        def emerg_fn(q):
            return {"is_emergency": False, "severity": "LOW", "score": 0, "action": None}

        result = run_c_team_parallel(
            query="근처 내과", intent="hospital_search",
            lat=37.5, lng=127.0,
            rag_fn=rag_fn, hospital_fn=hosp_fn, emergency_fn=emerg_fn,
        )
        assert not rag_called.is_set()
        assert result["rag_context"] is None
        assert result["hospitals"] is not None

    def test_medication_info는_병원검색_안함(self):
        hosp_called = threading.Event()

        def rag_fn(q):
            return {"context": "약물 정보", "sources": []}

        def hosp_fn(q, lat, lng):
            hosp_called.set()
            return {"department": "내과", "nearby": []}

        def emerg_fn(q):
            return {"is_emergency": False, "severity": "LOW", "score": 0, "action": None}

        result = run_c_team_parallel(
            query="혈압약 먹어도 되나요", intent="medication_info",
            lat=37.5, lng=127.0,
            rag_fn=rag_fn, hospital_fn=hosp_fn, emergency_fn=emerg_fn,
        )
        assert not hosp_called.is_set()
        assert result["rag_context"] == "약물 정보"
        assert result["hospitals"] is None


# ─────────────────────────────────────────────────────────────
# ② Routing — IntentRouter
# ─────────────────────────────────────────────────────────────

class TestIntentRouter:
    def test_등록된_핸들러로_라우팅(self):
        router = IntentRouter(default_handler=lambda b: {"handled_by": "default"})
        router.register("emergency", lambda b: {"handled_by": "emg"})
        router.register("hospital_search", lambda b: {"handled_by": "hosp"})

        assert router.route({"intent": "emergency"})["handled_by"] == "emg"
        assert router.route({"intent": "hospital_search"})["handled_by"] == "hosp"

    def test_미등록_의도는_default_핸들러로(self):
        router = IntentRouter(default_handler=lambda b: {"handled_by": "default"})
        assert router.route({"intent": "unknown"})["handled_by"] == "default"
        assert router.route({})["handled_by"] == "default"
