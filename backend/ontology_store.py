"""Graph DB (Ontology) Store — rdflib 기반 인프로세스 지식그래프.

docs/ontology/hellodoctor.ttl (OWL/SKOS) 를 RDF 그래프로 로드하고 SPARQL 로 질의한다.
backend/main.py 의 코드 사전(EMERGENCY_SCORES / SYMPTOM_DEPT_MAP / FOLLOWUP_QUESTIONS /
FORBIDDEN_WORDS)을 온톨로지에서 직접 끌어와 런타임에 사용한다.

설계 의도:
  - 외부 그래프 DB 서버(Neo4j 등) 없이 인프로세스로 동작 → 온프렘 Docker 에 가볍게 통합.
  - 코드 dict 로는 불가능한 **추이적 추론**(partOf*)을 SPARQL property path 로 제공.
  - rdflib/파일 부재 시 graceful degradation — 호출부가 기존 dict 로 폴백할 수 있게
    None/빈값을 반환한다 (예외를 던지지 않는다).

HITL: 온톨로지의 응급·금지어·진료과 매핑은 의사/법률 자문단 검수 대상.
      (CLAUDE.md HITL 매트릭스 #4·#5, docs/ontology/README.md)
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

HD = "http://lghellodoctor.ai/ontology#"


def _default_ontology_path() -> str:
    """기본 .ttl 경로 — 환경변수 우선, 없으면 repo 상대 경로 탐색."""
    env = os.environ.get("ONTOLOGY_PATH")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "docs", "ontology", "hellodoctor.ttl"),
        os.path.join(here, "ontology", "hellodoctor.ttl"),
        os.path.join(here, "hellodoctor.ttl"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.abspath(candidates[0])


class OntologyStore:
    """RDF 그래프 래퍼. 그래프는 최초 사용 시 1회 로드(lazy)된다."""

    def __init__(self, ttl_path: Optional[str] = None):
        self.ttl_path = ttl_path or _default_ontology_path()
        self._graph = None          # rdflib.Graph | None
        self._loaded = False

    # ── 로딩 ────────────────────────────────────────────────────────────────
    @property
    def graph(self):
        if not self._loaded:
            self._load()
        return self._graph

    def _load(self) -> None:
        self._loaded = True
        try:
            from rdflib import Graph
        except Exception as e:  # rdflib 미설치
            print(f"[Ontology] rdflib 사용 불가, dict 폴백: {e}")
            self._graph = None
            return
        if not os.path.exists(self.ttl_path):
            print(f"[Ontology] .ttl 없음({self.ttl_path}), dict 폴백")
            self._graph = None
            return
        try:
            g = Graph()
            g.parse(self.ttl_path, format="turtle")
            self._graph = g
            print(f"[Ontology] 로드 완료: {self.ttl_path} (triples={len(g)})")
        except Exception as e:
            print(f"[Ontology] 파싱 실패, dict 폴백: {e}")
            self._graph = None

    @property
    def available(self) -> bool:
        return self.graph is not None

    def _query(self, q: str):
        g = self.graph
        if g is None:
            return []
        try:
            return list(g.query(q, initNs=self._ns()))
        except Exception as e:
            print(f"[Ontology] SPARQL 오류: {e}")
            return []

    @staticmethod
    def _ns() -> Dict[str, str]:
        from rdflib import Namespace
        from rdflib.namespace import RDFS, SKOS
        return {"hd": Namespace(HD), "rdfs": RDFS, "skos": SKOS}

    # ── 1) 응급 점수 (EMERGENCY_SCORES 대체) ─────────────────────────────────
    @lru_cache(maxsize=1)
    def _emergency_pairs(self) -> Tuple[Tuple[str, int], ...]:
        rows = self._query(
            "SELECT ?label ?score WHERE { "
            "?s a hd:Symptom ; hd:emergencyScore ?score ; skos:hiddenLabel ?label . }"
        )
        out = []
        for label, score in rows:
            try:
                out.append((str(label), int(score)))
            except (TypeError, ValueError):
                continue
        return tuple(out)

    def emergency_score(self, text: str) -> Dict:
        """발화에 매칭되는 응급 키워드 점수 합산. dict EMERGENCY_SCORES 와 동형.

        2개 이상 매칭 시 1.2배 가중(상한 100) — main.emergency_check 와 동일 규칙.
        """
        total, matched = 0, []
        for label, score in self._emergency_pairs():
            if label and label in text:
                total += score
                matched.append(label)
        if len(matched) >= 2:
            total = min(total * 1.2, 100)
        return {"score": round(total), "matched": matched}

    # ── 2) 증상/부위 → 진료과 (SYMPTOM_DEPT_MAP 대체) ────────────────────────
    @lru_cache(maxsize=1)
    def _bodypart_dept_map(self) -> Tuple[Tuple[str, str, str], ...]:
        """(부위 라벨, 진료과 한국어명, kakao 코드) 목록. altLabel 포함."""
        q = (
            "SELECT ?bpLabel ?deptLabel ?code WHERE { "
            "  ?sym hd:affectsBodyPart ?bp ; hd:treatedBy ?dept . "
            "  ?dept rdfs:label ?deptLabel . "
            "  OPTIONAL { ?dept hd:kakaoCategoryCode ?code } "
            "  { ?bp rdfs:label ?bpLabel . FILTER(lang(?bpLabel)='ko') } "
            "  UNION { ?bp skos:altLabel ?bpLabel . FILTER(lang(?bpLabel)='ko') } "
            "  FILTER(lang(?deptLabel)='ko') "
            "}"
        )
        out = []
        for bp, dept, code in self._query(q):
            out.append((str(bp), str(dept), str(code) if code is not None else ""))
        return tuple(out)

    def symptom_to_department(self, text: str) -> Optional[Tuple[str, str]]:
        """발화에서 부위 키워드를 찾아 (진료과명, kakao 코드) 반환. 없으면 None."""
        for bp_label, dept, code in self._bodypart_dept_map():
            if bp_label and bp_label in text:
                return dept, code
        return None

    # ── 3) 부위별 후속 질문 (FOLLOWUP_QUESTIONS 대체) ────────────────────────
    @lru_cache(maxsize=1)
    def _followup_pairs(self) -> Tuple[Tuple[str, str], ...]:
        q = (
            "SELECT ?bpLabel ?q WHERE { "
            "  ?bp hd:followupQuestion ?q . "
            "  { ?bp rdfs:label ?bpLabel . FILTER(lang(?bpLabel)='ko') } "
            "  UNION { ?bp skos:altLabel ?bpLabel . FILTER(lang(?bpLabel)='ko') } "
            "}"
        )
        return tuple((str(bp), str(qq)) for bp, qq in self._query(q))

    def followup_question(self, text: str) -> Optional[Tuple[str, str]]:
        """발화에서 부위를 찾아 (부위라벨, 후속질문) 반환. 없으면 None."""
        for bp_label, question in self._followup_pairs():
            if bp_label and bp_label in text:
                return bp_label, question
        return None

    # ── 4) 의료법 금지어 (FORBIDDEN_WORDS 대체) ──────────────────────────────
    @lru_cache(maxsize=1)
    def forbidden_terms(self) -> Tuple[str, ...]:
        rows = self._query(
            "SELECT ?label WHERE { ?t a hd:ForbiddenTerm ; rdfs:label ?label . }"
        )
        return tuple(sorted({str(r[0]) for r in rows}))

    # ── 5) 추이적 추론: 특정 부위 하위 모든 신체부위 (dict 불가) ──────────────
    def body_parts_under(self, region_local_name: str) -> List[str]:
        """hd:partOf* property path 로 region 에 속한 모든 부위 라벨(ko) 반환.

        예: body_parts_under('LowerLimb') → ['하지', '무릎', ...].
        코드 dict 로는 불가능한 형식 온톨로지의 핵심 가치 (추론기 없이 SPARQL path).
        """
        q = (
            f"SELECT ?label WHERE {{ "
            f"  ?bp hd:partOf* hd:{region_local_name} . "
            f"  ?bp rdfs:label ?label . FILTER(lang(?label)='ko') "
            f"}}"
        )
        return sorted({str(r[0]) for r in self._query(q)})


# 모듈 레벨 싱글톤 — import 시 즉시 로드하지 않고 첫 호출에서 lazy load
ontology = OntologyStore()
