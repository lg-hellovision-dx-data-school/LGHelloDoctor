"""Domain layer 테스트 — Clean Architecture 안쪽 계층 (순수 규칙·엔티티).

실행: python -m pytest tests/test_domain.py -v

main.py(무거운 모델 로드)를 import 하지 않으므로 단독 실행 가능.
도메인 규칙은 의료법·응급·시니어 UX 의 **단일 출처(Single Source of Truth)** —
이 테스트가 깨지면 backend 전체가 영향을 받는다.

────────────────────────────────────────────────────────────────────────────
HITL 거버넌스 — 1차 책임자 매핑
  TestMedicalCorrections   → 의사 (일반의)
  TestForbiddenWords       → 법률·컴플라이언스
  TestEmergencyScoring     → 의사 (응급의학)
  TestDepartmentLookup     → 의사 (일반의)
────────────────────────────────────────────────────────────────────────────
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from adapters.presenters import format_response  # noqa: E402
from domain import rules as R  # noqa: E402
from domain.entities import (  # noqa: E402
    INTENT_LABELS,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    Emergency,
    Hospital,
    Intent,
)


# ── 상수·사전 ────────────────────────────────────────────────────────────────

class TestMedicalCorrections:
    """🧑‍⚕️ 의사(일반의) — STT 보정 사전 의학적 정확성."""

    def test_보정_사전_50개_이상(self):
        assert len(R.MEDICAL_CORRECTIONS) >= 50, f"보정 사전 부족: {len(R.MEDICAL_CORRECTIONS)}"

    def test_진료과_보정_샘플(self):
        assert R.MEDICAL_CORRECTIONS.get("정형외가") == "정형외과"
        assert R.MEDICAL_CORRECTIONS.get("안과가") == "안과"


class TestForbiddenWords:
    """⚖️ 법률·컴플라이언스 — 의료법 위반 어휘 차단."""

    def test_최소_10개_유지(self):
        assert len(R.FORBIDDEN_WORDS) >= 10

    def test_핵심_금지어_포함(self):
        for w in ["진단", "처방전", "완치", "치료"]:
            assert w in R.FORBIDDEN_WORDS, f"누락: {w}"


class TestEmergencyKeywords:
    """🚨 의사(응급의학) — 100% 감지 강제."""

    def test_키워드_충분(self):
        assert len(R.EMERGENCY_KEYWORDS) >= 9

    def test_핵심_응급_포함(self):
        for kw in ["숨이 안 쉬어", "의식이 없", "쓰러"]:
            assert kw in R.EMERGENCY_KEYWORDS


# ── 순수 규칙 함수 ──────────────────────────────────────────────────────────

class TestPreprocessText:
    def test_호출어_제거(self):
        assert "헬로비" not in R.preprocess_text("헬로비야 무릎이 아파")

    def test_간투어_제거(self):
        out = R.preprocess_text("음~ 무릎이 아파요")
        assert "음~" not in out and "음 " not in out

    def test_진료과명_보정(self):
        assert "정형외과" in R.preprocess_text("정형외가 어디에 있어요")

    def test_중복_단어_제거(self):
        out = R.preprocess_text("무릎 무릎이 아파요")
        # 연속 동일 단어 1회로
        assert out.count("무릎") <= 2


class TestEmergencyScoring:
    """🚨 의사(응급의학) — EMERGENCY_SCORES 가중 합산 규칙."""

    def test_단일_매칭(self):
        r = R.score_emergency("갑자기 숨이 안 쉬어요")
        assert r["score"] == 100
        assert "숨이 안 쉬어" in r["matched"]

    def test_복수_매칭_1점2배_상한_100(self):
        r = R.score_emergency("쓰러졌고 의식이 없어요")  # 3개 매칭
        assert r["score"] == 100
        assert len(r["matched"]) >= 2

    def test_비응급_0점(self):
        assert R.score_emergency("날씨가 좋네요")["score"] == 0


class TestClassifyEmergency:
    def test_HIGH_70이상(self):
        c = R.classify_emergency(80)
        assert c["severity"] == SEVERITY_HIGH and c["is_emergency"] is True
        assert "119" in c["action"]

    def test_MEDIUM_40이상_70미만(self):
        c = R.classify_emergency(50)
        assert c["severity"] == SEVERITY_MEDIUM and c["is_emergency"] is True
        assert "응급실" in c["action"]

    def test_LOW_40미만(self):
        c = R.classify_emergency(20)
        assert c["severity"] == SEVERITY_LOW and c["is_emergency"] is False
        assert c["action"] is None


class TestContainsEmergencyKeyword:
    @pytest.mark.parametrize("text", [
        "숨이 안 쉬어요", "숨이안쉬어", "의식이없어요", "쓰러졌어요", "한쪽이 마비됐어요"
    ])
    def test_응급_즉시_감지(self, text):
        assert R.contains_emergency_keyword(text) is True

    def test_일반발화_미감지(self):
        assert R.contains_emergency_keyword("무릎이 좀 아파요") is False


class TestDepartmentLookup:
    @pytest.mark.parametrize("text,dept,code", [
        ("무릎이 아파요", "정형외과", "05"),
        ("허리가 결려요", "정형외과", "05"),
        ("배가 아파요", "소화기내과", "01"),
        ("머리가 아파요", "신경과", "02"),
        ("귀가 잘 안 들려요", "이비인후과", "13"),
    ])
    def test_부위별_매핑(self, text, dept, code):
        result = R.lookup_department(text)
        assert result == (dept, code), f"{text} → {result}"

    def test_미매칭_None(self):
        assert R.lookup_department("기분이 우울해요") is None


class TestQueryRewrite:
    def test_부위_매칭시_확장(self):
        out = R.query_rewrite("무릎이 아파요")
        assert "정형외과" in out and out != "무릎이 아파요"

    def test_미매칭시_원본_반환(self):
        assert R.query_rewrite("xyz unknown") == "xyz unknown"


class TestFilterForbidden:
    def test_금지어_제거(self):
        assert "치료" not in R.filter_forbidden("이게 치료입니다")
        assert "진단" not in R.filter_forbidden("진단 결과")


# ── Entities ────────────────────────────────────────────────────────────────

class TestEntities:
    def test_의도_라벨_5종(self):
        assert len(INTENT_LABELS) == 5
        for label in ["symptom_inquiry", "hospital_search", "medication_info", "emergency", "general_chat"]:
            assert label in INTENT_LABELS

    def test_intent_dataclass(self):
        i = Intent(label="emergency", confidence=1.0)
        assert i.label == "emergency"

    def test_hospital_dataclass_기본값(self):
        h = Hospital(name="튼튼병원", distance=200)
        assert h.address == "" and h.department == ""

    def test_emergency_dataclass(self):
        e = Emergency(is_emergency=True, severity=SEVERITY_HIGH, score=100, action="119")
        assert e.severity == SEVERITY_HIGH


# ── Adapters: Presenters (domain 의 FORBIDDEN_WORDS 만 의존) ─────────────────

class TestFormatResponse:
    def test_응급_고정문구(self):
        assert "119" in format_response("아무거나", is_emergency=True)

    def test_빈답변_재질문(self):
        assert "다시" in format_response("")

    def test_금지어_제거(self):
        out = format_response("이건 치료가 필요합니다. 진단을 받으세요.")
        assert "치료" not in out and "진단" not in out

    def test_영어단어_제거(self):
        out = format_response("OK 어르신 무릎이 아프시군요. that is good.")
        assert "OK" not in out and "that" not in out
