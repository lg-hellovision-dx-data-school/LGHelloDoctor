"""
LG HelloDoctor 프론트엔드 API 레이어 테스트
(TypeScript 빌드 없이 Python으로 API 동작 검증)

실행: python -m pytest tests/test_frontend.py -v
"""
import re
import pytest
import requests
import os

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:80")


# ====== 프론트엔드 서버 테스트 ======

class TestFrontendServer:
    """nginx로 서빙되는 프론트엔드 서버 테스트"""

    def test_메인_페이지_응답(self):
        try:
            res = requests.get(FRONTEND_URL, timeout=5)
            assert res.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("프론트엔드 서버 미실행")

    def test_HTML_반환(self):
        try:
            res = requests.get(FRONTEND_URL, timeout=5)
            assert "text/html" in res.headers.get("Content-Type", "")
        except requests.exceptions.ConnectionError:
            pytest.skip("프론트엔드 서버 미실행")

    def test_SPA_라우팅(self):
        """존재하지 않는 경로도 index.html 반환 (SPA 라우팅)"""
        try:
            res = requests.get(f"{FRONTEND_URL}/some/unknown/path", timeout=5)
            assert res.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("프론트엔드 서버 미실행")


# ====== chat.ts 로직 검증 (Python으로 동일 로직 구현) ======

class TestSanitizeChatAnswer:
    """sanitizeChatAnswer() 동일 로직 테스트"""

    def sanitize(self, text: str) -> str:
        """frontend/src/api/chat.ts의 sanitizeChatAnswer 동일 로직"""
        text = re.sub(r'\[\s*\d+\s*턴\s*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[AI\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[USER\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[사용자\]', '', text)
        text = re.sub(r'\[어시스턴트\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def test_턴_표식_제거(self):
        result = self.sanitize("[1턴] 무릎이 아프시군요.")
        assert "[1턴]" not in result
        assert "무릎이 아프시군요." in result

    def test_AI_표식_제거(self):
        result = self.sanitize("[AI] 안녕하세요.")
        assert "[AI]" not in result

    def test_USER_표식_제거(self):
        result = self.sanitize("[USER] 머리가 아파요.")
        assert "[USER]" not in result

    def test_정상_텍스트_유지(self):
        text = "어르신, 무릎이 많이 아프시군요."
        result = self.sanitize(text)
        assert result == text

    def test_연속_공백_제거(self):
        result = self.sanitize("무릎이   아파요.")
        assert "  " not in result


class TestChatApiUrl:
    """getChatApiUrl() 동일 로직 테스트"""

    def get_chat_api_url(self, env_value: str) -> str:
        """frontend/src/api/chat.ts의 getChatApiUrl 동일 로직"""
        default = "http://localhost:8000/chat"
        if not env_value or not re.match(r'^https?://', env_value, re.IGNORECASE):
            return default
        if re.search(r'/chat/?$', env_value, re.IGNORECASE):
            return env_value
        return env_value.rstrip('/') + '/chat'

    def test_기본_URL(self):
        result = self.get_chat_api_url("")
        assert result == "http://localhost:8000/chat"

    def test_베이스_URL에_chat_추가(self):
        result = self.get_chat_api_url("http://localhost:8000")
        assert result.endswith("/chat")

    def test_이미_chat_포함된_URL_유지(self):
        url = "http://localhost:8000/chat"
        result = self.get_chat_api_url(url)
        assert result == url

    def test_ngrok_URL_처리(self):
        result = self.get_chat_api_url("https://abc.ngrok-free.dev")
        assert result == "https://abc.ngrok-free.dev/chat"


# ====== 백엔드-프론트 계약 테스트 ======

class TestChatAPIContract:
    """프론트엔드가 기대하는 백엔드 응답 형식 검증"""

    @pytest.fixture
    def chat_response(self):
        try:
            res = requests.post(f"{BASE_URL}/chat", json={
                "text": "무릎이 아파요",
                "session_id": "contract-test",
                "lat": 37.5012,
                "lng": 127.0396,
            }, timeout=30)
            return res.json()
        except Exception:
            pytest.skip("백엔드 서버 미실행")

    def test_answer_필드_존재(self, chat_response):
        assert "answer" in chat_response
        assert isinstance(chat_response["answer"], str)
        assert len(chat_response["answer"]) > 0

    def test_intent_필드_존재(self, chat_response):
        assert "intent" in chat_response
        valid_intents = ["symptom_inquiry", "hospital_search", "medication_info", "emergency"]
        assert chat_response["intent"] in valid_intents

    def test_ready_for_c_필드_존재(self, chat_response):
        assert "ready_for_c" in chat_response
        assert isinstance(chat_response["ready_for_c"], bool)

    def test_session_id_필드_존재(self, chat_response):
        assert "session_id" in chat_response
        assert chat_response["session_id"] == "contract-test"

    def test_hospitals_필드_형식(self, chat_response):
        hospitals = chat_response.get("hospitals")
        if hospitals:
            assert isinstance(hospitals, list)
            for h in hospitals:
                assert "name" in h
                assert "address" in h
                assert "phone" in h
                assert "distance" in h

    def test_답변에_영어단어_없음(self, chat_response):
        answer = chat_response.get("answer", "")
        english_words = re.findall(r'\b[a-zA-Z]{2,}\b', answer)
        assert len(english_words) == 0, f"영어 단어 혼입: {english_words}"
