"""Entities — 도메인 핵심 모델 (프레임워크 독립).

"외부 시스템이 사라져도 살아남는 의료 도메인 그 자체" (docs/CLEAN_ARCHITECTURE.md §1).
순수 dataclass 만 사용한다. DB/HTTP/모델 라이브러리 의존 없음.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# B팀(의도 분류기)의 5개 출력 라벨 — 온톨로지 hd:Intent 와 동기
INTENT_LABELS = (
    "symptom_inquiry",
    "hospital_search",
    "medication_info",
    "emergency",
    "general_chat",
)

# 응급도 (EMERGENCY_SCORES 임계값 기반)
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"


@dataclass
class Intent:
    """발화 의도."""
    label: str
    confidence: float = 0.0


@dataclass
class Symptom:
    """증상 — 부위·강도 등."""
    text: str
    body_part: Optional[str] = None


@dataclass
class Hospital:
    """병원 — 진료과·좌표·거리."""
    name: str
    address: str = ""
    phone: str = ""
    distance: int = 0
    department: str = ""
    lat: Optional[str] = None
    lng: Optional[str] = None


@dataclass
class Emergency:
    """응급 판단 결과."""
    is_emergency: bool
    severity: str
    score: int
    action: Optional[str] = None


@dataclass
class MedicalKnowledge:
    """RAG 의료 지식 청크."""
    text: str
    doc_id: str = ""
    score: float = 0.0
    source: str = "질병관리청 국가건강정보포털"


@dataclass
class Conversation:
    """다중턴 대화 세션 상태."""
    session_id: str
    step: int = 1
    body_part: Optional[str] = None
    history: List[str] = field(default_factory=list)
