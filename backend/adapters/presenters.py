"""Presenters — Use Case 결과를 시니어 친화 출력으로 변환.

domain 규칙(FORBIDDEN_WORDS)에만 의존한다. 프레임워크 의존 없음.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from domain.rules import FORBIDDEN_WORDS


def format_response(raw_answer: str, is_emergency: bool = False) -> str:
    """답변 정제: 응급 고정 문구 / 금지어·영어 제거 / 최대 6문장."""
    if is_emergency:
        return '지금 바로 119에 전화해 주세요. 매우 위험한 상황일 수 있습니다.'
    if not raw_answer:
        return "죄송합니다. 다시 한번 말씀해 주시겠어요?"
    answer = raw_answer
    for word in FORBIDDEN_WORDS:
        answer = answer.replace(word, '')
    # 영어 단어 제거 (한국어 문장 사이 영어 접속사/단어)
    answer = re.sub(r'\b[a-zA-Z]+\b', '', answer)
    answer = re.sub(r'\s+', ' ', answer).strip()
    sentences = re.split(r'([.!?])', answer)
    combined = []
    for i in range(0, len(sentences) - 1, 2):
        s = sentences[i].strip() + sentences[i + 1]
        if s:
            combined.append(s)
    final_text = ' '.join(combined[:6]).strip()
    return final_text if final_text else answer


def format_hospital_text(hospitals: Optional[Dict]) -> str:
    """병원 목록 → 답변용 컨텍스트 텍스트 (거리·도보·주소·전화)."""
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
