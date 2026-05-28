"""도메인 규칙 — 의료법·응급·STT 보정·진료과 매핑 (프레임워크 독립).

외부 라이브러리는 표준 `re` 만 사용한다. 모든 비즈니스 규칙(응급 점수·금지어·
진료과 매칭·발화 전처리)의 단일 출처(Single Source of Truth)이며,
adapters/usecases/main 은 이 모듈을 import 한다(의존성은 안쪽으로).

HITL 거버넌스 1차 책임자 (CLAUDE.md HITL 매트릭스):
  EMERGENCY_KEYWORDS·EMERGENCY_SCORES → 의사(응급의학)
  MEDICAL_CORRECTIONS·SYMPTOM_DEPT_MAP → 의사(일반의)
  FORBIDDEN_WORDS → 법률·컴플라이언스
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .entities import SEVERITY_HIGH, SEVERITY_LOW, SEVERITY_MEDIUM

# ── STT 전처리 상수 ──────────────────────────────────────────────────────────
WAKE_WORDS = ['헬로비야', '헬로비이', '헬로 비', '헬로비']
FILLER_PATTERN = re.compile(r'(?<!\w)(어+~*|음+~*|에+~*|그+~*|뭐+~*|저+~*|아+~*)(?=\s|$)(?!\w)')

# STT 오인식 보정 사전 (진료과명·증상·약물·검사명·질병명) — 의사(일반의) 검수
MEDICAL_CORRECTIONS = {
    "정형외가": "정형외과", "정형외꽈": "정형외과", "정형외와": "정형외과", "정영외과": "정형외과",
    "이비인후가": "이비인후과", "이비인호과": "이비인후과", "이비인우과": "이비인후과",
    "소화기가": "소화기내과", "피부가": "피부과", "피부부가": "피부과", "안과가": "안과",
    "내과가": "내과", "신경가": "신경과", "신경내가": "신경내과", "산부인가": "산부인과",
    "흉부외가": "흉부외과", "비뇨기가": "비뇨의학과", "재활의학가": "재활의학과", "가정의학가": "가정의학과",
    "무릅": "무릎", "어꺠": "어깨", "머리아포": "두통", "배아포": "복통", "울렁거려": "구역질",
    "체했어": "소화불량", "소화안돼": "소화불량", "오심이": "오심", "구통이": "구토",
    "기침이": "기침", "가래가": "가래", "콧물나": "콧물", "숨차": "호흡곤란", "붓기": "부종",
    "쑤셔": "통증", "결려": "통증", "욱신거려": "통증", "띵해": "두통", "가슴답답": "흉통",
    "혈압야": "혈압약", "혈압아": "혈압약", "혈압박": "혈압약", "당뇨야": "당뇨약", "당뇨약이": "당뇨약",
    "감기야": "감기약", "감기박": "감기약", "수면야": "수면약", "타이래놀": "타이레놀",
    "진통제가": "진통제", "소염제가": "소염제", "항생제가": "항생제",
    "엑스레이": "X-ray", "엑스래이": "X-ray", "엠알아이": "MRI", "씨티": "CT",
    "피검사": "혈액검사", "혈액검사가": "혈액검사", "소변검사가": "소변검사", "초음파가": "초음파",
    "고혈암": "고혈압", "당뇨병이": "당뇨병", "골다골증": "골다공증", "관절염이": "관절염",
    "치매가": "치매", "뇌경색이": "뇌경색", "뇌출혈이": "뇌출혈", "심근경새": "심근경색", "심근경섹": "심근경색",
}

# 응급 발화 트리거 (즉시 119 분기) — 의사(응급의학) 검수, 100% 감지 강제
EMERGENCY_KEYWORDS = [
    '숨이 안 쉬어', '가슴이 너무 아프', '의식이 없', '쓰러', '피를 토',
    '말이 어눌', '입이 돌아', '한쪽이 마비', '갑자기 안 보여',
]

# 부위별 다중턴 후속 질문
FOLLOWUP_QUESTIONS = {
    '무릎': '무릎이 많이 아프시군요. 혹시 걷기가 많이 힘드신가요?',
    '허리': '허리가 아프시군요. 혹시 허리를 펴거나 숙이기가 어려우신가요?',
    '어깨': '어깨가 불편하시군요. 팔을 위로 올리기가 힘드신 상태인가요?',
    '머리': '머리가 아프시군요. 갑자기 핑 돌거나 망치로 맞은 듯이 아픈가요?',
    '배': '배가 아프시군요. 속이 메스껍거나 콕콕 찌르는 느낌이 드세요?',
    '가슴': '가슴이 답답하시군요. 숨을 쉬기가 벅차거나 조이는 느낌인가요?',
}

# RAG 확장 질의
QUERY_REWRITE_MAP = {
    "무릎": "무릎통증 정형외과 관련 증상 치료 방법",
    "허리": "허리디스크 정형외과 척추 관련 증상 치료",
    "어깨": "어깨통증 정형외과 회전근개 관련 증상 치료",
    "머리": "두통이나 어지럼증 관련 증상 치료",
    "배": "복통 소화 소화기로 소화기내과 관련",
    "가래": "기침가래 폐 기관지 관련 증상 치료",
    "비뇨의학과": "비뇨의학과 관련 증상 전문 의원",
    "산부인과": "산부인과 관련 증상 전문 의원",
}

# 증상/부위 → (진료과, Kakao 카테고리 코드)
SYMPTOM_DEPT_MAP = {
    "무릎": ("정형외과", "05"), "허리": ("정형외과", "05"), "어깨": ("정형외과", "05"),
    "눈": ("안과", "12"), "귀": ("이비인후과", "13"), "코": ("이비인후과", "13"),
    "피부": ("피부과", "14"), "산부": ("산부인과", "15"), "머리": ("신경과", "02"),
    "가래": ("호흡기내과", "01"), "배": ("소화기내과", "01"), "가슴": ("내과", "01"),
}

# 응급도 가중치 (0~100) — 의사(응급의학) 검수
EMERGENCY_SCORES = {
    "숨이 안 쉬어": 100, "의식이 없": 100, "피를 토": 90,
    "가슴이 너무 아파": 90, "가슴통증이 심해": 90, "쓰러": 85,
    "쓰러졌": 80, "혈압이 200": 80, "혈압약을": 30, "혈압이 높아": 40,
}

# 의료법 위반 가능 어휘 (단정적 진단·처방 금지) — 법률·컴플라이언스 검수, 최소 10개 유지
FORBIDDEN_WORDS = ['예후', '처방전', '투약', '병변', '진단', '확정', '완치', '확신', '치료', '부작용']

# 응급 분기 임계값
EMERGENCY_HIGH_THRESHOLD = 70
EMERGENCY_MEDIUM_THRESHOLD = 40


# ── 순수 규칙 함수 ───────────────────────────────────────────────────────────

def preprocess_text(raw_text: str) -> str:
    """STT 원문 → 호출어/간투어 제거 + 오인식 보정 + 중복 제거."""
    text = raw_text
    for ww in WAKE_WORDS:
        text = text.replace(ww, '')
    text = re.sub(r'^[야아아]+\s*', '', text).strip()
    text = FILLER_PATTERN.sub('', text).strip()
    for wrong, correct in MEDICAL_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    words = text.split()
    deduped = [w for i, w in enumerate(words) if i == 0 or w != words[i - 1]]
    text = ' '.join(deduped)
    return re.sub(r'\s+', ' ', text).strip()


def query_rewrite(query: str) -> str:
    """RAG 리트리버용 확장 질의 변환."""
    for kw, rewritten in QUERY_REWRITE_MAP.items():
        if kw in query:
            return rewritten
    return query


def contains_emergency_keyword(text: str) -> bool:
    """즉시 119 분기 키워드 포함 여부 (공백 무시 비교)."""
    clean = text.strip().replace(" ", "")
    return any(kw.replace(" ", "") in clean for kw in EMERGENCY_KEYWORDS)


def score_emergency(text: str) -> Dict[str, object]:
    """EMERGENCY_SCORES 기반 응급 점수 합산. 2개 이상 매칭 시 1.2배(상한 100)."""
    total, matched = 0, []
    for kw, score in EMERGENCY_SCORES.items():
        if kw in text:
            total += score
            matched.append(kw)
    if len(matched) >= 2:
        total = min(total * 1.2, 100)
    return {"score": round(total), "matched": matched}


def classify_emergency(score: float) -> Dict[str, object]:
    """점수 → 응급도 분류(HIGH/MEDIUM/LOW) + 권고 행동."""
    if score >= EMERGENCY_HIGH_THRESHOLD:
        return {"is_emergency": True, "severity": SEVERITY_HIGH, "score": round(score),
                "action": "지금 바로 119에 전화해 주세요."}
    if score >= EMERGENCY_MEDIUM_THRESHOLD:
        return {"is_emergency": True, "severity": SEVERITY_MEDIUM, "score": round(score),
                "action": "응급실에 방문하시는 게 좋을 수 있어요."}
    return {"is_emergency": False, "severity": SEVERITY_LOW, "score": round(score), "action": None}


def lookup_department(symptom_text: str) -> Optional[Tuple[str, str]]:
    """발화에서 부위 키워드를 찾아 (진료과, Kakao 코드) 반환. 없으면 None."""
    for symptom, (name, code) in SYMPTOM_DEPT_MAP.items():
        if symptom in symptom_text:
            return name, code
    return None


def filter_forbidden(text: str) -> str:
    """의료법 금지어 제거."""
    out = text
    for word in FORBIDDEN_WORDS:
        out = out.replace(word, '')
    return out
