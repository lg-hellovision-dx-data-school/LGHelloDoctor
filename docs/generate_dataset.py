# ============================================================
# LG HelloDoctor — 학습 데이터셋 자동 생성 및 분할
# 시니어 실제 발화 특성 반영 버전
# 총 8,800개 (카테고리별 2,200개)
# train 7,040 / validation 880 / test 880 (8:1:1)
# ============================================================

import json
import random
import os
from collections import Counter
from sklearn.model_selection import train_test_split

random.seed(42)

# ============================================================
# 1. 시니어 발화 특성 재료
# ============================================================

# 간투어 / 감탄사 (어르신 발화 특성)
INTERJECTIONS = [
    "", "", "", "", "",          # 없는 경우가 더 많도록 가중치
    "아이고 ", "아이고, ", "어머 ", "어머나 ",
    "있잖아요 ", "저기요 ", "저기 ", "있잖아 ",
    "에이 ", "아 ", "아, ", "그게 ",
    "글쎄요 ", "근데요 ", "있죠 ",
]

# 시간/상황 표현
TIME_CONTEXT = [
    "", "", "", "",              # 없는 경우가 더 많도록 가중치
    "어제부터 ", "며칠 전부터 ", "오늘 아침부터 ",
    "갑자기 ", "아까부터 ", "요즘 계속 ",
    "어젯밤부터 ", "며칠째 ", "아침에 일어나니까 ",
    "밥 먹고 나서 ", "걷다가 ", "자고 일어났더니 ",
]

# 정도 표현
DEGREE = [
    "", "", "",
    "많이 ", "너무 ", "조금 ", "좀 ",
    "심하게 ", "엄청 ", "약간 ",
]

# 구어체 어미
ENDINGS = [
    "요", "요", "요",           # 기본형 가중치
    "는데요", "거든요", "잖아요",
    "는데 어떡하죠", "는데 어떻게 해요",
    "는데 괜찮을까요", "어서 걱정이에요",
    "네요", "는 것 같아요",
]

# ============================================================
# 2. 카테고리별 핵심 표현
# ============================================================

# ── emergency ──
EMERGENCY_CORE = [
    ("숨이 안 쉬어져", "숨이 안 쉬어요"),
    ("쓰러졌어", "쓰러졌어요"),
    ("의식이 없어", "의식이 없어요"),
    ("피를 토했어", "피를 토했어요"),
    ("말이 어눌해졌어", "말이 어눌해졌어요"),
    ("입이 돌아갔어", "입이 돌아갔어요"),
    ("한쪽이 마비됐어", "한쪽이 마비됐어요"),
    ("갑자기 안 보여", "갑자기 안 보여요"),
    ("심장이 멈추는 것 같아", "심장이 멈추는 것 같아요"),
    ("심한 가슴 통증이야", "심한 가슴 통증이에요"),
    ("숨을 쉬기가 너무 힘들어", "숨을 쉬기가 너무 힘들어요"),
    ("온몸에 힘이 없어", "온몸에 힘이 없어요"),
    ("눈앞이 캄캄해", "눈앞이 캄캄해요"),
    ("식은땀이 나고 어지러워", "식은땀이 나고 어지러워요"),
    ("팔다리가 마비됐어", "팔다리가 마비됐어요"),
    ("얼굴이 한쪽만 처졌어", "얼굴이 한쪽만 처졌어요"),
    ("말을 못 하겠어", "말을 못 하겠어요"),
    ("의식을 잃었어", "의식을 잃었어요"),
    ("심장 박동이 너무 빨라", "심장 박동이 너무 빨라요"),
    ("가슴을 쥐어짜는 것 같아", "가슴을 쥐어짜는 것 같아요"),
    ("뼈가 부러진 것 같아", "뼈가 부러진 것 같아요"),
    ("머리를 세게 부딪혔어", "머리를 세게 부딪혔어요"),
    ("약을 너무 많이 먹었어", "약을 너무 많이 먹었어요"),
    ("아이가 경련을 해", "아이가 경련을 해요"),
    ("숨이 막혀", "숨이 막혀요"),
    ("가슴이 너무 아파 죽을 것 같아", "가슴이 너무 아파 죽을 것 같아요"),
    ("혀가 마비된 것 같아", "혀가 마비된 것 같아요"),
    ("몸을 못 움직이겠어", "몸을 못 움직이겠어요"),
    ("머리가 깨질 것 같이 아파", "머리가 깨질 것 같이 아파요"),
    ("눈이 갑자기 안 보여", "눈이 갑자기 안 보여요"),
]

EMERGENCY_DIRECT = [
    "119 불러주세요", "응급차 불러주세요", "빨리 도와주세요",
    "지금 너무 위험해요", "제발 도와주세요", "어떡해요 빨리요",
]

# ── symptom_inquiry ──
BODY_PARTS = [
    "무릎", "허리", "머리", "목", "어깨", "팔", "다리", "손", "발", "배",
    "가슴", "눈", "귀", "코", "입", "목구멍", "손목", "발목", "엉덩이",
    "등", "옆구리", "턱", "이마", "두피", "발바닥", "손가락", "발가락",
    "종아리", "허벅지", "겨드랑이",
]

SYMPTOM_VERBS = [
    "이 아파", "이 너무 아파", "이 욱신거려", "이 저려",
    "이 붓고 있어", "이 가려워", "에 통증이 있어", "이 뻐근해",
    "이 시큰거려", "이 쑤셔", "이 결려", "에 뭔가 이상한 것 같아",
    "이 잘 안 움직여", "에 멍이 들었어", "이 시려", "이 화끈거려",
    "이 무거워", "에 뭔가 걸린 것 같아",
]

GENERAL_SYMPTOMS = [
    ("열이 나", "열이 나요"),
    ("기침이 나", "기침이 나요"),
    ("기침이 심해", "기침이 심해요"),
    ("콧물이 나", "콧물이 나요"),
    ("코가 막혀", "코가 막혀요"),
    ("소화가 안 돼", "소화가 안 돼요"),
    ("구역질이 나", "구역질이 나요"),
    ("속이 울렁거려", "속이 울렁거려요"),
    ("설사를 해", "설사를 해요"),
    ("변비가 심해", "변비가 심해요"),
    ("어지러워", "어지러워요"),
    ("두통이 심해", "두통이 심해요"),
    ("피부에 발진이 났어", "피부에 발진이 났어요"),
    ("두드러기가 났어", "두드러기가 났어요"),
    ("피부가 가려워", "피부가 가려워요"),
    ("눈이 충혈됐어", "눈이 충혈됐어요"),
    ("눈이 침침해", "눈이 침침해요"),
    ("귀에서 소리가 나", "귀에서 소리가 나요"),
    ("잠을 못 자겠어", "잠을 못 자겠어요"),
    ("식욕이 없어", "식욕이 없어요"),
    ("입이 마르고 갈증이 나", "입이 마르고 갈증이 나요"),
    ("소변이 자주 마려워", "소변이 자주 마려워요"),
    ("손이 떨려", "손이 떨려요"),
    ("다리가 부었어", "다리가 부었어요"),
    ("피로감이 심해", "피로감이 심해요"),
    ("숨이 차", "숨이 차요"),
    ("체중이 갑자기 줄었어", "체중이 갑자기 줄었어요"),
    ("코피가 나", "코피가 나요"),
]

# ── hospital_search ──
DEPARTMENTS = [
    "내과", "외과", "정형외과", "신경과", "피부과", "안과", "이비인후과",
    "비뇨기과", "산부인과", "소아과", "치과", "한의원", "재활의학과",
    "심장내과", "정신건강의학과", "내분비내과", "소화기내과", "호흡기내과",
    "신장내과", "류마티스내과",
]

HOSPITAL_PATTERNS = [
    "근처에 {dept} 있어요",
    "근처 {dept} 어디 있어요",
    "가까운 {dept} 찾아줘요",
    "주변에 {dept} 있나요",
    "{dept} 병원 알려줘요",
    "{dept} 가고 싶은데요",
    "{dept} 좀 찾아줘요",
    "여기서 {dept} 어디예요",
    "{dept} 예약하고 싶어요",
    "걸어갈 수 있는 {dept} 있나요",
    "{dept} 어디로 가면 돼요",
]

HOSPITAL_GENERAL = [
    "근처 병원 좀 알려줘요", "가까운 병원 어디 있어요",
    "응급실 어디예요", "지금 열려있는 병원 있나요",
    "오늘 진료하는 병원 있나요", "야간 진료 병원 알려줘요",
    "주말에 여는 병원 있나요", "MRI 찍을 수 있는 병원 어디예요",
    "혈액검사 받을 수 있는 곳 알려줘요", "종합병원 어디 있어요",
    "지금 당장 갈 수 있는 병원 있어요", "도수치료 받는 곳 있나요",
    "내일 아침 진료 병원 있나요", "어르신 진료 잘 봐주는 병원 알려줘요",
]

# ── medication_info ──
MEDICATIONS = [
    "타이레놀", "부루펜", "아스피린", "게보린", "판피린",
    "지르텍", "클라리틴", "베아제", "훼스탈", "가스활명수", "겔포스",
    "아로나민", "임팩타민", "오메가3", "비타민D",
    "혈압약", "당뇨약", "고지혈증약", "수면제", "항생제",
    "소화제", "진통제", "해열제", "감기약", "기침약", "연고",
]

MED_PATTERNS = [
    "이거 어떻게 먹는 건가요",
    "하루에 몇 번 먹어요",
    "언제 먹어야 해요",
    "밥 먹고 먹어야 해요",
    "공복에 먹어도 돼요",
    "얼마나 먹어야 해요",
    "다른 약이랑 같이 먹어도 돼요",
    "오래 먹어도 괜찮아요",
    "노인이 먹어도 돼요",
    "한 번에 두 알 먹어도 돼요",
]

MED_GENERAL = [
    "약 먹고 술 마셔도 돼요", "두 가지 약 같이 먹어도 돼요",
    "약 빠뜨리면 어떡해요", "약 냉장 보관해야 해요",
    "유통기한 지난 약 먹어도 돼요", "진통제 자주 먹으면 안 좋아요",
    "항생제 다 먹어야 해요", "약 먹고 졸음이 오는데요",
    "영양제 아무 때나 먹어도 돼요", "처방약 다 먹었는데 증상이 계속돼요",
    "약 갈아서 먹어도 괜찮아요", "약 반으로 잘라 먹어도 돼요",
]


# ============================================================
# 3. 발화 생성 함수 (시니어 특성 반영)
# ============================================================

def make_senior_utterance(core: str, add_time: bool = True) -> str:
    """간투어 + 시간표현 + 정도표현 조합"""
    interjection = random.choice(INTERJECTIONS)
    time_ctx = random.choice(TIME_CONTEXT) if add_time else ""
    degree = random.choice(DEGREE)
    return f"{interjection}{time_ctx}{degree}{core}".strip()


def generate_emergency(n: int) -> list:
    data = []
    while len(data) < n:
        if random.random() < 0.15:
            # 직접 구조 요청형
            text = random.choice(EMERGENCY_DIRECT)
        else:
            formal, informal = random.choice(EMERGENCY_CORE)
            core = random.choice([formal, informal])
            # 응급은 시간표현 없이 (즉각성 강조)
            interjection = random.choice(INTERJECTIONS)
            text = f"{interjection}{core}".strip()
        data.append({
            "instruction": "사용자 발화의 의도를 분류하세요.",
            "input": text,
            "output": '{"intent": "emergency"}'
        })
    return data[:n]


def generate_symptom_inquiry(n: int) -> list:
    data = []

    # 신체부위 + 증상 조합
    for part in BODY_PARTS:
        for verb in SYMPTOM_VERBS:
            core = f"{part}{verb}"
            text = make_senior_utterance(core)
            # 구어체 어미 추가 (50% 확률)
            if random.random() > 0.5:
                ending = random.choice(ENDINGS)
                if not text.endswith("요"):
                    text = f"{text}{ending}"
            data.append({
                "instruction": "사용자 발화의 의도를 분류하세요.",
                "input": text,
                "output": '{"intent": "symptom_inquiry"}'
            })

    # 일반 증상
    for formal, informal in GENERAL_SYMPTOMS:
        core = random.choice([formal, informal])
        text = make_senior_utterance(core)
        data.append({
            "instruction": "사용자 발화의 의도를 분류하세요.",
            "input": text,
            "output": '{"intent": "symptom_inquiry"}'
        })

    # 부족분 채우기
    while len(data) < n:
        part = random.choice(BODY_PARTS)
        verb = random.choice(SYMPTOM_VERBS)
        core = f"{part}{verb}"
        text = make_senior_utterance(core)
        data.append({
            "instruction": "사용자 발화의 의도를 분류하세요.",
            "input": text,
            "output": '{"intent": "symptom_inquiry"}'
        })

    random.shuffle(data)
    return data[:n]


def generate_hospital_search(n: int) -> list:
    data = []

    # 진료과 + 패턴 조합
    for dept in DEPARTMENTS:
        for pattern in HOSPITAL_PATTERNS:
            core = pattern.format(dept=dept)
            interjection = random.choice(INTERJECTIONS)
            text = f"{interjection}{core}".strip()
            data.append({
                "instruction": "사용자 발화의 의도를 분류하세요.",
                "input": text,
                "output": '{"intent": "hospital_search"}'
            })

    # 일반 병원 검색
    for core in HOSPITAL_GENERAL:
        interjection = random.choice(INTERJECTIONS)
        text = f"{interjection}{core}".strip()
        data.append({
            "instruction": "사용자 발화의 의도를 분류하세요.",
            "input": text,
            "output": '{"intent": "hospital_search"}'
        })

    # 부족분 채우기
    while len(data) < n:
        dept = random.choice(DEPARTMENTS)
        pattern = random.choice(HOSPITAL_PATTERNS)
        core = pattern.format(dept=dept)
        interjection = random.choice(INTERJECTIONS)
        text = f"{interjection}{core}".strip()
        data.append({
            "instruction": "사용자 발화의 의도를 분류하세요.",
            "input": text,
            "output": '{"intent": "hospital_search"}'
        })

    random.shuffle(data)
    return data[:n]


def generate_medication_info(n: int) -> list:
    data = []

    # 약 이름 + 질문 패턴 조합
    for med in MEDICATIONS:
        for pattern in MED_PATTERNS:
            core = f"{med} {pattern}"
            interjection = random.choice(INTERJECTIONS)
            text = f"{interjection}{core}".strip()
            data.append({
                "instruction": "사용자 발화의 의도를 분류하세요.",
                "input": text,
                "output": '{"intent": "medication_info"}'
            })

    # 일반 복약 질문
    for core in MED_GENERAL:
        interjection = random.choice(INTERJECTIONS)
        text = f"{interjection}{core}".strip()
        data.append({
            "instruction": "사용자 발화의 의도를 분류하세요.",
            "input": text,
            "output": '{"intent": "medication_info"}'
        })

    # 부족분 채우기
    while len(data) < n:
        med = random.choice(MEDICATIONS)
        pattern = random.choice(MED_PATTERNS)
        core = f"{med} {pattern}"
        interjection = random.choice(INTERJECTIONS)
        text = f"{interjection}{core}".strip()
        data.append({
            "instruction": "사용자 발화의 의도를 분류하세요.",
            "input": text,
            "output": '{"intent": "medication_info"}'
        })

    random.shuffle(data)
    return data[:n]


# ============================================================
# 4. 전체 데이터 생성 (8,800개)
# ============================================================

PER_CLASS = 2200
TOTAL = PER_CLASS * 4

print("데이터 생성 중...")
all_data = (
    generate_emergency(PER_CLASS) +
    generate_symptom_inquiry(PER_CLASS) +
    generate_hospital_search(PER_CLASS) +
    generate_medication_info(PER_CLASS)
)
random.shuffle(all_data)
print(f"총 {len(all_data)}개 생성 완료")

label_counter = Counter(
    json.loads(d["output"])["intent"] for d in all_data
)
print("카테고리 분포:", dict(label_counter))

# 샘플 확인
print("\n[생성 샘플 확인]")
samples = random.sample(all_data, 12)
for item in samples:
    label = json.loads(item["output"])["intent"]
    print(f"  [{label:20s}] {item['input']}")


# ============================================================
# 5. Train / Validation / Test 분할 (8:1:1)
# ============================================================

labels = [json.loads(d["output"])["intent"] for d in all_data]

train_data, temp_data, _, temp_labels = train_test_split(
    all_data, labels,
    test_size=0.2,
    random_state=42,
    stratify=labels,
)

val_data, test_data = train_test_split(
    temp_data,
    test_size=0.5,
    random_state=42,
    stratify=temp_labels,
)

print(f"\n분할 결과")
print(f"  Train:      {len(train_data):,}개  ({len(train_data)/TOTAL*100:.0f}%)")
print(f"  Validation: {len(val_data):,}개  ({len(val_data)/TOTAL*100:.0f}%)")
print(f"  Test:       {len(test_data):,}개  ({len(test_data)/TOTAL*100:.0f}%)")
print(f"  합계:       {len(train_data)+len(val_data)+len(test_data):,}개")


# ============================================================
# 6. JSON 파일 저장
# ============================================================

OUTPUT_DIR = "./dataset"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(f"{OUTPUT_DIR}/train.json", "w", encoding="utf-8") as f:
    json.dump(train_data, f, ensure_ascii=False, indent=2)

with open(f"{OUTPUT_DIR}/validation.json", "w", encoding="utf-8") as f:
    json.dump(val_data, f, ensure_ascii=False, indent=2)

with open(f"{OUTPUT_DIR}/test.json", "w", encoding="utf-8") as f:
    json.dump(test_data, f, ensure_ascii=False, indent=2)

print(f"\nJSON 저장 완료")
print(f"  {OUTPUT_DIR}/train.json      → {len(train_data):,}개")
print(f"  {OUTPUT_DIR}/validation.json → {len(val_data):,}개")
print(f"  {OUTPUT_DIR}/test.json       → {len(test_data):,}개")
