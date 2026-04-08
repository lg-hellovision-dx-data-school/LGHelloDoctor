"""Neo4j 지식 그래프 시딩 — 이미지 기준 증상→질환→진료과 데이터 추가"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI', '').replace('neo4j+s://', 'neo4j+ssc://'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

# ── 시딩 데이터: (증상, 질환, 진료과) ─────────────────────────────────────────
# 이미지 기준: 증상 → 어디로 가야 할까?
SEED_DATA = [
    # 기침·열·감기 → 내과 / 이비인후과
    ("기침",        "상기도감염",     "내과"),
    ("열",          "발열",           "내과"),
    ("감기",        "감기",           "내과"),
    ("콧물",        "비염",           "이비인후과"),
    ("코막힘",      "비염",           "이비인후과"),
    ("인후통",      "편도염",         "이비인후과"),

    # 소화기 → 내과
    ("속쓰림",      "위염",           "내과"),
    ("체함",        "소화불량",       "내과"),
    ("복통",        "위장염",         "내과"),
    ("소화불량",    "소화불량",       "내과"),
    ("구토",        "위장염",         "내과"),

    # 설사·혈변·치질 → 내과 / 외과
    ("설사",        "장염",           "내과"),
    ("혈변",        "대장질환",       "외과"),
    ("치질",        "치핵",           "외과"),

    # 두통·어지럼증 → 신경과
    ("두통",        "편두통",         "신경과"),
    ("어지럼증",    "뇌졸중 전구증",  "신경과"),
    ("편두통",      "편두통",         "신경과"),

    # 허리·목 통증 → 정형외과
    ("허리 통증",   "요추 디스크",    "정형외과"),
    ("목 통증",     "경추 디스크",    "정형외과"),
    ("무릎 통증",   "퇴행성 관절염",  "정형외과"),
    ("어깨 통증",   "회전근개 파열",  "정형외과"),
    ("골절",        "골절",           "정형외과"),
    ("교통사고 후 통증", "타박상",    "정형외과"),

    # 손저림·다리 당김 → 신경과 / 정형외과
    ("손저림",      "말초신경병증",   "신경과"),
    ("다리 당김",   "좌골신경통",     "신경과"),
    ("마비",        "뇌졸중",         "신경과"),

    # 피부 → 피부과
    ("여드름",      "여드름",         "피부과"),
    ("피부염",      "접촉성 피부염",  "피부과"),
    ("두드러기",    "두드러기",       "피부과"),
    ("습진",        "습진",           "피부과"),
    ("아토피",      "아토피 피부염",  "피부과"),

    # 눈 → 안과
    ("눈 충혈",     "결막염",         "안과"),
    ("시야 흐림",   "백내장",         "안과"),
    ("눈 통증",     "녹내장",         "안과"),
    ("시력 저하",   "굴절이상",       "안과"),

    # 귀 → 이비인후과
    ("귀 먹먹함",   "중이염",         "이비인후과"),
    ("이통",        "중이염",         "이비인후과"),
    ("이명",        "메니에르병",     "이비인후과"),
    ("중이염",      "중이염",         "이비인후과"),

    # 치과
    ("잇몸통증",    "치주염",         "치과"),
    ("충치",        "치아우식증",     "치과"),

    # 산부인과
    ("생리불순",    "월경불순",       "산부인과"),
    ("생리통",      "월경통",         "산부인과"),
    ("질염",        "질염",           "산부인과"),

    # 비뇨의학과
    ("소변 시 통증", "방광염",        "비뇨의학과"),
    ("잔뇨감",      "전립선비대증",   "비뇨의학과"),
    ("빈뇨",        "과민성 방광",    "비뇨의학과"),

    # 가슴 두근거림·압박 → 내과
    ("가슴 두근거림", "부정맥",       "내과"),
    ("가슴 압박",   "협심증",         "내과"),
    ("흉통",        "심근경색",       "응급실"),

    # 호흡곤란·기침 지속 → 내과
    ("호흡곤란",    "천식",           "내과"),
    ("기침 지속",   "만성기관지염",   "내과"),
    ("숨가쁨",      "심부전",         "내과"),

    # 갑상선·당뇨·체중변화 → 내과
    ("갑상선",      "갑상선기능이상", "내과"),
    ("당뇨",        "당뇨병",         "내과"),
    ("체중변화",    "대사질환",       "내과"),
    ("고혈압",      "고혈압",         "내과"),
    ("고지혈증",    "이상지질혈증",   "내과"),

    # 소아청소년과
    ("아이 열",     "소아 발열",      "소아청소년과"),
    ("소아 기침",   "소아 호흡기감염", "소아청소년과"),
    ("피부트러블",  "소아 피부질환",  "소아청소년과"),
]

# ── 합병증 관계 ────────────────────────────────────────────────────────────────
COMPLICATION_DATA = [
    ("당뇨병",      "심근경색"),
    ("당뇨병",      "만성신부전"),
    ("고혈압",      "뇌졸중"),
    ("고혈압",      "심근경색"),
    ("편두통",      "뇌졸중"),
    ("천식",        "만성폐쇄성폐질환"),
]

# ── 동반 질환 관계 ─────────────────────────────────────────────────────────────
RELATED_DATA = [
    ("당뇨병",      "고혈압"),
    ("당뇨병",      "이상지질혈증"),
    ("위염",        "역류성식도염"),
    ("편두통",      "긴장성두통"),
    ("아토피 피부염", "천식"),
]


def seed(tx, symptom, disease, department):
    tx.run("""
        MERGE (s:Symptom {name: $symptom})
        MERGE (d:Disease {name: $disease})
        MERGE (dept:Department {name: $department})
        MERGE (s)-[:SUGGESTS]->(d)
        MERGE (d)-[:TREATED_BY]->(dept)
    """, symptom=symptom, disease=disease, department=department)


def seed_complication(tx, disease, complication):
    tx.run("""
        MERGE (d:Disease {name: $disease})
        MERGE (c:Disease {name: $complication})
        MERGE (d)-[:COMPLICATION_OF]->(c)
    """, disease=disease, complication=complication)


def seed_related(tx, disease, related):
    tx.run("""
        MERGE (d:Disease {name: $disease})
        MERGE (r:Disease {name: $related})
        MERGE (d)-[:RELATED_TO]->(r)
    """, disease=disease, related=related)


def run_seed():
    with driver.session() as session:
        print("증상→질환→진료과 데이터 시딩 중...")
        for symptom, disease, department in SEED_DATA:
            session.execute_write(seed, symptom, disease, department)
        print(f"  ✓ {len(SEED_DATA)}개 노드/관계 추가")

        print("합병증 관계 시딩 중...")
        for disease, complication in COMPLICATION_DATA:
            session.execute_write(seed_complication, disease, complication)
        print(f"  ✓ {len(COMPLICATION_DATA)}개 합병증 관계 추가")

        print("동반 질환 관계 시딩 중...")
        for disease, related in RELATED_DATA:
            session.execute_write(seed_related, disease, related)
        print(f"  ✓ {len(RELATED_DATA)}개 동반질환 관계 추가")

        # 결과 확인
        result = session.run("MATCH (s:Symptom) RETURN count(s) AS cnt")
        print(f"\n현재 Neo4j Symptom 노드 수: {result.single()['cnt']}")
        result = session.run("MATCH (d:Disease) RETURN count(d) AS cnt")
        print(f"현재 Neo4j Disease 노드 수: {result.single()['cnt']}")
        result = session.run("MATCH (dept:Department) RETURN count(dept) AS cnt")
        print(f"현재 Neo4j Department 노드 수: {result.single()['cnt']}")

    driver.close()
    print("\n시딩 완료!")


if __name__ == "__main__":
    run_seed()
