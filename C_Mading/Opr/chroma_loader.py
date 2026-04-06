from Opr.chroma_client import get_medical_collection
import itertools
import random


dept_symptom_map = [
    ("이비인후과", ["귀", "삐 소리", "이명", "코피", "목소리", "인후통", "목에 걸린", "목에 뭔가 걸린", "콧물", "코막힘", "후각", "미각", "목이 아파서 잘 못 먹", "목이 아파서 잘 못 자"]),
    ("정형외과", ["무릎", "허리", "어깨", "손목", "발목", "관절", "디스크", "삐끗", "팔을 못 들", "못 걷", "뼈", "근육", "인대", "척추", "골절", "염좌", "좌골신경통", "오십견", "골다공증", "관절염"]),
    ("피부과", ["두드러기", "피부", "가렵", "빨개", "발진", "염증", "화농", "뾰루지", "여드름", "습진", "건조", "각질", "탈모", "지루성", "아토피", "알레르기", "접촉성", "두피", "사마귀", "티눈", "무좀", "버짐", "옴", "한포진"]),
    ("치과", ["치아", "이가", "잇몸", "사랑니", "턱", "입이 잘 안 벌어", "치통", "입 냄새", "충치", "치석", "치주염", "치근염", "치수염", "치은염", "치조농루", "치조낭종", "치아 파절", "치아 골절", "치아 균열"]),
    ("안과", ["눈", "시야", "캄캄", "충혈", "눈물", "눈이 아파서 잘 못 자", "눈이 아파서 잘 못 먹", "안구건조", "눈부심", "눈꺼풀", "눈 밑이 검어"]),
    ("산부인과", ["생리", "질", "자궁", "임신", "하혈", "유산", "피임", "월경", "갱년기", "유방", "생리통", "생리불순", "분만", "산후", "부인과", "여성호르몬"]),
    ("정신건강의학과", ["불안", "우울", "불면", "공황", "스트레스", "자살", "사회생활", "대인관계", "화병", "분노", "집중력", "기억력", "자해", "환청", "망상"]),
    ("내과", ["위", "속쓰림", "신물", "복통", "설사", "혈압", "갑상선", "당뇨", "열", "몸살", "기침", "가슴 답답", "소화", "배가 아파", "체중", "콜레스테롤", "간 기능", "심장", "호흡기", "신장", "비뇨기", "감염"]),
]


SEED_RANDOM = 42
MAX_DOCS_PER_DEPT = 80  # 과당 최대 생성 개수


TEMPLATES = [
    "{kw1} 증상은 {dept} 진료와 관련될 수 있습니다.",
    "{kw1} 증상이 있으면 {dept} 진료를 고려할 수 있습니다.",
    "{kw1} 때문에 병원을 찾는다면 {dept}를 먼저 생각할 수 있습니다.",
    "{kw1} 관련 증상은 보통 {dept}에서 상담할 수 있습니다.",
    "{kw1} 같은 증상이 계속되면 {dept} 진료가 도움이 될 수 있습니다.",
    "{kw1}이면 어느 과를 가야 하나요? 보통 {dept}를 고려할 수 있습니다.",
    "{kw1}이(가) 심하면 {dept} 진료가 필요할 수 있습니다.",
    "{kw1} 때문에 불편하면 {dept} 상담을 받아볼 수 있습니다.",

    "{kw1}, {kw2} 증상은 {dept}와 관련될 가능성이 있습니다.",
    "{kw1}하고 {kw2}가 같이 있으면 {dept} 진료를 고려할 수 있습니다.",
    "{kw1}, {kw2} 같은 증상은 {dept}에서 볼 수 있습니다.",
    "{kw1}와 {kw2}가 계속되면 {dept} 상담이 도움이 될 수 있습니다.",
    "{kw1}도 있고 {kw2}도 있으면 {dept} 쪽 진료를 생각할 수 있습니다.",
    "{kw1}, {kw2} 때문에 불편하면 {dept}를 먼저 가볼 수 있습니다.",

    "{kw1}, {kw2}, {kw3} 증상 조합은 {dept} 진료 대상일 수 있습니다.",
    "{kw1}하면서 {kw2}도 있고 {kw3}까지 있으면 {dept}를 고려할 수 있습니다.",
    "{kw1}, {kw2}, {kw3} 같은 증상이 함께 있으면 {dept} 상담이 필요할 수 있습니다.",

    "요즘 {kw1} 때문에 불편한데 어느 과를 가야 하나요? {dept}를 고려할 수 있습니다.",
    "갑자기 {kw1} 증상이 생겼다면 {dept} 상담이 도움이 될 수 있습니다.",
    "며칠 전부터 {kw1}이(가) 계속되면 {dept} 진료를 생각할 수 있습니다.",
    "{kw1} 때문에 잘 못 먹거나 잘 못 자면 {dept} 진료가 필요할 수 있습니다.",

    "아이고 {kw1}이(가) 너무 불편한데 {dept}를 가야 할 수 있습니다.",
    "혹시 {kw1}이면 {dept}에 가보는 게 좋을 수 있습니다.",
    "계속 {kw1}이(가) 있으면 {dept} 진료를 받아볼 수 있습니다.",
]


def _dedupe_keep_order(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _safe_format(template: str, dept: str, combo: tuple[str, ...]) -> str:
    values = {
        "dept": dept,
        "kw1": combo[0] if len(combo) > 0 else "",
        "kw2": combo[1] if len(combo) > 1 else combo[0] if len(combo) > 0 else "",
        "kw3": combo[2] if len(combo) > 2 else combo[-1] if combo else "",
    }
    return template.format(**values)


def _make_keyword_combos(keywords: list[str], max_pairs=24, max_triples=18, rng=None):
    if rng is None:
        rng = random.Random(SEED_RANDOM)

    keywords = _dedupe_keep_order(keywords)

    singles = [(k,) for k in keywords]

    pair_candidates = list(itertools.combinations(keywords, 2))
    triple_candidates = list(itertools.combinations(keywords, 3))

    rng.shuffle(pair_candidates)
    rng.shuffle(triple_candidates)

    pairs = pair_candidates[:max_pairs]
    triples = triple_candidates[:max_triples]

    return singles + pairs + triples


def build_seed_docs_from_map():
    """
    dept_symptom_map 기반 seed 자동 생성
    - 1/2/3개 키워드 조합
    - 다양한 템플릿
    - 과당 최대 문서 수 제한
    """
    rng = random.Random(SEED_RANDOM)
    docs = []

    for dept, keywords in dept_symptom_map:
        combos = _make_keyword_combos(
            keywords,
            max_pairs=min(24, max(8, len(keywords))),
            max_triples=min(18, max(6, len(keywords) // 2)),
            rng=rng,
        )

        dept_docs = []

        for combo in combos:
            for template in TEMPLATES:
                need_kw2 = "{kw2}" in template
                need_kw3 = "{kw3}" in template

                if need_kw3 and len(combo) < 3:
                    continue
                if need_kw2 and len(combo) < 2:
                    continue

                text = _safe_format(template, dept, combo)

                dept_docs.append({
                    "document": text,
                    "metadata": {
                        "department": dept,
                        "category": "symptom",
                        "source": "auto_generated_v2",
                        "keywords": ", ".join(combo),
                        "keyword_count": len(combo),
                    },
                })

        rng.shuffle(dept_docs)

        unique_docs = []
        seen_texts = set()
        for d in dept_docs:
            text = d["document"]
            if text in seen_texts:
                continue
            seen_texts.add(text)
            unique_docs.append(d)
            if len(unique_docs) >= MAX_DOCS_PER_DEPT:
                break

        for idx, d in enumerate(unique_docs, start=1):
            docs.append({
                "id": f"auto2_{dept}_{idx}",
                "document": d["document"],
                "metadata": d["metadata"],
            })

    return docs


def seed_chroma():
    collection = get_medical_collection()
    seed_docs = build_seed_docs_from_map()

    existing = collection.get(include=[])
    existing_ids = set(existing["ids"]) if existing and existing.get("ids") else set()

    new_docs = [doc for doc in seed_docs if doc["id"] not in existing_ids]

    if not new_docs:
        print("추가할 문서 없음")
        return

    collection.add(
        ids=[doc["id"] for doc in new_docs],
        documents=[doc["document"] for doc in new_docs],
        metadatas=[doc["metadata"] for doc in new_docs],
    )

    print(f"{len(new_docs)}건 추가 완료")


if __name__ == "__main__":
    seed_chroma()