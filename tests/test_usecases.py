"""Use Cases / Infra layer 테스트 — 순수 전략 로직 + 어댑터(mock).

실행: python -m pytest tests/test_usecases.py -v

main.py(모델 로드) 미import. RAG 검색 전략·병원 탐색 유스케이스·Kakao 어댑터를
모델/네트워크 없이 검증한다.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import infra.map_kakao as mk  # noqa: E402
from usecases.hospital import find_nearby_hospital  # noqa: E402
from usecases.rag import rrf_fuse, select_confident  # noqa: E402


# ── usecases.rag — 검색 전략 ─────────────────────────────────────────────────

class TestRRFFusion:
    def test_단일_리스트_순위_보존(self):
        hits = [{"doc_id": "a"}, {"doc_id": "b"}, {"doc_id": "c"}]
        assert [r["doc_id"] for r in rrf_fuse((hits,))] == ["a", "b", "c"]

    def test_두_리스트_공통상위_가중(self):
        l1 = [{"doc_id": "a"}, {"doc_id": "b"}, {"doc_id": "c"}]
        l2 = [{"doc_id": "c"}, {"doc_id": "a"}, {"doc_id": "d"}]
        ids = [r["doc_id"] for r in rrf_fuse((l1, l2))]
        assert ids[0] in ("a", "c")   # 양쪽 상위 등장 → 최상위
        assert set(ids) == {"a", "b", "c", "d"}

    def test_top_n_제한(self):
        hits = [{"doc_id": str(i)} for i in range(30)]
        assert len(rrf_fuse((hits,), top_n=20)) == 20


class TestSelectConfident:
    def test_임계값_미만_제외(self):
        items = [{"rerank_score": 0.9}, {"rerank_score": -0.1}, {"rerank_score": 0.3}]
        out = select_confident(items, threshold=0.0, top=3)
        assert len(out) == 2 and all(c["rerank_score"] >= 0 for c in out)

    def test_top_제한_후_필터(self):
        items = [{"rerank_score": s} for s in [0.5, 0.4, 0.3, 0.2]]
        assert len(select_confident(items, top=2)) == 2


# ── usecases.hospital — 병원 탐색 (DI) ───────────────────────────────────────

class _FakeOntology:
    available = True

    def symptom_to_department(self, text):
        return ("이비인후과", "13") if "목" in text else None


def _fake_map(dept, lat, lng):
    return [
        {"name": "가까운병원", "phone": "02-1", "distance": 100, "address": "A"},
        {"name": "먼병원", "phone": "02-2", "distance": 900, "address": "B"},
        {"name": "전화없음", "phone": "", "distance": 50, "address": "C"},
    ]


class TestFindNearbyHospital:
    def test_도메인_매핑_우선(self):
        r = find_nearby_hospital("무릎이 아파요", map_search=_fake_map, ontology=_FakeOntology())
        assert r["department"] == "정형외과"

    def test_전화없음_제외_거리순_정렬(self):
        r = find_nearby_hospital("무릎이 아파요", map_search=_fake_map, ontology=None)
        assert [h["name"] for h in r["nearby"]] == ["가까운병원", "먼병원"]

    def test_도메인_미매칭시_온톨로지_폴백(self):
        r = find_nearby_hospital("목이 칼칼해요", map_search=_fake_map, ontology=_FakeOntology())
        assert r["department"] == "이비인후과"

    def test_온톨로지도_미매칭시_내과_기본(self):
        r = find_nearby_hospital("기분이 우울해요", map_search=_fake_map, ontology=None)
        assert r["department"] == "내과"


# ── infra.map_kakao — Kakao 어댑터 (requests mock) ──────────────────────────

class TestKakaoGateway:
    def test_검색결과_파싱(self, monkeypatch):
        class _Resp:
            def json(self):
                return {"documents": [
                    {"place_name": "튼튼정형외과", "road_address_name": "서울 강남",
                     "phone": "02-111", "distance": "250", "y": "37.5", "x": "127.0"},
                ]}
        monkeypatch.setattr(mk.requests, "get", lambda *a, **k: _Resp())
        out = mk.search_kakao("정형외과", 37.5, 127.0)
        assert out[0]["name"] == "튼튼정형외과"
        assert out[0]["distance"] == 250 and out[0]["phone"] == "02-111"

    def test_예외시_빈리스트(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("network")
        monkeypatch.setattr(mk.requests, "get", _boom)
        assert mk.search_kakao("내과", 37.5, 127.0) == []

    def test_gateway_클래스_위임(self, monkeypatch):
        monkeypatch.setattr(mk, "search_kakao", lambda d, la, ln: [{"name": d}])
        assert mk.KakaoMapGateway().nearby("내과", 37.5, 127.0)[0]["name"] == "내과"
