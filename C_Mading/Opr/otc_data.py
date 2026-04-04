COMMON_OTC_DISCLAIMER = (
    "아래 내용은 건강한 일반 성인을 기준으로 한 일반적 복용 예시입니다. "
    "제품별 성분과 함량이 다를 수 있으니 포장지의 용법·용량을 먼저 확인하고, "
    "자세한 사항은 약국 또는 의사·약사와 상담 후 복용하세요."
)

SPECIAL_CONSULT_GROUPS = [
    "임산부",
    "수유부",
    "고령자",
    "간 질환자",
    "신장 질환자",
    "위장 질환자",
    "만성질환 약 복용자",
    "복용약이 많은 사용자",
]

OTC_RED_FLAG_KEYWORDS = [
    "고열 지속",
    "호흡곤란",
    "흉통",
    "혈변",
    "검은 변",
    "반복 구토",
    "심한 복통",
    "의식저하",
]

OTC_KNOWLEDGE = {
    "tylenol": {
        "aliases": ["타이레놀", "아세트아미노펜", "acetaminophen", "paracetamol", "tylenol"],
        "category": "해열진통제",
        "effect": "열과 두통, 몸살, 치통 같은 통증 완화에 쓰입니다.",
        "dosage": "일반 성인 기준으로는 보통 500mg 1~2정을 최소 4시간 간격으로 복용합니다.",
        "caution": "다른 감기약과 성분이 겹칠 수 있어 중복 복용에 주의하세요.",
        "recommendation": "고열이 오래가거나 통증이 심하면 약국 또는 의료진 상담이 필요할 수 있습니다.",
        "consult_priority_conditions": [
            "간 질환",
            "음주가 잦음",
            "복용 중인 감기약 있음",
        ],
        "show_numeric_dosage": True,
    },
    "ibuprofen": {
        "aliases": ["이부프로펜", "덱시부프로펜", "부루펜", "애드빌", "advil", "ibuprofen"],
        "category": "소염진통제",
        "effect": "두통, 근육통, 생리통처럼 염증이나 통증이 있을 때 자주 쓰입니다.",
        "dosage": "일반 성인 기준으로는 보통 정해진 용량을 4시간 이상 간격으로 복용하며 식후 복용이 권장될 수 있습니다.",
        "caution": "위가 약하거나 신장 질환이 있거나 다른 약을 복용 중이라면 주의가 필요합니다.",
        "recommendation": "속쓰림이 심하거나 검은 변, 심한 복통이 있으면 복용을 멈추고 상담이 필요합니다.",
        "consult_priority_conditions": [
            "위염",
            "위궤양",
            "신장 질환",
            "혈액희석제 복용",
        ],
        "show_numeric_dosage": False,
    },
    "cold_medicine": {
        "aliases": ["종합감기약", "감기약", "판콜", "콜대원", "테라플루"],
        "category": "종합감기약",
        "effect": "콧물, 기침, 목아픔, 몸살처럼 여러 감기 증상이 함께 있을 때 사용할 수 있습니다.",
        "dosage": "제품마다 성분과 함량이 달라 포장지의 용법·용량을 먼저 확인하세요.",
        "caution": "졸릴 수 있고 해열진통제 성분이 포함된 경우 다른 감기약이나 타이레놀과 중복될 수 있습니다.",
        "recommendation": "숨이 차거나 고열이 오래가거나 증상이 빠르게 심해지면 진료가 필요할 수 있습니다.",
        "consult_priority_conditions": [
            "복용 중인 감기약 있음",
            "졸림 우려 상황",
            "기저질환 있음",
        ],
        "show_numeric_dosage": False,
    },
    "digestive": {
        "aliases": ["소화제", "제산제", "속쓰림약", "겔포스", "개비스콘", "베아제", "훼스탈"],
        "category": "소화제·제산제",
        "effect": "더부룩함, 과식 후 불편감, 가벼운 속쓰림이 있을 때 도움될 수 있습니다.",
        "dosage": "제품마다 복용 횟수와 시점이 달라 포장지 안내를 먼저 확인하는 것이 좋습니다.",
        "caution": "다른 약과 함께 먹을 때는 복용 간격이 필요할 수 있습니다.",
        "recommendation": "증상이 자주 반복되거나 심한 복통, 반복 구토, 검은 변이 있다면 진료가 필요할 수 있습니다.",
        "consult_priority_conditions": [
            "증상 반복",
            "복용약 다수",
            "위장 질환",
        ],
        "show_numeric_dosage": False,
    },
    "antidiarrheal": {
        "aliases": ["지사제", "설사약", "로페라마이드", "스멕타"],
        "category": "지사제",
        "effect": "갑작스러운 설사나 단순 배탈 증상을 줄이는 데 쓰일 수 있습니다.",
        "dosage": "제품에 따라 복용 방법이 다르므로 포장지의 용법·용량을 먼저 확인하세요.",
        "caution": "복용 중에는 탈수를 막기 위해 물을 충분히 마시는 것이 중요합니다.",
        "recommendation": "열이 나거나 피가 섞인 설사, 심한 복통, 증상이 오래 지속되는 경우에는 병원이나 약국 상담을 우선하세요.",
        "consult_priority_conditions": [
            "혈변",
            "고열",
            "탈수 우려",
        ],
        "show_numeric_dosage": False,
    },
}