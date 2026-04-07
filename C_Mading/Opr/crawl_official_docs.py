# Opr/crawl_official_docs.py
import requests
import re
import time
from Opr.chroma_client import get_medical_collection

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://health.kdca.go.kr/healthinfo/biz/health/unifiedSearch/unifiedSearchMain.do'
}
VIEW_URL = 'https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do'

# (이름, 카테고리, cntnts_sn) — 2026년 4월 기준
CRAWL_TARGETS = [
    # 질환 정보
    ('무릎관절염',      '증상_진료과', '5969'),
    ('허리디스크',      '증상_진료과', '3348'),
    ('오십견',          '증상_진료과', '1567'),
    ('고혈압',          '증상_진료과', '6765'),
    ('당뇨병',          '증상_진료과', '5305'),
    ('심근경색',        '증상_진료과', '6770'),
    ('뇌졸중',          '증상_진료과', '5495'),
    ('위염',            '증상_진료과', '6777'),
    ('역류성식도염',    '증상_진료과', '2057'),
    ('폐렴',            '증상_진료과', '5249'),
    ('천식',            '증상_진료과', '6784'),
    ('편두통',          '증상_진료과', '6557'),
    ('어지럼증',        '증상_진료과', '6550'),
    ('아토피',          '증상_진료과', '6582'),
    ('두드러기',        '증상_진료과', '6581'),
    # 복약 안내
    ('항생제',          '복약_안내',   '6475'),
    ('노인 약물복용',   '복약_안내',   '5428'),
    ('당뇨환자 식이요법', '복약_안내', '3388'),
    ('당뇨환자 운동요법', '복약_안내', '3390'),
    # 응급 안내
    ('심폐소생술',      '응급_안내',   '6226'),
    ('동물·곤충 응급',  '응급_안내',   '5483'),
    # 추가 질환
    ('수면장애',        '증상_진료과', '6558'),
    ('갑상선기능저하증','증상_진료과', '6782'),
    ('갑상선기능항진증','증상_진료과', '6783'),
    ('협심증',          '증상_진료과', '6769'),
    ('소화불량',        '증상_진료과', '6776'),
    ('이명',            '증상_진료과', '5706'),
    ('결막염',          '증상_진료과', '6583'),
    ('치통',            '증상_진료과', '6584'),
    ('사랑니',          '증상_진료과', '6585'),
    ('골절',            '증상_진료과', '5543'),
    ('요로감염',        '증상_진료과', '6586'),
    ('두통',            '증상_진료과', '6553'),
    ('불면증',          '증상_진료과', '6559'),
    ('폐결핵',          '증상_진료과', '5250'),
    ('빈혈',            '증상_진료과', '1104'),
]

DISEASE_DEPT_MAP = {
    '무릎관절염': '정형외과', '허리디스크': '정형외과', '오십견': '정형외과',
    '고혈압': '내과',         '당뇨병': '내과',         '심근경색': '심장내과',
    '뇌졸중': '신경과',       '위염': '소화기내과',     '역류성식도염': '소화기내과',
    '폐렴': '내과',           '천식': '호흡기내과',     '편두통': '신경과',
    '어지럼증': '이비인후과', '아토피': '피부과',       '두드러기': '피부과',
    '수면장애': '신경과',     '갑상선기능저하증': '내과', '갑상선기능항진증': '내과',
    '협심증': '심장내과',     '소화불량': '소화기내과', '이명': '이비인후과',
    '결막염': '안과',         '치통': '치과',            '사랑니': '치과',
    '골절': '정형외과',       '요로감염': '비뇨의학과', '두통': '신경과',
    '불면증': '신경과',       '폐결핵': '내과',          '빈혈': '내과',
}

def crawl_health_info(name: str, cntnts_sn: str) -> dict:
    try:
        response = requests.post(
            VIEW_URL,
            headers=HEADERS,
            data={'cntnts_sn': cntnts_sn},
            timeout=10
        )
        response.encoding = 'utf-8'
        content_parts = []

        for div_id in ['contentsDiv3', 'contentsDiv4', 'contentsDiv5']:
            if f'id="{div_id}"' in response.text:
                idx = response.text.index(f'id="{div_id}"')
                section = response.text[idx:idx+3000]
                clean = re.sub(r'<[^>]+>', ' ', section)
                clean = re.sub(r'\s+', ' ', clean).strip()
                content_parts.append(clean[:400])

        content = ' '.join(content_parts)[:500].strip()
        return {'text': content, 'success': bool(content)}
    except Exception:
        return {'text': '', 'success': False}


def add_to_chroma(documents: list[dict]):
    collection = get_medical_collection()

    existing = collection.get(include=[])
    existing_ids = set(existing["ids"]) if existing and existing.get("ids") else set()

    new_docs = [doc for doc in documents if doc["id"] not in existing_ids]

    if not new_docs:
        print("새로 추가할 문서 없음")
        return

    collection.add(
        ids=[doc["id"] for doc in new_docs],
        documents=[doc["text"] for doc in new_docs],
        metadatas=[
            {
                "category": doc["category"],
                "source": doc["source"],
            }
            for doc in new_docs
        ],
    )
    print(f"ChromaDB 추가 완료: {len(new_docs)}건")


ALL_DOCUMENTS = []
print('국가건강정보포털 크롤링 중...')

for name, category, sn in CRAWL_TARGETS:
    result = crawl_health_info(name, sn)
    time.sleep(0.5)

    if result['success']:
        dept = DISEASE_DEPT_MAP.get(name, '')
        text = f"{name}: {result['text']} (진료과: {dept})" if dept else result['text']

        ALL_DOCUMENTS.append({
            'id':       f'crawl_{name}',
            'text':     text,
            'category': category,
            'source':   'health.kdca.go.kr'
        })
        print(f'v {name}')
    else:
        print(f'x {name} 실패')

print(f'크롤링 완료: {len(ALL_DOCUMENTS)}개')

add_to_chroma(ALL_DOCUMENTS)