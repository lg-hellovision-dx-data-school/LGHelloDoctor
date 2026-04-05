import os
from dotenv import load_dotenv

load_dotenv()

# TODO:
# 실제 배포 시 아래 설정값을 환경변수/설정파일로 분리 예정

RAG_BACKEND = "dummy"
HOSPITAL_SEARCH_BACKEND = "hybrid"   # dummy / kakao / hira / hybrid
SEVERITY_BACKEND = "rule"
DEFAULT_LOCATION = "서울 강남구"

# Kakao Local API
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_LOCAL_BASE_URL = "https://dapi.kakao.com/v2/local"

# HIRA
HIRA_API_KEY = os.getenv("HIRA_API_KEY", "")

# 약국정보서비스는 공식 요청주소가 확인됨
HIRA_PHARMACY_ENDPOINT = "https://apis.data.go.kr/B551182/pharmacyInfoService/getParmacyBasisList"

# 병원정보서비스는 공식 페이지에서 GET/getHospBasisList가 확인되지만
# 전체 요청주소 문자열은 여기서 직접 확인이 덜 됐으니 config에서 관리
# Swagger/OpenAPI 명세에서 요청주소 확인 후 필요시 수정
HIRA_HOSPITAL_ENDPOINT = os.getenv(
    "HIRA_HOSPITAL_ENDPOINT",
    "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
)