# LoRA 재머지 v2 — Unsloth 내부 머지로 전환

## 왜 다시 하나
- 기존 intent 노트북 cell 59 는 `AutoModelForImageTextToText` + `PeftModel.from_pretrained` 경로로 머지를 시도했고, 모듈 경로 불일치로 `merge_and_unload()` 가 silently 실패했음 (LoRA 미반영 GGUF 생성).
- 해결: **Unsloth `FastLanguageModel.from_pretrained(LORA_PATH)`** 가 베이스+어댑터를 통합 로드 → `save_pretrained_merged(save_method="merged_16bit")` 가 Unsloth 내부 머지를 수행.

## 사용법
1. Colab 새 런타임 (T4 GPU) 시작
2. 아래 5개 셀을 **순서대로** 붙여넣고 실행 (총 ~30분)
3. 끝나면 Drive 의 `intent_gguf_v2/`, `answer_gguf_v2/` 다운로드
4. 로컬 `models/intent_gguf/`, `models/answer_gguf/` 의 `.gguf` 와 `Modelfile` 교체
5. `ollama create hellodoctor-intent -f Modelfile` / `ollama create hellodoctor-answer -f Modelfile` 재등록

---

## Cell 1 — 환경 + 경로

> ⚠️ **xformers 핀을 쓰지 마세요** — 2025년 Colab T4 에서 `"xformers<0.0.27"` 은 prebuilt wheel 이 없어 30~60분 소스 빌드에 들어갑니다. 아래처럼 Unsloth 한 줄로 설치하면 호환 xformers 가 자동 해결돼요.

```python
# 의존성 자동 해결 — 약 2분
!pip install --quiet unsloth

from google.colab import drive
drive.mount('/content/drive')

import os, gc, torch
DRIVE_DIR      = "/content/drive/MyDrive/LG_HelloDoctor_혼자_논문"
MAX_SEQ_LENGTH = 2048

INTENT_LORA   = f"{DRIVE_DIR}/intent_lora_rank16"
ANSWER_LORA   = f"{DRIVE_DIR}/answer_finetune/answer_lora_rank16"
INTENT_MERGED = f"{DRIVE_DIR}/intent_merged_v2"
ANSWER_MERGED = f"{DRIVE_DIR}/answer_merged_v2"
INTENT_GGUF   = f"{DRIVE_DIR}/intent_gguf_v2"
ANSWER_GGUF   = f"{DRIVE_DIR}/answer_gguf_v2"

for p in [INTENT_LORA, ANSWER_LORA]:
    assert os.path.exists(p), f"❌ LoRA 어댑터 없음: {p}"
for d in [INTENT_MERGED, ANSWER_MERGED, INTENT_GGUF, ANSWER_GGUF]:
    os.makedirs(d, exist_ok=True)

print("✅ 환경 준비 완료")
print(f"  INTENT_LORA: {INTENT_LORA}")
print(f"  ANSWER_LORA: {ANSWER_LORA}")
```

---

## Cell 2 — Intent 머지

```python
from unsloth import FastLanguageModel

print("[INTENT 1/2] Unsloth 로 LoRA + 베이스 통합 로드…")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=INTENT_LORA,        # 베이스가 아닌 LoRA 경로 — Unsloth 가 자동으로 베이스 결정
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,
    load_in_4bit=False,            # GGUF 변환은 fp16 필요
)

print("[INTENT 2/2] 머지 → 16bit safetensors 저장…")
model.save_pretrained_merged(INTENT_MERGED, tokenizer, save_method="merged_16bit")

del model, tokenizer
gc.collect(); torch.cuda.empty_cache()

st_files = [f for f in os.listdir(INTENT_MERGED) if f.endswith('.safetensors')]
print(f"✅ intent 머지 완료: {INTENT_MERGED}")
print(f"   safetensors: {st_files}")
```

---

## Cell 3 — Answer 머지

```python
print("[ANSWER 1/2] Unsloth 로 LoRA + 베이스 통합 로드…")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=ANSWER_LORA,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,
    load_in_4bit=False,
)

print("[ANSWER 2/2] 머지 → 16bit safetensors 저장…")
model.save_pretrained_merged(ANSWER_MERGED, tokenizer, save_method="merged_16bit")

del model, tokenizer
gc.collect(); torch.cuda.empty_cache()

st_files = [f for f in os.listdir(ANSWER_MERGED) if f.endswith('.safetensors')]
print(f"✅ answer 머지 완료: {ANSWER_MERGED}")
print(f"   safetensors: {st_files}")
```

---

## Cell 4 — llama.cpp 빌드 + 두 모델 GGUF Q4_K_M 변환

```python
LLAMA_CPP_DIR = "/content/llama.cpp"
QUANTIZER     = f"{LLAMA_CPP_DIR}/build/bin/llama-quantize"

if not os.path.exists(QUANTIZER):
    print("llama.cpp 빌드…")
    !rm -rf {LLAMA_CPP_DIR}
    !git clone --depth 1 https://github.com/ggerganov/llama.cpp {LLAMA_CPP_DIR}
    !cd {LLAMA_CPP_DIR} && pip install -q -r requirements.txt
    !cd {LLAMA_CPP_DIR} && cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF \
        && cmake --build build --target llama-quantize --config Release -j 4
    assert os.path.exists(QUANTIZER), "❌ llama-quantize 빌드 실패"
print(f"✅ llama.cpp: {QUANTIZER}")

def convert_to_gguf(merged_dir, gguf_dir, basename, label):
    f16 = f"{gguf_dir}/{basename}.F16.gguf"
    q4  = f"{gguf_dir}/{basename}.Q4_K_M.gguf"
    print(f"\n[{label} 1/2] HF → F16")
    !cd {LLAMA_CPP_DIR} && python convert_hf_to_gguf.py {merged_dir} --outfile {f16} --outtype f16
    assert os.path.exists(f16), f"❌ {label} F16 변환 실패"
    print(f"\n[{label} 2/2] F16 → Q4_K_M")
    !{QUANTIZER} {f16} {q4} q4_k_m
    assert os.path.exists(q4), f"❌ {label} Q4_K_M 양자화 실패"
    !rm -f {f16}
    print(f"✅ {label}: {q4} ({os.path.getsize(q4)/1e6:.1f} MB)")

convert_to_gguf(INTENT_MERGED, INTENT_GGUF, "intent", "INTENT")
convert_to_gguf(ANSWER_MERGED, ANSWER_GGUF, "unsloth", "ANSWER")
```

---

## Cell 5 — Modelfile 자동 작성

```python
INTENT_SYSTEM = """너는 LG HelloDoctor 의료 특화 AI 에이전트의 의도 분류기다.
사용자 발화를 읽고 아래 5개 라벨 중 정확히 하나만 출력한다.

라벨:
- symptom_inquiry: 증상 설명, 증상 상담, 진료과 추정 요청
- hospital_search: 병원/의원/응급실/진료과 위치 검색 또는 추천
- medication_inquiry: 약 복용, 용량, 병용, 부작용, 처방 관련 문의
- emergency: 즉시 응급 대응이 필요할 수 있는 위험 증상
- general_chat: 인사, 사용법, 감사, 앱 기능, 일반 대화

출력 규칙:
- 반드시 라벨 문자열 하나만 출력한다.
- 설명, 문장부호, 한국어 설명을 붙이지 않는다.
- 가능한 출력은 다음 중 하나뿐이다:
symptom_inquiry, hospital_search, medication_inquiry, emergency, general_chat"""

ANSWER_SYSTEM = """당신은 시니어(어르신)에게 의료 정보를 따뜻하고 안전하게 안내하는 AI입니다.
- 한국어 존댓말, 1~3문장 이내
- 어려운 의학 용어는 풀어 쓰기
- 진단·처방 단정 금지. 권유형 사용
- 응급은 반드시 119 안내
- 컨텍스트에 없는 내용은 만들지 않기"""

def write_modelfile(gguf_dir, gguf_name, system, params, header_comment):
    lines = [
        header_comment,
        "",
        f"FROM ./{gguf_name}",
        "",
        '# Gemma 3 chat template (training format 와 일치)',
        'TEMPLATE """<start_of_turn>user',
        '{{ if .System }}{{ .System }}',
        '',
        '{{ end }}{{ .Prompt }}<end_of_turn>',
        '<start_of_turn>model',
        '{{ .Response }}<end_of_turn>"""',
        "",
        f'SYSTEM """{system}"""',
        "",
    ] + params
    with open(f"{gguf_dir}/Modelfile", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ {gguf_dir}/Modelfile")

write_modelfile(
    INTENT_GGUF, "intent.Q4_K_M.gguf", INTENT_SYSTEM,
    [
        '# 결정론적 — 분류 라벨만 출력',
        'PARAMETER temperature 0',
        'PARAMETER top_p 1.0',
        'PARAMETER num_predict 10',
        'PARAMETER stop "<end_of_turn>"',
        'PARAMETER stop "<start_of_turn>"',
    ],
    "# LG HelloDoctor 의도 분류 (v2 — Unsloth 내부 머지)",
)

write_modelfile(
    ANSWER_GGUF, "unsloth.Q4_K_M.gguf", ANSWER_SYSTEM,
    [
        '# 답변 — 약간의 다양성 허용',
        'PARAMETER temperature 0.3',
        'PARAMETER top_p 0.9',
        'PARAMETER num_predict 200',
        'PARAMETER stop "<end_of_turn>"',
        'PARAMETER stop "<start_of_turn>"',
    ],
    "# LG HelloDoctor 답변 생성 (v2 — Unsloth 내부 머지)",
)

print()
print("=" * 60)
print("✅ v2 완료 — 이제 Drive 에서 다운로드:")
print(f"   {INTENT_GGUF}/   ({len(os.listdir(INTENT_GGUF))} files)")
print(f"   {ANSWER_GGUF}/   ({len(os.listdir(ANSWER_GGUF))} files)")
```

---

## 다운로드 후 로컬 작업

```powershell
# 1) 기존 .gguf 백업 (선택)
cd C:\Users\juyeon\Desktop\project\LGHelloDoctor\models
Move-Item intent_gguf intent_gguf_v1_broken
Move-Item answer_gguf answer_gguf_v1_broken

# 2) Drive 에서 받은 intent_gguf_v2 / answer_gguf_v2 폴더를 위 위치로 이동 후
#    이름을 intent_gguf / answer_gguf 로 변경

# 3) Ollama 재등록 (기존 태그 덮어쓰기)
cd intent_gguf
ollama create hellodoctor-intent -f Modelfile

cd ..\answer_gguf
ollama create hellodoctor-answer -f Modelfile

ollama list  # 두 모델 확인
```

## 검증

```powershell
# Intent — 단일 라벨 출력 확인
$body = @{ model='hellodoctor-intent'; prompt='사용자 발화: 머리가 아파요'+"`n"+'의도 라벨:'; stream=$false; options=@{temperature=0; num_predict=10} } | ConvertTo-Json
(Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $body -ContentType 'application/json').response.Trim()
# 기대: symptom_inquiry

# Answer — 1~3문장 시니어 어조 확인
$body = @{ model='hellodoctor-answer'; prompt='[의도] symptom_inquiry'+"`n"+'[컨텍스트]'+"`n"+'두통은 흔한 증상입니다.'+"`n`n"+'[질문]'+"`n"+'머리가 아파요'; stream=$false; options=@{temperature=0.3; num_predict=200} } | ConvertTo-Json
(Invoke-RestMethod -Uri "http://localhost:11434/api/generate" -Method Post -Body $body -ContentType 'application/json').response
# 기대: 짧고 따뜻한 시니어 친화 답변
```

## 그 다음 — 도커 백엔드 띄우기

```powershell
docker compose up -d backend       # main.py 가 OLLAMA_URL=http://host.docker.internal:11434 로 두 모델 호출
docker compose logs -f backend     # "ChromaDB OK ... Ollama OK" 확인
```
