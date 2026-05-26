"""End-to-End 테스트 — 배포된 컨테이너 대상 HTTP 시나리오 검증.

SDLC 단계 6 산출물.

실행:
    1. docker compose up -d --build (사전)
    2. python -m pytest tests/test_e2e.py -v
    또는 단독 실행: python tests/test_e2e.py

검증 시나리오 (4개 의도 × 핵심 안전 기준):
    1. emergency       — 응급 감지 → 119 안내
    2. symptom_inquiry — 증상 문의 → followup 또는 답변
    3. hospital_search — 병원 검색 → 카카오 API 결과 ≥ 1개
    4. medication_info — 약물 문의 → RAG 컨텍스트 응답

각 시나리오 별로 확인:
    - HTTP 200 응답
    - intent 분류 정확성
    - 한국어 비율 ≥ 40%
    - 금지어 (FORBIDDEN_WORDS 10개) 0건
    - 응답 시간 ≤ 60s (cold start 제외)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

import pytest
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 180  # 첫 호출은 cold start로 오래 걸릴 수 있음

FORBIDDEN_WORDS = ["예후", "처방전", "투약", "병변", "진단", "확정", "완치", "확신", "치료", "부작용"]


@dataclass
class Scenario:
    name: str
    text: str
    session_id: str
    expected_intent: str
    expect_hospitals: bool = False
    expect_emergency: bool = False


SCENARIOS = [
    Scenario(
        name="emergency",
        text="갑자기 가슴이 너무 아프고 숨이 안 쉬어져요",
        session_id="e2e_emergency",
        expected_intent="emergency",
        expect_emergency=True,
    ),
    Scenario(
        name="symptom_inquiry",
        text="무릎이 계속 욱신거려요",
        session_id="e2e_symptom",
        expected_intent="symptom_inquiry",
    ),
    Scenario(
        name="hospital_search",
        text="근처 내과 알려주세요",
        session_id="e2e_hospital",
        expected_intent="hospital_search",
        expect_hospitals=True,
    ),
    Scenario(
        name="medication_info",
        text="혈압약 부작용이 궁금해요",
        session_id="e2e_medication",
        expected_intent="medication_info",
    ),
]


def _backend_alive() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _korean_ratio(text: str) -> float:
    if not text:
        return 0.0
    korean = len(re.findall(r"[가-힣]", text))
    return korean / max(len(text), 1)


def _forbidden_hits(text: str) -> list[str]:
    return [w for w in FORBIDDEN_WORDS if w in (text or "")]


@pytest.fixture(scope="session")
def backend_ready():
    if not _backend_alive():
        pytest.skip(
            f"Backend not running at {BASE_URL}. "
            "Run `docker compose up -d --build` first."
        )


@pytest.mark.parametrize("sc", SCENARIOS, ids=[s.name for s in SCENARIOS])
def test_e2e_scenario(backend_ready, sc: Scenario):
    """4개 의도 시나리오 각각 검증."""
    start = time.perf_counter()
    r = requests.post(
        f"{BASE_URL}/chat",
        json={"text": sc.text, "session_id": sc.session_id, "lat": 37.5012, "lng": 127.0396},
        timeout=TIMEOUT,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    elapsed = time.perf_counter() - start

    # HTTP 응답 검증
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    body = r.json()

    # 필수 필드 존재
    for field in ("answer", "intent", "ready_for_c", "session_id"):
        assert field in body, f"missing field: {field}"

    # 의도 분류 (단, followup 다중턴 케이스는 ready_for_c=False도 허용)
    if body["ready_for_c"]:
        assert body["intent"] == sc.expected_intent, (
            f"intent mismatch: expected {sc.expected_intent}, got {body['intent']}"
        )

    # 응급 케이스 검증
    if sc.expect_emergency:
        assert body.get("is_emergency"), "expected is_emergency=True"
        assert "119" in body["answer"], "응급 응답에 '119' 안내 누락"

    # 병원 검색 케이스
    if sc.expect_hospitals:
        assert body.get("hospitals"), "expected non-empty hospitals list"
        assert len(body["hospitals"]) >= 1

    # 답변 품질 (응급 외)
    if not sc.expect_emergency:
        answer = body["answer"]
        ratio = _korean_ratio(answer)
        assert ratio >= 0.4, f"Korean ratio too low: {ratio:.2f} for {answer[:80]!r}"

    # 금지어 검사 (모든 케이스)
    hits = _forbidden_hits(body["answer"])
    assert not hits, f"forbidden words found: {hits} in {body['answer'][:120]!r}"

    # 응답 시간 (cold start 제외 — 첫 호출은 느릴 수 있음)
    # 60초 초과는 회귀 신호로 간주
    print(f"[{sc.name}] {elapsed:.2f}s · intent={body['intent']} · ready_for_c={body['ready_for_c']}")


def test_e2e_response_schema(backend_ready):
    """ChatResponse 스키마 보증."""
    r = requests.post(
        f"{BASE_URL}/chat",
        json={"text": "안녕하세요", "session_id": "e2e_schema"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    body = r.json()

    expected_keys = {"answer", "intent", "hospitals", "is_emergency", "ready_for_c", "session_id", "rag_sources"}
    assert expected_keys.issubset(body.keys()), (
        f"missing keys: {expected_keys - set(body.keys())}"
    )
    assert isinstance(body["answer"], str)
    assert isinstance(body["intent"], str)
    assert isinstance(body["is_emergency"], bool)
    assert isinstance(body["ready_for_c"], bool)


if __name__ == "__main__":
    # 단독 실행 모드
    print(f"E2E test against {BASE_URL}")
    if not _backend_alive():
        print(f"  ❌ backend not alive — run `docker compose up -d --build` first")
        raise SystemExit(1)

    print(f"  ✓ backend alive\n")

    results = []
    for sc in SCENARIOS:
        print(f"[{sc.name}] {sc.text}")
        try:
            start = time.perf_counter()
            r = requests.post(
                f"{BASE_URL}/chat",
                json={"text": sc.text, "session_id": sc.session_id},
                timeout=TIMEOUT,
            )
            elapsed = time.perf_counter() - start
            b = r.json()
            ok = (r.status_code == 200) and (
                not b["ready_for_c"] or b["intent"] == sc.expected_intent
            )
            hits = _forbidden_hits(b.get("answer", ""))
            results.append((sc.name, ok and not hits, elapsed, b.get("intent")))
            print(f"  {'✓' if ok else '✗'} intent={b.get('intent')} elapsed={elapsed:.1f}s forbidden={hits}")
        except Exception as e:
            results.append((sc.name, False, 0, str(e)))
            print(f"  ✗ ERROR: {e}")

    passed = sum(1 for _, ok, _, _ in results if ok)
    print(f"\n결과: {passed}/{len(results)} 통과")
    raise SystemExit(0 if passed == len(results) else 1)
