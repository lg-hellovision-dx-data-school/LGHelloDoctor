# ============================================================
# LG HelloDoctor — LLM 고도화 비교 실험
# LLaMA 3.2 3B vs EXAONE 3.5 2.4B
# 베이스라인 / 프롬프트 엔지니어링 / 파인튜닝 / 파인튜닝+프롬프트
# Google Colab A100 환경 기준
# ============================================================

# %%
# ============================================================
# [Cell 1] 패키지 설치
# ============================================================
# !pip install -q unsloth transformers datasets peft trl accelerate bitsandbytes
# !pip install -q pandas scikit-learn

# %%
# ============================================================
# [Cell 2] 임포트
# ============================================================
import torch
import json
import re
import pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from sklearn.metrics import classification_report, confusion_matrix

# %%
# ============================================================
# [Cell 3] 평가 데이터셋 정의
# 의도 분류 4종 + 응급 감지 테스트케이스
# ============================================================

# 의도 분류 평가셋 (각 카테고리 25개 = 총 100개)
EVAL_DATASET = [
    # --- emergency (응급) ---
    {"text": "숨이 안 쉬어요", "label": "emergency"},
    {"text": "쓰러졌어요", "label": "emergency"},
    {"text": "의식이 없어요", "label": "emergency"},
    {"text": "피를 토했어요", "label": "emergency"},
    {"text": "말이 어눌해졌어요", "label": "emergency"},
    {"text": "입이 돌아갔어요", "label": "emergency"},
    {"text": "한쪽이 마비됐어요", "label": "emergency"},
    {"text": "갑자기 안 보여요", "label": "emergency"},
    {"text": "심장이 너무 빨리 뛰어요", "label": "emergency"},
    {"text": "가슴이 너무 아파요 죽을 것 같아요", "label": "emergency"},
    {"text": "머리가 갑자기 너무 아파요", "label": "emergency"},
    {"text": "식은땀이 나고 어지러워요", "label": "emergency"},
    {"text": "팔다리에 힘이 없어요", "label": "emergency"},
    {"text": "눈앞이 캄캄해요", "label": "emergency"},
    {"text": "아이가 경련을 해요", "label": "emergency"},
    {"text": "약을 너무 많이 먹었어요", "label": "emergency"},
    {"text": "불이 났어요", "label": "emergency"},
    {"text": "교통사고가 났어요", "label": "emergency"},
    {"text": "뼈가 부러진 것 같아요", "label": "emergency"},
    {"text": "심한 알레르기 반응이 나타났어요", "label": "emergency"},
    {"text": "숨을 쉬기가 힘들어요", "label": "emergency"},
    {"text": "갑자기 의식을 잃었어요", "label": "emergency"},
    {"text": "심한 복통으로 움직이기 힘들어요", "label": "emergency"},
    {"text": "머리를 세게 부딪혔어요", "label": "emergency"},
    {"text": "119 불러주세요", "label": "emergency"},

    # --- symptom_inquiry (증상 문의) ---
    {"text": "무릎이 아파요", "label": "symptom_inquiry"},
    {"text": "머리가 자주 아파요", "label": "symptom_inquiry"},
    {"text": "기침이 계속 나요", "label": "symptom_inquiry"},
    {"text": "소화가 잘 안 돼요", "label": "symptom_inquiry"},
    {"text": "허리가 너무 아파요", "label": "symptom_inquiry"},
    {"text": "눈이 침침해요", "label": "symptom_inquiry"},
    {"text": "귀에서 소리가 나요", "label": "symptom_inquiry"},
    {"text": "코가 막혀요", "label": "symptom_inquiry"},
    {"text": "발목이 부었어요", "label": "symptom_inquiry"},
    {"text": "피부에 두드러기가 났어요", "label": "symptom_inquiry"},
    {"text": "손이 떨려요", "label": "symptom_inquiry"},
    {"text": "잠을 못 자겠어요", "label": "symptom_inquiry"},
    {"text": "식욕이 없어요", "label": "symptom_inquiry"},
    {"text": "목이 아파요", "label": "symptom_inquiry"},
    {"text": "어깨가 결려요", "label": "symptom_inquiry"},
    {"text": "배가 더부룩해요", "label": "symptom_inquiry"},
    {"text": "가슴이 답답해요", "label": "symptom_inquiry"},
    {"text": "다리가 저려요", "label": "symptom_inquiry"},
    {"text": "눈이 충혈됐어요", "label": "symptom_inquiry"},
    {"text": "열이 나는 것 같아요", "label": "symptom_inquiry"},
    {"text": "어지럼증이 있어요", "label": "symptom_inquiry"},
    {"text": "입이 마르고 갈증이 나요", "label": "symptom_inquiry"},
    {"text": "소변이 자주 마려워요", "label": "symptom_inquiry"},
    {"text": "발이 차갑고 저려요", "label": "symptom_inquiry"},
    {"text": "턱이 아파요", "label": "symptom_inquiry"},

    # --- hospital_search (병원 검색) ---
    {"text": "근처 병원 알려주세요", "label": "hospital_search"},
    {"text": "가까운 내과 어디 있어요", "label": "hospital_search"},
    {"text": "정형외과 찾아주세요", "label": "hospital_search"},
    {"text": "주변에 안과 있나요", "label": "hospital_search"},
    {"text": "응급실 어디예요", "label": "hospital_search"},
    {"text": "피부과 가고 싶어요", "label": "hospital_search"},
    {"text": "이비인후과 찾아주세요", "label": "hospital_search"},
    {"text": "오늘 진료하는 병원 있나요", "label": "hospital_search"},
    {"text": "야간 진료 병원 알려주세요", "label": "hospital_search"},
    {"text": "신경과 병원 어디 있어요", "label": "hospital_search"},
    {"text": "치과 가야 할 것 같아요", "label": "hospital_search"},
    {"text": "비뇨기과 병원 찾아주세요", "label": "hospital_search"},
    {"text": "재활의학과 병원 알려주세요", "label": "hospital_search"},
    {"text": "심장내과 있는 병원 알려주세요", "label": "hospital_search"},
    {"text": "소아과 가야 해요", "label": "hospital_search"},
    {"text": "산부인과 찾아주세요", "label": "hospital_search"},
    {"text": "정신건강의학과 병원 알려주세요", "label": "hospital_search"},
    {"text": "한의원 찾아주세요", "label": "hospital_search"},
    {"text": "도수치료 받을 수 있는 병원 있나요", "label": "hospital_search"},
    {"text": "혈액검사 받을 수 있는 곳 알려주세요", "label": "hospital_search"},
    {"text": "MRI 찍을 수 있는 병원 알려주세요", "label": "hospital_search"},
    {"text": "내일 아침 진료 병원 있나요", "label": "hospital_search"},
    {"text": "지금 열려있는 병원 어디예요", "label": "hospital_search"},
    {"text": "걸어서 갈 수 있는 병원 있나요", "label": "hospital_search"},
    {"text": "어르신 진료 잘 해주는 병원 알려주세요", "label": "hospital_search"},

    # --- medication_info (복약 정보) ---
    {"text": "타이레놀 어떻게 먹어요", "label": "medication_info"},
    {"text": "부루펜 하루에 몇 번 먹어요", "label": "medication_info"},
    {"text": "혈압약 언제 먹어야 해요", "label": "medication_info"},
    {"text": "이 약 밥 먹고 먹어야 해요", "label": "medication_info"},
    {"text": "약 먹고 술 마셔도 돼요", "label": "medication_info"},
    {"text": "두 가지 약 같이 먹어도 돼요", "label": "medication_info"},
    {"text": "감기약 졸음이 와요", "label": "medication_info"},
    {"text": "소화제 하루 몇 번 먹어요", "label": "medication_info"},
    {"text": "항생제 다 먹어야 해요", "label": "medication_info"},
    {"text": "약 빠뜨리면 어떻게 해요", "label": "medication_info"},
    {"text": "이 약 냉장 보관해야 해요", "label": "medication_info"},
    {"text": "약 언제까지 먹어야 해요", "label": "medication_info"},
    {"text": "파스 하루에 몇 번 붙여요", "label": "medication_info"},
    {"text": "연고 어떻게 바르는 거예요", "label": "medication_info"},
    {"text": "안약 넣는 방법 알려주세요", "label": "medication_info"},
    {"text": "콜레스테롤 약 아침에 먹어야 해요 저녁에 먹어야 해요", "label": "medication_info"},
    {"text": "당뇨약 식전이에요 식후예요", "label": "medication_info"},
    {"text": "변비약 효과가 언제 나타나요", "label": "medication_info"},
    {"text": "진통제 자주 먹으면 안 좋아요", "label": "medication_info"},
    {"text": "위장약이랑 다른 약 같이 먹어도 돼요", "label": "medication_info"},
    {"text": "영양제 아무 때나 먹어도 돼요", "label": "medication_info"},
    {"text": "이 약 아이도 먹을 수 있어요", "label": "medication_info"},
    {"text": "약 유통기한 지나면 버려야 해요", "label": "medication_info"},
    {"text": "수면제 의존성 생기나요", "label": "medication_info"},
    {"text": "두통약 얼마나 자주 먹어도 돼요", "label": "medication_info"},
]

# 응급 감지 전용 평가셋 (경계 발화 포함)
EMERGENCY_EVAL = [
    # 명확한 응급 (True Positive여야 함)
    {"text": "숨이 안 쉬어요", "is_emergency": True},
    {"text": "쓰러졌어요", "is_emergency": True},
    {"text": "의식이 없어요", "is_emergency": True},
    {"text": "피를 토했어요", "is_emergency": True},
    {"text": "말이 어눌해졌어요", "is_emergency": True},
    {"text": "한쪽이 마비됐어요", "is_emergency": True},
    {"text": "갑자기 안 보여요", "is_emergency": True},
    {"text": "심한 가슴 통증이에요", "is_emergency": True},
    {"text": "심장이 멈추는 것 같아요", "is_emergency": True},
    {"text": "뇌졸중인 것 같아요", "is_emergency": True},
    # 경계 발화 (True Positive여야 함)
    {"text": "어지럽고 식은땀이 나요", "is_emergency": True},
    {"text": "갑자기 힘이 없고 말하기 힘들어요", "is_emergency": True},
    {"text": "눈앞이 흐릿하고 두통이 심해요", "is_emergency": True},
    {"text": "가슴이 답답하고 팔이 저려요", "is_emergency": True},
    {"text": "갑자기 얼굴이 한쪽만 처졌어요", "is_emergency": True},
    # 일반 증상 (False Positive 방지)
    {"text": "무릎이 아파요", "is_emergency": False},
    {"text": "기침이 나요", "is_emergency": False},
    {"text": "소화가 안 돼요", "is_emergency": False},
    {"text": "머리가 아파요", "is_emergency": False},
    {"text": "피부가 가려워요", "is_emergency": False},
]

print(f"의도 분류 평가셋: {len(EVAL_DATASET)}개")
print(f"응급 감지 평가셋: {len(EMERGENCY_EVAL)}개")


# %%
# ============================================================
# [Cell 4] 공통 유틸리티 함수
# ============================================================

LABELS = ["emergency", "symptom_inquiry", "hospital_search", "medication_info"]

def extract_intent(response: str) -> str:
    """LLM 응답에서 의도 레이블 추출"""
    response = response.lower().strip()
    for label in LABELS:
        if label in response:
            return label
    # JSON 형태 파싱 시도
    try:
        match = re.search(r'"intent"\s*:\s*"([^"]+)"', response)
        if match:
            return match.group(1)
    except:
        pass
    return "unknown"

def extract_emergency(response: str) -> bool:
    """LLM 응답에서 응급 여부 추출"""
    response = response.lower()
    if "emergency" in response or "응급" in response or "true" in response:
        return True
    return False

def evaluate_intent(model, tokenizer, dataset, prompt_fn, device="cuda"):
    """의도 분류 정확도 평가"""
    correct = 0
    results = []
    for item in dataset:
        prompt = prompt_fn(item["text"])
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.01,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        predicted = extract_intent(response)
        is_correct = (predicted == item["label"])
        if is_correct:
            correct += 1
        results.append({
            "text": item["text"],
            "label": item["label"],
            "predicted": predicted,
            "correct": is_correct,
            "response": response[:100],
        })
    accuracy = correct / len(dataset) * 100
    return accuracy, results

def evaluate_emergency(model, tokenizer, dataset, prompt_fn, device="cuda"):
    """응급 감지율 (Recall) 평가"""
    tp, fn, fp, tn = 0, 0, 0, 0
    for item in dataset:
        prompt = prompt_fn(item["text"])
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=30,
                temperature=0.01,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        predicted = extract_emergency(response)
        actual = item["is_emergency"]
        if actual and predicted:
            tp += 1
        elif actual and not predicted:
            fn += 1
        elif not actual and predicted:
            fp += 1
        else:
            tn += 1
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    return recall, precision, {"TP": tp, "FN": fn, "FP": fp, "TN": tn}


# %%
# ============================================================
# [Cell 5] 프롬프트 함수 정의
# ============================================================

# ── 베이스라인 프롬프트 (아무 가이드 없음) ──
def baseline_prompt(text: str) -> str:
    return f"다음 텍스트의 의도를 분류하세요: {text}"

def baseline_emergency_prompt(text: str) -> str:
    return f"다음 텍스트가 응급 상황인지 판단하세요: {text}"

# ── 프롬프트 엔지니어링 적용 버전 ──
# 적용 기법: 역할 부여 + 출력 형식 강제 + Few-shot + temperature=0

FEW_SHOT_EXAMPLES = """
입력: "무릎이 아파요" → {"intent": "symptom_inquiry"}
입력: "근처 내과 어디 있어요" → {"intent": "hospital_search"}
입력: "타이레놀 어떻게 먹어요" → {"intent": "medication_info"}
입력: "숨이 안 쉬어요" → {"intent": "emergency"}
입력: "허리가 너무 아파요" → {"intent": "symptom_inquiry"}
입력: "응급실 어디예요" → {"intent": "hospital_search"}
"""

def engineered_prompt(text: str) -> str:
    return f"""당신은 시니어 의료 AI 어시스턴트입니다.
사용자 발화를 아래 4가지 의도 중 하나로 분류하세요.

의도 종류:
- emergency: 즉각적인 응급 처치가 필요한 상황
- symptom_inquiry: 증상에 대한 정보나 진료과 안내 요청
- hospital_search: 주변 병원 위치 검색 요청
- medication_info: 약 복용법이나 의약품 정보 요청

예시:
{FEW_SHOT_EXAMPLES}

반드시 JSON 형식으로만 답하세요. 설명 없이 결과만 출력하세요.
입력: "{text}" → """

def engineered_emergency_prompt(text: str) -> str:
    return f"""당신은 응급 상황을 감지하는 의료 AI입니다.
아래 발화가 즉각적인 응급 처치가 필요한 상황인지 판단하세요.

응급 상황 기준:
- 의식 소실, 호흡 곤란, 심한 출혈
- 마비, 언어 장애, 시야 이상
- 심한 흉통, 쓰러짐

반드시 JSON으로만 답하세요.
입력: "{text}" → {{"is_emergency": true/false}}
답: """


# %%
# ============================================================
# [Cell 6] 베이스라인 — LLaMA 3.2 3B
# ============================================================
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

LLAMA_MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)

print("LLaMA 3.2 3B 로딩 중...")
llama_tokenizer = AutoTokenizer.from_pretrained(LLAMA_MODEL_ID)
llama_model = AutoModelForCausalLM.from_pretrained(
    LLAMA_MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
)
llama_model.eval()

# 베이스라인 평가
print("\n[LLaMA 베이스라인] 의도 분류 평가 중...")
llama_base_acc, llama_base_results = evaluate_intent(
    llama_model, llama_tokenizer, EVAL_DATASET, baseline_prompt
)
llama_base_emg_recall, llama_base_emg_prec, llama_base_emg_detail = evaluate_emergency(
    llama_model, llama_tokenizer, EMERGENCY_EVAL, baseline_emergency_prompt
)

print(f"LLaMA 베이스라인 의도 분류 정확도: {llama_base_acc:.1f}%")
print(f"LLaMA 베이스라인 응급 감지율(Recall): {llama_base_emg_recall:.1f}%")
print(f"LLaMA 베이스라인 응급 정밀도(Precision): {llama_base_emg_prec:.1f}%")


# %%
# ============================================================
# [Cell 7] 베이스라인 — EXAONE 3.5 2.4B
# ============================================================
EXAONE_MODEL_ID = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"

print("EXAONE 3.5 2.4B 로딩 중...")
exaone_tokenizer = AutoTokenizer.from_pretrained(EXAONE_MODEL_ID)
exaone_model = AutoModelForCausalLM.from_pretrained(
    EXAONE_MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
exaone_model.eval()

# 베이스라인 평가
print("\n[EXAONE 베이스라인] 의도 분류 평가 중...")
exaone_base_acc, exaone_base_results = evaluate_intent(
    exaone_model, exaone_tokenizer, EVAL_DATASET, baseline_prompt
)
exaone_base_emg_recall, exaone_base_emg_prec, exaone_base_emg_detail = evaluate_emergency(
    exaone_model, exaone_tokenizer, EMERGENCY_EVAL, baseline_emergency_prompt
)

print(f"EXAONE 베이스라인 의도 분류 정확도: {exaone_base_acc:.1f}%")
print(f"EXAONE 베이스라인 응급 감지율(Recall): {exaone_base_emg_recall:.1f}%")
print(f"EXAONE 베이스라인 응급 정밀도(Precision): {exaone_base_emg_prec:.1f}%")


# %%
# ============================================================
# [Cell 8] 프롬프트 엔지니어링 적용 평가
# ============================================================

print("\n[LLaMA + 프롬프트 엔지니어링] 평가 중...")
llama_prompt_acc, _ = evaluate_intent(
    llama_model, llama_tokenizer, EVAL_DATASET, engineered_prompt
)
llama_prompt_emg_recall, llama_prompt_emg_prec, _ = evaluate_emergency(
    llama_model, llama_tokenizer, EMERGENCY_EVAL, engineered_emergency_prompt
)

print(f"LLaMA + 프롬프트 의도 분류 정확도: {llama_prompt_acc:.1f}%")
print(f"LLaMA + 프롬프트 응급 감지율: {llama_prompt_emg_recall:.1f}%")

print("\n[EXAONE + 프롬프트 엔지니어링] 평가 중...")
exaone_prompt_acc, _ = evaluate_intent(
    exaone_model, exaone_tokenizer, EVAL_DATASET, engineered_prompt
)
exaone_prompt_emg_recall, exaone_prompt_emg_prec, _ = evaluate_emergency(
    exaone_model, exaone_tokenizer, EMERGENCY_EVAL, engineered_emergency_prompt
)

print(f"EXAONE + 프롬프트 의도 분류 정확도: {exaone_prompt_acc:.1f}%")
print(f"EXAONE + 프롬프트 응급 감지율: {exaone_prompt_emg_recall:.1f}%")

# 메모리 해제 (파인튜닝 전)
del llama_model
del exaone_model
torch.cuda.empty_cache()


# %%
# ============================================================
# [Cell 9] 파인튜닝 — LoRA (Unsloth)
# 두 모델 각각 동일 데이터로 파인튜닝
# ============================================================
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import Dataset

# ── 학습 데이터 로드 ──
# 실제 학습 데이터 경로로 교체하세요
# 형식: [{"instruction": "...", "input": "...", "output": "..."}]
# Google Drive 마운트 필요 시:
# from google.colab import drive
# drive.mount('/content/drive')
# TRAIN_DATA_PATH = "/content/drive/MyDrive/hellodoctor_train.json"

# 샘플 학습 데이터 (실제 데이터로 교체)
SAMPLE_TRAIN_DATA = [
    {"instruction": "사용자 발화의 의도를 분류하세요.", "input": "무릎이 아파요", "output": '{"intent": "symptom_inquiry"}'},
    {"instruction": "사용자 발화의 의도를 분류하세요.", "input": "숨이 안 쉬어요", "output": '{"intent": "emergency"}'},
    {"instruction": "사용자 발화의 의도를 분류하세요.", "input": "근처 내과 어디 있어요", "output": '{"intent": "hospital_search"}'},
    {"instruction": "사용자 발화의 의도를 분류하세요.", "input": "타이레놀 어떻게 먹어요", "output": '{"intent": "medication_info"}'},
    # ... 실제 8800개 데이터로 교체
]

def format_train_sample(sample):
    return f"""### 지시사항:
{sample['instruction']}

### 입력:
{sample['input']}

### 응답:
{sample['output']}"""

ALPACA_PROMPT = """### 지시사항:
{}

### 입력:
{}

### 응답:
{}"""

def finetune_model(model_id: str, train_data: list, output_dir: str):
    """Unsloth LoRA 파인튜닝"""
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_id,
        max_seq_length=512,
        dtype=None,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    def formatting_fn(examples):
        texts = []
        for inst, inp, out in zip(
            examples["instruction"], examples["input"], examples["output"]
        ):
            text = ALPACA_PROMPT.format(inst, inp, out) + tokenizer.eos_token
            texts.append(text)
        return {"text": texts}

    dataset = Dataset.from_list(train_data)
    dataset = dataset.map(formatting_fn, batched=True)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=512,
        args=TrainingArguments(
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            warmup_steps=10,
            num_train_epochs=3,
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10,
            optim="adamw_8bit",
            output_dir=output_dir,
            seed=42,
        ),
    )
    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"파인튜닝 완료 → {output_dir}")
    return model, tokenizer


# %%
# ============================================================
# [Cell 10] LLaMA 파인튜닝 실행 및 평가
# ============================================================

print("LLaMA 3.2 3B 파인튜닝 시작...")
llama_ft_model, llama_ft_tokenizer = finetune_model(
    model_id=LLAMA_MODEL_ID,
    train_data=SAMPLE_TRAIN_DATA,  # 실제 데이터로 교체
    output_dir="./llama_finetuned",
)

# 파인튜닝만 적용 (베이스라인 프롬프트)
print("\n[LLaMA 파인튜닝] 베이스라인 프롬프트로 평가 중...")
llama_ft_acc, _ = evaluate_intent(
    llama_ft_model, llama_ft_tokenizer, EVAL_DATASET, baseline_prompt
)
llama_ft_emg_recall, llama_ft_emg_prec, _ = evaluate_emergency(
    llama_ft_model, llama_ft_tokenizer, EMERGENCY_EVAL, baseline_emergency_prompt
)

# 파인튜닝 + 프롬프트 엔지니어링
print("\n[LLaMA 파인튜닝 + 프롬프트] 평가 중...")
llama_ft_prompt_acc, _ = evaluate_intent(
    llama_ft_model, llama_ft_tokenizer, EVAL_DATASET, engineered_prompt
)
llama_ft_prompt_emg_recall, llama_ft_prompt_emg_prec, _ = evaluate_emergency(
    llama_ft_model, llama_ft_tokenizer, EMERGENCY_EVAL, engineered_emergency_prompt
)

del llama_ft_model
torch.cuda.empty_cache()


# %%
# ============================================================
# [Cell 11] EXAONE 파인튜닝 실행 및 평가
# ============================================================

print("EXAONE 3.5 2.4B 파인튜닝 시작...")
exaone_ft_model, exaone_ft_tokenizer = finetune_model(
    model_id=EXAONE_MODEL_ID,
    train_data=SAMPLE_TRAIN_DATA,  # 실제 데이터로 교체
    output_dir="./exaone_finetuned",
)

# 파인튜닝만 적용
print("\n[EXAONE 파인튜닝] 베이스라인 프롬프트로 평가 중...")
exaone_ft_acc, _ = evaluate_intent(
    exaone_ft_model, exaone_ft_tokenizer, EVAL_DATASET, baseline_prompt
)
exaone_ft_emg_recall, exaone_ft_emg_prec, _ = evaluate_emergency(
    exaone_ft_model, exaone_ft_tokenizer, EMERGENCY_EVAL, baseline_emergency_prompt
)

# 파인튜닝 + 프롬프트 엔지니어링
print("\n[EXAONE 파인튜닝 + 프롬프트] 평가 중...")
exaone_ft_prompt_acc, _ = evaluate_intent(
    exaone_ft_model, exaone_ft_tokenizer, EVAL_DATASET, engineered_prompt
)
exaone_ft_prompt_emg_recall, exaone_ft_prompt_emg_prec, _ = evaluate_emergency(
    exaone_ft_model, exaone_ft_tokenizer, EMERGENCY_EVAL, engineered_emergency_prompt
)

del exaone_ft_model
torch.cuda.empty_cache()


# %%
# ============================================================
# [Cell 12] 최종 결과 테이블 출력
# ============================================================

results = {
    "실험 조건": [
        "베이스라인",
        "+ 프롬프트 엔지니어링",
        "+ 파인튜닝",
        "+ 파인튜닝 + 프롬프트",
    ],
    "LLaMA 3.2 3B\n의도분류(%)": [
        f"{llama_base_acc:.1f}",
        f"{llama_prompt_acc:.1f}",
        f"{llama_ft_acc:.1f}",
        f"{llama_ft_prompt_acc:.1f}",
    ],
    "LLaMA 3.2 3B\n응급감지(%)": [
        f"{llama_base_emg_recall:.1f}",
        f"{llama_prompt_emg_recall:.1f}",
        f"{llama_ft_emg_recall:.1f}",
        f"{llama_ft_prompt_emg_recall:.1f}",
    ],
    "EXAONE 3.5 2.4B\n의도분류(%)": [
        f"{exaone_base_acc:.1f}",
        f"{exaone_prompt_acc:.1f}",
        f"{exaone_ft_acc:.1f}",
        f"{exaone_ft_prompt_acc:.1f}",
    ],
    "EXAONE 3.5 2.4B\n응급감지(%)": [
        f"{exaone_base_emg_recall:.1f}",
        f"{exaone_prompt_emg_recall:.1f}",
        f"{exaone_ft_emg_recall:.1f}",
        f"{exaone_ft_prompt_emg_recall:.1f}",
    ],
}

df = pd.DataFrame(results)
print("\n" + "="*70)
print("LLM 고도화 실험 결과 — Ablation Study")
print("="*70)
print(df.to_string(index=False))
print("="*70)

# CSV 저장
df.to_csv("llm_experiment_results.csv", index=False, encoding="utf-8-sig")
print("\n결과 저장 완료: llm_experiment_results.csv")
