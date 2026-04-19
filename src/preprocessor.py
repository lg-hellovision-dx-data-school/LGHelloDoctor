import re
import os
from dotenv import load_dotenv

load_dotenv()

# 간투어 패턴
FILLER_PATTERN = re.compile(r'(?<!\w)(어+~*|음+~*|에+~*|그+~*|뭐+~*|저+~*|아+~*)(?=\s|$)(?!\w)')

# 의료 용어 오탈자 보정 사전
MEDICAL_CORRECTIONS = {
    # ── 진료과 오탈자 ──────────────────────────────────────────────
    "정형외가":   "정형외과",
    "정형외꽈":   "정형외과",
    "정형외와":   "정형외과",
    "이비인호과": "이비인후과",
    "이비인우과": "이비인후과",
    "이비인후가": "이비인후과",
    "소화기가":   "소화기과",
    "피부가":     "피부과",
    "안과가":     "안과",
    "내과가":     "내과",
    "신경가":     "신경과",
    "신경내가":   "신경내과",
    "산부인가":   "산부인과",
    "흉부외가":   "흉부외과",
    "비뇨기가":   "비뇨기과",
    "재활의학가": "재활의학과",
    "가정의학가": "가정의학과",

    # ── 증상·신체 부위 ─────────────────────────────────────────────
    "무릅":       "무릎",
    "어꺠":       "어깨",
    "어깨가":     "어깨",
    "허리가":     "허리",
    "발목이":     "발목",
    "두통이":     "두통",
    "복통이":     "복통",
    "흉통이":     "흉통",
    "오심이":     "오심",
    "구통이":     "구토",
    "기침이":     "기침",
    "가래가":     "가래",
    "호흡이":     "호흡",
    "혈압이":     "혈압",
    "혈당이":     "혈당",

    # ── 약 관련 ────────────────────────────────────────────────────
    "혈압야":     "혈압약",
    "혈압아":     "혈압약",
    "혈압박":     "혈압약",
    "당뇨약이":   "당뇨약",
    "당뇨야":     "당뇨약",
    "진통제가":   "진통제",
    "소염제가":   "소염제",
    "항생제가":   "항생제",
    "감기야":     "감기약",
    "감기박":     "감기약",
    "수면야":     "수면약",
    "수면제가":   "수면제",

    # ── 검사·처치 ──────────────────────────────────────────────────
    "엑스레이":   "X-ray",
    "엑스래이":   "X-ray",
    "엠알아이":   "MRI",
    "씨티":       "CT",
    "초음파가":   "초음파",
    "혈액검사가": "혈액검사",
    "소변검사가": "소변검사",

    # ── 병명 ───────────────────────────────────────────────────────
    "고혈암":     "고혈압",
    "당뇨병이":   "당뇨병",
    "골다골증":   "골다공증",
    "관절염이":   "관절염",
    "치매가":     "치매",
    "뇌경색이":   "뇌경색",
    "뇌출혈이":   "뇌출혈",
    "심근경새":   "심근경색",
    "심근경섹":   "심근경색",
}

# 금지 단어
FORBIDDEN_WORDS = ["예후", "처방전", "투약", "병변"]

# Groq LLM 시스템 프롬프트
_LLM_SYSTEM_PROMPT = """당신은 노인 음성인식 텍스트 교정 전문가입니다.
STT로 변환된 노인 발화 텍스트를 자연스럽게 교정해주세요.

교정 규칙:
1. 불명확한 발음으로 인한 오탈자 교정 (예: 무릅 → 무릎)
2. 의료 용어 정확하게 교정 (예: 정형외가 → 정형외과)
3. 앞뒤 문맥을 보고 의미에 맞게 교정
4. 노인 특유의 말투와 어투는 그대로 유지
5. 원문의 의미를 절대 바꾸지 말 것
6. 교정된 텍스트만 출력 (설명 없이)"""


def correct_medical_terms(text: str) -> str:
    for wrong, correct in MEDICAL_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    return text


def remove_fillers(text: str) -> str:
    return FILLER_PATTERN.sub('', text).strip()


def normalize(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def filter_forbidden(text: str) -> str:
    """금지 단어를 일반 표현으로 대체합니다."""
    REPLACEMENTS = {
        "예후":   "앞으로의 상태",
        "처방전": "약 처방 내용",
        "투약":   "약 복용",
        "병변":   "이상 부위",
    }
    for word, replacement in REPLACEMENTS.items():
        text = text.replace(word, replacement)
    return text


def correct_with_llm(text: str) -> str:
    """
    Groq LLM으로 문맥 기반 텍스트 교정.
    규칙 기반 교정으로 잡지 못한 오류를 LLM이 보완합니다.
    API 오류 시 원본 텍스트 반환 (fallback).
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return text  # API 키 없으면 스킵

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user",   "content": text},
            ],
            temperature=0.1,   # 낮게 설정 → 일관된 교정
            max_tokens=256,
        )
        corrected = response.choices[0].message.content.strip()
        return corrected if corrected else text
    except Exception as e:
        print(f"[LLM 교정 오류] {e} → 규칙 기반 결과 사용")
        return text


def preprocess(raw_text: str, use_llm: bool = True) -> dict:
    """
    STT 결과 텍스트를 전처리합니다.
    반환값은 B팀 의도 분류기로 전달됩니다.

    Args:
        raw_text : STT 원본 텍스트
        use_llm  : True → Groq LLM 교정 추가 (기본값)
                   False → 규칙 기반만 사용 (빠름, 오프라인)
    """
    text = raw_text

    # Step 1: 간투어 제거
    text = remove_fillers(text)

    # Step 2: 규칙 기반 의료 용어 교정
    text = correct_medical_terms(text)

    # Step 3: 금지 단어 필터
    text = filter_forbidden(text)

    # Step 4: 정규화
    text = normalize(text)

    # Step 5: LLM 문맥 교정 (규칙으로 못 잡은 오류 보완)
    if use_llm:
        text = correct_with_llm(text)

    return {
        "text":     text,       # 전처리된 텍스트 (B팀으로 전달)
        "raw_text": raw_text,   # 원본 텍스트 (디버깅용)
    }