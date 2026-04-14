"""
LG HelloDoctor AI 모델 테스트
STT 전처리, 응답 품질, 금지어 필터 검증

실행: python -m pytest tests/test_ai_model.py -v
"""
import sys
import os
import re
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


# ====== STT 전처리 테스트 ======

class TestMedicalCorrections:
    """MEDICAL_CORRECTIONS 보정 사전 테스트"""

    def test_보정_사전_크기(self):
        from main import MEDICAL_CORRECTIONS
        assert len(MEDICAL_CORRECTIONS) >= 50, \
            f"보정 사전 항목 부족: {len(MEDICAL_CORRECTIONS)}개 (최소 50개)"

    def test_진료과명_보정(self):
        from main import preprocess_text
        cases = [
            ("정형외가", "정형외과"),
            ("이비인후가", "이비인후과"),
            ("피부가", "피부과"),
        ]
        for wrong, correct in cases:
            result = preprocess_text(wrong)
            assert correct in result, f"'{wrong}' → '{correct}' 보정 실패"

    def test_증상_보정(self):
        from main import preprocess_text
        cases = [
            ("무릅이 아파요", "무릎"),
            ("머리아포요", "두통"),
        ]
        for wrong, correct in cases:
            result = preprocess_text(wrong)
            assert correct in result, f"'{wrong}' → '{correct}' 보정 실패"

    def test_호출어_제거(self):
        from main import preprocess_text
        wake_words = ["헬로비야", "헬로비이", "헬로 비", "헬로비"]
        for wake in wake_words:
            result = preprocess_text(f"{wake} 머리가 아파요")
            assert wake not in result, f"호출어 '{wake}' 제거 실패"


# ====== 금지어 필터 테스트 ======

class TestForbiddenWords:
    """FORBIDDEN_WORDS 의료법 금지어 필터 테스트"""

    def test_금지어_개수(self):
        from main import FORBIDDEN_WORDS
        assert len(FORBIDDEN_WORDS) >= 10, \
            f"금지어 부족: {len(FORBIDDEN_WORDS)}개 (최소 10개)"

    def test_핵심_금지어_포함(self):
        from main import FORBIDDEN_WORDS
        must_include = ["진단", "처방전", "치료", "완치"]
        for word in must_include:
            assert word in FORBIDDEN_WORDS, f"필수 금지어 '{word}' 누락"

    def test_금지어_필터링(self):
        from main import format_response
        text = "이것은 치료가 필요한 진단입니다. 완치를 보장합니다."
        result = format_response(text)
        for word in ["치료", "진단", "완치"]:
            assert word not in result, f"금지어 '{word}' 필터링 실패"


# ====== 응답 품질 테스트 ======

class TestResponseQuality:
    """format_response() 응답 품질 테스트"""

    def test_영어단어_제거(self):
        from main import format_response
        text = "어르신, that 증상이 있으시군요. which 병원에 가시면 좋겠어요."
        result = format_response(text)
        english = re.findall(r'\b[a-zA-Z]{2,}\b', result)
        assert len(english) == 0, f"영어 단어 혼입: {english}"

    def test_문장수_제한(self):
        from main import format_response
        long_text = "문장입니다. " * 10
        result = format_response(long_text)
        sentences = re.split(r'[.!?]', result)
        sentences = [s.strip() for s in sentences if s.strip()]
        assert len(sentences) <= 6, f"문장 수 초과: {len(sentences)}개"

    def test_응급_응답_119_포함(self):
        from main import format_response
        result = format_response("", is_emergency=True)
        assert "119" in result

    def test_빈_입력_처리(self):
        from main import format_response
        result = format_response("")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_한국어_중심_응답(self):
        from main import format_response
        result = format_response("무릎이 많이 아프시군요. 정형외과에 가보세요.")
        # 한글 비율 확인
        korean_chars = len(re.findall(r'[가-힣]', result))
        total_chars = len(re.sub(r'\s', '', result))
        if total_chars > 0:
            korean_ratio = korean_chars / total_chars
            assert korean_ratio >= 0.7, f"한국어 비율 부족: {korean_ratio:.0%}"


# ====== 의도 분류 품질 테스트 ======

class TestIntentClassification:
    """classify_intent() 키워드 기반 부분 테스트"""

    EMERGENCY_CASES = [
        "숨이 안 쉬어요",
        "의식이 없어요",
        "피를 토했어요",
        "쓰러졌어요",
    ]

    def test_응급_키워드_100퍼센트_감지(self):
        from main import classify_intent
        for text in self.EMERGENCY_CASES:
            result = classify_intent(text)
            assert result["intent"] == "emergency", \
                f"응급 감지 실패: '{text}'"
            assert result["confidence"] == 1.0

    def test_응급_신뢰도_최대(self):
        from main import classify_intent
        result = classify_intent("숨이 안 쉬어요")
        assert result["confidence"] == 1.0
