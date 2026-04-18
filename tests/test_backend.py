"""
LG HelloDoctor 백엔드 테스트
실행: python -m pytest tests/test_backend.py -v
"""
import sys
import os
import re
import pytest

# 백엔드 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


# ====== A팀: STT 전처리 테스트 ======

class TestPreprocessText:
    """preprocess_text() 단위 테스트"""

    def test_호출어_제거(self):
        from main import preprocess_text
        result = preprocess_text("헬로비 머리가 아파요")
        assert "헬로비" not in result
        assert "머리" in result

    def test_간투어_제거(self):
        from main import preprocess_text
        result = preprocess_text("어 음 머리가 아파요")
        assert result.strip() in ["머리가 아파요", "머리가 아파요"]

    def test_의료용어_보정(self):
        from main import preprocess_text
        result = preprocess_text("무릅이 아파요")
        assert "무릎" in result

    def test_빈_문자열_처리(self):
        from main import preprocess_text
        result = preprocess_text("")
        assert result == ""


# ====== B팀: 의도 분류 테스트 ======

class TestClassifyIntent:
    """classify_intent() 단위 테스트 (Groq API 미사용 — 키워드 기반만)"""

    def test_응급_키워드_감지(self):
        from main import classify_intent
        result = classify_intent("숨이 안 쉬어요")
        assert result["intent"] == "emergency"
        assert result["confidence"] == 1.0

    def test_응급_키워드_감지2(self):
        from main import classify_intent
        result = classify_intent("의식이 없어요 쓰러졌어요")
        assert result["intent"] == "emergency"


# ====== B팀: 응급 판단 테스트 ======

class TestEmergencyCheck:
    """emergency_check() 단위 테스트"""

    def test_HIGH_응급(self):
        from main import emergency_check
        result = emergency_check("숨이 안 쉬어요")
        assert result["is_emergency"] is True
        assert result["severity"] == "HIGH"

    def test_일반_증상_LOW(self):
        from main import emergency_check
        result = emergency_check("무릎이 조금 아파요")
        assert result["severity"] == "LOW"

    def test_score_범위(self):
        from main import emergency_check
        result = emergency_check("숨이 안 쉬어요")
        assert 0 <= result["score"] <= 100


# ====== D팀: 응답 포맷 테스트 ======

class TestFormatResponse:
    """format_response() 단위 테스트"""

    def test_금지어_제거(self):
        from main import format_response
        result = format_response("치료가 필요합니다. 진단이 필요해요.")
        assert "치료" not in result
        assert "진단" not in result

    def test_영어단어_제거(self):
        from main import format_response
        result = format_response("that 증상이 있으시군요. which 병원에 가세요.")
        assert "that" not in result
        assert "which" not in result

    def test_응급_응답(self):
        from main import format_response
        result = format_response("", is_emergency=True)
        assert "119" in result

    def test_빈_입력_처리(self):
        from main import format_response
        result = format_response("")
        assert len(result) > 0


# ====== API 엔드포인트 테스트 ======

class TestAPI:
    """FastAPI 엔드포인트 테스트 (서버 실행 중일 때)"""

    @pytest.fixture
    def client(self):
        try:
            from fastapi.testclient import TestClient
            from main import app
            return TestClient(app)
        except Exception:
            pytest.skip("백엔드 모듈 로드 실패 (모델 파일 필요)")

    def test_루트_엔드포인트(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_chat_요청_형식(self, client):
        response = client.post("/chat", json={
            "text": "무릎이 아파요",
            "session_id": "test-session",
            "lat": 37.5012,
            "lng": 127.0396,
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "intent" in data
        assert "ready_for_c" in data
        assert "session_id" in data

    def test_chat_응급_응답(self, client):
        response = client.post("/chat", json={
            "text": "숨이 안 쉬어요",
            "session_id": "emergency-test",
            "lat": 37.5012,
            "lng": 127.0396,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "emergency"
