"""Anthropic Agent Design Patterns — LG HelloDoctor 적용 모듈.

5가지 패턴(프롬프트 체이닝 · 라우팅 · 병렬 처리 · 오케스트레이터-워커 · 평가-최적화)을
명시적으로 캡슐화한다. 기존 main.py 함수를 워커로 위임받아 호출하므로
파이프라인 동작은 동일하게 유지된다.

Anthropic 원문: https://www.anthropic.com/engineering/building-effective-agents
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# 공통 게이트 — Prompt Chaining 단계 간 검증
# ─────────────────────────────────────────────────────────────────────────────

def gate_stt_to_intent(stt_out: Dict[str, Any]) -> bool:
    """A→B 게이트: STT 결과가 다음 단계로 진행 가능한지 검증."""
    text = (stt_out or {}).get("text", "")
    return bool(text and len(text.strip()) >= 2)


def gate_intent_to_tools(b_out: Dict[str, Any]) -> bool:
    """B→C 게이트: 다중턴 중간이 아니라 도구 호출 가능한 상태인지 검증."""
    return bool(b_out and b_out.get("ready_for_c"))


# ─────────────────────────────────────────────────────────────────────────────
# ① Prompt Chaining — A→B→C→D 순차 체인 + 게이트 검증
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ChainStep:
    name: str
    fn: Callable[..., Any]
    gate: Optional[Callable[[Any], bool]] = None


class PromptChain:
    """순차 호출 + 게이트 실패 시 조기 종료(early exit).

    각 step의 출력은 다음 step의 입력 가공에 쓰일 수 있도록 state에 보관된다.
    """

    def __init__(self, steps: List[ChainStep]):
        self.steps = steps

    def run(self, initial_input: Any) -> Dict[str, Any]:
        state: Dict[str, Any] = {"input": initial_input, "outputs": {}, "halted_at": None}
        current = initial_input
        for step in self.steps:
            current = step.fn(current, state) if _accepts_state(step.fn) else step.fn(current)
            state["outputs"][step.name] = current
            if step.gate and not step.gate(current):
                state["halted_at"] = step.name
                break
        state["final"] = current
        return state


def _accepts_state(fn: Callable) -> bool:
    try:
        import inspect
        return len(inspect.signature(fn).parameters) >= 2
    except (TypeError, ValueError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# ② Routing — 의도 분류 결과로 핸들러 분기
# ─────────────────────────────────────────────────────────────────────────────

class IntentRouter:
    """B팀 분류 결과(intent) → 등록된 핸들러로 라우팅.

    main.py의 tool_router를 패턴 관점에서 추상화한 wrapper.
    """

    def __init__(self, default_handler: Callable[[Dict], Dict]):
        self._handlers: Dict[str, Callable[[Dict], Dict]] = {}
        self._default = default_handler

    def register(self, intent: str, handler: Callable[[Dict], Dict]) -> None:
        self._handlers[intent] = handler

    def route(self, b_output: Dict) -> Dict:
        intent = b_output.get("intent", "symptom_inquiry")
        handler = self._handlers.get(intent, self._default)
        return handler(b_output)


# ─────────────────────────────────────────────────────────────────────────────
# ③ Parallelization — RAG · Hospital · Emergency 동시 실행
# ─────────────────────────────────────────────────────────────────────────────

def run_c_team_parallel(
    query: str,
    intent: str,
    lat: float,
    lng: float,
    rag_fn: Callable[[str], Dict],
    hospital_fn: Callable[[str, float, float], Dict],
    emergency_fn: Callable[[str], Dict],
    max_workers: int = 3,
) -> Dict[str, Any]:
    """C팀의 독립적인 3개 호출(RAG / Kakao / Emergency)을 ThreadPoolExecutor로 병렬화.

    네트워크 I/O 위주이므로 GIL 영향은 거의 없고, 직렬 대비 약 1.5~2x 응답 단축.
    intent별로 필요한 작업만 제출한다.
    """
    needs_rag = intent in ("symptom_inquiry", "medication_info")
    needs_hospital = intent in ("symptom_inquiry", "hospital_search")

    result: Dict[str, Any] = {
        "rag_context": None,
        "rag_sources": [],
        "hospitals": None,
        "emergency": None,
    }

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures: Dict[str, Any] = {"emergency": pool.submit(emergency_fn, query)}
        if needs_rag:
            futures["rag"] = pool.submit(rag_fn, query)
        if needs_hospital:
            futures["hospital"] = pool.submit(hospital_fn, query, lat, lng)

        if "rag" in futures:
            rag = futures["rag"].result()
            result["rag_context"] = rag.get("context")
            result["rag_sources"] = rag.get("sources", [])
        if "hospital" in futures:
            result["hospitals"] = futures["hospital"].result()
        result["emergency"] = futures["emergency"].result()

    return result


# ─────────────────────────────────────────────────────────────────────────────
# ⑤ Evaluator-Optimizer — 답변 품질 평가 후 재생성
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvalReport:
    passed: bool
    score: float
    issues: List[str] = field(default_factory=list)


class AnswerEvaluator:
    """D팀 답변에 대한 품질 평가자.

    기준:
      - 한국어 비율 ≥ 0.4 (영어 출력 방지)
      - 최소 길이 ≥ 15자 (너무 짧은 답변 차단)
      - 금지어 미포함 (FORBIDDEN_WORDS — 의료법 위반 차단)
    """

    KOREAN_RATIO_THRESHOLD = 0.4
    MIN_LENGTH = 15

    def __init__(self, forbidden_words: List[str]):
        self.forbidden_words = forbidden_words

    def evaluate(self, answer: str) -> EvalReport:
        issues: List[str] = []
        if not answer or not answer.strip():
            return EvalReport(False, 0.0, ["empty_answer"])

        korean_chars = len(re.findall(r"[가-힣]", answer))
        ratio = korean_chars / max(len(answer), 1)
        if ratio < self.KOREAN_RATIO_THRESHOLD:
            issues.append(f"low_korean_ratio({ratio:.2f})")

        if len(answer.strip()) < self.MIN_LENGTH:
            issues.append(f"too_short({len(answer)}자)")

        hit = [w for w in self.forbidden_words if w in answer]
        if hit:
            issues.append(f"forbidden_word:{','.join(hit)}")

        score = max(0.0, 1.0 - 0.25 * len(issues))
        return EvalReport(not issues, score, issues)


def generate_with_evaluator(
    generator: Callable[[], Dict[str, str]],
    evaluator: AnswerEvaluator,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """답변 생성 → 평가 → 실패 시 재생성. 최대 max_retries회 시도 후 마지막 결과 반환."""
    last_answer = ""
    last_report: Optional[EvalReport] = None
    attempts = 0
    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        out = generator()
        last_answer = (out or {}).get("answer", "")
        last_report = evaluator.evaluate(last_answer)
        if last_report.passed:
            break
    return {
        "answer": last_answer,
        "attempts": attempts,
        "eval_passed": bool(last_report and last_report.passed),
        "eval_issues": last_report.issues if last_report else ["no_eval"],
        "eval_score": last_report.score if last_report else 0.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ④ Orchestrator-Worker — 전체 파이프라인 조율
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineWorkers:
    """A/B/C/D 팀의 워커 함수 핸들 모음 — main.py에서 주입한다."""
    stt: Callable[[str], Dict]
    chat_followup: Callable[[str, str], Dict]
    tool_router: Callable[[Dict, float, float], Dict]
    answer_generator: Callable[[str, str, float, Dict], Dict]
    formatter: Callable[[str, bool], str]


class PipelineOrchestrator:
    """A→B→C→D를 조율하는 중앙 오케스트레이터.

    각 워커는 외부에서 주입(DI)되며, 오케스트레이터는
      - 라우팅 결정 (응급 → 119 즉시 분기 등)
      - 다중턴 게이트 (B 단계에서 followup 필요 시 조기 종료)
      - 컨텍스트 조립 (RAG + 병원 목록 텍스트 합성)
    역할만 담당한다.
    """

    def __init__(self, workers: PipelineWorkers, evaluator: Optional[AnswerEvaluator] = None):
        self.workers = workers
        self.evaluator = evaluator

    def run(
        self,
        raw_text: str,
        session_id: str = "default",
        lat: float = 37.5012,
        lng: float = 127.0396,
        use_evaluator: bool = True,
    ) -> Dict[str, Any]:
        # A: STT — 오디오 경로면 STT, 텍스트면 그대로
        audio_ext = (".wav", ".mp3", ".m4a", ".flac", ".ogg")
        if isinstance(raw_text, str) and raw_text.lower().endswith(audio_ext):
            text = self.workers.stt(raw_text).get("text", "")
        else:
            text = raw_text

        # B: 의도 분류 + 다중턴
        b_result = self.workers.chat_followup(text, session_id)
        if not gate_intent_to_tools(b_result):
            return {
                "answer": self.workers.formatter(b_result.get("answer", ""), False),
                "intent": b_result.get("intent"),
                "ready_for_c": False,
                "hospitals": None,
                "emergency": None,
            }

        # C: 라우팅 + 도구 호출 (main.py의 tool_router가 이미 라우터 역할)
        c_result = self.workers.tool_router(b_result["output_for_c"], lat, lng)

        # 컨텍스트 조립
        hospital_text = self._format_hospital_text(c_result.get("hospitals"))
        rag_context = c_result.get("rag_context") or ""
        combined = f"{rag_context}\n{hospital_text}".strip()

        # D: 응급이면 즉시 119, 아니면 답변 생성 (+ Evaluator-Optimizer)
        if c_result.get("emergency") and c_result["emergency"]["severity"] == "HIGH":
            final = self.workers.formatter("", True)
            eval_meta = None
        else:
            entities = b_result["output_for_c"].get("entities") or {}
            confidence = b_result["output_for_c"].get("confidence", 0.85)

            def _gen():
                return self.workers.answer_generator(text, combined, confidence, entities)

            if use_evaluator and self.evaluator is not None:
                result = generate_with_evaluator(_gen, self.evaluator, max_retries=2)
                final = self.workers.formatter(result["answer"], False)
                eval_meta = {
                    "attempts": result["attempts"],
                    "passed": result["eval_passed"],
                    "issues": result["eval_issues"],
                    "score": result["eval_score"],
                }
            else:
                raw_answer = _gen().get("answer", "")
                final = self.workers.formatter(raw_answer, False)
                eval_meta = None

        return {
            "answer": final,
            "intent": b_result["intent"],
            "ready_for_c": True,
            "hospitals": c_result.get("hospitals"),
            "emergency": c_result.get("emergency"),
            "rag_sources": c_result.get("rag_sources") or [],
            "eval": eval_meta,
        }

    @staticmethod
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
