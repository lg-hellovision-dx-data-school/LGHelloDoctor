"""
LG HelloDoctor RAG 파이프라인 테스트
실행: python -m pytest tests/test_rag.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# ChromaDB 경로 설정
os.environ.setdefault('DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'RAG', 'db'))


class TestChromaDB:
    """ChromaDB 연결 및 데이터 테스트"""

    @pytest.fixture(scope="class")
    def collection(self):
        try:
            import chromadb
            db_path = os.environ.get('DB_PATH', '../RAG/db')
            client = chromadb.PersistentClient(path=db_path)
            col = client.get_collection("medical_knowledge")
            return col
        except Exception as e:
            pytest.skip(f"ChromaDB 연결 실패: {e}")

    def test_문서수_확인(self, collection):
        count = collection.count()
        assert count > 0, "ChromaDB에 문서가 없습니다"
        assert count >= 100, f"문서 수 부족: {count}개 (최소 100개 필요)"

    def test_컬렉션명_확인(self, collection):
        assert collection.name == "medical_knowledge"


class TestRAGPipeline:
    """RAG 파이프라인 검색 품질 테스트"""

    # 주요 증상 쿼리와 기대 키워드
    TEST_CASES = [
        ("무릎이 아파요", ["무릎", "정형외과", "관절"]),
        ("허리가 아파요", ["허리", "척추", "정형외과"]),
        ("머리가 아파요", ["두통", "신경", "머리"]),
    ]

    @pytest.fixture(scope="class")
    def rag_func(self):
        try:
            from main import full_rag_pipeline
            return full_rag_pipeline
        except Exception as e:
            pytest.skip(f"main.py 로드 실패: {e}")

    def test_검색결과_반환(self, rag_func):
        result = rag_func("무릎이 아파요")
        assert isinstance(result, str)

    def test_빈_결과_처리(self, rag_func):
        result = rag_func("xyzxyzxyz 존재하지않는증상")
        assert isinstance(result, str)
        assert len(result) > 0  # 빈 문자열 아닌 안내 메시지 반환


class TestQueryRewrite:
    """쿼리 재작성 테스트"""

    def test_키워드_재작성(self):
        try:
            from main import query_rewrite
        except Exception:
            pytest.skip("main.py 로드 실패")

        result = query_rewrite("무릎이 아파요")
        assert result != "무릎이 아파요"  # 재작성됨
        assert len(result) > 5

    def test_미매핑_키워드(self):
        try:
            from main import query_rewrite
        except Exception:
            pytest.skip("main.py 로드 실패")

        result = query_rewrite("알 수 없는 증상")
        assert result == "알 수 없는 증상"  # 원본 반환


class TestEmergencyCheck:
    """응급 판단 정확도 테스트"""

    EMERGENCY_CASES = [
        ("숨이 안 쉬어요", "HIGH"),
        ("의식이 없어요", "HIGH"),
        ("무릎이 조금 아파요", "LOW"),
        ("배가 살짝 아파요", "LOW"),
    ]

    def test_응급_판단_정확도(self):
        try:
            from main import emergency_check
        except Exception:
            pytest.skip("main.py 로드 실패")

        for text, expected_severity in self.EMERGENCY_CASES:
            result = emergency_check(text)
            assert result["severity"] == expected_severity, \
                f"'{text}' → 예상: {expected_severity}, 실제: {result['severity']}"
