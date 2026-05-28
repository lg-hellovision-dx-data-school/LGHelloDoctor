"""Graph DB (Ontology) Store 테스트 — rdflib SPARQL over hellodoctor.ttl.

실행: python -m pytest tests/test_ontology_store.py -v

main.py 를 import 하지 않으므로(무거운 모델 로드 없음) 단독 실행 가능.

────────────────────────────────────────────────────────────────────────────
HITL 거버넌스 — 본 테스트의 1차 책임자 매핑
  TestEmergencyGraph      → 의사 (응급의학)   | 응급 점수 온톨로지 정합성
  TestDepartmentGraph     → 의사 (일반의)      | 증상→진료과 매핑
  TestForbiddenGraph      → 법률·컴플라이언스 | 금지어 온톨로지 동기화
  TestTransitiveReasoning → 개발팀            | dict 불가능한 추론 검증
────────────────────────────────────────────────────────────────────────────
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ontology_store import OntologyStore  # noqa: E402

ONT = OntologyStore()
_pytestmark_available = ONT.available


@pytest.mark.skipif(not _pytestmark_available, reason="rdflib/.ttl 미사용 환경 — dict 폴백")
class TestOntologyLoad:
    def test_그래프_로드됨(self):
        assert ONT.available, "온톨로지 그래프 로드 실패"

    def test_트리플_충분(self):
        assert len(ONT.graph) >= 400, f"트리플 수 부족: {len(ONT.graph)}"


@pytest.mark.skipif(not _pytestmark_available, reason="dict 폴백 환경")
class TestEmergencyGraph:
    """🚨 1차 책임자: 의사(응급의학) — EMERGENCY_SCORES 온톨로지 동기화"""

    def test_단일_응급_키워드_점수(self):
        r = ONT.emergency_score("갑자기 숨이 안 쉬어요")
        assert r["score"] == 100
        assert "숨이 안 쉬어" in r["matched"]

    def test_복수_매칭_가중(self):
        # 2개 이상 매칭 → 1.2배(상한 100). 둘 다 100점이라 100 유지
        r = ONT.emergency_score("쓰러졌고 의식이 없어요")
        assert r["score"] == 100
        assert len(r["matched"]) >= 2

    def test_비응급_0점(self):
        assert ONT.emergency_score("날씨가 좋네요")["score"] == 0


@pytest.mark.skipif(not _pytestmark_available, reason="dict 폴백 환경")
class TestDepartmentGraph:
    """🧑‍⚕️ 1차 책임자: 의사(일반의) — 증상→진료과 SPARQL 매핑"""

    @pytest.mark.parametrize("text,dept,code", [
        ("무릎이 아파요", "정형외과", "05"),
        ("허리가 결려요", "정형외과", "05"),
        ("머리가 아파요", "신경과", "02"),
        ("배가 아파요", "소화기내과", "01"),
    ])
    def test_부위별_진료과_매핑(self, text, dept, code):
        result = ONT.symptom_to_department(text)
        assert result is not None, f"매핑 실패: {text}"
        assert result[0] == dept
        assert result[1] == code

    def test_미매칭_None(self):
        assert ONT.symptom_to_department("날씨 이야기") is None


@pytest.mark.skipif(not _pytestmark_available, reason="dict 폴백 환경")
class TestFollowupGraph:
    def test_부위별_후속질문(self):
        r = ONT.followup_question("허리가 아파요")
        assert r is not None
        assert r[0] == "허리"
        assert "허리" in r[1]


@pytest.mark.skipif(not _pytestmark_available, reason="dict 폴백 환경")
class TestForbiddenGraph:
    """⚖️ 1차 책임자: 법률·컴플라이언스 — 금지어 온톨로지 동기화"""

    def test_금지어_최소_10개(self):
        terms = ONT.forbidden_terms()
        assert len(terms) >= 10, f"금지어 부족: {len(terms)}개"

    def test_핵심_금지어_포함(self):
        terms = ONT.forbidden_terms()
        for w in ["진단", "처방전", "완치", "치료"]:
            assert w in terms, f"핵심 금지어 누락: {w}"


@pytest.mark.skipif(not _pytestmark_available, reason="dict 폴백 환경")
class TestTransitiveReasoning:
    """🔬 dict 로는 불가능한 hd:partOf* 추이추론 — 형식 온톨로지의 핵심 가치"""

    def test_하지_하위부위_추론(self):
        parts = ONT.body_parts_under("LowerLimb")
        # 무릎 partOf 하지 → 추이추론으로 무릎과 하지 모두 포함
        assert "하지" in parts
        assert "무릎" in parts

    def test_머리_하위부위_추론(self):
        parts = ONT.body_parts_under("Head")
        # 눈·귀·코 partOf 두부(Head)
        assert "눈" in parts
        assert "귀" in parts
