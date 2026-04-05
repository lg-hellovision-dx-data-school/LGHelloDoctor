from Opr.chroma_client import get_medical_collection


SEED_DOCS = [
    {
        "id": "dept_ent_001",
        "document": "귀에서 삐 소리가 나거나 코피가 자주 나고 목소리가 쉬면 이비인후과 진료가 필요할 수 있습니다.",
        "metadata": {"department": "이비인후과", "category": "symptom"},
    },
    {
        "id": "dept_ortho_001",
        "document": "무릎 통증, 허리 통증, 어깨 통증, 손목 저림, 발목 통증, 관절 통증, 디스크 증상은 정형외과 관련일 수 있습니다.",
        "metadata": {"department": "정형외과", "category": "symptom"},
    },
    {
        "id": "dept_derm_001",
        "document": "두드러기, 피부 발진, 가려움, 피부가 빨개짐, 습진, 아토피, 여드름은 피부과 관련 증상일 수 있습니다.",
        "metadata": {"department": "피부과", "category": "symptom"},
    },
    {
        "id": "dept_dent_001",
        "document": "치아 통증, 잇몸 출혈, 사랑니 통증, 치아 흔들림, 턱 통증은 치과 진료가 필요할 수 있습니다.",
        "metadata": {"department": "치과", "category": "symptom"},
    },
    {
        "id": "dept_im_001",
        "document": "속쓰림, 신물, 복통, 설사, 혈압 상승, 갑상선 이상, 당뇨 관련 증상은 내과와 관련될 수 있습니다.",
        "metadata": {"department": "내과", "category": "symptom"},
    },
    {
        "id": "dept_obgyn_001",
        "document": "생리통, 생리불순, 임신, 하혈, 자궁 관련 증상은 산부인과 진료가 필요할 수 있습니다.",
        "metadata": {"department": "산부인과", "category": "symptom"},
    },
    {
        "id": "dept_psych_001",
        "document": "불안, 우울, 불면, 공황, 스트레스, 환청, 망상은 정신건강의학과 상담 대상일 수 있습니다.",
        "metadata": {"department": "정신건강의학과", "category": "symptom"},
    },
]


def seed_chroma():
    collection = get_medical_collection()

    existing = collection.get(include=[])
    existing_ids = set(existing["ids"]) if existing and existing.get("ids") else set()

    new_docs = [doc for doc in SEED_DOCS if doc["id"] not in existing_ids]

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