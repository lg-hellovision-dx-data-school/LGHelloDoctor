"""
다중턴 시나리오 50개 생성 스크립트.
- 5개 패턴 × 10개 = 50 시나리오
- 패턴: 격상 / 약상담 / 병원검색 / 주제전환 / 잡담섞임
- 총 200턴 (시나리오당 평균 4턴)
- source: synthetic_multiturn_v1
"""
import json
import random
from collections import Counter
from pathlib import Path

random.seed(42)

OUTPUT_PATH = Path(__file__).parent / "medical_intent_multiturn.json"


def turn(text, label):
    return {"text": text, "label": label}


scenarios = [
    # ─────────────────────────────────────────────────────────
    # Pattern 1: 격상 (general/symptom → emergency)  10개
    # ─────────────────────────────────────────────────────────
    {
        "id": "MT-0001",
        "scenario_type": "격상",
        "turns": [
            turn("안녕하세요", "general_chat"),
            turn("머리가 좀 어지러워요", "symptom_inquiry"),
            turn("갑자기 한쪽 팔에 힘이 빠져요", "emergency"),
            turn("119 불러야 하나요", "emergency"),
        ],
    },
    {
        "id": "MT-0002",
        "scenario_type": "격상",
        "turns": [
            turn("안녕", "general_chat"),
            turn("가슴이 좀 답답해요", "symptom_inquiry"),
            turn("점점 심해져서 식은땀이 나요", "emergency"),
            turn("빨리 도와주세요", "emergency"),
        ],
    },
    {
        "id": "MT-0003",
        "scenario_type": "격상",
        "turns": [
            turn("도와주세요", "general_chat"),
            turn("손주가 열이 38도예요", "symptom_inquiry"),
            turn("갑자기 경련을 시작했어요", "emergency"),
            turn("119 좀 불러주세요", "emergency"),
        ],
    },
    {
        "id": "MT-0004",
        "scenario_type": "격상",
        "turns": [
            turn("잘 들리나요", "general_chat"),
            turn("영감이 어지럽다고 해요", "symptom_inquiry"),
            turn("갑자기 쓰러졌어요", "emergency"),
            turn("의식이 없어요 어떡하죠", "emergency"),
        ],
    },
    {
        "id": "MT-0005",
        "scenario_type": "격상",
        "turns": [
            turn("안녕하세요", "general_chat"),
            turn("어제부터 두통이 있어요", "symptom_inquiry"),
            turn("갑자기 한쪽 눈이 안 보여요", "emergency"),
        ],
    },
    {
        "id": "MT-0006",
        "scenario_type": "격상",
        "turns": [
            turn("처음 써봐요", "general_chat"),
            turn("배가 좀 아파요", "symptom_inquiry"),
            turn("토했는데 피가 섞여 있어요", "emergency"),
        ],
    },
    {
        "id": "MT-0007",
        "scenario_type": "격상",
        "turns": [
            turn("안녕", "general_chat"),
            turn("알레르기 약 먹었어요", "medication_inquiry"),
            turn("갑자기 목이 부어요", "emergency"),
            turn("숨을 못 쉬겠어요", "emergency"),
        ],
    },
    {
        "id": "MT-0008",
        "scenario_type": "격상",
        "turns": [
            turn("도와줘", "general_chat"),
            turn("영감이 변이 까매요", "symptom_inquiry"),
            turn("의식이 흐려지고 있어요", "emergency"),
        ],
    },
    {
        "id": "MT-0009",
        "scenario_type": "격상",
        "turns": [
            turn("어떻게 써요", "general_chat"),
            turn("가슴이 좀 답답한데", "symptom_inquiry"),
            turn("점점 더 아파서 식은땀이 나요", "emergency"),
        ],
    },
    {
        "id": "MT-0010",
        "scenario_type": "격상",
        "turns": [
            turn("안녕하세요", "general_chat"),
            turn("손이 좀 저려요", "symptom_inquiry"),
            turn("갑자기 말을 못 하겠어요", "emergency"),
        ],
    },

    # ─────────────────────────────────────────────────────────
    # Pattern 2: 약 상담 (symptom → medication → followup)  10개
    # ─────────────────────────────────────────────────────────
    {
        "id": "MT-0011",
        "scenario_type": "약상담",
        "turns": [
            turn("감기 기운이 있어요", "symptom_inquiry"),
            turn("감기약 먹어도 되나요", "medication_inquiry"),
            turn("혈압약이랑 같이 먹어도 돼요", "medication_inquiry"),
            turn("고마워요", "general_chat"),
        ],
    },
    {
        "id": "MT-0012",
        "scenario_type": "약상담",
        "turns": [
            turn("머리가 아파요", "symptom_inquiry"),
            turn("타이레놀 먹어도 돼요", "medication_inquiry"),
            turn("하루에 몇 번 먹어요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0013",
        "scenario_type": "약상담",
        "turns": [
            turn("무릎이 욱신거려요", "symptom_inquiry"),
            turn("진통제 먹어도 돼요", "medication_inquiry"),
            turn("부작용이 뭐가 있나요", "medication_inquiry"),
            turn("알겠습니다", "general_chat"),
        ],
    },
    {
        "id": "MT-0014",
        "scenario_type": "약상담",
        "turns": [
            turn("감기 걸렸어요", "symptom_inquiry"),
            turn("감기약 추천해주세요", "medication_inquiry"),
            turn("식전 식후 언제 먹어요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0015",
        "scenario_type": "약상담",
        "turns": [
            turn("자꾸 어지러워요", "symptom_inquiry"),
            turn("혈압약을 빼먹었어요", "medication_inquiry"),
            turn("한 번에 두 알 먹어도 돼요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0016",
        "scenario_type": "약상담",
        "turns": [
            turn("영감이 머리가 아파요", "symptom_inquiry"),
            turn("진통제 두 알 먹여도 돼요", "medication_inquiry"),
            turn("위가 약한데 괜찮아요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0017",
        "scenario_type": "약상담",
        "turns": [
            turn("알레르기인 것 같아요", "symptom_inquiry"),
            turn("알레르기약 먹어도 돼요", "medication_inquiry"),
            turn("졸음이 와도 운전해도 돼요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0018",
        "scenario_type": "약상담",
        "turns": [
            turn("위가 쓰려요", "symptom_inquiry"),
            turn("위장약 먹어도 돼요", "medication_inquiry"),
            turn("식전에 먹는 게 맞나요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0019",
        "scenario_type": "약상담",
        "turns": [
            turn("손주가 열이 나요", "symptom_inquiry"),
            turn("어린이 해열제 먹여도 돼요", "medication_inquiry"),
            turn("용량은 어떻게 되나요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0020",
        "scenario_type": "약상담",
        "turns": [
            turn("항생제 처방받았어요", "medication_inquiry"),
            turn("다 먹어야 하나요", "medication_inquiry"),
            turn("부작용이 있는데 계속 먹어요", "medication_inquiry"),
        ],
    },

    # ─────────────────────────────────────────────────────────
    # Pattern 3: 병원 검색 (symptom → hospital → details)  10개
    # ─────────────────────────────────────────────────────────
    {
        "id": "MT-0021",
        "scenario_type": "병원검색",
        "turns": [
            turn("허리가 너무 아파요", "symptom_inquiry"),
            turn("근처 정형외과 알려주세요", "hospital_search"),
            turn("지금 문 연 곳 있나요", "hospital_search"),
            turn("감사합니다", "general_chat"),
        ],
    },
    {
        "id": "MT-0022",
        "scenario_type": "병원검색",
        "turns": [
            turn("무릎이 시려요", "symptom_inquiry"),
            turn("가까운 정형외과 좀요", "hospital_search"),
            turn("예약 가능한 곳으로요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0023",
        "scenario_type": "병원검색",
        "turns": [
            turn("안녕하세요", "general_chat"),
            turn("손주가 열이 나요", "symptom_inquiry"),
            turn("가까운 소아과 알려주세요", "hospital_search"),
            turn("야간 진료도 되나요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0024",
        "scenario_type": "병원검색",
        "turns": [
            turn("눈이 침침해요", "symptom_inquiry"),
            turn("안과 어디 있어요", "hospital_search"),
            turn("가까운 곳으로요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0025",
        "scenario_type": "병원검색",
        "turns": [
            turn("귀가 잘 안 들려요", "symptom_inquiry"),
            turn("이비인후과 알려주세요", "hospital_search"),
            turn("지금 영업 중인 곳요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0026",
        "scenario_type": "병원검색",
        "turns": [
            turn("영감이 다쳤어요", "symptom_inquiry"),
            turn("외과 가까운 곳 알려줘요", "hospital_search"),
            turn("응급실도 갈 수 있나요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0027",
        "scenario_type": "병원검색",
        "turns": [
            turn("어지러워요", "symptom_inquiry"),
            turn("신경과 어디 있어요", "hospital_search"),
            turn("종합병원도 좋아요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0028",
        "scenario_type": "병원검색",
        "turns": [
            turn("안녕", "general_chat"),
            turn("노친네가 호흡이 가빠요", "symptom_inquiry"),
            turn("응급실 가까운 곳", "hospital_search"),
            turn("24시간 운영하는 곳요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0029",
        "scenario_type": "병원검색",
        "turns": [
            turn("변비가 심해요", "symptom_inquiry"),
            turn("내과 추천해주세요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0030",
        "scenario_type": "병원검색",
        "turns": [
            turn("가슴이 답답해요", "symptom_inquiry"),
            turn("심장내과 어디 있어요", "hospital_search"),
            turn("큰 병원으로요", "hospital_search"),
        ],
    },

    # ─────────────────────────────────────────────────────────
    # Pattern 4: 주제전환 (혼합)  10개
    # ─────────────────────────────────────────────────────────
    {
        "id": "MT-0031",
        "scenario_type": "주제전환",
        "turns": [
            turn("어제부터 두통이 있어요", "symptom_inquiry"),
            turn("타이레놀 먹어도 돼요", "medication_inquiry"),
            turn("그런데 속도 안 좋아요", "symptom_inquiry"),
            turn("병원 어디 가야 해요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0032",
        "scenario_type": "주제전환",
        "turns": [
            turn("무릎이 아파요", "symptom_inquiry"),
            turn("근처 정형외과 알려주세요", "hospital_search"),
            turn("진통제 먹어도 돼요", "medication_inquiry"),
            turn("가서 처방받을게요", "general_chat"),
        ],
    },
    {
        "id": "MT-0033",
        "scenario_type": "주제전환",
        "turns": [
            turn("영감이 어지러워요", "symptom_inquiry"),
            turn("혈압약 빼먹었어요", "medication_inquiry"),
            turn("한 번에 두 알 먹여도 돼요", "medication_inquiry"),
            turn("병원도 가야 하나요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0034",
        "scenario_type": "주제전환",
        "turns": [
            turn("감기 같아요", "symptom_inquiry"),
            turn("약국 어디 있어요", "hospital_search"),
            turn("감기약 추천해주세요", "medication_inquiry"),
            turn("잘 알겠습니다", "general_chat"),
        ],
    },
    {
        "id": "MT-0035",
        "scenario_type": "주제전환",
        "turns": [
            turn("손주가 토해요", "symptom_inquiry"),
            turn("소아과 알려주세요", "hospital_search"),
            turn("그 사이 약 먹여도 돼요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0036",
        "scenario_type": "주제전환",
        "turns": [
            turn("가슴이 답답해요", "symptom_inquiry"),
            turn("심장내과 알려주세요", "hospital_search"),
            turn("진통제 먹어도 돼요", "medication_inquiry"),
            turn("갑자기 식은땀이 나요", "emergency"),
        ],
    },
    {
        "id": "MT-0037",
        "scenario_type": "주제전환",
        "turns": [
            turn("안녕하세요", "general_chat"),
            turn("알레르기인 것 같아요", "symptom_inquiry"),
            turn("알레르기약 먹어도 돼요", "medication_inquiry"),
            turn("가까운 피부과 알려주세요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0038",
        "scenario_type": "주제전환",
        "turns": [
            turn("도와주세요", "general_chat"),
            turn("영감이 화상을 입었어요", "emergency"),
            turn("응급실 가까운 곳요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0039",
        "scenario_type": "주제전환",
        "turns": [
            turn("처음이에요", "general_chat"),
            turn("무릎이 결려요", "symptom_inquiry"),
            turn("진통제랑 같이 먹는 약요", "medication_inquiry"),
            turn("병원도 가야겠죠", "hospital_search"),
        ],
    },
    {
        "id": "MT-0040",
        "scenario_type": "주제전환",
        "turns": [
            turn("안녕", "general_chat"),
            turn("자꾸 머리가 띵해요", "symptom_inquiry"),
            turn("두통약 먹어도 돼요", "medication_inquiry"),
            turn("신경과도 가야 해요", "hospital_search"),
        ],
    },

    # ─────────────────────────────────────────────────────────
    # Pattern 5: 잡담섞임 (greeting + 일반 + 의료)  10개
    # ─────────────────────────────────────────────────────────
    {
        "id": "MT-0041",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("안녕하세요", "general_chat"),
            turn("오늘 날씨가 추워요", "general_chat"),
            turn("감기에 걸린 것 같아요", "symptom_inquiry"),
            turn("감기약 추천해주세요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0042",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("처음 써봐요", "general_chat"),
            turn("손주가 깔아줬어요", "general_chat"),
            turn("무릎이 좀 아파서요", "symptom_inquiry"),
            turn("정형외과 알려주세요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0043",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("잘 들리나요", "general_chat"),
            turn("음성으로 말해도 돼요", "general_chat"),
            turn("어지러운데 어떡하죠", "symptom_inquiry"),
        ],
    },
    {
        "id": "MT-0044",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("안녕", "general_chat"),
            turn("화면 크게 좀 해줘", "general_chat"),
            turn("허리가 자꾸 아파요", "symptom_inquiry"),
            turn("정형외과 추천해주세요", "hospital_search"),
        ],
    },
    {
        "id": "MT-0045",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("도와줘", "general_chat"),
            turn("이거 어떻게 쓰는 거예요", "general_chat"),
            turn("머리가 아파서요", "symptom_inquiry"),
            turn("진통제 먹어도 돼요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0046",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("안녕하세요", "general_chat"),
            turn("음성 인식 잘 되나요", "general_chat"),
            turn("영감이 가슴이 답답하다고 해요", "symptom_inquiry"),
            turn("갑자기 너무 심해져요", "emergency"),
        ],
    },
    {
        "id": "MT-0047",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("처음이에요", "general_chat"),
            turn("잘 부탁해요", "general_chat"),
            turn("변비가 심해요", "symptom_inquiry"),
            turn("약 추천해주세요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0048",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("안녕", "general_chat"),
            turn("고마워요", "general_chat"),
            turn("손주가 열이 나요", "symptom_inquiry"),
            turn("해열제 먹여도 돼요", "medication_inquiry"),
        ],
    },
    {
        "id": "MT-0049",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("도와주세요", "general_chat"),
            turn("다시 말해줘요", "general_chat"),
            turn("알레르기인 것 같아요", "symptom_inquiry"),
            turn("가까운 피부과", "hospital_search"),
        ],
    },
    {
        "id": "MT-0050",
        "scenario_type": "잡담섞임",
        "turns": [
            turn("안녕하세요", "general_chat"),
            turn("글씨가 잘 안 보여요", "general_chat"),
            turn("눈이 침침해요", "symptom_inquiry"),
            turn("안과 알려주세요", "hospital_search"),
        ],
    },
]

# ── 검증 ─────────────────────────────────────────────────────────
assert len(scenarios) == 50, f"시나리오 수: {len(scenarios)} (50 필요)"

total_turns = sum(len(s["turns"]) for s in scenarios)
print(f"시나리오 수: {len(scenarios)}")
print(f"총 턴 수: {total_turns}")
print(f"평균 턴/시나리오: {total_turns/len(scenarios):.2f}")

# 라벨 분포
all_labels = [t["label"] for s in scenarios for t in s["turns"]]
print("\nLabel distribution (모든 턴 합산):")
for label, count in sorted(Counter(all_labels).items()):
    print(f"  {label}: {count}")

# 시나리오 타입 분포
print("\nScenario type distribution:")
for stype, count in sorted(Counter(s["scenario_type"] for s in scenarios).items()):
    print(f"  {stype}: {count}")

# 저장
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(scenarios, f, ensure_ascii=False, indent=2)

print(f"\nSaved to: {OUTPUT_PATH}")
